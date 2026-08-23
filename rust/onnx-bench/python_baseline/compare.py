"""
Compare les scores de similarité cosinus entre Python (sentence-transformers) et Rust (ONNX).
Usage : python compare.py
"""

import time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "Michelhe/everycli-minilm-ft-boosted"

# Requête et commande de référence
QUERY = "Je veux mettre mon travail de côté sans faire de commit"
COMMAND = "git stash"  # La commande attendue

print("Chargement du modèle...")
t0 = time.perf_counter()
model = SentenceTransformer(MODEL_NAME)
print(f"Modèle chargé en {time.perf_counter() - t0:.3f}s")

print("Génération des embeddings...")
# Encoder la requête et la commande
embeddings = model.encode([QUERY, COMMAND], convert_to_tensor=True, normalize_embeddings=True)

# Similarité cosinus (car normalize_embeddings=True, c'est un produit scalaire)
cos_sim = np.dot(embeddings[0], embeddings[1])

print(f"\n=== Résultats ===")
print(f"Requête : {QUERY}")
print(f"Commande : {COMMAND}")
print(f"Similarité cosinus (sentence-transformers) : {cos_sim:.6f}")