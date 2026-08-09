"""
Baseline de comparaison : mesure le temps d'inférence du chemin Python actuel
(sentence-transformers), dans les mêmes conditions que onnx-bench (modèle déjà
chargé, warmup fait, 1 requête à la fois) — pour une comparaison honnête.

Usage : python bench.py   (depuis rust/onnx-bench/python_baseline/, avec le
venv du projet activé)
"""

import time

from sentence_transformers import SentenceTransformer

MODEL_NAME = "Michelhe/everycli-minilm-ft-boosted"
ITERATIONS = 200
QUERY = "comment annuler mon dernier commit"

print("Chargement du modèle...")
t0 = time.perf_counter()
model = SentenceTransformer(MODEL_NAME)
print(f"Modèle chargé en {time.perf_counter() - t0:.3f}s")

print("Warmup...")
model.encode([QUERY], convert_to_numpy=True, show_progress_bar=False)

print(f"Benchmark ({ITERATIONS} itérations, 1 requête à la fois)...")
t0 = time.perf_counter()
for _ in range(ITERATIONS):
    model.encode([QUERY], convert_to_numpy=True, show_progress_bar=False)
elapsed = time.perf_counter() - t0

print(f"Total: {elapsed:.3f}s | Moyenne par requête: {elapsed / ITERATIONS * 1000:.2f}ms")
