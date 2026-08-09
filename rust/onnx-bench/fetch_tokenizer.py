"""
Récupère et sauvegarde les fichiers du tokenizer à côté du model.onnx déjà
exporté (l'export --library-name transformers ne les a pas copiés).

Usage : python fetch_tokenizer.py   (depuis rust/onnx-bench/, venv activé)
"""

from pathlib import Path
from transformers import AutoTokenizer

MODEL_NAME = "Michelhe/everycli-minilm-ft-boosted"
OUTPUT_DIR = Path("models/everycli-minilm-ft")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.save_pretrained(str(OUTPUT_DIR))

# Sanity check : on veut un tokenizer "fast" pour avoir un tokenizer.json
# exploitable directement par le crate Rust `tokenizers`.
is_fast = tokenizer.is_fast
print(f"Tokenizer sauvegardé dans {OUTPUT_DIR} (fast={is_fast})")
if not is_fast:
    print("ATTENTION: tokenizer lent (pas de tokenizer.json) — il faudra une conversion manuelle côté Rust.")

print("\nContenu du dossier :")
for f in sorted(OUTPUT_DIR.iterdir()):
    print(f"  {f.name}")
