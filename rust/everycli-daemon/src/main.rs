//! Serveur TCP Rust natif pour EveryCli — remplace le daemon Python
//! (`everycli/infra/daemon_server.py`) sans toucher au client (protocole
//! JSON ligne-par-ligne identique sur 127.0.0.1:51821, voir
//! `everycli-core::daemon` pour l'implémentation client).
//!
//! Combine la recherche lexicale existante d'`everycli-core` avec un
//! reranking sémantique via `everycli-inference` (ONNX Runtime).
//!
//! Un thread par connexion (voir `run_daemon`), état partagé derrière un
//! `Arc<Mutex<DaemonState>>` — l'acceptation de nouvelles connexions n'est
//! plus bloquée par une requête lente en cours de traitement.
//!
//! Variables d'environnement (toutes optionnelles, défauts pensés pour un
//! lancement depuis `C:\EveryCli\rust` avec `cargo run -p everycli-daemon`) :
//! - EVERYCLI_PORT (défaut 51821, doit matcher le client)
//! - EVERYCLI_DATA_DIR (défaut "../everycli/data/commands")
//! - EVERYCLI_MODEL_DIR (défaut "onnx-bench/models/everycli-minilm-ft")
//! - EVERYCLI_ONNXRUNTIME_DYLIB (défaut "onnx-bench/runtime/onnxruntime.dll")

use std::cmp::Ordering;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering as AtomicOrdering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use anyhow::Result;
use everycli_core::{Platform, Scenario, candidates_for_platform, explicit_namespace, load_corpus_merged, score as lexical_score};
use everycli_inference::{SemanticEncoder, cosine_similarity, init_runtime};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// Poids du score lexical vs sémantique dans le score hybride final.
/// Point de départ arbitraire — à calibrer contre le corpus réel une fois
/// qu'on a un jeu de requêtes de référence avec les résultats attendus.
const LEXICAL_WEIGHT: f32 = 0.45;
const SEMANTIC_WEIGHT: f32 = 0.55;

/// Bonus additif quand le namespace du scénario correspond au namespace
/// explicite détecté dans la requête (mot-clé comme "docker", "git"...).
/// C'est un BONUS, pas un filtre dur — un scénario hors du namespace
/// détecté reste candidat, il doit juste gagner honnêtement via son score
/// lexical/sémantique. Important pour que les commandes ajoutées par
/// l'utilisateur (`everycli add`), potentiellement dans un namespace
/// générique, restent toujours trouvables même quand une requête contient
/// un mot-clé d'un autre écosystème. Valeur arbitraire, à calibrer.
const NAMESPACE_BONUS: f32 = 0.2;

struct DaemonState {
    data_dir: PathBuf,
    user_dir: PathBuf,
    model_dir: PathBuf,
    scenarios: Vec<Scenario>,
    /// Embeddings parallèles à `scenarios` (même index).
    embeddings: Vec<Vec<f32>>,
    id_to_index: HashMap<String, usize>,
    encoder: SemanticEncoder,
    platform: Platform,
    debug: bool,
}

fn current_platform() -> Platform {
    if cfg!(windows) {
        Platform::Windows
    } else if cfg!(target_os = "macos") {
        Platform::Macos
    } else {
        Platform::Linux
    }
}

fn env_path(var: &str, default: &str) -> PathBuf {
    std::env::var(var)
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(default))
}

/// Dossier des commandes ajoutées par l'utilisateur via `everycli add`
/// (`~/.everycli/commands`), fusionné avec le corpus intégré — même
/// résolution de chemin que le côté client (`everycli-rs`), pour que le
/// daemon voie exactement les mêmes commandes perso que le repli local.
fn user_data_dir() -> PathBuf {
    if let Ok(path) = std::env::var("EVERYCLI_USER_DATA_DIR") {
        return PathBuf::from(path);
    }
    let home = if cfg!(windows) {
        std::env::var("USERPROFILE").unwrap_or_else(|_| ".".to_owned())
    } else {
        std::env::var("HOME").unwrap_or_else(|_| ".".to_owned())
    };
    Path::new(&home).join(".everycli").join("commands")
}

fn dylib_default_name() -> &'static str {
    if cfg!(windows) {
        "onnx-bench/runtime/onnxruntime.dll"
    } else if cfg!(target_os = "macos") {
        "onnx-bench/runtime/libonnxruntime.dylib"
    } else {
        "onnx-bench/runtime/libonnxruntime.so"
    }
}

/// Cache disque des embeddings du corpus — évite de recalculer les ~450
/// embeddings (4-6.5s mesurés) à chaque démarrage du daemon quand ni le
/// corpus ni le modèle n'ont changé.
#[derive(Serialize, Deserialize)]
struct EmbeddingsCache {
    /// Hash du contenu (ids+descriptions du corpus + métadonnées du fichier
    /// modèle) — toute divergence invalide le cache automatiquement, pas
    /// besoin de gestion manuelle de version.
    key: String,
    /// Même ordre que `ids` — `embeddings[i]` correspond à `ids[i]`.
    ids: Vec<String>,
    embeddings: Vec<Vec<f32>>,
}

fn cache_path(model_dir: &Path) -> PathBuf {
    model_dir.join("corpus_embeddings_cache.json")
}

/// Hash un échantillon du contenu du fichier modèle (début + fin + taille)
/// plutôt que sa date de modification -- une simple copie (comme le fait
/// `stage-release.ps1`/`install.ps1` à chaque réinstallation) change la
/// date mais pas le contenu, et changeait à tort la clé de cache avant ce
/// fix, forçant un recalcul inutile des embeddings à chaque réinstall.
/// Hasher le fichier entier (448 Mo) serait trop coûteux à chaque
/// démarrage -- un échantillon début/fin suffit en pratique (un modèle
/// ré-exporté/re-entraîné a une sérialisation de poids entièrement
/// différente, pas juste une modification localisée au milieu du fichier).
fn hash_model_file(model_path: &Path, hasher: &mut impl Hasher) -> Result<()> {
    use std::io::{Read, Seek, SeekFrom};

    const SAMPLE_SIZE: u64 = 1024 * 1024; // 1 MiB

    let mut file = std::fs::File::open(model_path)?;
    let len = file.metadata()?.len();
    len.hash(hasher);

    let head_size = SAMPLE_SIZE.min(len) as usize;
    let mut head = vec![0u8; head_size];
    file.read_exact(&mut head)?;
    head.hash(hasher);

    if len > SAMPLE_SIZE {
        file.seek(SeekFrom::End(-(SAMPLE_SIZE as i64)))?;
        let mut tail = vec![0u8; SAMPLE_SIZE as usize];
        file.read_exact(&mut tail)?;
        tail.hash(hasher);
    }

    Ok(())
}

fn compute_cache_key(scenarios: &[Scenario], documents: &[String], model_path: &Path) -> Result<String> {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    for (scenario, document) in scenarios.iter().zip(documents.iter()) {
        scenario.id.hash(&mut hasher);
        // On hash le texte RÉELLEMENT embeddé (description+tags+explication+
        // commande), pas juste `description` — sinon toute évolution de la
        // construction du document (voir build_corpus) laisse un cache
        // obsolète silencieusement "valide", et le daemon sert des
        // embeddings calculés avec une ancienne logique sans le signaler.
        document.hash(&mut hasher);
    }
    hash_model_file(model_path, &mut hasher)?;
    Ok(format!("{:x}", hasher.finish()))
}

/// (Re)charge le corpus. Réutilise les embeddings du cache disque s'ils
/// correspondent exactement (même hash de contenu) ; sinon les recalcule en
/// un seul appel batché et écrit le cache pour la prochaine fois (best
/// effort — un échec d'écriture du cache n'empêche pas le démarrage).
fn build_corpus(
    data_dir: &Path,
    user_dir: &Path,
    model_dir: &Path,
    encoder: &mut SemanticEncoder,
) -> Result<(Vec<Scenario>, Vec<Vec<f32>>, HashMap<String, usize>)> {
    let scenarios = load_corpus_merged(data_dir, user_dir)?;

    // Construit le texte embeddé par scénario AVANT le calcul de la clé de
    // cache, précisément pour que cette logique (description+tags×3+
    // explication+commande×3) soit prise en compte dans le hash et non
    // contournée silencieusement si elle change plus tard.
    let documents: Vec<String> = scenarios
        .iter()
        .map(|s| {
            let tags_boosted = s.tags.join(" ") + " " + &s.tags.join(" ") + " " + &s.tags.join(" ");
            let cmd_boosted = vec![s.commands.linux.clone(); 3].join(" ");
            format!("{} {} {} {}", s.description, tags_boosted, s.explanation, cmd_boosted)
        })
        .collect();

    let model_path = model_dir.join("model.onnx");
    let cache_key = compute_cache_key(&scenarios, &documents, &model_path)?;
    let cache_file = cache_path(model_dir);

    if let Ok(raw) = std::fs::read_to_string(&cache_file)
        && let Ok(cache) = serde_json::from_str::<EmbeddingsCache>(&raw)
        && cache.key == cache_key
        && cache.ids.len() == scenarios.len()
        && cache.ids.iter().zip(scenarios.iter()).all(|(id, s)| id == &s.id)
    {
        eprintln!("Cache d'embeddings valide trouvé ({} scénarios) — calcul évité.", scenarios.len());
        let id_to_index: HashMap<String, usize> = scenarios
            .iter()
            .enumerate()
            .map(|(i, s)| (s.id.clone(), i))
            .collect();
        return Ok((scenarios, cache.embeddings, id_to_index));
    }

    let descriptions: Vec<&str> = documents.iter().map(|s| s.as_str()).collect();
    eprintln!("Calcul des embeddings pour {} scénarios (pas de cache valide)...", scenarios.len());
    let start = std::time::Instant::now();
    let matrix = encoder.encode(&descriptions)?;
    eprintln!("Embeddings du corpus calculés en {:?}", start.elapsed());

    let embeddings: Vec<Vec<f32>> = matrix.outer_iter().map(|row| row.to_vec()).collect();
    let id_to_index: HashMap<String, usize> = scenarios
        .iter()
        .enumerate()
        .map(|(i, s)| (s.id.clone(), i))
        .collect();

    let cache = EmbeddingsCache {
        key: cache_key,
        ids: scenarios.iter().map(|s| s.id.clone()).collect(),
        embeddings: embeddings.clone(),
    };
    match serde_json::to_string(&cache) {
        Ok(serialized) => {
            if let Err(e) = std::fs::write(&cache_file, serialized) {
                eprintln!("Avertissement : échec d'écriture du cache d'embeddings ({e}) — pas bloquant.");
            }
        }
        Err(e) => eprintln!("Avertissement : échec de sérialisation du cache d'embeddings ({e}) — pas bloquant."),
    }

    Ok((scenarios, embeddings, id_to_index))
}

fn handle_search(state: &mut DaemonState, query: &str, top_k: usize) -> Result<Value> {
    if query.trim().is_empty() {
        return Ok(
            json!({"ok": false, "code": "EMPTY_QUERY", "error": "La requête ne peut pas être vide"}),
        );
    }
    if top_k < 1 {
        return Ok(json!({"ok": false, "code": "INVALID_TOP_K", "error": "top_k doit être positif"}));
    }

    let candidates = candidates_for_platform(&state.scenarios, state.platform);
    if candidates.is_empty() {
        return Ok(json!({"ok": true, "results": []}));
    }

    let detected_namespace = explicit_namespace(query);

    let query_matrix = state.encoder.encode(&[query])?;
    let query_vec: Vec<f32> = query_matrix.row(0).to_vec();

    let mut scored: Vec<(f32, &Scenario, String)> = candidates
        .into_iter()
        .map(|scenario| {
            let idx = state.id_to_index[&scenario.id];
            let semantic = cosine_similarity(&query_vec, &state.embeddings[idx]);
            let semantic_normalized = (semantic + 1.0) / 2.0;
            let lexical = lexical_score(scenario, query);
            let namespace_bonus = if detected_namespace.as_deref() == Some(scenario.namespace.as_str()) {
                NAMESPACE_BONUS
            } else {
                0.0
            };
            let hybrid = LEXICAL_WEIGHT * lexical + SEMANTIC_WEIGHT * semantic_normalized + namespace_bonus;
            let command = scenario.commands.for_platform(state.platform).to_owned();

            if state.debug {
                eprintln!(
                    "[DEBUG] Scenario: {} | Lexical: {:.4} | Semantic: {:.4} (raw: {:.4}) | NS bonus: {:.2} | Hybrid: {:.4}",
                    scenario.id, lexical, semantic_normalized, semantic, namespace_bonus, hybrid
                );
            }

            (hybrid, scenario, command)
        })
        .collect();

    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));
    scored.truncate(top_k);

    let results: Vec<Value> = scored
        .into_iter()
        .map(|(score, scenario, command)| {
            json!({
                "id": scenario.id,
                "description": scenario.description,
                "command": command,
                "explanation": scenario.explanation,
                "warning": scenario.warning,
                "tags": scenario.tags,
                "namespace": scenario.namespace,
                "score": score,
            })
        })
        .collect();

    Ok(json!({"ok": true, "results": results}))
}

fn handle_connection(stream: TcpStream, state: &Mutex<DaemonState>) -> Result<()> {
    eprintln!("Connexion reçue de {:?}", stream.peer_addr());
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut writer = stream;

    let mut line = String::new();
    reader.read_line(&mut line)?;
    if line.trim().is_empty() {
        return Ok(());
    }

    eprintln!("Requête : {}", line.trim());

    let response = match serde_json::from_str::<Value>(line.trim_end()) {
        Err(_) => json!({"ok": false, "code": "BAD_JSON", "error": "Requête JSON invalide"}),
        Ok(request) => {
            let action = request.get("action").and_then(Value::as_str).unwrap_or("");
            match action {
                "ping" => json!({"ok": true, "pong": true}),
                "reload" => {
                    // Contrairement à "search" (verrou tenu brèvement), on
                    // garde le verrou pendant tout le recalcul ici -- reload
                    // est une action rare et volontaire (déclenchée par
                    // `everycli add`/`remove`), pas un chemin à haute
                    // fréquence : bloquer les recherches concurrentes
                    // pendant les quelques secondes du recalcul est un
                    // compromis largement acceptable, pas la peine de
                    // complexifier le code pour l'éviter.
                    let mut guard = state.lock().expect("daemon state lock poisoned");
                    let data_dir = guard.data_dir.clone();
                    let user_dir = guard.user_dir.clone();
                    let model_dir = guard.model_dir.clone();
                    match build_corpus(&data_dir, &user_dir, &model_dir, &mut guard.encoder) {
                        Ok((scenarios, embeddings, id_to_index)) => {
                            guard.scenarios = scenarios;
                            guard.embeddings = embeddings;
                            guard.id_to_index = id_to_index;
                            json!({"ok": true, "reloaded": true})
                        }
                        Err(e) => json!({"ok": false, "code": "RELOAD_ERROR", "error": e.to_string()}),
                    }
                }
                "search" => {
                    let query = request.get("query").and_then(Value::as_str).unwrap_or("");
                    let top_k = request
                        .get("top_k")
                        .and_then(Value::as_u64)
                        .unwrap_or(1) as usize;
                    // Le verrou n'est tenu que pendant le scoring lui-même
                    // (quelques ms), pas pendant les I/O réseau (lecture de
                    // la requête, écriture de la réponse) -- ça laisse les
                    // autres threads de connexion progresser en parallèle.
                    let mut guard = state.lock().expect("daemon state lock poisoned");
                    match handle_search(&mut guard, query, top_k) {
                        Ok(response) => response,
                        Err(e) => json!({"ok": false, "code": "SEARCH_ERROR", "error": e.to_string()}),
                    }
                }
                _ => json!({"ok": false, "code": "UNKNOWN_ACTION", "error": "Action inconnue"}),
            }
        }
    };

    writer.write_all((response.to_string() + "\n").as_bytes())?;
    writer.flush()?;
    Ok(())
}

/// Coeur du daemon : init runtime/modèle/corpus, puis boucle d'acceptation
/// TCP. Partagé entre le mode console normal (`stop_flag = None`, boucle
/// bloquante classique) et le mode service Windows (`stop_flag = Some(...)`,
/// boucle non bloquante qui vérifie régulièrement si le SCM a demandé
/// l'arrêt).
fn run_daemon(stop_flag: Option<Arc<AtomicBool>>) -> Result<()> {
    let port: u16 = std::env::var("EVERYCLI_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(51821);
    let data_dir = env_path("EVERYCLI_DATA_DIR", "../everycli/data/commands");
    let user_dir = user_data_dir();
    let model_dir = env_path("EVERYCLI_MODEL_DIR", "onnx-bench/models/everycli-minilm-ft");
    let dylib_path = env_path("EVERYCLI_ONNXRUNTIME_DYLIB", dylib_default_name());

    eprintln!("Chargement du runtime ONNX depuis {:?}...", dylib_path);
    init_runtime(&dylib_path)?;

    eprintln!("Chargement de l'encodeur sémantique depuis {:?}...", model_dir);
    let mut encoder = SemanticEncoder::new(&model_dir)?;

    eprintln!("Chargement du corpus depuis {:?} (+ commandes utilisateur dans {:?})...", data_dir, user_dir);
    let (scenarios, embeddings, id_to_index) = build_corpus(&data_dir, &user_dir, &model_dir, &mut encoder)?;
    eprintln!("{} scénarios chargés.", scenarios.len());

    let debug = std::env::args().any(|arg| arg == "--debug");
    eprintln!("Mode debug: {}", if debug { "activé" } else { "désactivé" });

    let state = DaemonState {
        data_dir,
        user_dir,
        model_dir,
        scenarios,
        embeddings,
        id_to_index,
        encoder,
        platform: current_platform(),
        debug,
    };

    let listener = match TcpListener::bind(("127.0.0.1", port)) {
        Ok(listener) => listener,
        Err(e) if e.kind() == std::io::ErrorKind::AddrInUse => {
            // Message clair au lieu de l'erreur OS brute -- ce cas arrive
            // systématiquement si le service Windows ET le lanceur du
            // dossier Démarrage tournent tous les deux (voir install.ps1,
            // qui nettoie désormais l'autre mécanisme à chaque install pour
            // éviter ça), ou si le daemon est simplement déjà en cours
            // d'exécution.
            eprintln!(
                "Un daemon EveryCli écoute déjà sur le port {port} -- rien à faire, il répond déjà aux requêtes."
            );
            eprintln!(
                "(Si tu veux vraiment relancer cette instance-ci, arrête d'abord l'autre : `sc.exe stop EveryCliDaemon` ou tue le process `everycli-daemon`.)"
            );
            return Ok(());
        }
        Err(e) => return Err(e.into()),
    };
    eprintln!("everycli-daemon prêt sur 127.0.0.1:{port}");

    if stop_flag.is_some() {
        // Mode service : boucle non bloquante pour pouvoir vérifier
        // régulièrement si le SCM a demandé l'arrêt (Stop). En mode console
        // normal, on garde la boucle bloquante classique (plus simple, pas
        // de sleep inutile entre chaque connexion).
        listener.set_nonblocking(true)?;
    }

    // Arc<Mutex<>> plutôt qu'un simple &mut partagé par une boucle
    // séquentielle -- chaque connexion acceptée est traitée dans son propre
    // thread, donc une requête lente (ou un client qui traine à envoyer sa
    // ligne) ne bloque plus l'acceptation de nouvelles connexions. Le verrou
    // sérialise toujours l'accès au modèle/corpus lui-même (nécessaire,
    // `SemanticEncoder::encode` prend `&mut self`), mais c'est une amélioration
    // réelle par rapport à la boucle mono-thread précédente : plus de connexion
    // qui attend derrière une autre encore en train d'être lue/écrite.
    let state = Arc::new(Mutex::new(state));

    loop {
        if let Some(flag) = &stop_flag
            && flag.load(AtomicOrdering::Relaxed)
        {
            eprintln!("Arrêt demandé (service), fermeture du daemon.");
            break;
        }

        match listener.accept() {
            Ok((stream, _)) => {
                let state = Arc::clone(&state);
                std::thread::spawn(move || {
                    if let Err(e) = handle_connection(stream, &state) {
                        eprintln!("Erreur de connexion : {e}");
                    }
                });
            }
            Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(200));
            }
            Err(e) if stop_flag.is_none() => {
                eprintln!("Erreur d'acceptation : {e}");
            }
            Err(_) => {
                // Mode service, non bloquant : les erreurs autres que
                // WouldBlock sont rares (socket fermée, etc.), on continue
                // la boucle plutôt que de planter le service.
            }
        }
    }

    Ok(())
}

#[cfg(windows)]
mod windows_service_support {
    //! Enregistrement auprès du Service Control Manager (SCM) de Windows,
    //! pour tourner comme un vrai service (démarre avant toute session
    //! utilisateur, redémarrage automatique géré par Windows en cas de
    //! crash). Installation du service nécessite les droits administrateur
    //! (voir install.ps1) -- le mode console/dossier Démarrage reste
    //! l'option par défaut sans droits spéciaux.

    use std::ffi::OsString;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::time::Duration;

    use windows_service::service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    };
    use windows_service::service_control_handler::{self, ServiceControlHandlerResult};
    use windows_service::{define_windows_service, service_dispatcher};

    const SERVICE_NAME: &str = "EveryCliDaemon";
    const SERVICE_TYPE: ServiceType = ServiceType::OWN_PROCESS;

    define_windows_service!(ffi_service_main, service_main);

    /// Point d'entrée appelé depuis `main()` quand l'exe est lancé avec
    /// `--service` (c'est le SCM qui fait ça, configuré via le binPath lors
    /// de `sc.exe create`, voir install.ps1).
    pub fn run() -> anyhow::Result<()> {
        service_dispatcher::start(SERVICE_NAME, ffi_service_main)
            .map_err(|e| anyhow::anyhow!("echec du dispatcher de service Windows: {e}"))
    }

    fn service_main(_arguments: Vec<OsString>) {
        if let Err(e) = run_service() {
            eprintln!("Erreur du service EveryCliDaemon : {e}");
        }
    }

    fn run_service() -> anyhow::Result<()> {
        let stop_flag = Arc::new(AtomicBool::new(false));
        let stop_flag_for_handler = stop_flag.clone();

        let event_handler = move |control_event| -> ServiceControlHandlerResult {
            match control_event {
                ServiceControl::Stop => {
                    stop_flag_for_handler.store(true, Ordering::Relaxed);
                    ServiceControlHandlerResult::NoError
                }
                ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
                _ => ServiceControlHandlerResult::NotImplemented,
            }
        };

        let status_handle = service_control_handler::register(SERVICE_NAME, event_handler)
            .map_err(|e| anyhow::anyhow!("echec d'enregistrement aupres du SCM: {e}"))?;

        status_handle
            .set_service_status(ServiceStatus {
                service_type: SERVICE_TYPE,
                current_state: ServiceState::Running,
                controls_accepted: ServiceControlAccept::STOP,
                exit_code: ServiceExitCode::Win32(0),
                checkpoint: 0,
                wait_hint: Duration::default(),
                process_id: None,
            })
            .map_err(|e| anyhow::anyhow!("echec set_service_status(Running): {e}"))?;

        if let Err(e) = super::run_daemon(Some(stop_flag)) {
            eprintln!("Erreur du daemon (mode service) : {e}");
        }

        status_handle
            .set_service_status(ServiceStatus {
                service_type: SERVICE_TYPE,
                current_state: ServiceState::Stopped,
                controls_accepted: ServiceControlAccept::empty(),
                exit_code: ServiceExitCode::Win32(0),
                checkpoint: 0,
                wait_hint: Duration::default(),
                process_id: None,
            })
            .map_err(|e| anyhow::anyhow!("echec set_service_status(Stopped): {e}"))?;

        Ok(())
    }
}

fn main() -> Result<()> {
    #[cfg(windows)]
    {
        // Lancé par le SCM avec --service (voir install.ps1, sc.exe create
        // .../binPath contient ce flag) -> mode service Windows. Sinon,
        // comportement inchangé : mode console normal (dev, ou lancé
        // manuellement/via le dossier Démarrage).
        if std::env::args().any(|arg| arg == "--service") {
            return windows_service_support::run();
        }
    }

    run_daemon(None)
}
