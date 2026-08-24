# EveryCli

[English](README.md) · [Français](README.fr.md)

> **Ne cherche plus tes commandes : décris ce que tu veux faire.**

**EveryCli** est un assistant en ligne de commande piloté par le langage naturel. Tu décris ton intention — en français ou en anglais — et l'outil retrouve la commande shell correspondante dans un corpus local. La recherche s'exécute entièrement sur ta machine : un daemon Rust natif combine une correspondance lexicale et un reranking sémantique via ONNX Runtime, sans clé API ni appel réseau. Le passage de l'ancien flux Python/PyInstaller à cette pile Rust native signifie que l'utilisateur final n'a plus besoin de Rust, Cargo ou Python — une archive précompilée suffit.

> 🛟 **La sécurité d'abord.** EveryCli **ne lance jamais** une commande à ta place. Les résultats sont affichés pour que tu les relises ; `--run` demande toujours une confirmation, et les wrappers shell se contentent de placer la commande dans un buffer éditable.

---

## 🌱 Genèse & objectif

EveryCli est né d'une petite friction quotidienne. Chaque fois qu'une commande CLI m'échappait, je la demandais à un LLM en ligne — et chaque recherche imposait deux ou trois secondes d'attente. Dans cet intervalle, l'attention dérive : on bascule vers un autre onglet, une autre tâche, et le fil de ce qu'on faisait est perdu.

L'idée était de garder cette boucle **dans le terminal** — décrire l'intention, obtenir la commande instantanément depuis un corpus *local*, et enrichir petit à petit son **propre** jeu de commandes avec `add` / `list` / `remove`. Pas d'aller-retour, pas de changement de contexte, pas de réseau, et tu gardes toujours le contrôle de ce qui s'exécute vraiment.

EveryCli est par ailleurs antérieur au **hackathon Reverie** : il a été entamé avant le début de l'événement et avait déjà été développé lors de hackathons précédents, mais n'avait jamais été publié — faute de temps pour le finaliser.

> 🕰️ **Historique du projet.** Les changements majeurs avant → après et leur impact sont consignés dans **[CHANGELOG.md](CHANGELOG.md)**.

## 🪧 Public cible

| Public | Ce qu'apporte EveryCli |
|---|---|
| **Développeurs & utilisateurs avancés** | Décrire une intention plutôt que mémoriser des flags ; recherche bilingue FR/EN |
| **Utilisateurs soucieux de confidentialité / hors ligne** | `search` fonctionne 100 % hors ligne — pas de cloud, pas de clé API, pas de télémétrie |
| **Utilisateurs Linux & Windows** | Archives précompilées avec installeurs en une commande ; aucune toolchain requise |
| **Testeurs de release** | Un runbook reproductible d'installation, recherche et désinstallation |
| **Contributeurs & intégrateurs** | Un workspace Rust documenté, un protocole daemon et un contrat shell |

## 🗝️ Fonctionnalités principales

- 🔎 **Recherche en langage naturel** dans un corpus de commandes soigné et rangé par namespace (Git, Docker, Compose, npm, SSH, Python, Linux…).
- 🧬 **Classement hybride local** — correspondance lexicale **+** reranking sémantique (modèle ONNX) fusionnés en un seul score, calculé sur la machine.
- 🌍 **Bilingue** — fonctionne en **français** et en **anglais**, y compris pour des requêtes mixtes.
- 🛰️ **Daemon local** qui garde le modèle en mémoire sur `127.0.0.1:51821` pour des recherches répétées rapides, avec **repli lexical** automatique s'il est indisponible.
- ✍️ **Tes propres commandes** — `add`, `list`, `remove` ; stockées séparément du corpus intégré et conservées à travers les mises à jour.
- 🤝 **Assistance IA optionnelle** — `everycli ask` appelle une API compatible OpenAI pour synthétiser une commande quand le corpus n'a pas de correspondance.
- 🛡️ **Revue avant exécution** — Sentinel (`everycli plan`) propose une revue de sécurité d'une commande récupérée.
- 🐚 **Intégré au shell** — sélecteur interactif, `--json`, `--copy` et un protocole `--shell` déterministe pour les wrappers.
- 📦 **Installation sans dépendances** pour l'utilisateur final — Rust, Cargo et Python ne sont **pas** requis pour une release précompilée.

---

## 🧰 Installation

Les utilisateurs finaux téléchargent une archive de plateforme depuis **[GitHub Releases](https://github.com/HE11032006/EveryCli/releases)**. Aucune toolchain nécessaire.

### 🐧 Linux x86_64

Télécharge `everycli-linux-x86_64.tar.gz`, puis :

```bash
mkdir everycli-linux-x86_64
tar -xzf everycli-linux-x86_64.tar.gz -C everycli-linux-x86_64
cd everycli-linux-x86_64
./install.sh --language fr
```

L'installeur installe le bundle dans `~/.local/share/everycli`, crée les liens dans `~/.local/bin` et active un service `systemd --user`. Recharge ensuite le profil :

```bash
source ~/.profile
everycli search "comment annuler mon dernier commit"
```

> ⏳ Le **premier** démarrage est plus lent : le daemon charge le modèle et calcule les embeddings du corpus (jusqu'à ~3 minutes sur une machine lente ou sous WSL). Les démarrages suivants utilisent un cache disque.

### 🪟 Windows x86_64

Télécharge `everycli-windows-x86_64.zip`, extrais-le, ouvre **PowerShell** dans le dossier et exécute :

```powershell
.\install.ps1 -Language fr
```

L'archive fournit le client, le daemon, `model.onnx`, le tokenizer, `onnxruntime.dll` et le corpus. Utilise `-Version vX.Y.Z` pour laisser le script télécharger une release précise, ou `-NoService` pour éviter l'élévation et utiliser le dossier de démarrage Windows au lieu d'un service.

### 🍎 macOS

macOS est **compilé et testé par la CI**, mais aucune archive macOS installable n'est publiée pour le moment — le runtime natif et l'installeur doivent encore être validés de bout en bout.

📖 **Guide complet :** parcours depuis un bundle, téléchargement par script seul, vérification des checksums, désinstallation et dépannage → **[docs/tutorial_installation.md](docs/tutorial_installation.md)**.

---

## ⌨️ Utilisation quotidienne

La forme générale :

```bash
everycli search "décris ton intention"
```

Options courantes :

```bash
everycli search "requête" --top 3        # nombre de candidats
everycli search "requête" --interactive  # choisir au clavier (-i)
everycli search "requête" --copy         # copier le résultat choisi
everycli search "requête" --run          # exécuter — demande confirmation
everycli search "requête" --json         # sortie exploitable par une machine
everycli search "requête" --no-daemon    # forcer le repli lexical local
```

Le mode interactif affiche les candidats proches et te laisse choisir ; `--copy` et `--run` ciblent un résultat explicite, et `--run` confirme avant d'exécuter.

**Gérer tes propres commandes :**

```bash
everycli add
everycli list
everycli remove
```

Les commandes personnelles vivent dans `~/.everycli/commands` (Linux) ou `%USERPROFILE%\.everycli\commands` (Windows). Elles sont séparées du corpus intégré et survivent à une mise à jour ou une désinstallation normale.

---

## 🛰️ `everycli ask` & 🛡️ Sentinel

`search` est le chemin **local** principal — corpus + daemon Rust, sans clé API. Deux compagnons optionnels existent :

- **`everycli ask`** appelle une **API compatible OpenAI** pour proposer une commande, une explication, un avertissement et des tags, puis propose de l'enregistrer dans ton corpus personnel. Ce n'est *pas* le classement local de `search`.
- **Sentinel** (`everycli plan`) est un planificateur **Python** séparé qui effectue une revue d'une commande déjà récupérée. Il n'exécute jamais de shell à ta place.

Configure une clé (protégée, `0600` sous Unix) :

```bash
everycli config set api_key "ta-cle-api"
everycli config show           # n'affiche jamais la clé complète
everycli ask "compresser le dossier courant"
```

La clé peut aussi venir de `EVERYCLI_API_KEY`. Les préfixes connus sont auto-détectés, ou fixe un fournisseur explicitement (`everycli config set provider openai`, plus `api_url` / `api_model` pour les endpoints compatibles OpenAI). Sans clé, `ask` affiche une erreur de configuration tandis que `search` continue de fonctionner hors ligne.

## 🎛️ Configuration

EveryCli est piloté par quelques variables d'environnement et un fichier `~/.everycli/config.toml`. L'essentiel :

| Variable | Rôle | Défaut de dev |
|---|---|---|
| `EVERYCLI_PORT` | Port TCP du daemon | `51821` |
| `EVERYCLI_MODEL_DIR` | Dossier de `model.onnx` + `tokenizer.json` | dossier du modèle |
| `EVERYCLI_ONNXRUNTIME_DYLIB` | Bibliothèque ONNX Runtime native | `.dll` / `.so` selon l'OS |
| `EVERYCLI_DATA_DIR` | Corpus YAML intégré | corpus fourni |
| `EVERYCLI_USER_DATA_DIR` | Corpus YAML personnel | `~/.everycli/commands` |
| `EVERYCLI_API_KEY` | Clé pour `everycli ask` | *non défini* |

Les installeurs remplacent les défauts de dev par des chemins absolus. Une entrée de corpus est un enregistrement YAML avec `id`, `description`, `tags`, des `commands` par plateforme, une `explanation` et un `warning` optionnel.

📖 **Référence complète :** toutes les variables, les chemins de données, le schéma du corpus et le protocole JSON du daemon → **[docs/reference_config.md](docs/reference_config.md)**.

---

## 🧬 Architecture en bref

```text
Utilisateur
    │
    ▼
everycli-rs  ── JSON/TCP localhost ──▶  everycli-daemon
    │                                      ├── corpus YAML
    │                                      ├── model.onnx
    │                                      ├── tokenizer.json
    │                                      └── ONNX Runtime natif
    └── repli lexical local si le daemon est indisponible
```

Le daemon garde le modèle en mémoire et répond à `ping`, `search` et `reload` sur `127.0.0.1:51821` — ce n'est **pas** une API réseau publique. Le score hybride est calibré empiriquement : **lexical `0.45`**, **sémantique `0.55`**, **bonus de namespace `+0.2`** (une route douce, pas un filtre dur), avec un **seuil minimal de pertinence de `0.50`** pour rejeter les requêtes hors sujet. Le chemin de recherche rapide est natif Rust ; Sentinel reste un composant Python séparé.

📖 **Plongée détaillée :** composants, pourquoi un daemon, protocole, modèle & runtime, corpus → **[docs/explanation_architecture.md](docs/explanation_architecture.md)**.

## 🐚 Intégration shell

EveryCli sépare l'interface humaine du protocole des wrappers pour qu'une commande ne soit jamais exécutée par surprise. Le mode `--shell` (`-s`) écrit **uniquement** la commande résolue sur `stdout` (sans newline final), envoie les diagnostics sur `stderr`, et **n'exécute rien** — idéal pour les wrappers Bash/Zsh/PowerShell qui placent la commande dans un buffer éditable.

```bash
everycli search "annuler mon dernier commit" --shell
```

Pour rester déterministe, `--shell` ne se combine pas avec `-i`, `--run`, `--copy`, `--error` ou `--top` > 1.

📖 **Guide complet :** mode interactif, wrappers Bash/Zsh/PowerShell, règles de sécurité d'exécution → **[docs/shell_integration.md](docs/shell_integration.md)**.

## ⚗️ Build & tests

Pour une release précompilée tu n'en as pas besoin — cette partie s'adresse aux développeurs qui construisent un bundle local.

```bash
# Binaires Rust
cd rust
cargo build --release -p everycli-rs -p everycli-daemon

# Tests ciblés
cargo test -p everycli-rs
cargo test -p everycli-core
cargo test -p everycli-daemon
```

L'artefact ONNX de production vit dans [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx) ; la CI fige une révision et vérifie les SHA-256. Le crate `ort 2.0.0-rc.13` exige une bibliothèque **ONNX Runtime 1.27.x+** native (le workflow épingle 1.27.0).

📖 **Guide complet :** artefacts ONNX, runtime natif, staging local, flux CI/release → **[docs/how_to_build.md](docs/how_to_build.md)**.

## 📐 Benchmarks & validation

Les mesures sont des observations de développement, pas des garanties universelles. Sur l'ensemble bilingue `eval/confusion_set.yaml`, le résultat de ranking enregistré est de **58/66 requêtes (87,9 %)**. Une baseline de latence Windows indicative : **~383 ms** pour une recherche complète via daemon contre **~33 ms** pour le repli lexical local (un premier chargement à froid est bien plus lent).

```bash
python tools/evaluate_confusion.py                    # chemin hybride
python tools/evaluate_confusion.py --matcher lexical  # lexical seul
```

📖 **Guide complet :** règles de mesure, validation des bundles, contrôles CI, rapports de régression → **[docs/benchmarking.md](docs/benchmarking.md)**.

---

## 🗺️ Statut & feuille de route

| Domaine | Statut vérifié |
|---|---|
| Client Rust, daemon Rust et recherche hybride | ✔️ Disponible |
| Modèle `model.onnx` et tokenizer distribuables | ✔️ Dans les bundles CI validés |
| Installation Windows depuis un bundle complet | ✔️ Vérifiée de bout en bout |
| Installation Linux depuis un bundle complet | ✔️ Vérifiée sous WSL (service, recherche, désinstallation) |
| CI Ubuntu & Windows | ✔️ Bundles complets avec checksums de modèle |
| macOS | 🔧 Compilation/tests CI ; pas encore d'installeur ni d'archive publique |
| Quantification du modèle | 🔭 À étudier (le modèle actuel est float32 et volumineux) |
| Index ANN pour très grands corpus | 🔭 À étudier |

Voir **[CHANGELOG.md](CHANGELOG.md)** pour l'historique factuel des changements et les mesures.

## 🗂️ Documentation

| Document | Pour qui ? | Contenu |
|---|---|---|
| [Tutoriel d'installation](docs/tutorial_installation.md) | Utilisateurs & testeurs | Installation, usage, désinstallation, dépannage |
| [Architecture](docs/explanation_architecture.md) | Développeurs curieux | Client, daemon, modèle, scoring, cycle de vie |
| [Build & tests](docs/how_to_build.md) | Développeurs | Compilation Rust, artefacts ONNX, staging, validation |
| [Référence de configuration](docs/reference_config.md) | Intégrateurs | Variables, chemins, schéma YAML, protocole daemon |
| [Intégration shell](docs/shell_integration.md) | Utilisateurs avancés | Protocole `--shell`, wrappers, sécurité d'exécution |
| [Benchmarks & validation](docs/benchmarking.md) | Développeurs | Tests, benchmark de ranking, latence, CI |
| [Guide Linux de validation](LINUX_TEST_GUIDE.md) | Testeurs de release | Runbook installation/recherche/désinstallation Linux |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributeurs | Setup, tests, règles de contribution |
| [CHANGELOG.md](CHANGELOG.md) | Lecteurs techniques | Historique factuel des changements |

## 🗄️ Structure du dépôt

```text
EveryCli/
├── everycli/                   # Composant Python Sentinel et données historiques
│   └── data/commands/          # Corpus YAML intégré
├── rust/
│   ├── everycli-core/          # Corpus et recherche lexicale
│   ├── everycli-inference/     # Encodeur sémantique ONNX Runtime
│   ├── everycli-daemon/        # Serveur local TCP
│   └── everycli-rs/            # Client CLI Rust
├── docs/                       # Guides techniques autonomes
├── scripts/                    # Scripts de staging par plateforme
├── install.sh / install.ps1    # Installeurs Linux / Windows
├── uninstall.sh / uninstall.ps1
└── .github/workflows/build.yml # Tests, builds et bundles CI
```

## 📜 Licence

Le code est distribué sous licence **MIT** ; la documentation sous licence **Creative Commons**. Voir [LICENSE.md](LICENSE.md).

---

<div align="center"><sub>EveryCli — pour les développeurs qui préfèrent décrire une intention plutôt que mémoriser des flags.</sub></div>
