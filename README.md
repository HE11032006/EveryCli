# EveryCli

[English](README.md) · [Français](README.fr.md)

> **Stop hunting for commands. Describe what you want to do.**

**EveryCli** is a natural-language command-line assistant. You describe your intent — in English or French — and it retrieves the matching shell command from a local corpus. Search runs entirely on your machine: a native Rust daemon combines lexical matching with semantic reranking through ONNX Runtime, with no API key and no network call. The move from the historical Python/PyInstaller flow to this native Rust stack means end users no longer need Rust, Cargo or Python — a prebuilt archive is enough.

> 🛟 **Safety first.** EveryCli **never** runs a command on your behalf. Results are shown for you to read; `--run` always asks for confirmation, and shell wrappers only place the command in an editable buffer.

---

## 🌱 Origin & purpose

EveryCli grew out of a small daily friction. Whenever a CLI command slipped my mind, I'd ask an online LLM — and each lookup meant a two- or three-second wait. In that gap attention drifts: you switch to another tab, another task, and the thread of what you were doing is gone.

The idea was to keep that loop **inside the terminal** — describe the intent, get the command instantly from a *local* corpus, and gradually grow your **own** set of commands with `add` / `list` / `remove`. No round-trip, no context switch, no network, and you always stay in control of what actually runs.

EveryCli also predates the **Reverie hackathon**: it was started before the event began and had already been built during earlier hackathons, but was never published — for lack of time to ship it.

> 🕰️ **Project history.** The major before → after changes and their impact are tracked in **[CHANGELOG.md](CHANGELOG.md)**.

## 🪧 Who it's for

| Audience | What EveryCli offers |
|---|---|
| **Developers & power users** | Describe an intent instead of memorizing flags; bilingual EN/FR search |
| **Privacy-conscious / offline users** | `search` works fully offline — no cloud, no API key, no telemetry |
| **Linux & Windows users** | Prebuilt archives with one-command installers; no toolchain required |
| **Release testers** | A reproducible install/search/uninstall runbook |
| **Contributors & integrators** | A documented Rust workspace, daemon protocol and shell contract |

## 🗝️ Key features

- 🔎 **Natural-language search** over a curated, namespaced command corpus (Git, Docker, Compose, npm, SSH, Python, Linux…).
- 🧬 **Hybrid local ranking** — lexical matching **+** semantic reranking (ONNX model) fused into a single score, computed on-device.
- 🌍 **Bilingual** — works in **English** and **French**, including mixed queries.
- 🛰️ **Local daemon** keeps the model in memory on `127.0.0.1:51821` for fast repeat queries, with an automatic **lexical fallback** if it is unavailable.
- ✍️ **Your own commands** — `add`, `list`, `remove`; stored separately from the built-in corpus and preserved across updates.
- 🤝 **Optional AI assist** — `everycli ask` calls an OpenAI-compatible API to synthesize a command when the corpus has no match.
- 🛡️ **Review before run** — Sentinel (`everycli plan`) offers an LLM safety review of a retrieved command.
- 🐚 **Shell-native** — interactive picker, `--json`, `--copy`, and a deterministic `--shell` protocol for wrappers.
- 📦 **Zero-dependency install** for end users — Rust, Cargo and Python are **not** required for a prebuilt release.

---

## 🧰 Installation

End users should download a platform archive from **[GitHub Releases](https://github.com/HE11032006/EveryCli/releases)**. No toolchain needed.

### 🐧 Linux x86_64

Download `everycli-linux-x86_64.tar.gz`, then:

```bash
mkdir everycli-linux-x86_64
tar -xzf everycli-linux-x86_64.tar.gz -C everycli-linux-x86_64
cd everycli-linux-x86_64
./install.sh --language en
```

The installer places the bundle in `~/.local/share/everycli`, links binaries into `~/.local/bin`, and enables a `systemd --user` service. Then reload your profile:

```bash
source ~/.profile
everycli search "how to undo my last commit"
```

> ⏳ The **first** start is slower: the daemon loads the model and computes corpus embeddings (up to ~3 minutes on a slow machine or WSL). Later starts use a disk cache.

### 🪟 Windows x86_64

Download `everycli-windows-x86_64.zip`, extract it, open **PowerShell** in the folder and run:

```powershell
.\install.ps1 -Language en
```

The archive ships the CLI, daemon, `model.onnx`, tokenizer, `onnxruntime.dll` and corpus. Use `-Version vX.Y.Z` to let the script download a specific release, or `-NoService` to avoid elevation and use the Windows Startup folder instead of a service.

### 🍎 macOS

macOS is **compiled and tested by CI**, but no installable macOS archive is published yet — the native runtime and installer still need end-to-end validation.

📖 **Full guide:** parcours from a bundle, script-only download, checksum verification, uninstall and troubleshooting → **[docs/tutorial_installation.md](docs/tutorial_installation.md)**.

---

## ⌨️ Daily usage

The general form:

```bash
everycli search "describe your intent"
```

Common options:

```bash
everycli search "query" --top 3        # number of candidates
everycli search "query" --interactive  # pick with the keyboard (-i)
everycli search "query" --copy         # copy the chosen result
everycli search "query" --run          # run it — asks for confirmation
everycli search "query" --json         # machine-readable output
everycli search "query" --no-daemon    # force the local lexical fallback
```

Interactive mode shows the closest candidates and lets you choose; `--copy` and `--run` target an explicit result, and `--run` confirms before executing.

**Manage your own commands:**

```bash
everycli add
everycli list
everycli remove
```

Personal commands live in `~/.everycli/commands` (Linux) or `%USERPROFILE%\.everycli\commands` (Windows). They are separate from the built-in corpus and survive a normal update or uninstall.

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

## 🧬 Architecture at a glance

```text
User
  │
  ▼
everycli-rs  ── JSON over localhost TCP ──▶  everycli-daemon
  │                                             ├── YAML corpus
  │                                             ├── model.onnx
  │                                             ├── tokenizer.json
  │                                             └── native ONNX Runtime
  └── local lexical fallback if the daemon is unavailable
```

The daemon keeps the model in memory and answers `ping`, `search` and `reload` on `127.0.0.1:51821` — it is **not** a public network API. The hybrid score is calibrated empirically: **lexical `0.45`**, **semantic `0.55`**, **namespace bonus `+0.2`** (a soft route, not a hard filter), with a **`0.50` minimum-relevance threshold** to reject off-topic queries. The fast search path is native Rust; Sentinel remains a separate Python component.

📖 **Deep dive:** components, why a daemon, protocol, model & runtime, corpus → **[docs/explanation_architecture.md](docs/explanation_architecture.md)**.

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

## 📜 License

Code is released under the **MIT License**; documentation under a **Creative Commons** license. See [LICENSE.md](LICENSE.md).

---

<div align="center"><sub>EveryCli — for developers who would rather describe an intent than memorize flags.</sub></div>
