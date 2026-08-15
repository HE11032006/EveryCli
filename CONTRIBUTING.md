# Contributing to EveryCli

Thank you for your interest in contributing to EveryCli! Whether you're fixing bugs, improving documentation, or adding new CLI scenarios, your help is welcome.

## 📖 Documentation First

Before you start, please take a look at our detailed documentation:
- [Tutorial: Installation](docs/tutorial_installation.md)
- [How to Build & Test](docs/how_to_build.md)
- [Architecture Explanation](docs/explanation_architecture.md)
- [Reference Configuration](docs/reference_config.md)
- [Changelog](CHANGELOG.md) — recent architecture changes (Python daemon → Rust/ONNX)

## 🚀 Ways to Contribute

### 1. Adding New Scenarios
The easiest way to contribute is by adding new command scenarios to the `everycli/data/commands/` directory.
- Scenarios are stored in YAML files.
- You can use the command `everycli add` to generate a new entry interactively (writes to your personal `~/.everycli/commands`, not the built-in corpus — for a contribution, move the entry into `everycli/data/commands/` by hand before opening a PR).

### 2. Improving the search engine
Search combines a lexical matcher (`rust/everycli-core`) with a semantic reranker (`rust/everycli-inference`, ONNX Runtime) — see [`rust/everycli-daemon`](rust/everycli-daemon) for how they're combined. If you find that some searches don't return the expected results, `eval/confusion_set.yaml` plus the daemon's `--debug` flag (shows lexical/semantic/hybrid scores separately) are the fastest way to diagnose why.

### 3. Working on the ONNX export tooling
**Only relevant if you're fine-tuning or re-exporting the semantic model** — most contributions (new scenarios, CLI features, bug fixes) don't need this at all. If you are:
- The runtime app dependencies (`requirements.txt`) don't include the export tooling — it's a separate, one-time-use set of dependencies in [`training/requirements-onnx-export.txt`](training/requirements-onnx-export.txt), with usage notes and known pitfalls documented at the top of that file.
- Install with `pip install -r training/requirements-onnx-export.txt --break-system-packages`, in the same `.venv` as the rest of the project (no separate venv needed).

### 4. Reporting Bugs
Please use GitHub Issues to report any bugs or suggest new features.

## 🛠️ Development Setup

EveryCli's fast path (search, `add`) is Rust; a separate Python component (Sentinel, the LLM-based safety planner) remains Python-based. Set up whichever you're working on.

### Rust (search, add, daemon)

1. Fork and clone the repository.
2. Build: `cd rust && cargo build --release -p everycli-rs -p everycli-daemon`.
3. See [`rust/onnx-bench/`](rust/onnx-bench) for how to export/place the ONNX model and ONNX Runtime library needed to run the daemon locally.
4. Run the daemon: `cargo run -p everycli-daemon` (add `--debug` to see per-scenario lexical/semantic/hybrid scores).
5. Test your changes: `cargo run -p everycli-rs -- search "your query"`.
6. Run the Rust test suite: `cargo test` (from `rust/`).

### Python (Sentinel planner)

1. Install dependencies: `pip install -r requirements.txt --break-system-packages`.
2. Test your changes: `python -m everycli.everycli plan "your query"`.

## 📜 Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---
*Thank you for making EveryCli better for everyone!*
