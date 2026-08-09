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
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};

use anyhow::Result;
use everycli_core::{Platform, Scenario, filter_candidates, load_corpus, score as lexical_score};
use everycli_inference::{SemanticEncoder, cosine_similarity, init_runtime};
use serde_json::{Value, json};

/// Poids du score lexical vs sémantique dans le score hybride final.
/// Point de départ arbitraire — à calibrer contre le corpus réel une fois
/// qu'on a un jeu de requêtes de référence avec les résultats attendus.
const LEXICAL_WEIGHT: f32 = 0.35;
const SEMANTIC_WEIGHT: f32 = 0.65;

struct DaemonState {
    data_dir: PathBuf,
    scenarios: Vec<Scenario>,
    /// Embeddings parallèles à `scenarios` (même index).
    embeddings: Vec<Vec<f32>>,
    id_to_index: HashMap<String, usize>,
    encoder: SemanticEncoder,
    platform: Platform,
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

/// (Re)charge le corpus et recalcule tous les embeddings en un seul appel
/// batché (plutôt que scénario par scénario) — même API que le batching déjà
/// validé dans `rust/onnx-bench`.
fn build_corpus(
    data_dir: &Path,
    encoder: &mut SemanticEncoder,
) -> Result<(Vec<Scenario>, Vec<Vec<f32>>, HashMap<String, usize>)> {
    let scenarios = load_corpus(data_dir)?;
    let descriptions: Vec<&str> = scenarios.iter().map(|s| s.description.as_str()).collect();

    eprintln!("Calcul des embeddings pour {} scénarios...", scenarios.len());
    let start = std::time::Instant::now();
    let matrix = encoder.encode(&descriptions)?;
    eprintln!("Embeddings du corpus calculés en {:?}", start.elapsed());

    let embeddings: Vec<Vec<f32>> = matrix.outer_iter().map(|row| row.to_vec()).collect();
    let id_to_index: HashMap<String, usize> = scenarios
        .iter()
        .enumerate()
        .map(|(i, s)| (s.id.clone(), i))
        .collect();

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

    let candidates = filter_candidates(&state.scenarios, query, state.platform);
    if candidates.is_empty() {
        return Ok(json!({"ok": true, "results": []}));
    }

    let query_matrix = state.encoder.encode(&[query])?;
    let query_vec: Vec<f32> = query_matrix.row(0).to_vec();

    let mut scored: Vec<(f32, &Scenario, String)> = candidates
        .into_iter()
        .map(|scenario| {
            let idx = state.id_to_index[&scenario.id];
            let semantic = cosine_similarity(&query_vec, &state.embeddings[idx]);
            let semantic_normalized = (semantic + 1.0) / 2.0; // -1..1 -> 0..1
            let lexical = lexical_score(scenario, query);
            let hybrid = LEXICAL_WEIGHT * lexical + SEMANTIC_WEIGHT * semantic_normalized;
            let command = scenario.commands.for_platform(state.platform).to_owned();
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
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut writer = stream;

    let mut line = String::new();
    reader.read_line(&mut line)?;
    if line.trim().is_empty() {
        return Ok(());
    }

    let response = match serde_json::from_str::<Value>(line.trim_end()) {
        Err(_) => json!({"ok": false, "code": "BAD_JSON", "error": "Requête JSON invalide"}),
        Ok(request) => {
            let action = request.get("action").and_then(Value::as_str).unwrap_or("");
            match action {
                "ping" => json!({"ok": true, "pong": true}),
                "reload" => match build_corpus(&state.data_dir, &mut state.encoder) {
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
    let (scenarios, embeddings, id_to_index) = build_corpus(&data_dir, &mut encoder)?;
    eprintln!("{} scénarios chargés.", scenarios.len());

    let mut state = DaemonState {
        data_dir,
        scenarios,
        embeddings,
        id_to_index,
        encoder,
        platform: current_platform(),
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
