from sentence_transformers import SentenceTransformer
import numpy as np

old_model = SentenceTransformer('Karmelkke/everycli-minilm-ft')
new_model = SentenceTransformer('onnx-bench/models/everycli-minilm-ft-boosted')  # chemin local, déjà patché

query = 'Annuler le dernier commit mais garder les fichiers modifiés'
commands = [
    'git reset --soft HEAD~1',
    'git reset --hard HEAD~1',
    'git stash',
    'git commit --amend'
]

emb_query_old = old_model.encode(query, normalize_embeddings=True)
emb_query_new = new_model.encode(query, normalize_embeddings=True)

print("=== Scores avec l'ancien modèle ===")
for cmd in commands:
    emb_cmd = old_model.encode(cmd, normalize_embeddings=True)
    print(f'  {cmd}: {np.dot(emb_query_old, emb_cmd):.4f}')

print("\n=== Scores avec le nouveau modèle ===")
for cmd in commands:
    emb_cmd = new_model.encode(cmd, normalize_embeddings=True)
    print(f'  {cmd}: {np.dot(emb_query_new, emb_cmd):.4f}')