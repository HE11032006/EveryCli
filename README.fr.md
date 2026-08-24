# EveryCli

[English](README.md) · [Français](README.fr.md)

> **Ne cherche plus tes commandes : décris ce que tu veux faire.**

**EveryCli** est un assistant en ligne de commande piloté par le langage naturel. Tu décris ton intention — en français ou en anglais — et l'outil retrouve la commande shell correspondante dans un corpus local. La recherche s'exécute entièrement sur ta machine : un daemon Rust natif combine une correspondance lexicale et un reranking sémantique via ONNX Runtime, sans clé API ni appel réseau. Le passage de l'ancien flux Python/PyInstaller à cette pile Rust native signifie que l'utilisateur final n'a plus besoin de Rust, Cargo ou Python — une archive précompilée suffit.

> 🛟 **La sécurité d'abord.** EveryCli **ne lance jamais** une commande à ta place. Les résultats sont affichés pour que tu les relises ; `--run` demande toujours une confirmation, et les wrappers shell se contentent de placer la commande dans un buffer éditable.

---

## 🌱 Genèse & objectif

EveryCli est né d'une petite friction quotidienne. Chaque fois qu'une commande CLI m'échappait, je la demandais à un LLM en ligne — et chaque recherche ajoutait souvent deux ou trois secondes d'attente. Ce délai paraît court, mais il suffit parfois à sortir du contexte : on change d'onglet, on commence une autre tâche, puis il faut reconstruire mentalement ce qu'on était en train de faire. Dans les interfaces numériques, l'attention ne se partage pas sans coût ; le changement rapide de tâche augmente la charge de reprise et le risque de perdre le fil [1].

L'idée était donc de garder cette boucle **dans le terminal** — décrire l'intention, obtenir rapidement une commande depuis un corpus *local*, puis enrichir progressivement son **propre** jeu de commandes avec `add` / `list` / `remove`. Le choix n'est pas de remplacer un grand modèle distant par un modèle local prétendument supérieur : c'est d'accepter un modèle plus compact et un périmètre maîtrisé pour réduire la latence, préserver le contexte et éviter un détour vers un autre onglet. Quand la couverture locale ne suffit pas, `everycli ask` reste disponible comme aide LLM optionnelle. L'objectif est simple : moins d'attente, moins de changement de contexte et toujours le contrôle de ce qui s'exécute réellement [1].

> **Un modèle suffisamment rapide et disponible localement peut être plus utile, dans ce contexte, qu'un modèle plus lourd qui impose un aller-retour et une rupture d'attention.**

[1]: https://www.nngroup.com/articles/serial-task-switching/ "Nielsen Norman Group — Serial Task Switching"

## 🪧 Public cible

| Public | Ce qu'apporte EveryCli |
|---|---|
| **Développeurs & utilisateurs avancés** | Décrire une intention plutôt que mémoriser des flags ; recherche bilingue FR/EN |
| **Utilisateurs soucieux de confidentialité / hors ligne** | `search` fonctionne 100 % hors ligne — pas de cloud, pas de clé API, pas de télémétrie |
| **Utilisateurs Linux & Windows** | Archives précompilées avec installeurs en une commande ; aucune toolchain requise |
| **Testeurs de release** | Un runbook reproductible d'installation, recherche et désinstallation |
| **Contributeurs & intégrateurs** | Un workspace Rust documenté, un protocole daemon et un contrat shell |

## 🧬 Architecture avant tout

EveryCli sépare l'interface utilisateur du calcul sémantique plus coûteux. Le client Rust reçoit ton intention et communique avec un daemon local, qui garde le modèle en mémoire et répond rapidement aux recherches. Cette séparation évite de recharger le modèle à chaque commande et permet de rester dans le terminal, aussi bien sous Ubuntu/Linux que sous Windows.

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

Le daemon écoute uniquement sur `127.0.0.1:51821` : ce n'est pas une API réseau publique. Il combine le corpus YAML, le modèle ONNX et le runtime natif de la plateforme. Le client conserve également un repli lexical local afin que la recherche reste utile même si le daemon n'est pas disponible.

📖 **Architecture détaillée :** composants, rôle du daemon, protocole, modèle, runtime, corpus et cycle de vie → **[docs/explanation_architecture.md](docs/explanation_architecture.md)**.

## 🗝️ Fonctionnalités principales

- 🔎 **Recherche en langage naturel** — décris ce que tu veux faire au lieu de mémoriser la syntaxe, dans un corpus organisé par namespace (Git, Docker, Compose, npm, SSH, Python, Linux…).
- 🧬 **Classement hybride local** — la correspondance lexicale et le reranking sémantique ONNX sont fusionnés sur ta machine pour rapprocher les commandes réellement pertinentes, sans envoyer ta requête dans le cloud.
- 🌍 **Recherche bilingue** — formule ta demande en français, en anglais ou dans une requête mixte, ce qui évite de devoir traduire mentalement une commande ou sa description.
- 🛰️ **Daemon local rapide** — le modèle reste chargé sur `127.0.0.1:51821`, ce qui permet aux recherches répétées de répondre en quelques centaines de millisecondes après le premier chargement ; cet ordre de grandeur a été observé sur le matériel testé et le même daemon natif est prévu pour Ubuntu/Linux comme pour Windows, afin de rester dans le rythme de travail au lieu d'attendre une requête distante.
- ✍️ **Possibilité d'ajouter tes propres commandes** — avec `add`, `list` et `remove`, tu construis progressivement ton corpus personnel ; tes fichiers restent séparés du corpus intégré et sont conservés lors des mises à jour.
- 🤝 **Assistance IA optionnelle** — si aucune commande locale ne correspond suffisamment, `everycli ask` permet de demander une proposition à une API compatible OpenAI, puis de l'ajouter à ton corpus pour éviter de refaire plus tard une requête distante pour le même besoin.
- 🛡️ **Revue avant exécution** — Sentinel (`everycli plan`) peut relire une commande récupérée et signaler les risques avant que tu décides de l'exécuter.
- 🐚 **Intégration au shell** — le sélecteur interactif, `--json`, `--copy` et le protocole `--shell` permettent de passer d'une recherche humaine à un usage scriptable, sans exécution automatique.
- 📦 **Installation sans dépendances de développement** — une release précompilée contient les binaires, le modèle, le tokenizer, le runtime et le corpus ; l'utilisateur final n'a besoin ni de Rust, ni de Cargo, ni de Python.

---

## 🧰 Installation

Le moyen le plus simple est d'utiliser l'installeur directement depuis la branche `main`. Il télécharge la dernière release, vérifie son intégrité et configure automatiquement le client, le daemon, le modèle, le runtime, le corpus et le démarrage en arrière-plan. Rust, Cargo et Python ne sont pas nécessaires.

> ⚠️ Utilise la prochaine release corrigée **v1.2.1 ou ultérieure**. La release publique `v1.2.0` a été publiée avec une bibliothèque ONNX Runtime trop ancienne pour la version du crate `ort` utilisée par le daemon ; elle ne doit pas être présentée comme une installation sémantique fonctionnelle.

### 🐧 Ubuntu/Linux x86_64 — installation rapide

```bash
curl -fsSL https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.sh | bash
```

L'installeur demande la langue, installe EveryCli dans `~/.local/share/everycli`, crée les liens dans `~/.local/bin` et configure le service `systemd --user`. À la fin, recharge ton profil :

```bash
source ~/.profile
everycli search "comment annuler mon dernier commit"
```

Si `everycli` n'est pas encore reconnu, ouvre simplement un nouveau terminal. Le premier démarrage peut être plus lent : le daemon charge le modèle et calcule les embeddings du corpus. Les recherches suivantes profitent du daemon déjà chargé et du cache disque.

### 🪟 Windows x86_64 — installation rapide

Dans **PowerShell**, exécute :

```powershell
irm https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.ps1 | iex
```

L'installeur demande la langue, télécharge la release, vérifie son intégrité et configure EveryCli dans ton profil utilisateur. Ce premier parcours peut être un peu lent, notamment pendant le téléchargement et le premier chargement du modèle. Un nouveau terminal peut être nécessaire pour que la commande `everycli` soit disponible.

### 📦 Installation depuis une archive téléchargée

Pour inspecter les fichiers avant installation, télécharge l'archive correspondante depuis **[GitHub Releases](https://github.com/HE11032006/EveryCli/releases)**, puis lance l'installeur sans argument depuis le dossier extrait.

Sous Ubuntu/Linux :

```bash
mkdir everycli-linux-x86_64
tar -xzf everycli-linux-x86_64.tar.gz -C everycli-linux-x86_64
cd everycli-linux-x86_64
./install.sh
source ~/.profile
```

Sous Windows PowerShell :

```powershell
Expand-Archive .\everycli-windows-x86_64.zip .\everycli-windows-x86_64
cd .\everycli-windows-x86_64
.\install.ps1
```

L'archive complète contient le client, le daemon, `model.onnx`, `tokenizer.json`, la bibliothèque ONNX Runtime native et le corpus. Pour la désinstallation, utilise `./uninstall.sh` sous Linux ou `./uninstall.ps1` sous Windows ; les données personnelles sont conservées par défaut.

### 🍎 macOS

macOS est **compilé et testé par la CI**, mais aucune archive macOS installable n'est publiée pour le moment — le runtime natif et l'installeur doivent encore être validés de bout en bout.

📖 **Guide complet :** prérequis, installation en une commande, installation depuis une archive, vérification des checksums, désinstallation et dépannage → **[docs/tutorial_installation.md](docs/tutorial_installation.md)**.

---

## ⌨️ Utilisation quotidienne

La commande la plus utile au quotidien est le parcours interactif suivant :

```bash
everycli search "annuler mon dernier commit" --top 2 -i
```

> ⭐ **Parcours recommandé.** `--top 2` limite l'affichage aux deux candidats les plus pertinents et `-i` ouvre le choix interactif. Après ta sélection, tu peux récupérer la commande choisie et la copier, au lieu de devoir parcourir une liste de résultats qui peut en afficher deux ou trois sans activer ce parcours.

La forme simple reste disponible :

```bash
everycli search "décris ton intention"
```

Options courantes :

```bash
everycli search "requête" --top 3        # nombre maximal de candidats
everycli search "requête" -i             # choisir au clavier
everycli search "requête" --copy         # copier le résultat choisi
everycli search "requête" --run          # exécuter après confirmation
everycli search "requête" --json         # sortie exploitable par une machine
everycli search "requête" --no-daemon    # forcer le repli lexical local
```

Le mode interactif te laisse relire les candidats avant de choisir. EveryCli ne lance jamais une commande sans confirmation explicite.

**Ajouter et entretenir tes propres commandes :**

```bash
everycli add
everycli list
everycli remove
```

Tu peux ainsi transformer une commande trouvée une seule fois en raccourci local réutilisable. Les commandes personnelles vivent dans `~/.everycli/commands` (Linux) ou `%USERPROFILE%\.everycli\commands` (Windows), séparées du corpus intégré et conservées lors d'une mise à jour ou d'une désinstallation normale.

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

## 📬 Contact & support

| Ressource | Lien |
|---|---|
| **Website** |  |
| **Support** |  |

## 📜 Licence

Le code est distribué sous licence **MIT** ; la documentation sous licence **Creative Commons**. Voir [LICENSE.md](LICENSE.md).

---

<div align="center"><sub>EveryCli — pour les développeurs qui préfèrent décrire une intention plutôt que mémoriser des flags.</sub></div>
