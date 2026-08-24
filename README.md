# EveryCli

[English](README.md) · [Français](README.fr.md)

> **Stop hunting for commands. Describe what you want to do.**

**EveryCli** is a natural-language command-line assistant. You describe your intent — in English or French — and it retrieves the matching shell command from a local corpus. Search runs entirely on your machine: a native Rust daemon combines lexical matching with semantic reranking through ONNX Runtime, with no API key and no network call. The move from the historical Python/PyInstaller flow to this native Rust stack means end users no longer need Rust, Cargo or Python — a prebuilt archive is enough.

> 🛟 **Safety first.** EveryCli **never** runs a command on your behalf. Results are shown for you to read; `--run` always asks for confirmation, and shell wrappers only place the command in an editable buffer.

---

## 🌱 Origin & purpose

EveryCli grew out of a small daily friction. Whenever a CLI command slipped my mind, I'd ask an online LLM — and each lookup added two or three seconds of waiting. That delay sounds small, but it can be enough to break context: you switch to another tab, start another task, and later have to reconstruct what you were doing. Digital attention is not split without cost; rapid task switching increases the effort of resuming context and the risk of losing the thread [1].

The idea was to keep that loop **inside the terminal** — describe the intent, get a command quickly from a *local* corpus, and gradually grow your **own** set of commands with `add` / `list` / `remove`. The goal is not to claim that a compact local model is universally better than a large remote one. It is to accept a smaller, controlled scope when that reduces latency, preserves context and avoids a detour to another tab. When local coverage is not enough, `everycli ask` remains available as an optional LLM assistant. The objective is simple: less waiting, fewer context switches, and continued control over what actually runs [1].

> **In this setting, a model that is fast and available locally can be more useful than a heavier model that imposes a round-trip and breaks attention.**

[1]: https://www.nngroup.com/articles/serial-task-switching/ "Nielsen Norman Group — Serial Task Switching"

## 🪧 Who it's for

| Audience | What EveryCli offers |
|---|---|
| **Developers & power users** | Describe an intent instead of memorizing flags; bilingual EN/FR search |
| **Privacy-conscious / offline users** | `search` works fully offline — no cloud, no API key, no telemetry |
| **Linux & Windows users** | Prebuilt archives with one-command installers; no toolchain required |
| **Release testers** | A reproducible install/search/uninstall runbook |
| **Contributors & integrators** | A documented Rust workspace, daemon protocol and shell contract |

## 🧬 Architecture first

EveryCli separates the user interface from the more expensive semantic computation. The Rust client receives your intent and communicates with a local daemon that keeps the model in memory and answers searches quickly. This avoids reloading the model for every command and helps you stay in the terminal on both Ubuntu/Linux and Windows.

```text
User
  │
  ▼
everycli-rs  ── JSON/TCP localhost ──▶  everycli-daemon
  │                                      ├── YAML corpus
  │                                      ├── model.onnx
  │                                      ├── tokenizer.json
  │                                      └── native ONNX Runtime
  └── local lexical fallback if the daemon is unavailable
```

The daemon listens only on `127.0.0.1:51821`; it is not a public network API. It combines the YAML corpus, ONNX model and platform-native runtime. The client also keeps a local lexical fallback so search remains useful when the daemon is unavailable.

📖 **Architecture deep dive:** components, daemon role, protocol, model, runtime, corpus and lifecycle → **[docs/explanation_architecture.md](docs/explanation_architecture.md)**.

## 🗝️ Key features

- 🔎 **Natural-language search** — describe what you want to do instead of memorizing syntax, using a corpus organized by namespace (Git, Docker, Compose, npm, SSH, Python, Linux…).
- 🧬 **Hybrid local ranking** — lexical matching and ONNX semantic reranking are fused on your machine to surface relevant commands without sending your query to the cloud.
- 🌍 **Bilingual search** — write your request in English, French or a mixed query, without mentally translating a command or its description.
- 🛰️ **Fast local daemon** — the model stays loaded on `127.0.0.1:51821`, allowing repeated searches to answer in a few hundred milliseconds after the first load on tested hardware, on Ubuntu/Linux and Windows, so you can stay in the work rhythm instead of waiting for a remote request.
- ✍️ **Add your own commands** — with `add`, `list` and `remove`, you gradually build a personal corpus; its files remain separate from the built-in corpus and survive updates.
- 🤝 **Optional AI assistance** — when no local command matches sufficiently, `everycli ask` can request a proposal from an OpenAI-compatible API and add it to your corpus, so you do not need to repeat a remote lookup for the same need later.
- 🛡️ **Review before execution** — Sentinel (`everycli plan`) can review a retrieved command and flag risks before you decide whether to run it.
- 🐚 **Shell integration** — the interactive picker, `--json`, `--copy` and deterministic `--shell` protocol support human and scriptable workflows without automatic execution.
- 📦 **No development dependencies for end users** — a prebuilt release includes the binaries, model, tokenizer, runtime and corpus; end users do not need Rust, Cargo or Python.

---

## 🧰 Installation

The simplest path is to run the installer directly from the `main` branch. It downloads the latest release, verifies its integrity and configures the client, daemon, model, runtime, corpus and background startup automatically. Rust, Cargo and Python are not required.

> ⚠️ Use the next corrected release, **v1.2.1 or later**. The public `v1.2.0` release shipped an ONNX Runtime library that is too old for the `ort` crate version used by the daemon; it should not be presented as a working semantic installation.

### 🐧 Ubuntu/Linux x86_64 — quick install

```bash
curl -fsSL https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.sh | bash
```

The installer asks for the language, places EveryCli in `~/.local/share/everycli`, creates links in `~/.local/bin` and configures the `systemd --user` service. At the end, reload your profile:

```bash
source ~/.profile
everycli search "how to undo my last commit"
```

If `everycli` is not recognized yet, open a new terminal. The first start may take longer while the daemon loads the model and computes corpus embeddings; later searches benefit from the warm daemon and disk cache.

### 🪟 Windows x86_64 — quick install

In **PowerShell**, run:

```powershell
irm https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.ps1 | iex
```

The installer asks for the language, downloads the release, verifies its integrity and configures EveryCli in your user profile. The first path can be somewhat slow, especially during the download and first model load. Open a new terminal if needed for the `everycli` command to become available.

### 📦 Install from a downloaded archive

To inspect files before installation, download the matching archive from **[GitHub Releases](https://github.com/HE11032006/EveryCli/releases)**, extract it and run the installer without arguments from the extracted folder.

On Ubuntu/Linux:

```bash
mkdir everycli-linux-x86_64
tar -xzf everycli-linux-x86_64.tar.gz -C everycli-linux-x86_64
cd everycli-linux-x86_64
./install.sh
source ~/.profile
```

On Windows PowerShell:

```powershell
Expand-Archive .\everycli-windows-x86_64.zip .\everycli-windows-x86_64
cd .\everycli-windows-x86_64
.\install.ps1
```

The complete archive contains the client, daemon, `model.onnx`, `tokenizer.json`, the native ONNX Runtime library and the built-in corpus. To uninstall, use `./uninstall.sh` on Linux or `./uninstall.ps1` on Windows; personal data is preserved by default.

### 🍎 macOS

macOS is **compiled and tested by CI**, but no installable macOS archive is published yet — the native runtime and installer still need end-to-end validation.

📖 **Full guide:** prerequisites, one-command installation, archive installation, checksum verification, uninstall and troubleshooting → **[docs/tutorial_installation.md](docs/tutorial_installation.md)**.

---

## ⌨️ Daily usage

The most useful everyday workflow is the interactive path:

```bash
everycli search "how to undo my last commit" --top 2 -i
```

> ⭐ **Recommended workflow.** `--top 2` limits the display to the two most relevant candidates and `-i` opens the interactive picker. After choosing, you can retrieve and copy the selected command instead of scanning a longer result list that may not activate this flow.

The simple form remains available:

```bash
everycli search "describe your intent"
```

Common options:

```bash
everycli search "query" --top 3        # maximum number of candidates
everycli search "query" -i             # choose with the keyboard
everycli search "query" --copy         # copy the selected result
everycli search "query" --run          # run after confirmation
everycli search "query" --json         # machine-readable output
everycli search "query" --no-daemon    # force the local lexical fallback
```

Interactive mode lets you review candidates before choosing. EveryCli never runs a command without explicit confirmation.

**Add and maintain your own commands:**

```bash
everycli add
everycli list
everycli remove
```

This turns a command found once into a reusable local shortcut. Personal commands live in `~/.everycli/commands` (Linux) or `%USERPROFILE%\.everycli\commands` (Windows), separate from the built-in corpus and preserved through a normal update or uninstall.

---

## 🛰️ `everycli ask` & 🛡️ Sentinel

`search` is the main **local** path — corpus + Rust daemon, no API key. Two optional companions exist:

- **`everycli ask`** calls an **OpenAI-compatible API** to propose a command, explanation, warning and tags, then offers to save it to your personal corpus. It is *not* the local ranking of `search`.
- **Sentinel** (`everycli plan`) is a separate **Python** planner that reviews an already-retrieved command. It never executes a shell command for you.

Configure a key (stored privately, `0600` on Unix):

```bash
everycli config set api_key "your-api-key"
everycli config show           # never prints the full key
everycli ask "compress the current directory"
```

The key may also come from `EVERYCLI_API_KEY`. Known prefixes are auto-detected, or set a provider explicitly (`everycli config set provider openai`, plus `api_url` / `api_model` for OpenAI-compatible endpoints). Without a key, `ask` reports a config error while `search` keeps working offline.

## 🎛️ Configuration

EveryCli is driven by a handful of environment variables and a `~/.everycli/config.toml` file. The essentials:

| Variable | Role | Dev default |
|---|---|---|
| `EVERYCLI_PORT` | Daemon TCP port | `51821` |
| `EVERYCLI_MODEL_DIR` | Folder holding `model.onnx` + `tokenizer.json` | model dir |
| `EVERYCLI_ONNXRUNTIME_DYLIB` | Native ONNX Runtime library | `.dll` / `.so` per OS |
| `EVERYCLI_DATA_DIR` | Built-in YAML corpus | shipped corpus |
| `EVERYCLI_USER_DATA_DIR` | Personal YAML corpus | `~/.everycli/commands` |
| `EVERYCLI_API_KEY` | Key for `everycli ask` | *unset* |

Installers replace the dev defaults with absolute paths. A corpus entry is a YAML record with `id`, `description`, `tags`, per-platform `commands`, `explanation` and an optional `warning`.

📖 **Full reference:** every variable, data paths, corpus schema and the JSON daemon protocol → **[docs/reference_config.md](docs/reference_config.md)**.

---

## 🐚 Shell integration

EveryCli separates the human interface from the wrapper protocol so a command is never executed by surprise. The `--shell` (`-s`) mode prints **only** the resolved command to `stdout` (no trailing newline), sends diagnostics to `stderr`, and does **not** confirm or run anything — ideal for Bash/Zsh/PowerShell wrappers that place the command in an editable buffer.

```bash
everycli search "undo my last commit" --shell
```

To stay deterministic, `--shell` does not combine with `-i`, `--run`, `--copy`, `--error` or `--top` > 1.

📖 **Full guide:** interactive mode, Bash/Zsh/PowerShell wrappers, execution-safety rules → **[docs/shell_integration.md](docs/shell_integration.md)**.

## ⚗️ Build & tests

For a prebuilt release you don't need this — it targets developers building a local bundle.

```bash
# Rust binaries
cd rust
cargo build --release -p everycli-rs -p everycli-daemon

# Targeted tests
cargo test -p everycli-rs
cargo test -p everycli-core
cargo test -p everycli-daemon
```

The production ONNX artifact lives in [`Michelhe/everycli-minilm-ft-boosted-onnx`](https://huggingface.co/Michelhe/everycli-minilm-ft-boosted-onnx); CI pins a revision and verifies SHA-256 checksums. The `ort 2.0.0-rc.13` crate requires a native **ONNX Runtime 1.27.x+** library (the workflow pins 1.27.0).

📖 **Full guide:** ONNX assets, native runtime, local staging, CI/release flow → **[docs/how_to_build.md](docs/how_to_build.md)**.

## 📐 Benchmarks & validation

Measurements are development observations, not universal guarantees. On the bilingual `eval/confusion_set.yaml` set the recorded ranking result was **58/66 queries (87.9%)**. An indicative Windows latency baseline: **~383 ms** for a full daemon search vs **~33 ms** for the local lexical fallback (a cold first load is much slower).

```bash
python tools/evaluate_confusion.py                 # hybrid path
python tools/evaluate_confusion.py --matcher lexical  # lexical only
```

📖 **Full guide:** measurement rules, bundle validation, CI checks, regression reports → **[docs/benchmarking.md](docs/benchmarking.md)**.

---

## 🗺️ Status & roadmap

| Area | Verified status |
|---|---|
| Rust client, Rust daemon and hybrid search | ✔️ Available |
| Distributable `model.onnx` and tokenizer | ✔️ In validated CI bundles |
| Windows install from a complete bundle | ✔️ Verified end to end |
| Linux install from a complete bundle | ✔️ Verified under WSL (service, search, uninstall) |
| Ubuntu & Windows CI | ✔️ Complete bundles with model checksums |
| macOS | 🔧 CI build/tests only; no installer or public archive yet |
| Model quantization | 🔭 To explore (current model is large float32) |
| ANN index for very large corpora | 🔭 To explore |

See **[CHANGELOG.md](CHANGELOG.md)** for factual change history and measurements.

## 🗂️ Documentation

| Document | Audience | Scope |
|---|---|---|
| [Installation tutorial](docs/tutorial_installation.md) | Users & testers | Install, usage, uninstall, troubleshooting |
| [Architecture](docs/explanation_architecture.md) | Curious developers | Client, daemon, model, ranking, lifecycle |
| [Build & tests](docs/how_to_build.md) | Developers | Rust builds, ONNX assets, staging, validation |
| [Configuration reference](docs/reference_config.md) | Integrators | Env vars, paths, YAML schema, daemon protocol |
| [Shell integration](docs/shell_integration.md) | Advanced users | `--shell` protocol, wrappers, execution safety |
| [Benchmarks & validation](docs/benchmarking.md) | Developers | Tests, ranking benchmark, latency, CI |
| [Linux validation guide](LINUX_TEST_GUIDE.md) | Release testers | Linux install/search/uninstall runbook |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Setup, tests, contribution rules |
| [CHANGELOG.md](CHANGELOG.md) | Technical readers | Factual change history |

## 🗄️ Repository structure

```text
EveryCli/
├── everycli/                   # Sentinel Python component and historical data
│   └── data/commands/          # Built-in YAML corpus
├── rust/
│   ├── everycli-core/          # Corpus loading and lexical search
│   ├── everycli-inference/     # Semantic encoder and ONNX Runtime
│   ├── everycli-daemon/        # Local TCP server
│   └── everycli-rs/            # Rust CLI client
├── docs/                       # Standalone technical guides
├── scripts/                    # Platform staging scripts
├── install.sh / install.ps1    # Linux / Windows installers
├── uninstall.sh / uninstall.ps1
└── .github/workflows/build.yml # Tests, builds and CI bundles
```

## 📬 Contact & support

| Resource | Link |
|---|---|
| **Website** |  |
| **Support** |  |

## 📜 License

Code is released under the **MIT License**; documentation under a **Creative Commons** license. See [LICENSE.md](LICENSE.md).

---

<div align="center"><sub>EveryCli — for developers who would rather describe an intent than memorize flags.</sub></div>
