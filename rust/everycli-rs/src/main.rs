use everycli_core::{Platform, Scenario, daemon, find_error_hint, load_corpus_merged, search};
use owo_colors::OwoColorize;
use std::env;
use std::io::{self, BufRead, BufReader, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode, Stdio};
use std::time::Duration;

/// A search hit ready to render, regardless of whether it came from the
/// daemon or the local lexical fallback.
#[derive(Clone)]
struct DisplayHit {
    id: String,
    namespace: String,
    command: String,
    explanation: String,
    warning: String,
    tags: Vec<String>,
    score: f32,
}

/// Keep only hits whose `tags` contain `env`, case-insensitively — mirrors
/// `everycli.py`'s `env.lower() in r.scenario.tags` filter.
fn filter_by_env<'a>(hits: &'a [DisplayHit], env: &str) -> Vec<&'a DisplayHit> {
    let env = env.to_lowercase();
    hits.iter()
        .filter(|hit| hit.tags.iter().any(|tag| tag.to_lowercase() == env))
        .collect()
}

/// True when the top two scores are within 5% of each other and the top
/// score is nonzero — mirrors `everycli.py`'s auto-disambiguation (O4) rule.
fn should_disambiguate(hits: &[DisplayHit]) -> bool {
    match hits {
        [first, second, ..] => first.score > 0.0 && (first.score - second.score) < 0.05,
        _ => false,
    }
}

fn main() -> ExitCode {
    match run(env::args().skip(1).collect()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("everycli-rs: {message}");
            ExitCode::from(2)
        }
    }
}

fn run(mut arguments: Vec<String>) -> Result<(), String> {
    if arguments.is_empty() || arguments[0] == "--help" || arguments[0] == "-h" {
        print_help();
        return Ok(());
    }
    if arguments[0] == "add" {
        return cmd_add();
    }
    if arguments[0] == "list" {
        return cmd_list();
    }
    if arguments[0] == "remove" {
        let id_arg = arguments.get(1).cloned();
        return cmd_remove(id_arg);
    }
    if arguments.remove(0) != "search" {
        return Err("expected the `search`, `add`, `list`, or `remove` command; run `everycli-rs --help`".to_owned());
    }

    let mut query = Vec::new();
    let mut data_dir = None;
    let mut top_k = 1usize;
    let mut platform = default_platform();
    let mut json = false;
    let mut error_message: Option<String> = None;
    let mut env_filter: Option<String> = None;
    let mut copy = false;
    let mut run_it = false;
    let mut interactive = false;
    let mut shell = false;
    let mut no_daemon = false;
    let mut debug = false;
    let mut index = 0;

    while index < arguments.len() {
        match arguments[index].as_str() {
            "--data" => {
                index += 1;
                data_dir = Some(PathBuf::from(required_value(&arguments, index, "--data")?));
            }
            "--top" | "-t" => {
                index += 1;
                top_k = required_value(&arguments, index, "--top")?
                    .parse()
                    .map_err(|_| "--top must be a positive integer".to_owned())?;
                if top_k == 0 {
                    return Err("--top must be at least 1".to_owned());
                }
            }
            "--platform" => {
                index += 1;
                platform = Platform::parse(required_value(&arguments, index, "--platform")?)
                    .ok_or_else(|| "--platform must be linux, windows, or macos".to_owned())?;
            }
            "--error" | "-e" => {
                index += 1;
                error_message = Some(required_value(&arguments, index, "--error")?.to_owned());
            }
            "--env" => {
                index += 1;
                env_filter = Some(required_value(&arguments, index, "--env")?.to_owned());
            }
            "--json" => json = true,
            "--copy" | "-c" => copy = true,
            "--run" | "-r" => run_it = true,
            "--interactive" | "-i" => interactive = true,
            "--shell" | "-s" => shell = true,
            "--no-daemon" => no_daemon = true,
            "--debug" => debug = true,
            "--help" | "-h" => {
                print_help();
                return Ok(());
            }
            value if value.starts_with('-') => return Err(format!("unknown option: {value}")),
            value => query.push(value.to_owned()),
        }
        index += 1;
    }

    // --shell is a strict machine-readable protocol: only the resolved
    // command may reach stdout, so it cannot combine with anything that
    // also wants to own stdout or the terminal. Mirrors everycli.py's
    // `search` validation block.
    if shell {
        if interactive {
            return Err("-s ne se combine pas avec -i.".to_owned());
        }
        if run_it || copy {
            return Err("-s ne se combine pas avec --run ou --copy.".to_owned());
        }
        if error_message.is_some() {
            return Err("-s ne se combine pas avec --error.".to_owned());
        }
        if top_k != 1 {
            return Err("-s retourne une seule commande ; utilise --top 1.".to_owned());
        }
        if query.is_empty() {
            return Err("Le mode -s necessite une requete explicite.".to_owned());
        }
    }

    if query.is_empty() {
        return Err("provide a natural-language query".to_owned());
    }
    let query = query.join(" ");
    let data_dir = data_dir.unwrap_or_else(default_data_dir);

    // Chargement paresseux du corpus local : le parser maison YAML coûte
    // un temps non négligeable (mesuré ~0.5s pour 450+ scénarios), et n'est
    // en fait nécessaire que si le daemon est indisponible (repli local) ou
    // si --error a besoin de chercher un indice dans le corpus -- pas dans
    // le cas courant (daemon répond avec succès, pas de --error).
    let mut corpus: Option<Vec<Scenario>> = None;
    macro_rules! ensure_corpus {
        () => {{
            if corpus.is_none() {
                corpus = Some(
                    load_corpus_merged(&data_dir, user_data_dir()).map_err(|error| error.to_string())?,
                );
            }
            corpus.as_ref().unwrap()
        }};
    }

    // Fetch extra candidates so disambiguation/interactive selection has
    // something to choose from, same as everycli.py's `search_top`.
    let search_top = if interactive { 10 } else { top_k.max(3) };

    let mut hits: Vec<DisplayHit> = if no_daemon {
        local_search(ensure_corpus!(), &query, search_top, platform)
    } else {
        let config = daemon::DaemonConfig::default();
        let repo_root = repo_root_from_data_dir(&data_dir);
        match daemon::search(&config, &repo_root, &query, search_top) {
            Ok(daemon_hits) => daemon_hits
                .into_iter()
                .map(|hit| DisplayHit {
                    id: hit.id,
                    namespace: hit.namespace,
                    command: hit.command,
                    explanation: hit.explanation,
                    warning: hit.warning,
                    tags: hit.tags,
                    score: hit.score,
                })
                .collect(),
            Err(error) => {
                eprintln!(
                    "everycli-rs: daemon fallback ({}), using local search",
                    daemon_error_message(&error)
                );
                local_search(ensure_corpus!(), &query, search_top, platform)
            }
        }
    };

    if let Some(env_name) = &env_filter {
        hits = filter_by_env(&hits, env_name)
            .into_iter()
            .cloned()
            .collect();
    }

    if hits.is_empty() {
        return Err("no command matched this query".to_owned());
    }

    let mut ordered = hits;
    if interactive && ordered.len() > 1 {
        let choice = pick_interactive(&ordered).unwrap_or(0);
        ordered = vec![ordered[choice].clone()];
    }

    // Quand les deux meilleurs scores sont trop proches pour trancher avec
    // confiance, on ne bloque plus avec une question forcee (l'outil ne
    // doit pas decider a la place de l'utilisateur) -- on montre plusieurs
    // resultats, meme format que --top N, et l'utilisateur choisit en
    // lisant. Le mode -s (shell) fait exception : il doit toujours rendre
    // une seule commande deterministe pour rester utilisable en script.
    let ambiguous = !interactive && !shell && should_disambiguate(&ordered);
    let effective_top_k = if ambiguous { top_k.max(2) } else { top_k };

    let shown_count = effective_top_k.min(ordered.len());
    let shown = &ordered[..shown_count];

    // --shell is a machine-readable protocol: stdout may only ever carry the
    // resolved command. Every diagnostic that would normally go to stdout
    // goes to stderr instead, mirroring everycli.py's `Console(stderr=True)`
    // switch for shell mode.
    if shell {
        if let Some(first) = shown.first() {
            eprintln!("{} | {}", first.namespace, first.id);
            eprintln!("> {}", first.command);
            eprintln!("  {}", first.explanation);
            eprintln!("  score {:.2}", first.score);
        }
    } else if json {
        println!("{}", render_json(shown));
    } else {
        render_human(shown, &query, debug);

        if let Some(message) = &error_message
            && let Some(first) = shown.first()
            && let Some(hint) = find_hint_for(ensure_corpus!(), first, message)
        {
            use owo_colors::Stream::Stdout;
            println!();
            println!(
                "  {} {}",
                "cause:".if_supports_color(Stdout, |t| t.yellow().to_string()),
                hint.cause
            );
            println!(
                "  {} {}",
                "fix:  ".if_supports_color(Stdout, |t| t.green().to_string()),
                hint.fix
            );
        }

        if let Some(first) = shown.first() {
            if copy {
                if clipboard_copy(&first.command) {
                    eprintln!("Commande copiee dans le presse-papier.");
                } else {
                    eprintln!("Impossible de copier dans le presse-papier.");
                }
            }
            if run_it {
                run_confirmed(&first.command);
            }
        }
    }

    if shell && let Some(first) = shown.first() {
        print!("{}", first.command);
        io::stdout().flush().ok();
    }

    Ok(())
}

fn local_search(
    corpus: &[Scenario],
    query: &str,
    top_k: usize,
    platform: Platform,
) -> Vec<DisplayHit> {
    search(corpus, query, top_k, platform)
        .into_iter()
        .map(|result| DisplayHit {
            id: result.scenario.id,
            namespace: result.scenario.namespace,
            command: result.command,
            explanation: result.scenario.explanation,
            warning: result.scenario.warning,
            tags: result.scenario.tags,
            score: result.score,
        })
        .collect()
}

/// `data_dir` is `<repo_root>/everycli/data/commands`.
fn repo_root_from_data_dir(data_dir: &Path) -> PathBuf {
    data_dir
        .ancestors()
        .nth(3)
        .map(Path::to_path_buf)
        .unwrap_or_else(|| data_dir.to_path_buf())
}

fn find_hint_for<'a>(
    corpus: &'a [Scenario],
    hit: &DisplayHit,
    error_message: &str,
) -> Option<&'a everycli_core::ErrorHint> {
    corpus
        .iter()
        .find(|scenario| scenario.id == hit.id)
        .and_then(|scenario| find_error_hint(scenario, error_message))
}

/// Sélection au clavier (flèches haut/bas + Entrée) parmi les résultats,
/// via `inquire` -- remplace l'ancienne saisie "tape un numéro". Si
/// l'utilisateur annule (Echap/Ctrl+C) ou si le terminal ne supporte pas le
/// mode interactif (pipe, script), retourne `None` et l'appelant retombe
/// sur le premier résultat (comportement inchangé).
fn pick_interactive(hits: &[DisplayHit]) -> Option<usize> {
    struct Choice {
        index: usize,
        label: String,
    }

    impl std::fmt::Display for Choice {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(f, "{}", self.label)
        }
    }

    let choices: Vec<Choice> = hits
        .iter()
        .enumerate()
        .map(|(index, hit)| Choice {
            index,
            label: format!("{}  —  {}", hit.command, hit.explanation),
        })
        .collect();

    inquire::Select::new("Choisis une commande :", choices)
        .prompt()
        .ok()
        .map(|choice| choice.index)
}

fn clipboard_copy(text: &str) -> bool {
    let spawned = if cfg!(target_os = "windows") {
        Command::new("clip").stdin(Stdio::piped()).spawn()
    } else if cfg!(target_os = "macos") {
        Command::new("pbcopy").stdin(Stdio::piped()).spawn()
    } else {
        Command::new("xclip")
            .args(["-selection", "clipboard"])
            .stdin(Stdio::piped())
            .spawn()
            .or_else(|_| {
                Command::new("xsel")
                    .args(["--clipboard", "--input"])
                    .stdin(Stdio::piped())
                    .spawn()
            })
    };

    let Ok(mut child) = spawned else {
        return false;
    };
    if let Some(mut stdin) = child.stdin.take()
        && stdin.write_all(text.as_bytes()).is_err()
    {
        return false;
    }
    child.wait().map(|status| status.success()).unwrap_or(false)
}

fn run_confirmed(command: &str) {
    eprint!("Executer `{command}` ? [y/N] ");
    io::stderr().flush().ok();
    let mut answer = String::new();
    if io::stdin().read_line(&mut answer).is_err() {
        return;
    }
    if !matches!(
        answer.trim().to_lowercase().as_str(),
        "y" | "yes" | "o" | "oui"
    ) {
        return;
    }

    let output = if cfg!(target_os = "windows") {
        Command::new("cmd").args(["/C", command]).output()
    } else {
        Command::new("sh").args(["-c", command]).output()
    };

    match output {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            let text = if !stdout.trim().is_empty() {
                stdout.trim()
            } else {
                stderr.trim()
            };
            if !text.is_empty() {
                println!("{text}");
            }
            if !output.status.success() {
                eprintln!(
                    "Commande terminee avec le code {}.",
                    output.status.code().unwrap_or(1)
                );
            }
        }
        Err(error) => eprintln!("Echec de l'execution : {error}"),
    }
}

fn required_value<'a>(
    arguments: &'a [String],
    index: usize,
    option: &str,
) -> Result<&'a str, String> {
    arguments
        .get(index)
        .map(String::as_str)
        .ok_or_else(|| format!("{option} requires a value"))
}

fn default_platform() -> Platform {
    if cfg!(target_os = "windows") {
        Platform::Windows
    } else if cfg!(target_os = "macos") {
        Platform::Macos
    } else {
        Platform::Linux
    }
}

fn default_data_dir() -> PathBuf {
    if let Ok(path) = env::var("EVERYCLI_DATA_DIR") {
        return PathBuf::from(path);
    }
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let local = cwd.join("everycli").join("data").join("commands");
    if local.exists() {
        return local;
    }
    cwd.join("..")
        .join("everycli")
        .join("data")
        .join("commands")
}

/// Dossier des commandes ajoutées par l'utilisateur (`everycli add`),
/// séparé du corpus intégré pour ne jamais être écrasé par une mise à jour
/// (voir HACKATHON_PLAN.md, Axe 5). Même résolution de chemin que le
/// daemon (`everycli-daemon::user_data_dir`).
fn user_data_dir() -> PathBuf {
    if let Ok(path) = env::var("EVERYCLI_USER_DATA_DIR") {
        return PathBuf::from(path);
    }
    let home = if cfg!(windows) {
        env::var("USERPROFILE").unwrap_or_else(|_| ".".to_owned())
    } else {
        env::var("HOME").unwrap_or_else(|_| ".".to_owned())
    };
    Path::new(&home).join(".everycli").join("commands")
}

/// `everycli add` — ajoute une commande personnalisée via une série de
/// prompts, l'écrit dans le corpus utilisateur, et demande au daemon de
/// recharger s'il tourne (best effort — pas bloquant s'il n'est pas
/// joignable, la commande sera prise en compte au prochain démarrage).
fn cmd_add() -> Result<(), String> {
    let user_dir = user_data_dir();
    std::fs::create_dir_all(&user_dir)
        .map_err(|error| format!("impossible de creer {}: {error}", user_dir.display()))?;

    println!("=== Ajouter une commande a EveryCli ===");

    let namespace_input = prompt("Categorie / nom de fichier (ex: mes-scripts) : ")?;
    let namespace = slugify(&namespace_input, 8);
    if namespace.is_empty() {
        return Err("la categorie ne peut pas etre vide".to_owned());
    }

    let description = prompt("Description (utilisee pour la recherche) : ")?;
    if description.trim().is_empty() {
        return Err("la description ne peut pas etre vide".to_owned());
    }

    let command = prompt("Commande : ")?;
    if command.trim().is_empty() {
        return Err("la commande ne peut pas etre vide".to_owned());
    }

    let explanation = prompt("Explication (affichee a l'utilisateur) : ")?;
    let tags_raw = prompt("Tags, separes par des virgules (optionnel) : ")?;
    let warning = prompt("Avertissement si commande risquee (optionnel, Entree pour ignorer) : ")?;

    let data_dir = default_data_dir();
    let existing = load_corpus_merged(&data_dir, &user_dir).unwrap_or_default();
    let id = generate_unique_id(&namespace, &description, &existing);

    let tags: Vec<String> = tags_raw
        .split(',')
        .map(|tag| tag.trim().to_owned())
        .filter(|tag| !tag.is_empty())
        .collect();

    let file_path = user_dir.join(format!("{namespace}.yaml"));
    append_scenario_yaml(&file_path, &id, &description, &command, &explanation, &tags, &warning)
        .map_err(|error| format!("echec d'ecriture dans {}: {error}", file_path.display()))?;

    println!();
    println!("Commande ajoutee : {id}");
    println!("  Fichier : {}", file_path.display());

    match reload_daemon() {
        Ok(()) => println!("Daemon recharge -- disponible immediatement."),
        Err(_) => println!(
            "Daemon non joignable -- sera pris en compte au prochain demarrage (ou lance `everycli search --no-daemon` pour l'utiliser des maintenant en local)."
        ),
    }

    Ok(())
}

/// Charge uniquement les commandes personnalisees de l'utilisateur (pas le
/// corpus integre) -- utilise par `list`/`remove`. Contrairement a
/// `load_corpus`, l'absence du dossier ou l'absence de fichiers .yaml
/// dedans n'est PAS une erreur : ça veut juste dire qu'il n'y a encore rien
/// d'ajoute (cas normal d'une installation fraiche).
fn user_scenarios() -> Result<Vec<Scenario>, String> {
    let user_dir = user_data_dir();
    if !user_dir.is_dir() {
        return Ok(Vec::new());
    }
    Ok(everycli_core::load_corpus(&user_dir).unwrap_or_default())
}

/// `everycli list` -- affiche toutes les commandes personnalisees ajoutees
/// via `everycli add` (pas le corpus integre).
fn cmd_list() -> Result<(), String> {
    use owo_colors::Stream::Stdout;

    let scenarios = user_scenarios()?;
    if scenarios.is_empty() {
        println!("Aucune commande personnalisee pour l'instant. Utilise `everycli add` pour en ajouter une.");
        return Ok(());
    }

    println!();
    println!(
        "{} :",
        format!("{} commande(s) personnalisee(s)", scenarios.len())
            .if_supports_color(Stdout, |t| t.bold().to_string())
    );
    for scenario in &scenarios {
        println!();
        println!(
            "{}  {}",
            scenario.id.if_supports_color(Stdout, |t| t.bold().to_string()),
            format!("({})", scenario.namespace).if_supports_color(Stdout, |t| t.dimmed().to_string())
        );
        println!(
            "   {} {}",
            ">".if_supports_color(Stdout, |t| t.dimmed().to_string()),
            scenario.commands.linux.if_supports_color(Stdout, |t| t.cyan().to_string())
        );
        println!("   {}", scenario.explanation);
    }
    println!();
    Ok(())
}

/// `everycli remove [id]` -- supprime une commande personnalisee. Si `id`
/// n'est pas donne, propose une selection au clavier (comme `--interactive`
/// pour la recherche). Demande toujours une confirmation avant d'ecrire
/// quoi que ce soit sur disque -- une suppression n'est pas annulable.
fn cmd_remove(id_arg: Option<String>) -> Result<(), String> {
    let scenarios = user_scenarios()?;
    if scenarios.is_empty() {
        println!("Aucune commande personnalisee a supprimer.");
        return Ok(());
    }

    let target_id = match id_arg {
        Some(id) => id,
        None => {
            struct Choice {
                id: String,
                label: String,
            }
            impl std::fmt::Display for Choice {
                fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                    write!(f, "{}", self.label)
                }
            }
            let choices: Vec<Choice> = scenarios
                .iter()
                .map(|scenario| Choice {
                    id: scenario.id.clone(),
                    label: format!("{}  ({})  {}", scenario.id, scenario.namespace, scenario.commands.linux),
                })
                .collect();
            match inquire::Select::new("Quelle commande supprimer ?", choices).prompt() {
                Ok(choice) => choice.id,
                Err(_) => return Ok(()), // annule (Echap/Ctrl+C) -- pas une erreur
            }
        }
    };

    let Some(target) = scenarios.iter().find(|scenario| scenario.id == target_id) else {
        return Err(format!("aucune commande personnalisee avec l'id '{target_id}'"));
    };

    let confirmed = inquire::Confirm::new(&format!(
        "Supprimer '{}' ({}) ?",
        target.id, target.commands.linux
    ))
    .with_default(false)
    .prompt()
    .unwrap_or(false);

    if !confirmed {
        println!("Annule.");
        return Ok(());
    }

    let namespace = target.namespace.clone();
    let remaining: Vec<&Scenario> = scenarios
        .iter()
        .filter(|scenario| scenario.namespace == namespace && scenario.id != target_id)
        .collect();
    let file_path = user_data_dir().join(format!("{namespace}.yaml"));

    if remaining.is_empty() {
        std::fs::remove_file(&file_path)
            .map_err(|error| format!("echec de suppression de {}: {error}", file_path.display()))?;
    } else {
        write_user_yaml_file(&file_path, &remaining)
            .map_err(|error| format!("echec d'ecriture dans {}: {error}", file_path.display()))?;
    }

    println!("Commande '{target_id}' supprimee.");

    match reload_daemon() {
        Ok(()) => println!("Daemon recharge -- disponible immediatement."),
        Err(_) => println!("Daemon non joignable -- sera pris en compte au prochain demarrage."),
    }

    Ok(())
}

/// Reecrit un fichier YAML utilisateur entier depuis une liste de
/// scenarios (remplace tout le contenu) -- utilise par `remove` pour
/// regenerer un fichier sans l'entree supprimee. Duplique volontairement
/// une partie de la logique de serialisation d'`append_scenario_yaml`
/// (append incrementale pour `add`, reecriture complete ici pour `remove`)
/// plutot que de forcer les deux a partager un chemin de code commun pour
/// une si petite quantite de code.
fn write_user_yaml_file(path: &Path, scenarios: &[&Scenario]) -> io::Result<()> {
    let mut file = std::fs::File::create(path)?;
    for (index, scenario) in scenarios.iter().enumerate() {
        if index > 0 {
            writeln!(file)?;
        }
        writeln!(file, "- id: {}", scenario.id)?;
        writeln!(file, "  description: {}", yaml_scalar(&scenario.description))?;
        if !scenario.tags.is_empty() {
            let quoted_tags = scenario
                .tags
                .iter()
                .map(|tag| yaml_scalar(tag))
                .collect::<Vec<_>>()
                .join(", ");
            writeln!(file, "  tags: [{quoted_tags}]")?;
        }
        writeln!(file, "  commands:")?;
        writeln!(file, "    linux: {}", yaml_scalar(&scenario.commands.linux))?;
        writeln!(file, "    windows: {}", yaml_scalar(&scenario.commands.windows))?;
        if !scenario.commands.macos.is_empty() {
            writeln!(file, "    macos: {}", yaml_scalar(&scenario.commands.macos))?;
        }
        writeln!(file, "  explanation: {}", yaml_scalar(&scenario.explanation))?;
        if !scenario.warning.trim().is_empty() {
            writeln!(file, "  warning: {}", yaml_scalar(&scenario.warning))?;
        }
    }
    Ok(())
}

fn prompt(label: &str) -> Result<String, String> {
    print!("{label}");
    io::stdout().flush().ok();
    let mut line = String::new();
    io::stdin()
        .read_line(&mut line)
        .map_err(|error| error.to_string())?;
    Ok(line.trim().to_owned())
}

/// Slug alphanumerique en minuscules, mots joints par underscore, limite a
/// `max_words` mots pour garder des ids/noms de fichiers raisonnables.
fn slugify(text: &str, max_words: usize) -> String {
    text.chars()
        .map(|character| {
            if character.is_alphanumeric() {
                character.to_ascii_lowercase()
            } else {
                ' '
            }
        })
        .collect::<String>()
        .split_whitespace()
        .take(max_words)
        .collect::<Vec<_>>()
        .join("_")
}

/// Génère un id unique (namespace + slug de la description), en ajoutant un
/// suffixe numérique en cas de collision avec le corpus existant (intégré +
/// utilisateur).
fn generate_unique_id(namespace: &str, description: &str, existing: &[Scenario]) -> String {
    let slug = slugify(description, 5);
    let base = if slug.is_empty() {
        namespace.to_owned()
    } else {
        format!("{namespace}_{slug}")
    };
    if !existing.iter().any(|scenario| scenario.id == base) {
        return base;
    }
    let mut suffix = 2;
    loop {
        let candidate = format!("{base}_{suffix}");
        if !existing.iter().any(|scenario| scenario.id == candidate) {
            return candidate;
        }
        suffix += 1;
    }
}

/// Toujours entre guillemets, pour un round-trip fiable avec le parseur
/// maison d'everycli-core (`clean_scalar`), qui ne gère pas l'echappement
/// -- on remplace donc les guillemets internes plutôt que d'essayer de les
/// echapper.
fn yaml_scalar(value: &str) -> String {
    format!("\"{}\"", value.replace('"', "'"))
}

fn append_scenario_yaml(
    path: &Path,
    id: &str,
    description: &str,
    command: &str,
    explanation: &str,
    tags: &[String],
    warning: &str,
) -> io::Result<()> {
    use std::fs::OpenOptions;

    let mut file = OpenOptions::new().create(true).append(true).open(path)?;

    writeln!(file)?;
    writeln!(file, "- id: {id}")?;
    writeln!(file, "  description: {}", yaml_scalar(description))?;
    if !tags.is_empty() {
        let quoted_tags = tags
            .iter()
            .map(|tag| yaml_scalar(tag))
            .collect::<Vec<_>>()
            .join(", ");
        writeln!(file, "  tags: [{quoted_tags}]")?;
    }
    writeln!(file, "  commands:")?;
    writeln!(file, "    linux: {}", yaml_scalar(command))?;
    writeln!(file, "    windows: {}", yaml_scalar(command))?;
    writeln!(file, "  explanation: {}", yaml_scalar(explanation))?;
    if !warning.trim().is_empty() {
        writeln!(file, "  warning: {}", yaml_scalar(warning))?;
    }
    Ok(())
}

/// Demande au daemon de recharger le corpus (best effort -- si le daemon
/// n'est pas joignable, l'appelant doit traiter ca comme un simple
/// avertissement, pas une erreur bloquante).
fn reload_daemon() -> Result<(), String> {
    let mut stream = TcpStream::connect("127.0.0.1:51821").map_err(|error| error.to_string())?;
    stream
        .set_read_timeout(Some(Duration::from_secs(15)))
        .ok();
    writeln!(stream, "{{\"action\":\"reload\"}}").map_err(|error| error.to_string())?;

    let mut reader = BufReader::new(stream);
    let mut line = String::new();
    reader
        .read_line(&mut line)
        .map_err(|error| error.to_string())?;

    if line.contains("\"ok\":true") {
        Ok(())
    } else {
        Err(line)
    }
}

fn daemon_error_message(error: &everycli_core::daemon::DaemonError) -> String {
    use everycli_core::daemon::DaemonError;
    match error {
        DaemonError::Unavailable => "daemon indisponible (unavailable)".to_owned(),
        DaemonError::RespawnFailed => "impossible de demarrer le daemon automatiquement".to_owned(),
        DaemonError::Timeout => "le daemon ne repond pas (timeout)".to_owned(),
        DaemonError::Server { code, message } => format!("{code}: {message}"),
    }
}

fn print_help() {
    println!("EveryCli Rust fast path");
    println!("Usage: everycli-rs search <query> [options]");
    println!("       everycli-rs add");
    println!("       everycli-rs list");
    println!("       everycli-rs remove [id]");
    println!();
    println!("Search options:");
    println!("  --top N, -t N            Number of results (default 1)");
    println!("  --platform linux|windows|macos");
    println!("  --data DIR               Corpus directory override");
    println!("  --json                   Machine-readable output");
    println!("  --error MSG, -e MSG      Diagnose an error message against known hints");
    println!("  --env NAME               Filter results by environment tag");
    println!("  --copy, -c               Copy the resolved command to the clipboard");
    println!("  --run, -r                Confirm and execute the resolved command");
    println!("  --interactive, -i        Pick a result from a numbered list");
    println!("  --shell, -s              Print only the resolved command to stdout");
    println!("  --no-daemon              Skip the daemon and search the local corpus directly");
    println!("  --debug                  Show scores in human-readable output (always in --json)");
    println!();
    println!("'add' lance une serie de prompts pour ajouter une commande personnalisee");
    println!("dans ~/.everycli/commands (ou %USERPROFILE%\\.everycli\\commands sur Windows).");
    println!("'list' affiche les commandes personnalisees deja ajoutees.");
    println!("'remove [id]' en supprime une (selection au clavier si aucun id donne).");
}

fn render_human(shown: &[DisplayHit], query: &str, debug: bool) {
    use owo_colors::Stream::Stdout;

    if shown.len() == 1 {
        let hit = &shown[0];
        println!();
        println!(
            "{} {} {} {}",
            "✓".if_supports_color(Stdout, |t| t.green().bold().to_string()),
            hit.namespace.if_supports_color(Stdout, |t| t.dimmed().to_string()),
            "·".if_supports_color(Stdout, |t| t.dimmed().to_string()),
            hit.id.if_supports_color(Stdout, |t| t.bold().to_string())
        );
        println!();
        println!(
            "  {}",
            hit.command.if_supports_color(Stdout, |t| t.cyan().to_string())
        );
        println!();
        println!("  {}", hit.explanation);
        if !hit.warning.is_empty() {
            println!();
            println!(
                "  {} {}",
                "⚠".if_supports_color(Stdout, |t| t.yellow().bold().to_string()),
                hit.warning.if_supports_color(Stdout, |t| t.yellow().to_string())
            );
        }
        if debug {
            println!();
            println!(
                "  {}",
                format!("score {:.4}", hit.score)
                    .if_supports_color(Stdout, |t| t.dimmed().to_string())
            );
        }
    } else {
        println!();
        println!(
            "{} pour \"{}\"",
            format!("{} resultats", shown.len())
                .if_supports_color(Stdout, |t| t.bold().to_string()),
            query
        );
        for (index, hit) in shown.iter().enumerate() {
            println!();
            let number = format!("{}.", index + 1);
            if debug {
                println!(
                    "{} {}  {}",
                    number.if_supports_color(Stdout, |t| t.bold().to_string()),
                    hit.id.if_supports_color(Stdout, |t| t.bold().to_string()),
                    format!("{:.2}", hit.score).if_supports_color(Stdout, |t| t.dimmed().to_string())
                );
            } else {
                println!(
                    "{} {}",
                    number.if_supports_color(Stdout, |t| t.bold().to_string()),
                    hit.id.if_supports_color(Stdout, |t| t.bold().to_string())
                );
            }
            println!(
                "   {} {}",
                ">".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                hit.command
                    .if_supports_color(Stdout, |t| t.cyan().bold().to_string())
            );
            println!("   {}", hit.explanation);
            if !hit.warning.is_empty() {
                println!(
                    "   {} {}",
                    "⚠".if_supports_color(Stdout, |t| t.yellow().bold().to_string()),
                    hit.warning.if_supports_color(Stdout, |t| t.yellow().to_string())
                );
            }
        }
    }
    println!();
}

fn render_json(hits: &[DisplayHit]) -> String {
    let mut out = String::from("[");
    for (index, hit) in hits.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        let tags = hit
            .tags
            .iter()
            .map(|tag| format!("\"{}\"", json_escape(tag)))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{{\"id\":\"{}\",\"namespace\":\"{}\",\"command\":\"{}\",\"explanation\":\"{}\",\"warning\":\"{}\",\"tags\":[{}],\"score\":{:.4}}}",
            json_escape(&hit.id),
            json_escape(&hit.namespace),
            json_escape(&hit.command),
            json_escape(&hit.explanation),
            json_escape(&hit.warning),
            tags,
            hit.score,
        ));
    }
    out.push(']');
    out
}

fn json_escape(value: &str) -> String {
    value
        .chars()
        .flat_map(|character| match character {
            '"' => "\\\"".chars().collect::<Vec<_>>(),
            '\\' => "\\\\".chars().collect::<Vec<_>>(),
            '\n' => "\\n".chars().collect::<Vec<_>>(),
            '\r' => "\\r".chars().collect::<Vec<_>>(),
            '\t' => "\\t".chars().collect::<Vec<_>>(),
            control if control.is_control() => {
                format!("\\u{:04x}", control as u32).chars().collect()
            }
            regular => vec![regular],
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(json_escape("a\"b\n"), "a\\\"b\\n");
    }

    fn hit(id: &str, tags: &[&str], score: f32) -> DisplayHit {
        DisplayHit {
            id: id.to_owned(),
            namespace: "docker".to_owned(),
            command: format!("cmd-{id}"),
            explanation: "explanation".to_owned(),
            warning: String::new(),
            tags: tags.iter().map(|tag| tag.to_string()).collect(),
            score,
        }
    }

    #[test]
    fn filter_by_env_keeps_only_matching_tags_case_insensitively() {
        let hits = vec![
            hit("a", &["Docker", "compose"], 0.9),
            hit("b", &["git"], 0.8),
        ];
        let filtered = filter_by_env(&hits, "docker");
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].id, "a");
    }

    #[test]
    fn filter_by_env_returns_empty_when_nothing_matches() {
        let hits = vec![hit("a", &["git"], 0.9)];
        assert!(filter_by_env(&hits, "npm").is_empty());
    }

    #[test]
    fn should_disambiguate_true_when_top_two_scores_are_close() {
        let hits = vec![hit("a", &[], 0.80), hit("b", &[], 0.78)];
        assert!(should_disambiguate(&hits));
    }

    #[test]
    fn should_disambiguate_false_when_gap_is_large() {
        let hits = vec![hit("a", &[], 0.90), hit("b", &[], 0.10)];
        assert!(!should_disambiguate(&hits));
    }

    #[test]
    fn should_disambiguate_false_when_top_score_is_zero() {
        let hits = vec![hit("a", &[], 0.0), hit("b", &[], 0.0)];
        assert!(!should_disambiguate(&hits));
    }

    #[test]
    fn should_disambiguate_false_with_fewer_than_two_hits() {
        let hits = vec![hit("a", &[], 0.9)];
        assert!(!should_disambiguate(&hits));
    }

    #[test]
    fn render_json_includes_tags_and_warning() {
        let mut single = hit("docker_build_image", &["docker", "build"], 0.91);
        single.warning = "careful".to_owned();
        let json = render_json(&[single]);
        assert!(json.contains("\"tags\":[\"docker\",\"build\"]"));
        assert!(json.contains("\"warning\":\"careful\""));
        assert!(json.contains("\"id\":\"docker_build_image\""));
    }

    #[test]
    fn daemon_error_message_reports_unavailable() {
        let message = daemon_error_message(&everycli_core::daemon::DaemonError::Unavailable);
        assert!(message.contains("indisponible") || message.contains("unavailable"));
    }

    #[test]
    fn daemon_error_message_includes_server_reason() {
        let error = everycli_core::daemon::DaemonError::Server {
            code: "EMPTY_QUERY".to_owned(),
            message: "vide".to_owned(),
        };
        let message = daemon_error_message(&error);
        assert!(message.contains("vide"));
    }
}
