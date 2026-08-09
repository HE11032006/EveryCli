//! Serveur TCP Rust natif pour EveryCli — remplace le daemon Python
//! (`everycli/infra/daemon_server.py`) sans toucher au client (protocole
//! JSON ligne-par-ligne identique sur 127.0.0.1:51821, voir
//! `everycli-core::daemon` pour l'implémentation client).
//!
//! Combine la recherche lexicale existante d'`everycli-core` avec un
//! reranking sémantique via `everycli-inference` (ONNX Runtime).
//!
//! ATTENTION — hypothèses à valider (voir HACKATHON_PLAN.md, Axe 1) :
//! - Le texte embeddé par scénario est `scenario.description` — pas encore
//!   confirmé identique à ce qu'utilise `semantic_matcher.py` côté Python.
//! - Les poids de combinaison lexical/sémantique (0.35/0.65 ci-dessous) sont
//!   un point de départ arbitraire, pas calibrés contre le corpus réel.
//! - Boucle serveur mono-thread (une connexion à la fois) — suffisant pour
//!   un usage personnel local, mais pas concurrent. À revoir si besoin.
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

use anyhow::Result;
use everycli_core::{Platform, Scenario, candidates_for_platform, explicit_namespace, load_corpus, score as lexical_score};
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
    let metadata = std::fs::metadata(model_path)?;
    metadata.len().hash(&mut hasher);
    if let Ok(modified) = metadata.modified() {
        modified.hash(&mut hasher);
    }
    Ok(format!("{:x}", hasher.finish()))
}

/// (Re)charge le corpus. Réutilise les embeddings du cache disque s'ils
/// correspondent exactement (même hash de contenu) ; sinon les recalcule en
/// un seul appel batché et écrit le cache pour la prochaine fois (best
/// effort — un échec d'écriture du cache n'empêche pas le démarrage).
fn build_corpus(
    data_dir: &Path,
    model_dir: &Path,
    encoder: &mut SemanticEncoder,
) -> Result<(Vec<Scenario>, Vec<Vec<f32>>, HashMap<String, usize>)> {
    let scenarios = load_corpus(data_dir)?;

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

// fn handle_search(state: &mut DaemonState, query: &str, top_k: usize) -> Result<Value> {
//     if query.trim().is_empty() {
//         return Ok(
//             json!({"ok": false, "code": "EMPTY_QUERY", "error": "La requête ne peut pas être vide"}),
//         );
//     }
//     if top_k < 1 {
//         return Ok(json!({"ok": false, "code": "INVALID_TOP_K", "error": "top_k doit être positif"}));
//     }

//     let candidates = filter_candidates(&state.scenarios, query, state.platform);
//     if candidates.is_empty() {
//         return Ok(json!({"ok": true, "results": []}));
//     }

//     let query_matrix = state.encoder.encode(&[query])?;
//     let query_vec: Vec<f32> = query_matrix.row(0).to_vec();

//     let mut scored: Vec<(f32, &Scenario, String)> = candidates
//         .into_iter()
//         .map(|scenario| {
//             let idx = state.id_to_index[&scenario.id];
//             let semantic = cosine_similarity(&query_vec, &state.embeddings[idx]);
//             let semantic_normalized = (semantic + 1.0) / 2.0; // -1..1 -> 0..1
//             let lexical = lexical_score(scenario, query);
//             let hybrid = LEXICAL_WEIGHT * lexical + SEMANTIC_WEIGHT * semantic_normalized;
//             let command = scenario.commands.for_platform(state.platform).to_owned();
//             (hybrid, scenario, command)
//         })
//         .collect();

//     scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));
//     scored.truncate(top_k);

//     let results: Vec<Value> = scored
//         .into_iter()
//         .map(|(score, scenario, command)| {
//             json!({
//                 "id": scenario.id,
//                 "description": scenario.description,
//                 "command": command,
//                 "explanation": scenario.explanation,
//                 "warning": scenario.warning,
//                 "tags": scenario.tags,
//                 "namespace": scenario.namespace,
//                 "score": score,
//             })
//         })
//         .collect();

//         let (hybrid, scenario, command) = {
//         let idx = state.id_to_index[&scenario.id];
//         let semantic = cosine_similarity(&query_vec, &state.embeddings[idx]);
//         let semantic_normalized = (semantic + 1.0) / 2.0;
//         let lexical = lexical_score(scenario, query);
//         let hybrid = LEXICAL_WEIGHT * lexical + SEMANTIC_WEIGHT * semantic_normalized;
        
//         if state.debug {
//             eprintln!(
//                 "[DEBUG] Scenario: {} | Lexical: {:.4} | Semantic: {:.4} (raw: {:.4}) | Hybrid: {:.4}",
//                 scenario.id, lexical, semantic_normalized, semantic, hybrid
//             );
//         }
        
//         (hybrid, scenario, scenario.commands.for_platform(state.platform).to_owned())
//     };

//     Ok(json!({"ok": true, "results": results}))
// }

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

fn handle_connection(stream: TcpStream, state: &mut DaemonState) -> Result<()> {
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
                "reload" => match build_corpus(&state.data_dir, &state.model_dir, &mut state.encoder) {
                    Ok((scenarios, embeddings, id_to_index)) => {
                        state.scenarios = scenarios;
                        state.embeddings = embeddings;
                        state.id_to_index = id_to_index;
                        json!({"ok": true, "reloaded": true})
                    }
                    Err(e) => json!({"ok": false, "code": "RELOAD_ERROR", "error": e.to_string()}),
                },
                "search" => {
                    let query = request.get("query").and_then(Value::as_str).unwrap_or("");
                    let top_k = request
                        .get("top_k")
                        .and_then(Value::as_u64)
                        .unwrap_or(1) as usize;
                    match handle_search(state, query, top_k) {
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

fn main() -> Result<()> {
    let port: u16 = std::env::var("EVERYCLI_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(51821);
    let data_dir = env_path("EVERYCLI_DATA_DIR", "../everycli/data/commands");
    let model_dir = env_path("EVERYCLI_MODEL_DIR", "onnx-bench/models/everycli-minilm-ft");
    let dylib_path = env_path("EVERYCLI_ONNXRUNTIME_DYLIB", dylib_default_name());
    

    eprintln!("Chargement du runtime ONNX depuis {:?}...", dylib_path);
    init_runtime(&dylib_path)?;

    eprintln!("Chargement de l'encodeur sémantique depuis {:?}...", model_dir);
    let mut encoder = SemanticEncoder::new(&model_dir)?;

    eprintln!("Chargement du corpus depuis {:?}...", data_dir);
    let (scenarios, embeddings, id_to_index) = build_corpus(&data_dir, &model_dir, &mut encoder)?;
    eprintln!("{} scénarios chargés.", scenarios.len());

    let debug = std::env::args().any(|arg| arg == "--debug");
    eprintln!("Mode debug: {}", if debug { "activé" } else { "désactivé" });

    let mut state = DaemonState {
        data_dir,
        model_dir,
        scenarios,
        embeddings,
        id_to_index,
        encoder,
        platform: current_platform(),
        debug,
    };

    
    let listener = TcpListener::bind(("127.0.0.1", port))?;
    eprintln!("everycli-daemon prêt sur 127.0.0.1:{port}");

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                if let Err(e) = handle_connection(stream, &mut state) {
                    eprintln!("Erreur de connexion : {e}");
                }
            }
            Err(e) => eprintln!("Erreur d'acceptation : {e}"),
        }
    }

    Ok(())
}
