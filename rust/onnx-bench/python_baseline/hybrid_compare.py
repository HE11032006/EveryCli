"""
Calcule le score hybride (lexical + sémantique) en Python pour comparer avec Rust.
Usage : python hybrid_compare.py
"""

import time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "Michelhe/everycli-minilm-ft-boosted"

# Requête et commande de référence
QUERY = "Je veux mettre mon travail de côté sans faire de commit"
COMMAND = "git stash"

# Poids utilisés par le daemon Rust
WEIGHT_LEXICAL = 0.35
WEIGHT_SEMANTIC = 0.65

def lexical_score(query: str, command: str) -> float:
    """Calcule un score lexical simple (similarité de tokens)."""
    query_tokens = set(query.lower().split())
    command_tokens = set(command.lower().split())
    if not query_tokens or not command_tokens:
        return 0.0
    overlap = len(query_tokens & command_tokens)
    total = len(query_tokens) + len(command_tokens)
    return (2 * overlap) / total if total > 0 else 0.0

print("Chargement du modèle sentence-transformers...")
t0 = time.perf_counter()
model = SentenceTransformer(MODEL_NAME)
print(f"Modèle chargé en {time.perf_counter() - t0:.3f}s")

print("Génération des embeddings...")
embeddings = model.encode([QUERY, COMMAND], convert_to_tensor=True, normalize_embeddings=True)

# Similarité cosinus sémantique
semantic_score = float(np.dot(embeddings[0], embeddings[1]))

# Score lexical (approximatif)
lex_score = lexical_score(QUERY, COMMAND)

# Score hybride (avec les mêmes poids que le daemon Rust)
hybrid_score = (WEIGHT_LEXICAL * lex_score) + (WEIGHT_SEMANTIC * semantic_score)

print(f"\n=== Résultats ===")
print(f"Requête : {QUERY}")
print(f"Commande : {COMMAND}")
print(f"Score lexical : {lex_score:.6f}")
print(f"Score sémantique (cosinus) : {semantic_score:.6f}")
print(f"Score hybride (0.35 lexical + 0.65 sémantique) : {hybrid_score:.6f}")