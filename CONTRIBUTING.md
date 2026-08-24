# Contribuer à EveryCli

Merci de contribuer à EveryCli. Ce document s’adresse aux personnes qui veulent modifier le code, ajouter des scénarios YAML, améliorer la recherche ou corriger la documentation. Il ne décrit pas l’installation utilisateur finale ; consulte [`docs/tutorial_installation.md`](docs/tutorial_installation.md) pour cela.

## Avant de commencer

Les zones principales du projet sont :

```text
Rust       → client, corpus, recherche, inference et daemon
Python     → Sentinel et outils associés
YAML       → corpus de commandes intégré
CI         → tests, audit, compilation et bundles de release
```

Lis d’abord les documents adaptés à ton changement :

| Changement | Document |
|---|---|
| Installation ou désinstallation | [`docs/tutorial_installation.md`](docs/tutorial_installation.md) |
| Architecture client/daemon | [`docs/explanation_architecture.md`](docs/explanation_architecture.md) |
| Build, staging et CI | [`docs/how_to_build.md`](docs/how_to_build.md) |
| Variables et protocole | [`docs/reference_config.md`](docs/reference_config.md) |
| Wrappers shell | [`docs/shell_integration.md`](docs/shell_integration.md) |
| Mesures et validation | [`docs/benchmarking.md`](docs/benchmarking.md) |

## Setup Rust

Installe Rust stable avec `rustup`, puis compile depuis le workspace :

```bash
rustup toolchain install stable
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
```

Les tests unitaires du chemin Rust se lancent ainsi :

```bash
cargo test -p everycli-rs
cargo test -p everycli-core
cargo test -p everycli-daemon
```

Le daemon local a besoin de `model.onnx`, `tokenizer.json`, du runtime natif ONNX Runtime et du corpus. Pour un développement courant, récupère les artefacts décrits dans [`docs/how_to_build.md`](docs/how_to_build.md). Ne committe pas les gros artefacts générés localement.

## Setup Python et Sentinel

Sentinel est séparé du chemin rapide Rust. Installe ses dépendances dans un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Teste le planificateur avec :

```bash
python -m everycli.everycli plan "supprimer les images Docker inutilisées en sécurité"
```

### Tester `everycli ask`

`everycli ask` appartient au client Rust, mais son chemin est distinct de `search` : il appelle une API compatible OpenAI et nécessite une clé API. `search`, `add`, `list` et `remove` restent utilisables sans cette clé.

Pour tester `ask` sans exposer une clé dans le dépôt :

```bash
everycli config set api_key "ta-cle-api"
everycli config show
everycli ask "compresser le dossier courant"
```

La clé peut aussi être injectée temporairement par l’environnement :

```bash
EVERYCLI_API_KEY="ta-cle-api" everycli ask "lister les fichiers"
```

Le client peut auto-détecter certains fournisseurs à partir du préfixe de clé. Pour un fournisseur compatible OpenAI, configure explicitement `provider`, `api_url` et `api_model` si nécessaire. `ask` affiche une proposition structurée, une explication, un avertissement éventuel et demande avant d’enregistrer le résultat dans le corpus personnel. Le test ne doit jamais utiliser une clé réelle dans une issue ou une sortie publique.

La configuration de `ask` est différente de celle du planificateur Python Sentinel. Sentinel utilise le chemin Python et peut utiliser `OPENAI_API_KEY` pour sa planification ; `ask` utilise `EVERYCLI_API_KEY` ou `~/.everycli/config.toml`.

Les dépendances d’export ONNX sont distinctes et ne sont nécessaires que pour réexporter un modèle :

```bash
python -m pip install -r training/requirements-onnx-export.txt
```

L’artefact ONNX de production est versionné hors du dépôt Git dans [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx). Une modification du modèle doit donc documenter sa révision et son hash.

## Ajouter un scénario YAML

Le corpus intégré se trouve dans `everycli/data/commands/`. Chaque entrée doit avoir un identifiant unique, une description utile pour la recherche, des tags et au moins une commande pour la plateforme concernée :

```yaml
- id: git_undo_last_commit_keep_changes
  description: Annuler le dernier commit en gardant les changements
  tags: [git, commit, undo, reset]
  commands:
    linux: "git reset --soft HEAD~1"
    windows: "git reset --soft HEAD~1"
    macos: "git reset --soft HEAD~1"
  explanation: Retire le commit mais conserve les fichiers en staging.
  warning: Vérifier l’état du dépôt avant d’utiliser la commande.
```

Le nom du fichier fournit le namespace. Les explications multi-lignes doivent utiliser un scalaire YAML en bloc `|`. Les commandes potentiellement destructrices doivent avoir un avertissement explicite.

`everycli add` écrit dans `~/.everycli/commands`, ce qui est utile pour tester personnellement une entrée. Pour contribuer au corpus intégré, transfère ensuite l’entrée validée vers `everycli/data/commands/` dans un changement dédié.

## Modifier le moteur de recherche

Le matcher lexical et le parsing du corpus se trouvent dans `rust/everycli-core`. Le reranking sémantique se trouve dans `rust/everycli-inference`. Le daemon combine les résultats dans `rust/everycli-daemon` et le client dans `rust/everycli-rs`.

Pour diagnostiquer un classement :

```bash
everycli search "ta requête" --debug --top 3
```

Compare les modifications avec `eval/confusion_set.yaml`. Le benchmark ne doit jamais exécuter les commandes retournées.

## Modifier les installeurs ou le packaging

Les scripts de staging sont spécifiques à la plateforme :

```text
scripts/windows/stage-release.ps1
scripts/linux/stage-release.sh
```

Un bundle complet doit contenir les binaires compilés, le modèle, le tokenizer, le runtime natif, le corpus et l’installeur/désinstalleur. Toute modification du workflow doit être testée sur les jobs concernés ; un changement Linux ne peut pas être considéré comme validé uniquement parce qu’il compile sous Windows.

Les commits ne doivent pas inclure de secrets, de caches d’embeddings ou de gros binaires locaux. Le modèle de production est géré via le dépôt Hugging Face versionné et les bundles CI.

## Vérifications avant une pull request

Depuis `rust/`, exécute les tests ciblés correspondant à ton changement, puis l’ensemble des tests :

```bash
cargo test -p everycli-rs
cargo test -p everycli-core
cargo test -p everycli-daemon
```

Depuis la racine, mesure le benchmark si la recherche a changé :

```bash
python tools/evaluate_confusion.py
```

Pour les scripts shell, vérifie la syntaxe sur Linux :

```bash
bash -n install.sh uninstall.sh scripts/linux/stage-release.sh
```

Pour les scripts PowerShell, utilise une vérification de parsing sur Windows sans lancer l’installation. Teste ensuite le bundle dans un environnement propre lorsque le changement concerne la distribution.

## Style et limites

Les changements doivent rester ciblés et conserver la séparation client/daemon. Ajoute ou mets à jour un test lorsque tu corriges un comportement observable. Ne supprime pas un test en échec pour faire passer la CI.

Demande une revue avant de modifier le schéma de données, le protocole daemon, le workflow de release, les dépendances ou la politique de sécurité. Ne committe jamais de clé API, de certificat, de fichier `.env`, de modèle local ou de cache généré.

## Pull requests et commits

Une pull request doit expliquer le problème, le changement, les commandes de vérification exécutées et les limites restantes. Les résultats non vérifiés doivent être présentés comme tels.

Les commits doivent rester atomiques et descriptifs. La branche principale ne doit recevoir que des changements dont la CI correspondante est verte. Les releases sont déclenchées par un tag `v*` après validation du commit intégré dans `main`.

## Signaler un bug

Ouvre une issue avec le système d’exploitation, la version de release ou le commit, les commandes exécutées, la sortie complète et les logs pertinents. Retire les secrets et les données personnelles avant de publier les logs.

## Code de conduite

Les contributions doivent respecter le [Code of Conduct](CODE_OF_CONDUCT.md) du projet.
