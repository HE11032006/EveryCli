//! Inférence sémantique 100% Rust via ONNX Runtime — remplace le pipeline
//! Python (`sentence-transformers`) de `everycli/infra/semantic_matcher.py`.
//!
//! API validée fonctionnellement dans `rust/onnx-bench` (voir
//! HACKATHON_PLAN.md, Axe 1) : chargement du modèle ~7.3x plus rapide,
//! latence d'inférence ~1.7x plus rapide que l'équivalent Python, sanity
//! check de similarité cosinus cohérent.
//!
//! # Exemple d'usage
//! ```no_run
//! use everycli_inference::{init_runtime, SemanticEncoder, cosine_similarity};
//!
//! # fn main() -> anyhow::Result<()> {
//! // Une seule fois, au démarrage du daemon.
//! init_runtime("runtime/onnxruntime.dll")?;
//!
//! let mut encoder = SemanticEncoder::new("models/everycli-minilm-ft")?;
//! let embeddings = encoder.encode(&["comment annuler mon dernier commit"])?;
//! # Ok(())
//! # }
//! ```

use std::path::Path;

use anyhow::Result;
use ndarray::{Array2, ArrayViewD};
use ort::session::builder::GraphOptimizationLevel;
use ort::session::Session;
use ort::value::Tensor;
use tokenizers::Tokenizer;

/// Convertit une erreur `ort` en `anyhow::Error` de façon explicite (via son
/// affichage texte). Nécessaire car `ort::Error<R>` embarque parfois la
/// ressource R elle-même (ex: SessionBuilder, avec des pointeurs bruts non
/// Send/Sync), ce qui fait échouer la conversion automatique `?` vers
/// anyhow::Error.
fn ort_err<E: std::fmt::Display>(e: E) -> anyhow::Error {
    anyhow::anyhow!("{e}")
}

/// Charge `onnxruntime` dynamiquement depuis le chemin donné (DLL/so/dylib).
///
/// À appeler **une seule fois**, avant toute création de [`SemanticEncoder`]
/// — c'est une initialisation globale au process, pas par instance.
///
/// On charge dynamiquement (plutôt que de lier statiquement à la
/// compilation) pour éviter un conflit de liaison MSVC rencontré sous
/// Windows entre le runtime C++ statique et dynamique (voir commentaires
/// dans `rust/onnx-bench/src/main.rs` pour le détail de l'investigation).
pub fn init_runtime(dylib_path: impl AsRef<Path>) -> Result<()> {
    let path = dylib_path.as_ref();
    if !path.exists() {
        anyhow::bail!("onnxruntime introuvable à {:?}", path);
    }

    let committed = ort::init_from(path.to_string_lossy().to_string())
        .map_err(ort_err)?
        .commit();

    if !committed {
        anyhow::bail!("échec du chargement dynamique de onnxruntime (commit() a retourné false)");
    }

    Ok(())
}

/// Encodeur sémantique — charge un modèle ONNX + son tokenizer, et produit
/// des embeddings de phrase via mean pooling masqué par l'attention_mask.
///
/// `model_dir` doit contenir `model.onnx` et `tokenizer.json` (voir
/// `rust/onnx-bench/fetch_tokenizer.py` pour comment les produire depuis un
/// repo HuggingFace).
pub struct SemanticEncoder {
    session: Session,
    tokenizer: Tokenizer,
}

impl SemanticEncoder {
    pub fn new(model_dir: impl AsRef<Path>) -> Result<Self> {
        let model_dir = model_dir.as_ref();
        let model_path = model_dir.join("model.onnx");
        let tokenizer_path = model_dir.join("tokenizer.json");

        if !model_path.exists() {
            anyhow::bail!("model.onnx introuvable dans {:?}", model_dir);
        }
        if !tokenizer_path.exists() {
            anyhow::bail!("tokenizer.json introuvable dans {:?}", model_dir);
        }

        let tokenizer = Tokenizer::from_file(&tokenizer_path)
            .map_err(|e| anyhow::anyhow!("tokenizer load error: {e}"))?;

        let session = Session::builder()
            .map_err(ort_err)?
            .with_optimization_level(GraphOptimizationLevel::Level3)
            .map_err(ort_err)?
            .commit_from_file(&model_path)
            .map_err(ort_err)?;

        Ok(Self { session, tokenizer })
    }

    /// Encode un lot de textes en embeddings de phrase (mean pooling).
    /// Retourne une matrice [batch, hidden_dim].
    pub fn encode(&mut self, texts: &[&str]) -> Result<Array2<f32>> {
        let encodings = self
            .tokenizer
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
            for j in 0..enc.get_ids().len() {
                token_type_ids[[i, j]] = 0;
            }
        }

        let attention_mask_for_pooling = attention_mask.clone();

        let input_ids_tensor = Tensor::from_array(input_ids).map_err(ort_err)?;
        let attention_mask_tensor = Tensor::from_array(attention_mask).map_err(ort_err)?;
        let token_type_ids_tensor = Tensor::from_array(token_type_ids).map_err(ort_err)?;

        let outputs = self
            .session
            .run(ort::inputs! {
                "input_ids" => input_ids_tensor,
                "attention_mask" => attention_mask_tensor,
                "token_type_ids" => token_type_ids_tensor,
            })
            .map_err(ort_err)?;

        let last_hidden_state = outputs["last_hidden_state"]
            .try_extract_array::<f32>()
            .map_err(ort_err)?;

        Ok(mean_pool(&last_hidden_state, &attention_mask_for_pooling))
    }
}

/// Mean pooling masqué par l'attention_mask — indexation directe (pas de
/// vues/slices intermédiaires) pour éviter tout problème d'emprunt.
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

/// Similarité cosinus entre deux vecteurs d'embedding.
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

#[cfg(test)]
mod tests {
    use super::cosine_similarity;

    #[test]
    fn cosine_similarity_identical_vectors_is_one() {
        let v = vec![0.5, 0.5, 0.5, 0.5];
        assert!((cosine_similarity(&v, &v) - 1.0).abs() < 1e-6);
    }

    #[test]
    fn cosine_similarity_orthogonal_vectors_is_zero() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        assert!(cosine_similarity(&a, &b).abs() < 1e-6);
    }

    #[test]
    fn cosine_similarity_zero_vector_is_zero_not_nan() {
        let a = vec![0.0, 0.0];
        let b = vec![1.0, 1.0];
        assert_eq!(cosine_similarity(&a, &b), 0.0);
    }

    // NOTE : pas de test ici qui charge un vrai modèle ONNX (nécessiterait
    // de committer un modèle dans le repo ou de le télécharger en CI) — les
    // tests d'intégration contre le vrai modèle et le corpus réel sont une
    // case non cochée du HACKATHON_PLAN.md, Axe 1, à faire séparément.
}
