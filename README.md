🇬🇧 English | [🇫🇷 Français](README.fr.md)

# 🚀 EveryCli

**Don't look for your commands, describe them.**

EveryCli is an intelligent command-line assistant that uses AI to instantly find the exact command you need, even if you don't know its syntax.

EveryCli now also includes **Sentinel**: a review-first command planner. It
turns an intent into a corpus-grounded command, a risk level, and checks to
complete before you run anything. It never executes a command for you.

![License](https://img.shields.io/github/license/HE11032006/EveryCli)
![Build Status](https://img.shields.io/github/actions/workflow/status/HE11032006/EveryCli/build.yml)

## 🚀 Before / After: Reverie Hacks 2026

> Voir [CHANGELOG.md](CHANGELOG.md) pour le détail complet. Statuts marqués "en cours" vérifiés partiellement seulement.

| Aspect | Avant (v1.1.1) | Après (branche `reverie-hacks-2026`) |
|---|---|---|
| Architecture du daemon | Python + PyInstaller, hang non résolu au démarrage sur Windows | 100% Rust + ONNX Runtime, aucun hang observé, démarrage ~1.6s |
| Vitesse d'inférence | ~21.6ms/requête | ~12.5ms/requête (mesuré, single-thread) |
| Installation Windows | Téléchargement manuel, renommage d'exe, config PATH manuelle | `install.ps1` en une commande, vérifié de bout en bout |
| Installation Linux | Manuelle | `install.sh` écrit, vérification en cours (WSL) |
| Installation macOS | Manuelle | Pas encore commencé |
| Persistance du daemon | Lancement manuel, bloque le terminal, ne survit pas à un reboot | Démarre automatiquement à l'ouverture de session, détaché |
| Commandes personnalisées | Aucune | `everycli add`, jamais écrasées par une mise à jour |
| Désambiguïsation | Question bloquante forcée | Affichage informatif, l'utilisateur choisit en lisant |
| Qualité du ranking | Non mesurée objectivement | 87.9% sur `confusion_set.yaml` (66 requêtes), reproductible |

---

## Contents

- [Getting started](#-getting-started)
- [Overview](#-overview)
- [Directory Structure](#directory-structure)
- [Status & Roadmap](#-status--roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✈️ Getting started

> **Note (branch `reverie-hacks-2026`)**: EveryCli's daemon has moved from a Python/PyInstaller architecture to a native Rust + ONNX Runtime one — see [CHANGELOG.md](CHANGELOG.md) for why and what changed. No public GitHub release ships these new binaries yet, so for now the install scripts work from a local build. The download-based Full/Lite/Rust flow further down still describes the previous release (`v1.1.1`).

### 🪟 Install (Windows) — verified end-to-end

```powershell
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
cd ..
.\scripts\windows\stage-release.ps1
.\install.ps1 -LocalSource "dist\windows"
```

This installs everycli into `%LOCALAPPDATA%\EveryCli`, adds it to your user PATH, and starts the daemon automatically at every login (via the Windows Startup folder — no admin rights needed). Open a **new** terminal and run:

```powershell
everycli search "how to undo my last commit"
```

### 🐧 Install (Linux) — written, verification in progress (WSL)

```bash
cd rust
cargo build --release -p everycli-rs -p everycli-daemon
cd ..
./scripts/linux/stage-release.sh
./install.sh --local-source dist/linux
```

Persistence is handled by a `systemd --user` service, installed and enabled automatically.

### 🍎 macOS

Not started yet.

### Add your own commands

```bash
everycli add
```

Walks you through a few prompts (category, description, command, explanation, optional tags/warning) and writes the result to `~/.everycli/commands` (`%USERPROFILE%\.everycli\commands` on Windows) — a separate directory from the built-in corpus, so your custom commands are never overwritten by an update.

### 📦 Older Python-based release (v1.1.1 and earlier)

Three versions were available for each operating system on the [Releases](https://github.com/HE11032006/EveryCli/releases) page:

- **Full Version** (~300MB): **Ready to use.** Includes the AI model. Perfect for offline use or fast first-run experience.
- **Lite Version** (~50MB): **Lightweight.** Will automatically download the AI model (~400MB) on the first search. Recommended if you have a good internet connection.
- **Rust Version** (`everycli-rs-*` + `everycli-data.zip`, a few MB total): **Fastest cold start, no Python.** Native, dependency-free binary with instant lexical search. Automatically upgrades to full semantic search if a Full/Lite daemon is running locally. See [`rust/README.md`](rust/README.md) for usage.

1. Download the version that fits your needs.
2. (Optional) Setup for easy access:

   #### 🐧 Linux / 🍎 macOS
   1. Download `everycli-linux-full` (the daemon).
   2. Place the `bin/everycli` wrapper in your PATH.
   ```bash
   chmod +x everycli-linux-full bin/everycli
   sudo ln -s $(pwd)/everycli-linux-full /usr/local/bin/everycli-daemon
   sudo ln -s $(pwd)/bin/everycli /usr/local/bin/everycli
   
   # Start the daemon once
   everycli-daemon --start
   
   # Search instantly!
   everycli "git commit"
   ```

   #### 🪟 Windows
   - Put `everycli-windows-full.exe` and `everycli.ps1` in a folder.
   - Rename the exe to `everycli-daemon.exe`.
   - Add the folder to your **PATH**.
   - Run: `everycli search "git commit"`

3. Check our [Detailed Installation Guide](docs/tutorial_installation.md) for more info (describes the v1.1.1 Python-based flow).

### 🛠️ Installation (Source, Python — Sentinel planner only)

Sentinel (the LLM-based safety planner, see below) is still Python-based and separate from the fast Rust search path. If you want to build/contribute to it:

1. Clone the repo: `git clone https://github.com/HE11032006/EveryCli.git`.
2. Go to the root: `cd EveryCli`.
3. Install dependencies: `pip install -r requirements.txt`.

### Running locally

Fast search (Rust, recommended — see Install sections above):
```bash
everycli search "how to undo my last commit"
```

Sentinel, the LLM-based safety planner, is still Python-based and separate from the fast Rust search path — plan a command safely before you paste it into a terminal:
```bash
python -m everycli.everycli plan "remove unused Docker images safely"
```

With `OPENAI_API_KEY` configured, Sentinel uses GPT-5.6 to select and explain
one of the commands already retrieved from the local corpus. Use `--local` to
force the fully offline safety planner.

### Measuring retrieval quality

`eval/confusion_set.yaml` is a bilingual set of natural-language queries for
Git, Docker, Compose, npm, Composer, SSH, Python, and Linux. It deliberately
stores no fictional score: measure the current corpus before a demo or release.

```bash
python tools/evaluate_confusion.py
```

Use `--fail-under 80` only after agreeing on a baseline for the target
environment. `--matcher lexical` is available to diagnose the BM25-only
baseline; the default is the same hybrid matcher used by EveryCli. The
evaluator never runs a returned command.

For a portable demo with no network, set `EVERYCLI_OFFLINE=1`; EveryCli uses a
cached semantic model when available and otherwise falls back to local lexical
signals instead of waiting for download retries.

> [!TIP]
> To enjoy sub-50ms response times, EveryCli uses a background Daemon. The first search will automatically start it.

---

## 📖 Overview

EveryCli is built for speed and intelligence. Almost all our content is generated from YAML files you can find in the `everycli/data/commands/` directory.

If you would like to contribute an edit or addition to the docs, read through our [Contributing Guide](CONTRIBUTING.md).

### Documentation Sources

For deep dives, check our dedicated documentation files:
- 📖 [Tutorial: Installation](docs/tutorial_installation.md)
- 🛠️ [How to Build & Test](docs/how_to_build.md)
- 🏗️ [Architecture Explanation](docs/explanation_architecture.md)
- ⚙️ [Reference Configuration](docs/reference_config.md)
- 🛡️ [Build Week / Sentinel](docs/BUILD_WEEK.md)

### Directory Structure

The following is a high-level overview of relevant files and folders.

```text
EveryCli/
├── .github/             # CI/CD Workflows (Auto-build binaries)
├── bin/                 # Fast shell wrappers (Linux/macOS)
├── docs/                # Detailed Diátaxis documentation
├── everycli/
│   ├── core/            # Domain logic (Models, Search Engine, Coordinator)
│   ├── data/
│   │   └── commands/    # YAML scenarios database (built-in corpus)
│   └── infra/           # Sentinel planner infra (LLM-based, Python)
├── rust/
│   ├── everycli-core/   # Corpus loading + lexical search (Rust, shared lib)
│   ├── everycli-inference/ # Semantic encoder (ONNX Runtime)
│   ├── everycli-daemon/ # TCP daemon (replaces daemon_server.py)
│   └── everycli-rs/     # CLI client (search, add)
├── scripts/
│   ├── windows/         # stage-release.ps1 (packaging for install.ps1)
│   └── linux/           # stage-release.sh (packaging for install.sh)
├── install.ps1          # Windows installer
├── install.sh           # Linux installer
├── everycli.ps1         # Windows PowerShell wrapper (legacy Python flow)
├── requirements.txt     # Python dependencies (Sentinel planner)
└── README.md            # You are here
```

---

## 🗺️ Status & Roadmap

### ✅ Completed Features
*   **Native Rust + ONNX daemon**: replaces the Python/PyInstaller daemon, no more startup hang, ~1.7x faster inference (see [CHANGELOG.md](CHANGELOG.md)).
*   **`everycli add`**: add your own commands, stored separately from the built-in corpus, never overwritten by an update.
*   **Semantic Precision Tuning**: hybrid lexical + semantic scoring (local ONNX model, fine-tuned on the EveryCli corpus), 87.9% on the `confusion_set.yaml` benchmark.
*   **Interactive Disambiguation (O4)**: when the semantic gap between top results is too narrow, EveryCli shows the close candidates instead of guessing for you.
*   **Tips & Troubleshooting Integration**: the search UI distinctively displays contextual tips (💡) and troubleshooting advice (🔧), preventing errors before they happen.
*   **Seamless Shell Integration**: support for Bash (`everycli.bash`), Zsh (`everycli.zsh` with ZLE widget), and PowerShell (`everycli.ps1`) for frictionless workflow.
*   **One-command installers**: `install.ps1` (Windows, verified end-to-end) and `install.sh` (Linux, in progress) set up PATH and a background daemon automatically.
*   **Sentinel Planner**: safe planning and verification powered by LLMs for complex, multi-step actions (Python, separate from the fast Rust search path).

### 🚧 Planned / Future Improvements
*   **macOS installer**: not started yet.
*   **Boost par Historique (History Boosting)**: up-rank commands based on the user's execution history to adapt to individual workflows.
*   **Index ANN (Approximate Nearest Neighbors)**: migrate from flat similarity search to an ANN index (e.g., FAISS) to maintain sub-10ms latencies even with a corpus of 10,000+ commands.
*   **Model quantization**: the ONNX model currently ships as float32 (~470MB) — int8 quantization would reduce install size.
*   **Native Windows service**: currently the daemon starts via the Windows Startup folder (works, no permissions needed); a real Windows Service (SCM-compliant, via the `windows-service` crate) would be more robust for auto-restart on crash.

---

## 👏 Contributing

We welcome all contributions! Whether it's adding a new command or improving the AI matcher.
Please see our [Contributing Guide](CONTRIBUTING.md) for more details.

---

## 📄 License

EveryCli is **MIT licensed**.
Documentation is Creative Commons licensed.

---
*Made with ❤️ for developers who hate memorizing flags.*
