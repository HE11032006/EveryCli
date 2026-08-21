# How-to : compiler EveryCli depuis les sources

Ce guide est destiné aux développeurs qui souhaitent modifier le code d'EveryCli ou générer leurs propres binaires à partir du dépôt Git.

> Architecture actuelle (branche `reverie-hacks-2026`) : le chemin de recherche rapide (`search`, `add`, `list`, `remove`) est 100% Rust. Seul Sentinel (`plan`, planificateur LLM) reste Python. Voir [CONTRIBUTING.md](../CONTRIBUTING.md) pour la boucle de développement rapide ; ce document couvre la compilation de release complète.

## 1. Compiler le client et le daemon (Rust)

```bash
git clone https://github.com/HE11032006/EveryCli.git
cd EveryCli/rust
cargo build --release -p everycli-rs -p everycli-daemon
```

Ça produit `target/release/everycli-rs(.exe)` et `target/release/everycli-daemon(.exe)`.

## 2. Obtenir le modèle ONNX et le runtime

Le daemon a besoin de trois choses à côté de lui pour tourner :
- `model.onnx` + `tokenizer.json` — le modèle sémantique exporté
- `onnxruntime.dll` (Windows) / `libonnxruntime.so` (Linux) — le runtime d'inférence
- le corpus YAML (`everycli/data/commands/`)

Pour exporter le modèle toi-même (pas nécessaire si tu as déjà ces fichiers) :

```bash
pip install -r requirements.txt --break-system-packages
pip install -r training/requirements-onnx-export.txt --break-system-packages
optimum-cli export onnx --model Karmelkke/everycli-minilm-ft --task feature-extraction --library-name transformers rust/onnx-bench/models/everycli-minilm-ft
cd rust/onnx-bench && python fetch_tokenizer.py && cd ../..
```

Pièges connus documentés en tête de [`training/requirements-onnx-export.txt`](../training/requirements-onnx-export.txt) (notamment un bug de compatibilité `tokenizer_class` selon la version de `transformers`).

Pour `onnxruntime`, télécharge le zip officiel `onnxruntime-{platform}-x64-*` depuis les [releases GitHub de microsoft/onnxruntime](https://github.com/microsoft/onnxruntime/releases/latest), et place la bibliothèque dans `rust/onnx-bench/runtime/`.

## 3. Assembler un dossier de distribution

```bash
# Windows
.\scripts\windows\stage-release.ps1
# Linux
./scripts/linux/stage-release.sh
```

Ça assemble `dist/windows` (ou `dist/linux`) avec la structure exacte attendue par `install.ps1`/`install.sh` : `bin/`, `model/`, `runtime/`, `data/`.

## 4. Tester localement

```bash
cargo run -p everycli-daemon         # terminal 1 -- laisse tourner
cargo run -p everycli-rs -- search "git commit"   # terminal 2
```

Ajoute `--debug` au daemon pour voir les scores lexical/sémantique/hybride séparément par résultat.

## 5. Tester l'installeur

```powershell
.\install.ps1 -LocalSource "dist\windows"
```

Voir [`docs/tutorial_installation.md`](tutorial_installation.md) pour le flux complet côté utilisateur final.

## 6. Dépannage

- **Erreurs de compilation liées à `ort`** : vérifie que la version d'`ort` dans `rust/everycli-inference/Cargo.toml` correspond à celle attendue par `rust/onnx-bench` (elles doivent matcher, y compris la version d'`ndarray` utilisée en interne).
- **Le daemon ne trouve pas le modèle** : vérifie les variables d'environnement `EVERYCLI_MODEL_DIR`, `EVERYCLI_ONNXRUNTIME_DYLIB`, `EVERYCLI_DATA_DIR` (voir [`docs/reference_config.md`](reference_config.md)).
- **Conflit de port au démarrage du daemon** (`os error 10048` / `AddrInUse`) : une autre instance tourne déjà (service Windows ou processus). Le daemon affiche maintenant un message clair dans ce cas plutôt que l'erreur brute — suis les instructions qu'il donne pour l'arrêter.

## Ancien flux PyInstaller (Python, releases v1.1.1 et antérieures)

Pour référence uniquement — ce flux est en cours de remplacement (voir [CHANGELOG.md](../CHANGELOG.md)) :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --break-system-packages
pyinstaller everycli-daemon.spec --clean
```
