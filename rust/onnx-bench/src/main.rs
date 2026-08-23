//! Test de vélocité isolé : charge le modèle ONNX exporté et mesure le temps
//! d'inférence, à comparer avec l'appel Python (`SemanticMatcher.match`) équivalent.
//!
//! Usage : cargo run --release (depuis rust/onnx-bench/)
//!
//! Écrit et vérifié contre la doc officielle de ort 2.0.0-rc.13
//! (https://docs.rs/ort/2.0.0-rc.13/ort/) le 08/08/2026.
//!
//! Utilise la feature "load-dynamic" : onnxruntime.dll est chargée au runtime
//! (via ort::init_from) au lieu d'être liée statiquement à la compilation —
//! ça évite le conflit de liaison MSVC (LNK2005/LNK1120) rencontré avec la
//! liaison statique par défaut. Place onnxruntime.dll dans ./runtime/ avant
//! de lancer (voir HACKATHON_PLAN.md, Axe 1).
//!
//! Piège important : `ort::Error<R>` embarque parfois la ressource R elle-même
//! (ex: SessionBuilder, qui contient des pointeurs bruts non Send/Sync). anyhow
//! refuse donc la conversion automatique via `?` sur ces erreurs — il faut les
//! convertir explicitement en String/anyhow::Error via `.map_err(ort_err)`
//! plutôt que `?` directement. Si `cargo build` sort encore des erreurs,
//! colle-les-moi telles quelles.

use std::path::Path;
use std::time::Instant;

use anyhow::Result;
use ndarray::{Array2, ArrayViewD};
use ort::session::builder::GraphOptimizationLevel;
use ort::session::Session;
use ort::value::Tensor;
use tokenizers::Tokenizer;

/// Convertit une erreur `ort` en `anyhow::Error` de façon explicite (via son
/// affichage texte), pour éviter de dépendre de `From<ort::Error<R>>` qui
/// échoue à cause de types internes non Send/Sync.
fn ort_err<E: std::fmt::Display>(e: E) -> anyhow::Error {
    anyhow::anyhow!("{e}")
}

/// Requêtes représentatives (français + anglais, comme le vrai corpus EveryCli)
const SAMPLE_QUERIES: &[&str] = &[
    "comment annuler mon dernier commit",
    "list all running docker containers",
    "comment supprimer une branche git distante",
    "how do I check disk usage on linux",
    "voir les logs d'un container docker en direct",
];

/// Nombre d'itérations pour la mesure de latence (après warmup).
const BENCH_ITERATIONS: usize = 200;

/// Mean pooling masqué par l'attention_mask — indexation directe, pas de
/// vues/slices intermédiaires, pour éviter tout problème d'emprunt.
fn mean_pool(last_hidden_state: &ArrayViewD<f32>, attention_mask: &Array2<i64>) -> Array2<f32> {
    let shape = last_hidden_state.shape();
    let (batch, seq_len, hidden) = (shape[0], shape[1], shape[2]);

    let mut pooled = Array2::<f32>::zeros((batch, hidden));

    for b in 0..batch {
        let mut mask_sum = 0.0f32;
        let mut acc = vec![0.0f32; hidden];

        for t in 0..seq_len {
            let m = attention_mask[[b, t]] as f32;
            if m == 0.0 {
                continue;
            }
            mask_sum += m;
            for h in 0..hidden {
                acc[h] += last_hidden_state[[b, t, h]] * m;
            }
        }

        let denom = mask_sum.max(1e-9);
        for h in 0..hidden {
            pooled[[b, h]] = acc[h] / denom;
        }
    }

    pooled
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

fn encode_batch(session: &mut Session, tokenizer: &Tokenizer, texts: &[&str]) -> Result<Array2<f32>> {
    let encodings = tokenizer
        .encode_batch(texts.to_vec(), true)
        .map_err(|e| anyhow::anyhow!("tokenizer error: {e}"))?;

    let max_len = encodings.iter().map(|e| e.get_ids().len()).max().unwrap_or(0);
    let batch = encodings.len();

    let mut input_ids = Array2::<i64>::zeros((batch, max_len));
    let mut attention_mask = Array2::<i64>::zeros((batch, max_len));
    let mut token_type_ids = Array2::<i64>::zeros((batch, max_len));

    for (i, enc) in encodings.iter().enumerate() {
        for (j, &id) in enc.get_ids().iter().enumerate() {
            input_ids[[i, j]] = id as i64;
        }
        for (j, &m) in enc.get_attention_mask().iter().enumerate() {
            attention_mask[[i, j]] = m as i64;
        }
        // BERT/MiniLM classique : une seule séquence par entrée, donc tout à 0.
        for j in 0..enc.get_ids().len() {
            token_type_ids[[i, j]] = 0;
        }
    }

    // `Tensor::from_array` prend possession de l'array — on garde une copie
    // de attention_mask pour le pooling, qui en a encore besoin après le run.
    let attention_mask_for_pooling = attention_mask.clone();

    let input_ids_tensor = Tensor::from_array(input_ids).map_err(ort_err)?;
    let attention_mask_tensor = Tensor::from_array(attention_mask).map_err(ort_err)?;
    let token_type_ids_tensor = Tensor::from_array(token_type_ids).map_err(ort_err)?;

    let outputs = session
        .run(ort::inputs! {
            "input_ids" => input_ids_tensor,
            "attention_mask" => attention_mask_tensor,
            "token_type_ids" => token_type_ids_tensor,
        })
        .map_err(ort_err)?;

    // Le nom de sortie dépend de comment optimum a exporté le modèle — si ça
    // plante ici avec "key not found", regarde les vrais noms avec :
    // python -c "import onnx; m = onnx.load('models/everycli-minilm-ft/model.onnx'); print([o.name for o in m.graph.output])"
    let last_hidden_state = outputs["last_hidden_state"]
        .try_extract_array::<f32>()
        .map_err(ort_err)?;

    let pooled = mean_pool(&last_hidden_state, &attention_mask_for_pooling);
    Ok(pooled)
}

fn main() -> Result<()> {
    // Chargement dynamique de onnxruntime.dll (feature "load-dynamic") — doit
    // être fait AVANT toute autre opération ort (Session::builder inclus).
    let dylib_path = Path::new("runtime").join(if cfg!(windows) {
        "onnxruntime.dll"
    } else if cfg!(target_os = "macos") {
        "libonnxruntime.dylib"
    } else {
        "libonnxruntime.so"
    });
    if !dylib_path.exists() {
        eprintln!(
            "onnxruntime introuvable dans {:?}. Télécharge le zip officiel et place la lib ici (voir instructions).",
            dylib_path
        );
        std::process::exit(1);
    }
    // ort::init_from(dylib_path.to_string_lossy().to_string())
    //     .commit()
    //     .map_err(ort_err)?;
    let env_builder = ort::init_from(dylib_path.to_string_lossy().to_string())
        .map_err(ort_err)?;
        env_builder.commit();

    let model_dir = Path::new("models/everycli-minilm-ft");
    let model_path = model_dir.join("model.onnx");
    let tokenizer_path = model_dir.join("tokenizer.json");

    if !model_path.exists() || !tokenizer_path.exists() {
        eprintln!(
            "Modèle introuvable dans {:?}. As-tu lancé l'export optimum-cli et fetch_tokenizer.py ?",
            model_dir
        );
        std::process::exit(1);
    }

    println!("Chargement du tokenizer...");
    let tokenizer = Tokenizer::from_file(&tokenizer_path)
        .map_err(|e| anyhow::anyhow!("tokenizer load error: {e}"))?;

    println!("Chargement de la session ONNX Runtime...");
    let load_start = Instant::now();
    let mut session = Session::builder()
        .map_err(ort_err)?
        .with_optimization_level(GraphOptimizationLevel::Level3)
        .map_err(ort_err)?
        .with_intra_threads(1)
        .map_err(ort_err)?
        .commit_from_file(&model_path)
        .map_err(ort_err)?;
    println!("Modèle chargé en {:?}", load_start.elapsed());

    // Warmup (le premier appel inclut souvent des coûts d'initialisation
    // internes à ORT qui fausseraient la mesure de latence si comptés).
    println!("Warmup...");
    let _ = encode_batch(&mut session, &tokenizer, &SAMPLE_QUERIES[..1])?;

    // Sanity check : une paraphrase git commit doit avoir un score cosinus
    // nettement plus haut qu'une requête sans rapport.
    let embeddings = encode_batch(&mut session, &tokenizer, SAMPLE_QUERIES)?;
    println!("\n--- Sanity check similarité cosinus ---");
    for i in 0..SAMPLE_QUERIES.len() {
        for j in (i + 1)..SAMPLE_QUERIES.len() {
            let sim = cosine_similarity(
                embeddings.row(i).as_slice().unwrap(),
                embeddings.row(j).as_slice().unwrap(),
            );
            println!(
                "  \"{}\" vs \"{}\" -> {:.4}",
                SAMPLE_QUERIES[i], SAMPLE_QUERIES[j], sim
            );
        }
    }

    // Benchmark de latence pure, requête par requête.
    println!("\n--- Benchmark latence ({BENCH_ITERATIONS} itérations, 1 requête à la fois) ---");
    let query = &SAMPLE_QUERIES[0..1];
    let bench_start = Instant::now();
    for _ in 0..BENCH_ITERATIONS {
        let _ = encode_batch(&mut session, &tokenizer, query)?;
    }
    let elapsed = bench_start.elapsed();
    println!(
        "Total: {:?} | Moyenne par requête: {:?}",
        elapsed,
        elapsed / BENCH_ITERATIONS as u32
    );

    Ok(())
}
