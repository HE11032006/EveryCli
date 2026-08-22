mod i18n;

use everycli_core::{Platform, Scenario, daemon, find_error_hint, load_corpus_merged, search};
use i18n::Lang;
use owo_colors::OwoColorize;
use serde::{Deserialize, Serialize};
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
    explanation_en: String,
    warning: String,
    warning_en: String,
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

fn search_limit(interactive: bool, top_k: usize) -> usize {
    if interactive {
        top_k.max(1)
    } else {
        top_k.max(3)
    }
}

fn localized_explanation<'a>(hit: &'a DisplayHit, lang: Lang) -> &'a str {
    if lang == Lang::En && !hit.explanation_en.is_empty() {
        &hit.explanation_en
    } else {
        &hit.explanation
    }
}

fn localized_warning<'a>(hit: &'a DisplayHit, lang: Lang) -> &'a str {
    if lang == Lang::En && !hit.warning_en.is_empty() {
        &hit.warning_en
    } else {
        &hit.warning
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
    let cfg = load_config();
    let lang = Lang::resolve(cfg.language.as_deref());

    if arguments.is_empty() || arguments[0] == "--help" || arguments[0] == "-h" {
        print_help(lang);
        return Ok(());
    }
    if arguments[0] == "add" {
        return cmd_add(lang);
    }
    if arguments[0] == "list" {
        return cmd_list(lang);
    }
    if arguments[0] == "remove" {
        let id_arg = arguments.get(1).cloned();
        return cmd_remove(id_arg, lang);
    }
    if arguments[0] == "config" {
        let sub = arguments.get(1).cloned();
        let key = arguments.get(2).cloned();
        let value = arguments.get(3).cloned();
        return cmd_config(sub, key, value, lang);
    }
    if arguments[0] == "ask" {
        let query: Vec<String> = arguments[1..].to_vec();
        return cmd_ask(query, lang);
    }
    if arguments.remove(0) != "search" {
        return Err("expected `search`, `add`, `list`, `remove`, `config`, or `ask`; run `everycli --help`".to_owned());
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
                print_help(lang);
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
    let search_top = search_limit(interactive, top_k);

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
                    explanation_en: hit.explanation_en,
                    warning: hit.warning,
                    warning_en: hit.warning_en,
                    tags: hit.tags,
                    score: hit.score,
                })
                .collect(),
            Err(error) => {
                eprintln!(
                    "everycli: {}",
                    lang.daemon_fallback_warn(&daemon_error_message(&error))
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
        return Err(lang.no_match_found().to_owned());
    }

    let mut ordered = hits;
    if interactive && ordered.len() > 1 {
        let choice = pick_interactive(&ordered, lang).unwrap_or(0);
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
            eprintln!("  {}", localized_explanation(first, lang));
            eprintln!("  score {:.2}", first.score);
        }
    } else if json {
        println!("{}", render_json(shown));
    } else {
        render_human(shown, &query, debug, lang);

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
            if shown.len() > 1 && (copy || run_it) {
                println!("  {}", lang.ambiguous_action_target(&first.id, &first.command));
            }

            // Copie automatique dans le presse-papier quand un seul résultat est affiché
            if shown.len() == 1 || copy {
                if clipboard_copy(&first.command) {
                    use owo_colors::Stream::Stdout;
                    println!(
                        "  {} {}",
                        "📋".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                        lang.copied_to_clipboard().if_supports_color(Stdout, |t| t.dimmed().to_string())
                    );
                    println!();
                } else if copy {
                    eprintln!("{}", lang.clipboard_failed());
                }
            }
            if run_it {
                run_confirmed(&first.command, lang);
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
            explanation_en: result.scenario.explanation_en,
            warning: result.scenario.warning,
            warning_en: result.scenario.warning_en,
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
fn pick_interactive(hits: &[DisplayHit], lang: Lang) -> Option<usize> {
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
            label: format!("{}  —  {}", hit.command, localized_explanation(hit, lang)),
        })
        .collect();

    let prompt = lang.pick_interactive_prompt(choices.len());
    inquire::Select::new(&prompt, choices)
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

fn run_confirmed(command: &str, lang: Lang) {
    eprint!("{}", lang.run_confirm_prompt(command));
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
                    "{}",
                    lang.exec_exit_code(output.status.code().unwrap_or(1))
                );
            }
        }
        Err(error) => eprintln!("{}", lang.exec_failed(&error.to_string())),
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
fn cmd_add(lang: Lang) -> Result<(), String> {
    let user_dir = user_data_dir();
    std::fs::create_dir_all(&user_dir)
        .map_err(|error| format!("impossible de creer {}: {error}", user_dir.display()))?;

    println!("{}", lang.add_title());

    let namespace_input = prompt(lang.add_category_prompt())?;
    let namespace = slugify(&namespace_input, 8);
    if namespace.is_empty() {
        return Err(lang.add_category_empty().to_owned());
    }

    let description = prompt(lang.add_description_prompt())?;
    if description.trim().is_empty() {
        return Err(lang.add_description_empty().to_owned());
    }

    let command = prompt(lang.add_command_prompt())?;
    if command.trim().is_empty() {
        return Err(lang.add_command_empty().to_owned());
    }

    let explanation = prompt(lang.add_explanation_prompt())?;
    let tags_raw = prompt(lang.add_tags_prompt())?;
    let warning = prompt(lang.add_warning_prompt())?;

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
    println!("{}", lang.add_success(&id, &file_path.display().to_string()));

    match reload_daemon() {
        Ok(()) => println!("{}", lang.daemon_reloaded()),
        Err(reason) => println!("{}", lang.daemon_reload_failed(&reason)),
    }

    Ok(())
}

fn user_scenarios() -> Result<Vec<Scenario>, String> {
    let user_dir = user_data_dir();
    if !user_dir.is_dir() {
        return Ok(Vec::new());
    }
    Ok(everycli_core::load_corpus(&user_dir).unwrap_or_default())
}

fn cmd_list(lang: Lang) -> Result<(), String> {
    use owo_colors::Stream::Stdout;

    let scenarios = user_scenarios()?;
    if scenarios.is_empty() {
        println!("{}", lang.list_empty());
        return Ok(());
    }

    println!();
    println!(
        "{} :",
        lang.list_header(scenarios.len())
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
        println!("   {}", scenario.explanation_for_lang(lang == Lang::En));
    }
    println!();
    Ok(())
}

fn cmd_remove(id_arg: Option<String>, lang: Lang) -> Result<(), String> {
    let scenarios = user_scenarios()?;
    if scenarios.is_empty() {
        println!("{}", lang.remove_empty());
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
            match inquire::Select::new(lang.remove_pick_prompt(), choices).prompt() {
                Ok(choice) => choice.id,
                Err(_) => return Ok(()),
            }
        }
    };

    let Some(target) = scenarios.iter().find(|scenario| scenario.id == target_id) else {
        return Err(lang.remove_not_found(&target_id));
    };

    let confirmed = inquire::Confirm::new(&lang.remove_confirm_prompt(&target.id, &target.commands.linux))
        .with_default(false)
        .prompt()
        .unwrap_or(false);

    if !confirmed {
        println!("{}", lang.remove_canceled());
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

    println!("{}", lang.remove_success(&target_id));

    match reload_daemon() {
        Ok(()) => println!("{}", lang.daemon_reloaded()),
        Err(reason) => println!("{}", lang.daemon_reload_failed(&reason)),
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

/// Demande au daemon de recharger le corpus. Retourne une raison exploitable
/// par l'interface si la connexion échoue, si le daemon ne répond pas à temps
/// ou s'il refuse explicitement le rechargement.
fn reload_daemon() -> Result<(), String> {
    let mut stream = TcpStream::connect("127.0.0.1:51821")
        .map_err(|error| format!("connexion impossible au daemon : {error}"))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(15)))
        .ok();
    writeln!(stream, "{{\"action\":\"reload\"}}")
        .map_err(|error| format!("échec d'envoi de la demande : {error}"))?;

    let mut reader = BufReader::new(stream);
    let mut line = String::new();
    reader
        .read_line(&mut line)
        .map_err(|error| format!("le daemon n'a pas répondu à temps : {error}"))?;

    validate_reload_response(&line)
}

fn validate_reload_response(line: &str) -> Result<(), String> {
    let response: serde_json::Value = serde_json::from_str(line.trim())
        .map_err(|error| format!("réponse JSON invalide ({error})"))?;
    if response.get("ok").and_then(serde_json::Value::as_bool) == Some(true) {
        return Ok(());
    }

    let code = response
        .get("code")
        .and_then(serde_json::Value::as_str)
        .unwrap_or("RELOAD_ERROR");
    let error = response
        .get("error")
        .and_then(serde_json::Value::as_str)
        .unwrap_or("le daemon a refusé le rechargement");
    Err(format!("{code}: {error}"))
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

fn print_help(lang: Lang) {
    println!("{}", lang.help_text());
}

fn render_human(shown: &[DisplayHit], query: &str, debug: bool, lang: Lang) {
    use owo_colors::Stream::Stdout;

    if shown.len() == 1 {
        let hit = &shown[0];
        let explanation = localized_explanation(hit, lang);
        let warning = localized_warning(hit, lang);

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
        println!(
            "  {} {}",
            "i".if_supports_color(Stdout, |t| t.dimmed().to_string()),
            explanation
        );
        if !warning.is_empty() {
            println!();
            println!(
                "  {} {}",
                "⚠".if_supports_color(Stdout, |t| t.yellow().bold().to_string()),
                warning.if_supports_color(Stdout, |t| t.yellow().to_string())
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
            "{}",
            lang.search_results_header(shown.len(), query)
                .if_supports_color(Stdout, |t| t.bold().to_string())
        );
        for (index, hit) in shown.iter().enumerate() {
            let explanation = localized_explanation(hit, lang);
            let warning = localized_warning(hit, lang);

            println!();
            let number = format!("{}.", index + 1);
            if debug {
                println!(
                    "{} {} {} {}",
                    number.if_supports_color(Stdout, |t| t.bold().to_string()),
                    hit.namespace.if_supports_color(Stdout, |t| t.dimmed().to_string()),
                    "·".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                    format!("{}  {:.2}", hit.id, hit.score)
                        .if_supports_color(Stdout, |t| t.bold().to_string())
                );
            } else {
                println!(
                    "{} {} {} {}",
                    number.if_supports_color(Stdout, |t| t.bold().to_string()),
                    hit.namespace.if_supports_color(Stdout, |t| t.dimmed().to_string()),
                    "·".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                    hit.id.if_supports_color(Stdout, |t| t.bold().to_string())
                );
            }
            println!(
                "   {} {}",
                ">".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                hit.command
                    .if_supports_color(Stdout, |t| t.cyan().bold().to_string())
            );
            println!(
                "   {} {}",
                "i".if_supports_color(Stdout, |t| t.dimmed().to_string()),
                explanation
            );
            if !warning.is_empty() {
                println!(
                    "   {} {}",
                    "⚠".if_supports_color(Stdout, |t| t.yellow().bold().to_string()),
                    warning.if_supports_color(Stdout, |t| t.yellow().to_string())
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

// ─── Config ──────────────────────────────────────────────────────────────────

/// Fichier de configuration utilisateur : `~/.everycli/config.toml`
#[derive(Debug, Default, Serialize, Deserialize)]
struct EveryCliConfig {
    language: Option<String>,
    provider: Option<String>,
    api_key: Option<String>,
    api_url: Option<String>,
    api_model: Option<String>,
}

fn config_path() -> PathBuf {
    let home = if cfg!(windows) {
        env::var("USERPROFILE").unwrap_or_else(|_| ".".to_owned())
    } else {
        env::var("HOME").unwrap_or_else(|_| ".".to_owned())
    };
    Path::new(&home).join(".everycli").join("config.toml")
}

fn load_config() -> EveryCliConfig {
    let path = config_path();
    let Ok(content) = std::fs::read_to_string(&path) else {
        return EveryCliConfig::default();
    };
    toml::from_str(&content).unwrap_or_default()
}

fn write_private_config(path: &Path, content: &str) -> Result<(), String> {
    use std::fs::OpenOptions;

    let mut options = OpenOptions::new();
    options.create(true).truncate(true).write(true);
    #[cfg(unix)]
    std::os::unix::fs::OpenOptionsExt::mode(&mut options, 0o600);

    let mut file = options
        .open(path)
        .map_err(|e| format!("ouverture config {}: {e}", path.display()))?;
    file.write_all(content.as_bytes())
        .map_err(|e| format!("ecriture config {}: {e}", path.display()))?;
    file.flush()
        .map_err(|e| format!("flush config {}: {e}", path.display()))?;

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))
            .map_err(|e| format!("permissions config {}: {e}", path.display()))?;
    }

    Ok(())
}

fn save_config(config: &EveryCliConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("impossible de creer {}: {e}", parent.display()))?;
    }
    let content = toml::to_string_pretty(config)
        .map_err(|e| format!("serialisation config: {e}"))?;
    write_private_config(&path, &content)
}

struct ProviderInfo {
    name: &'static str,
    url: &'static str,
    model: &'static str,
}

fn get_provider_preset(name: &str) -> Option<ProviderInfo> {
    match name.to_lowercase().as_str() {
        "openai" => Some(ProviderInfo {
            name: "OpenAI",
            url: "https://api.openai.com/v1",
            model: "gpt-4o-mini",
        }),
        "groq" => Some(ProviderInfo {
            name: "Groq",
            url: "https://api.groq.com/openai/v1",
            model: "llama-3.3-70b-versatile",
        }),
        "mistral" => Some(ProviderInfo {
            name: "Mistral AI",
            url: "https://api.mistral.ai/v1",
            model: "mistral-small-latest",
        }),
        "gemini" | "google" => Some(ProviderInfo {
            name: "Google Gemini",
            url: "https://generativelanguage.googleapis.com/v1beta/openai",
            model: "gemini-3.6-flash",
        }),
        "openrouter" => Some(ProviderInfo {
            name: "OpenRouter",
            url: "https://openrouter.ai/api/v1",
            model: "openai/gpt-4o-mini",
        }),
        "claude" | "anthropic" => Some(ProviderInfo {
            name: "Claude (via OpenRouter)",
            url: "https://openrouter.ai/api/v1",
            model: "anthropic/claude-3.5-sonnet",
        }),
        "deepseek" => Some(ProviderInfo {
            name: "DeepSeek",
            url: "https://api.deepseek.com",
            model: "deepseek-chat",
        }),
        "cloudflare" => Some(ProviderInfo {
            name: "Cloudflare Workers AI",
            url: "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/ai/v1",
            model: "@cf/meta/llama-3.1-8b-instruct",
        }),
        _ => None,
    }
}

fn auto_detect_provider(key: &str) -> Option<ProviderInfo> {
    if key.starts_with("gsk_") {
        get_provider_preset("groq")
    } else if key.starts_with("sk-or-") {
        get_provider_preset("openrouter")
    } else if key.starts_with("AIza") || key.starts_with("AQ.") {
        get_provider_preset("gemini")
    } else if key.starts_with("sk-ant-") {
        get_provider_preset("claude")
    } else if key.starts_with("sk-proj-") || key.starts_with("sk-") {
        get_provider_preset("openai")
    } else {
        None
    }
}

/// `everycli config set <key> <value>` / `everycli config get <key>` /
/// `everycli config show`
fn cmd_config(
    sub: Option<String>,
    key: Option<String>,
    value: Option<String>,
    lang: Lang,
) -> Result<(), String> {
    let sub = sub.ok_or_else(|| "Usage: everycli config set <key> <value> | get <key> | show".to_owned())?;
    let mut config = load_config();

    match sub.as_str() {
        "show" => {
            let path = config_path();
            println!("Config : {}", path.display());
            println!("  language  = {} ({})", lang.code(), lang.name());
            println!("  provider  = {}", config.provider.as_deref().unwrap_or("(auto / non defini)"));
            println!("  api_url   = {}", config.api_url.as_deref().unwrap_or("(defaut: https://api.openai.com/v1)"));
            println!("  api_model = {}", config.api_model.as_deref().unwrap_or("(defaut: gpt-4o-mini)"));
            println!("  api_key   = {}", if config.api_key.is_some() { "(definie)" } else { "(non definie)" });
        }
        "get" => {
            let key = key.ok_or_else(|| "everycli config get <key>".to_owned())?;
            let val = match key.as_str() {
                "language" | "lang" => config.language.as_deref().unwrap_or(lang.code()),
                "provider" => config.provider.as_deref().unwrap_or("(non defini)"),
                "api_key" => config.api_key.as_deref().unwrap_or("(non definie)"),
                "api_url" => config.api_url.as_deref().unwrap_or("(non definie)"),
                "api_model" => config.api_model.as_deref().unwrap_or("(non definie)"),
                other => return Err(format!("cle inconnue: {other} (valeurs: language, provider, api_key, api_url, api_model)")),
            };
            println!("{val}");
        }
        "set" => {
            let key = key.ok_or_else(|| "everycli config set <key> <value> (ex: set language en | set api_key ...)".to_owned())?;
            let value = value.ok_or_else(|| format!("everycli config set {key} <value>"))?;
            match key.as_str() {
                "language" | "lang" => {
                    let parsed = Lang::from_str_opt(&value).ok_or_else(|| {
                        "Langue non supportee. Choisissez: en (English) ou fr (Francais)".to_owned()
                    })?;
                    config.language = Some(parsed.code().to_owned());
                    println!("Language set to {} ({})", parsed.name(), parsed.code());
                }
                "provider" => {
                    let preset = get_provider_preset(&value).ok_or_else(|| {
                        format!("Provider inconnu: {value}.\nProviders supportes: openai, groq, mistral, gemini, openrouter, claude, deepseek, cloudflare")
                    })?;
                    config.provider = Some(preset.name.to_owned());
                    config.api_url = Some(preset.url.to_owned());
                    config.api_model = Some(preset.model.to_owned());
                    println!("Provider configure : {} (URL: {}, Modele: {})", preset.name, preset.url, preset.model);
                }
                "api_key" => {
                    config.api_key = Some(value.clone());
                    if let Some(detected) = auto_detect_provider(&value) {
                        config.provider = Some(detected.name.to_owned());
                        config.api_url = Some(detected.url.to_owned());
                        config.api_model = Some(detected.model.to_owned());
                        println!("Cle API enregistree (Provider auto-detecte : {}, Modele : {})", detected.name, detected.model);
                    } else {
                        println!("Cle API enregistree.");
                    }
                }
                "api_url" => config.api_url = Some(value),
                "api_model" => config.api_model = Some(value),
                other => return Err(format!("cle inconnue: {other} (valeurs acceptees: language, provider, api_key, api_url, api_model)")),
            }
            save_config(&config)?;
            println!("Configuration sauvegardee dans {}", config_path().display());
        }
        other => return Err(format!("sous-commande inconnue: {other} (set | get | show)")),
    }
    Ok(())
}

// ─── Ask ─────────────────────────────────────────────────────────────────────

/// Réponse structurée attendue du LLM pour `everycli ask`.
struct AskResult {
    command_linux: String,
    command_windows: String,
    explanation: String,
    warning: String,
    tags: Vec<String>,
}

/// `everycli ask <question>` — appelle l'API LLM configurée, affiche la
/// commande retournée, et propose à l'utilisateur de l'ajouter au corpus.
fn cmd_ask(query_parts: Vec<String>, lang: Lang) -> Result<(), String> {
    use owo_colors::Stream::Stdout;

    if query_parts.is_empty() {
        return Err("Usage: everycli ask <question>".to_owned());
    }
    let query = query_parts.join(" ");

    let config = load_config();
    let api_key = config
        .api_key
        .as_deref()
        .map(|s| s.to_owned())
        .or_else(|| env::var("EVERYCLI_API_KEY").ok())
        .ok_or_else(|| lang.no_api_key_error().to_owned())?;

    let api_url = config
        .api_url
        .as_deref()
        .unwrap_or("https://api.openai.com/v1")
        .trim_end_matches('/')
        .to_owned();
    let api_model = config
        .api_model
        .as_deref()
        .unwrap_or("gpt-4o-mini")
        .to_owned();

    eprintln!(
        "{}  {}",
        "⟳".if_supports_color(Stdout, |t| t.dimmed().to_string()),
        lang.ask_querying(&api_model).if_supports_color(Stdout, |t| t.dimmed().to_string())
    );

    let result = call_llm_api(&api_url, &api_key, &api_model, &query, lang)
        .map_err(|e| format!("API Error: {e}"))?;

    let is_windows = cfg!(windows);
    let primary_cmd = if is_windows && !result.command_windows.is_empty() {
        &result.command_windows
    } else {
        &result.command_linux
    };

    // Affichage du résultat
    println!();
    println!(
        "  {}",
        primary_cmd.if_supports_color(Stdout, |t| t.cyan().bold().to_string())
    );
    println!();
    println!("  {}", result.explanation);
    if !result.warning.is_empty() {
        println!();
        println!(
            "  {} {}",
            "⚠".if_supports_color(Stdout, |t| t.yellow().bold().to_string()),
            result.warning.if_supports_color(Stdout, |t| t.yellow().to_string())
        );
    }
    println!();

    // Copie automatique dans le presse-papier pour un usage immédiat
    if clipboard_copy(primary_cmd) {
        println!(
            "  {} {}",
            "📋".if_supports_color(Stdout, |t| t.dimmed().to_string()),
            lang.copied_to_clipboard().if_supports_color(Stdout, |t| t.dimmed().to_string())
        );
        println!();
    }

    // Proposition d'ajout au corpus
    eprint!("{}", lang.ask_save_prompt());
    io::stdout().flush().ok();
    let mut answer = String::new();
    if io::stdin().read_line(&mut answer).is_err() {
        return Ok(());
    }
    if !matches!(answer.trim().to_lowercase().as_str(), "o" | "oui" | "y" | "yes") {
        return Ok(());
    }

    // Demande du namespace (catégorie) avant d'écrire
    let namespace_input = prompt(lang.add_category_prompt())?;
    let namespace = slugify(&namespace_input, 8);
    if namespace.is_empty() {
        return Err(lang.add_category_empty().to_owned());
    }

    let user_dir = user_data_dir();
    std::fs::create_dir_all(&user_dir)
        .map_err(|e| format!("impossible de creer {}: {e}", user_dir.display()))?;

    let data_dir = default_data_dir();
    let existing = load_corpus_merged(&data_dir, &user_dir).unwrap_or_default();
    let id = generate_unique_id(&namespace, &query, &existing);

    let file_path = user_dir.join(format!("{namespace}.yaml"));

    let command_for_yaml = if result.command_windows.is_empty() {
        &result.command_linux
    } else {
        append_scenario_yaml_cross(
            &file_path,
            &id,
            &query,
            &result.command_linux,
            &result.command_windows,
            &result.explanation,
            &result.tags,
            &result.warning,
        )
        .map_err(|e| format!("echec d'ecriture: {e}"))?;

        println!();
        println!("{}", lang.add_success(&id, &file_path.display().to_string()));
        match reload_daemon() {
            Ok(()) => println!("{}", lang.daemon_reloaded()),
            Err(reason) => println!("{}", lang.daemon_reload_failed(&reason)),
        }
        return Ok(());
    };

    append_scenario_yaml(
        &file_path,
        &id,
        &query,
        command_for_yaml,
        &result.explanation,
        &result.tags,
        &result.warning,
    )
    .map_err(|e| format!("echec d'ecriture: {e}"))?;

    println!();
    println!("{}", lang.add_success(&id, &file_path.display().to_string()));

    match reload_daemon() {
        Ok(()) => println!("{}", lang.daemon_reloaded()),
        Err(reason) => println!("{}", lang.daemon_reload_failed(&reason)),
    }

    Ok(())
}

/// Appel HTTP vers une API compatible OpenAI (`/v1/chat/completions`).
/// Retourne un `AskResult` en parsant la réponse JSON manuellement pour
/// éviter une dépendance lourde à serde_json — on cherche juste le contenu
/// du premier choix de message.
fn call_llm_api(
    base_url: &str,
    api_key: &str,
    model: &str,
    user_query: &str,
    lang: Lang,
) -> Result<AskResult, String> {
    let lang_instruction = match lang {
        Lang::En => "Write the 'explanation' and 'warning' fields in English.",
        Lang::Fr => "Écris les champs 'explanation' et 'warning' en Français.",
    };

    let system_prompt = format!(
        r#"You are a CLI command assistant. Given a task description, respond with a JSON object (and ONLY the JSON object, no markdown, no explanation outside the JSON) with these fields:
{{
  "command_linux": "<shell command for Linux/macOS>",
  "command_windows": "<equivalent PowerShell/cmd command, or empty string if identical>",
  "explanation": "<one sentence explaining what the command does>",
  "warning": "<one sentence safety warning if the command is destructive, or empty string>",
  "tags": ["<tag1>", "<tag2>"]
}}
Tags should be short lowercase keywords (e.g. git, docker, npm, ssh, linux). Keep explanation and warning concise (under 120 chars). {lang_instruction}"#
    );

    let url = format!("{base_url}/chat/completions");

    let body = serde_json::json!({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.2
    });

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("construction du client HTTP: {e}"))?;

    let response = client
        .post(&url)
        .bearer_auth(api_key)
        .json(&body)
        .send()
        .map_err(|e| format!("requete HTTP: {e}"))?;

    let status = response.status();
    let text = response.text().map_err(|e| format!("lecture reponse: {e}"))?;

    if !status.is_success() {
        return Err(format!("API a retourne {status}: {text}"));
    }

    // Extraction du contenu de la réponse LLM depuis le JSON de l'API
    let content = extract_llm_content(&text)
        .ok_or_else(|| format!("impossible d'extraire le contenu de la reponse: {text}"))?;

    // Parse le JSON retourné par le LLM
    parse_ask_result(&content)
        .ok_or_else(|| format!("le LLM n'a pas retourne le JSON attendu:\n{content}"))
}

/// Extrait `choices[0].message.content` depuis la réponse JSON de l'API.
fn extract_llm_content(json: &str) -> Option<String> {
    // Recherche de `"content":"..."` après `"message":`
    // On utilise une extraction simple sans parser tout le JSON.
    let marker = "\"content\":\"";
    // On cherche après la première occurrence de `"message":`
    let after_message = json.split("\"message\":").nth(1)?;
    let start = after_message.find(marker)? + marker.len();
    let rest = &after_message[start..];
    // Lit jusqu'au premier `"` non échappé
    let mut content = String::new();
    let mut chars = rest.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\\' {
            match chars.next()? {
                '"' => content.push('"'),
                'n' => content.push('\n'),
                'r' => content.push('\r'),
                't' => content.push('\t'),
                '\\' => content.push('\\'),
                other => { content.push('\\'); content.push(other); }
            }
        } else if ch == '"' {
            break;
        } else {
            content.push(ch);
        }
    }
    if content.is_empty() { None } else { Some(content) }
}

/// Parse le JSON retourné par le LLM en `AskResult`.
/// Tolère que le LLM encadre sa réponse dans un bloc ```json ... ``` .
fn parse_ask_result(raw: &str) -> Option<AskResult> {
    // Retire les éventuels blocs markdown
    let clean = raw
        .trim()
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim();

    let command_linux = extract_json_string(clean, "command_linux")?;
    if command_linux.is_empty() {
        return None;
    }
    let command_windows = extract_json_string(clean, "command_windows").unwrap_or_default();
    let explanation = extract_json_string(clean, "explanation").unwrap_or_default();
    let warning = extract_json_string(clean, "warning").unwrap_or_default();
    let tags = extract_json_string_array(clean, "tags");

    Some(AskResult { command_linux, command_windows, explanation, warning, tags })
}

/// Extrait la valeur d'un champ string `"key": "value"` d'une chaîne JSON brute.
fn extract_json_string(json: &str, key: &str) -> Option<String> {
    let marker = format!("\"{key}\":");
    let after = json.split(&marker).nth(1)?.trim_start();
    if !after.starts_with('"') {
        return None;
    }
    let rest = &after[1..];
    let mut value = String::new();
    let mut chars = rest.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\\' {
            match chars.next()? {
                '"' => value.push('"'),
                'n' => value.push('\n'),
                'r' => value.push('\r'),
                't' => value.push('\t'),
                '\\' => value.push('\\'),
                other => { value.push('\\'); value.push(other); }
            }
        } else if ch == '"' {
            break;
        } else {
            value.push(ch);
        }
    }
    Some(value)
}

/// Extrait un tableau de strings `"key": ["a", "b"]` d'une chaîne JSON brute.
fn extract_json_string_array(json: &str, key: &str) -> Vec<String> {
    let marker = format!("\"{key}\":");
    let Some(after) = json.split(&marker).nth(1) else { return vec![]; };
    let trimmed = after.trim_start();
    if !trimmed.starts_with('[') { return vec![]; }
    let end = trimmed.find(']').unwrap_or(trimmed.len());
    let inner = &trimmed[1..end];
    inner
        .split(',')
        .filter_map(|part| {
            let part = part.trim();
            if part.starts_with('"') && part.ends_with('"') && part.len() >= 2 {
                Some(part[1..part.len() - 1].to_owned())
            } else {
                None
            }
        })
        .filter(|s| !s.is_empty())
        .collect()
}

/// Version de `append_scenario_yaml` pour `ask` quand Linux ≠ Windows.
fn append_scenario_yaml_cross(
    path: &Path,
    id: &str,
    description: &str,
    command_linux: &str,
    command_windows: &str,
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
        let quoted = tags.iter().map(|t| yaml_scalar(t)).collect::<Vec<_>>().join(", ");
        writeln!(file, "  tags: [{quoted}]")?;
    }
    writeln!(file, "  commands:")?;
    writeln!(file, "    linux: {}", yaml_scalar(command_linux))?;
    writeln!(file, "    windows: {}", yaml_scalar(command_windows))?;
    writeln!(file, "  explanation: {}", yaml_scalar(explanation))?;
    if !warning.trim().is_empty() {
        writeln!(file, "  warning: {}", yaml_scalar(warning))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(json_escape("a\"b\n"), "a\\\"b\\n");
    }

    #[cfg(unix)]
    #[test]
    fn config_file_permissions_are_private() {
        use std::os::unix::fs::PermissionsExt;

        let path = std::env::temp_dir().join(format!(
            "everycli-config-permissions-{}-{}",
            std::process::id(),
            std::thread::current().name().unwrap_or("test")
        ));
        write_private_config(&path, "api_key = \"test-secret\"\n").unwrap();
        let mode = std::fs::metadata(&path).unwrap().permissions().mode() & 0o777;
        std::fs::remove_file(&path).unwrap();

        assert_eq!(mode, 0o600);
    }

    fn hit(id: &str, tags: &[&str], score: f32) -> DisplayHit {
        DisplayHit {
            id: id.to_owned(),
            namespace: "docker".to_owned(),
            command: format!("cmd-{id}"),
            explanation: "explanation".to_owned(),
            explanation_en: String::new(),
            warning: String::new(),
            warning_en: String::new(),
            tags: tags.iter().map(|tag| tag.to_string()).collect(),
            score,
        }
    }

    #[test]
    fn localized_text_uses_english_when_available() {
        let mut scenario = hit("a", &[], 0.9);
        scenario.explanation = "Explication française".to_owned();
        scenario.explanation_en = "English explanation".to_owned();
        scenario.warning = "Avertissement français".to_owned();
        scenario.warning_en = "English warning".to_owned();

        assert_eq!(localized_explanation(&scenario, Lang::En), "English explanation");
        assert_eq!(localized_explanation(&scenario, Lang::Fr), "Explication française");
        assert_eq!(localized_warning(&scenario, Lang::En), "English warning");
        assert_eq!(localized_warning(&scenario, Lang::Fr), "Avertissement français");
    }

    #[test]
    fn localized_text_falls_back_to_french_when_english_is_missing() {
        let mut scenario = hit("a", &[], 0.9);
        scenario.explanation = "Explication française".to_owned();
        scenario.warning = "Avertissement français".to_owned();

        assert_eq!(localized_explanation(&scenario, Lang::En), "Explication française");
        assert_eq!(localized_warning(&scenario, Lang::En), "Avertissement français");
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
    fn search_limit_uses_requested_top_k_for_interactive_mode() {
        assert_eq!(search_limit(true, 3), 3);
        assert_eq!(search_limit(true, 0), 1);
    }

    #[test]
    fn search_limit_keeps_extra_candidates_for_non_interactive_mode() {
        assert_eq!(search_limit(false, 1), 3);
        assert_eq!(search_limit(false, 5), 5);
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

    #[test]
    fn slugify_produces_clean_lowercase_slug() {
        assert_eq!(slugify("Git: Squash Last 3 Commits!", 5), "git_squash_last_3_commits");
    }

    #[test]
    fn yaml_scalar_replaces_double_quotes() {
        assert_eq!(yaml_scalar("echo \"hello\""), "\"echo 'hello'\"");
    }

    #[test]
    fn parse_ask_result_extracts_all_fields() {
        let raw = r#"{
  "command_linux": "tar -czf archive.tar.gz ./folder",
  "command_windows": "Compress-Archive -Path ./folder -DestinationPath archive.zip",
  "explanation": "Compress a directory into an archive.",
  "warning": "Overwrites existing archive.",
  "tags": ["tar", "archive", "compression"]
}"#;
        let parsed = parse_ask_result(raw).expect("should parse ask result");
        assert_eq!(parsed.command_linux, "tar -czf archive.tar.gz ./folder");
        assert_eq!(parsed.command_windows, "Compress-Archive -Path ./folder -DestinationPath archive.zip");
        assert_eq!(parsed.explanation, "Compress a directory into an archive.");
        assert_eq!(parsed.warning, "Overwrites existing archive.");
        assert_eq!(parsed.tags, vec!["tar", "archive", "compression"]);
    }

    #[test]
    fn parse_ask_result_handles_markdown_fences() {
        let raw = "```json\n{\"command_linux\": \"git reset --soft HEAD~1\", \"command_windows\": \"\", \"explanation\": \"Undo last commit\", \"warning\": \"\", \"tags\": [\"git\"]}\n```";
        let parsed = parse_ask_result(raw).expect("should parse fenced json");
        assert_eq!(parsed.command_linux, "git reset --soft HEAD~1");
        assert_eq!(parsed.tags, vec!["git"]);
    }

    #[test]
    fn extract_llm_content_extracts_nested_message() {
        let api_response = r#"{"id":"chatcmpl-123","choices":[{"message":{"role":"assistant","content":"{\"command_linux\":\"ls -la\"}"}}]}"#;
        let content = extract_llm_content(api_response).expect("should extract content");
        assert_eq!(content, "{\"command_linux\":\"ls -la\"}");
    }

    #[test]
    fn auto_detect_provider_identifies_keys() {
        assert_eq!(auto_detect_provider("gsk_123456").unwrap().name, "Groq");
        assert_eq!(auto_detect_provider("sk-or-v1-abcdef").unwrap().name, "OpenRouter");
        assert_eq!(auto_detect_provider("AIzaSyD-1234").unwrap().name, "Google Gemini");
        assert_eq!(auto_detect_provider("sk-ant-api03-xyz").unwrap().name, "Claude (via OpenRouter)");
        assert_eq!(auto_detect_provider("sk-proj-999").unwrap().name, "OpenAI");
    }

    #[test]
    fn get_provider_preset_returns_correct_endpoints() {
        let groq = get_provider_preset("groq").unwrap();
        assert_eq!(groq.url, "https://api.groq.com/openai/v1");
        assert_eq!(groq.model, "llama-3.3-70b-versatile");

        let gemini = get_provider_preset("gemini").unwrap();
        assert_eq!(gemini.url, "https://generativelanguage.googleapis.com/v1beta/openai");
        assert_eq!(gemini.model, "gemini-3.6-flash");

        let mistral = get_provider_preset("mistral").unwrap();
        assert_eq!(mistral.url, "https://api.mistral.ai/v1");
    }

    #[test]
    fn lang_parsing_and_resolution() {
        assert_eq!(Lang::from_str_opt("fr"), Some(Lang::Fr));
        assert_eq!(Lang::from_str_opt("french"), Some(Lang::Fr));
        assert_eq!(Lang::from_str_opt("en"), Some(Lang::En));
        assert_eq!(Lang::from_str_opt("english"), Some(Lang::En));
        assert_eq!(Lang::from_str_opt("unknown"), None);

        assert_eq!(Lang::resolve(Some("fr")), Lang::Fr);
        assert_eq!(Lang::resolve(Some("en")), Lang::En);
    }

    #[test]
    fn lang_translations_exist() {
        assert!(Lang::En.help_text().contains("Natural language"));
        assert!(Lang::Fr.help_text().contains("langage naturel"));
        assert!(Lang::En.copied_to_clipboard().contains("Ctrl+V to paste"));
        assert!(Lang::Fr.copied_to_clipboard().contains("Ctrl+V pour coller"));
        assert!(Lang::Fr.daemon_reload_failed("timeout").contains("timeout"));
        assert!(Lang::En.pick_interactive_prompt(3).contains("3"));
        assert!(Lang::Fr.pick_interactive_prompt(3).contains("3"));
        let target = Lang::Fr.ambiguous_action_target("git_commit", "git commit -m message");
        assert!(target.contains("git_commit"));
        assert!(target.contains("git commit -m message"));
    }

    #[test]
    fn validate_reload_response_accepts_success() {
        assert!(validate_reload_response(r#"{"ok":true,"reloaded":true}"#).is_ok());
    }

    #[test]
    fn validate_reload_response_reports_server_rejection() {
        let error = validate_reload_response(
            r#"{"ok":false,"code":"RELOAD_ERROR","error":"corpus inaccessible"}"#,
        )
        .unwrap_err();
        assert_eq!(error, "RELOAD_ERROR: corpus inaccessible");
    }

    #[test]
    fn validate_reload_response_reports_invalid_json() {
        let error = validate_reload_response("not-json").unwrap_err();
        assert!(error.starts_with("réponse JSON invalide ("));
    }
}
