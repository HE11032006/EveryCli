# Compiler et tester EveryCli

Ce guide s’adresse aux développeurs qui modifient le code ou produisent un bundle local. Il ne décrit pas une étape nécessaire pour l’utilisateur final : une release précompilée contient déjà les binaires, le modèle et le runtime.

## Pré-requis

Le chemin de recherche rapide utilise Rust. Sentinel, le planificateur LLM, reste Python. Pour travailler sur le daemon et le client :

```bash
rustup toolchain install stable
```

Pour travailler sur Sentinel ou les outils de modèle, installe Python 3 et les dépendances du projet dans un environnement virtuel.

## Compiler les binaires Rust

Depuis la racine du dépôt :

```bash
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
```

Les binaires sont créés dans `rust/target/release/` :

```text
everycli-rs(.exe)
everycli-daemon(.exe)
```

Le binaire doit être compilé pour la plateforme sur laquelle il sera exécuté. Un exécutable Windows n’est pas un exécutable Linux ; le runtime ONNX est également différent selon le système.

## Préparer les artefacts ONNX

Le daemon attend au minimum :

```text
model.onnx
tokenizer.json
```

L’artefact de production est publié dans le dépôt Hugging Face [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx). La CI utilise une révision précise et vérifie les SHA-256 avant de construire les bundles.

Pour une préparation locale, place les fichiers dans :

```text
rust/onnx-bench/models/everycli-minilm-ft/
```

Le dépôt ONNX ne contient pas le runtime natif. Le runtime doit être obtenu séparément pour la plateforme cible :

```text
Windows : runtime/onnxruntime.dll
Linux   : runtime/libonnxruntime.so
```

Le crate `ort 2.0.0-rc.13` utilisé par EveryCli exige une bibliothèque ONNX Runtime native de la série `1.27.x` ou ultérieure. Le workflow épingle actuellement `ONNX Runtime 1.27.0`, qui fournit les archives CPU officielles `onnxruntime-win-x64-1.27.0.zip` et `onnxruntime-linux-x64-1.27.0.tgz`. La version 1.20.1 est incompatible avec le binaire actuel.

Les archives CPU officielles sont disponibles dans les [releases ONNX Runtime](https://github.com/microsoft/onnxruntime/releases). Le workflow CI est la méthode recommandée pour préparer simultanément les bundles Ubuntu et Windows, car chaque job s’exécute sur le système cible.

## Exporter un nouveau modèle

Cette opération n’est pas nécessaire pour une release normale. Elle ne doit être utilisée que lorsqu’un nouveau checkpoint doit être exporté. Les dépendances et les pièges d’export sont documentés dans [`training/requirements-onnx-export.txt`](../training/requirements-onnx-export.txt).

Le pipeline de release ne réexporte pas le modèle de production : il télécharge l’artefact ONNX publié, versionné et hashé. Cela évite de produire silencieusement un fichier différent lors d’un build ultérieur.

## Assembler un staging local

Sous Windows, depuis la racine du dépôt :

```powershell
.\scripts\windows\stage-release.ps1
```

Le script assemble `dist\windows` avec `bin`, `model`, `runtime` et `data`.

Sous Linux :

```bash
./scripts/linux/stage-release.sh
```

Le script assemble `dist/linux`. Il doit être exécuté dans un environnement Linux et nécessite le binaire Linux ainsi que `libonnxruntime.so` Linux.

La structure attendue est :

```text
bundle/
├── bin/
│   ├── everycli(.exe)
│   └── everycli-daemon(.exe)
├── model/
│   ├── model.onnx
│   └── tokenizer.json
├── runtime/
│   ├── onnxruntime.dll       # Windows
│   └── libonnxruntime.so     # Linux
├── data/commands/
├── install.ps1 ou install.sh
└── uninstall.ps1 ou uninstall.sh
```

## Tester un staging local

Windows :

```powershell
.\install.ps1 -LocalSource "dist\windows" -NoService
everycli search "how to undo my last commit"
.\uninstall.ps1
```

Linux :

```bash
./install.sh --local-source "$PWD/dist/linux" --language fr
source ~/.profile
hash -r
everycli search "comment annuler mon dernier commit"
./uninstall.sh
```

Le test Linux doit vérifier le service, le port et la conservation des données personnelles :

```bash
systemctl --user status everycli-daemon.service --no-pager -l
ss -ltn | grep 51821
find "$HOME/.everycli" -maxdepth 3 -type f -print
```

## Tester les crates Rust

Depuis `rust/` :

```bash
cargo test -p everycli-rs
cargo test -p everycli-core
cargo test -p everycli-daemon
```

Le test `everycli-core` couvre notamment le parsing du corpus, la recherche et la découverte du daemon. Le test du daemon couvre le seuil de pertinence.

## Mesurer la qualité de recherche

Depuis la racine du dépôt :

```bash
python tools/evaluate_confusion.py
```

Le benchmark `eval/confusion_set.yaml` contient des requêtes bilingues. L’évaluateur mesure le ranking et n’exécute jamais les commandes retournées. `--matcher lexical` permet de comparer le repli lexical ; `--fail-under` doit être choisi à partir d’une baseline explicitement acceptée.

## CI et releases

Le workflow [`.github/workflows/build.yml`](../.github/workflows/build.yml) :

1. télécharge `model.onnx` et `tokenizer.json` depuis une révision Hugging Face verrouillée ;
2. vérifie leurs SHA-256 ;
3. compile sur Ubuntu, Windows et macOS ;
4. télécharge le runtime natif propre à chaque job ;
5. assemble les archives Linux et Windows ;
6. publie une release et `SHA256SUMS` lorsqu’un tag `v*` est poussé.

Un push vers `main` valide et produit des artefacts CI. Un tag est nécessaire pour activer le job de publication.

L’audit des dépendances s’exécute dans le workspace Rust :

```yaml
working-directory: rust
run: cargo audit
```

## Dépannage développeur

Si le daemon ne trouve pas ses fichiers, vérifie `EVERYCLI_MODEL_DIR`, `EVERYCLI_ONNXRUNTIME_DYLIB`, `EVERYCLI_DATA_DIR` et `EVERYCLI_USER_DATA_DIR` dans [`reference_config.md`](reference_config.md).

Si le port `51821` est déjà utilisé, arrête l’ancien daemon avant de relancer le test. Sous Linux, utilise `systemctl --user stop everycli-daemon.service`. Sous Windows, vérifie le service et le processus `everycli-daemon`.

Si le daemon Linux démarre lentement, attends la fin du premier calcul des embeddings. Le cache peut ensuite accélérer les démarrages suivants.

## Références

- [ONNX Runtime — installation](https://onnxruntime.ai/docs/install/)
- [ONNX Runtime — releases](https://github.com/microsoft/onnxruntime/releases)
- [Artefact ONNX EveryCli](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx)
