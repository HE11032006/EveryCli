# EveryCli — Reverie Hacks 2026 Submission & Architecture Evidence

EveryCli is a **local-first, privacy-respecting semantic command discoverer** and assistant designed to turn natural-language developer intent into safe, ready-to-run shell commands in under 50ms.

---

## 1. What is EveryCli

Command line tools (Git, Docker, Kubernetes, Linux, SSH, NPM, etc.) have hundreds of complex flags that developers constantly forget or search online. EveryCli solves this directly inside the terminal:

- **Natural Language Intent**: Type what you want to achieve in plain English or French (e.g. `everycli search "undo my last commit without losing changes"`).
- **Hybrid Retrieval Engine**: Combines exact lexical matching with a fine-tuned multilingual MiniLM sentence-transformer model via ONNX Runtime for semantic understanding.
- **100% Native Rust & Offline**: Zero Python runtime needed at execution. A high-performance Rust background daemon (`everycli-daemon`) keeps the model warm in memory.
- **Local User Corpus (`add`, `list`, `remove`)**: Extend your CLI database with personal custom scripts stored in `~/.everycli/commands/` without modifying built-in data.
- **Universal LLM Assist (`ask` & `config`)**: Need a command outside the local corpus? Query any configured LLM API (OpenAI, Google Gemini, Groq, Mistral, OpenRouter, DeepSeek) with automatic provider detection, and save the result into your local corpus in one keystroke.
- **Automatic Clipboard Integration**: Resolved commands are instantly copied to your clipboard (`Ctrl+V` to paste and run).

---

## 2. Architecture Overview

```
                        ┌────────────────────────────────────────┐
                        │              everycli-rs               │
                        │       (Native Rust CLI Client)         │
                        └───────┬────────────────────────┬───────┘
                                │                        │
                       TCP Ping │ / Search               │ Direct HTTP (Optional)
                      127.0.0.1:51821                    ▼
                                │             ┌────────────────────────┐
                                ▼             │    Cloud LLM APIs      │
                    ┌───────────────────────┐ │ (Gemini/Groq/OpenAI...)│
                    │    everycli-daemon    │ └────────────────────────┘
                    │   (Rust Service /     │
                    │    Multi-threaded)    │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
┌───────────────────┐                       ┌───────────────────┐
│   everycli-core   │                       │everycli-inference │
│  (Lexical BM25,   │                       │  (ONNX Runtime    │
│  Corpus YAML, i18n│                       │   SentencePiece   │
│  Merged Storage)  │                       │   Embeddings)     │
└───────────────────┘                       └───────────────────┘
          │                                           │
          └─────────────────────┬─────────────────────┘
                                ▼
                    Hybrid Ranking Formulation:
     Score = 0.45 * Lexical + 0.55 * Semantic + 0.2 * NamespaceBonus
```

---

## 3. Retrieval Quality & Evaluation Benchmark

The repository includes `eval/confusion_set.yaml` with maintained French and English queries covering ambiguous and complex scenarios across Git, Docker, Composer, npm, Linux and SSH:

- **Evaluation Accuracy**: **87.9% Top-1 Precision** across the confusion benchmark.
- **Response Latency**: **~0.13s - 0.20s** cold start / **< 50ms** on warm daemon.
- **Cache Optimization**: Embedded representations are cached on disk with sampling-based model hash validation to avoid redundant recomputations.

---

## 4. Key CLI Commands

```bash
# 1. Search indexed commands with intent
everycli search "undo last commit"
everycli search "docker: remove dangling containers" --interactive

# 2. Ask an external AI provider for unknown commands
everycli ask "how to find files larger than 100MB on linux"

# 3. Configure API providers
everycli config set provider gemini
everycli config set api_key "AIza..."

# 4. Manage personal scenarios
everycli add
everycli list
everycli remove my_custom_command_id
```

---

## 5. Deployment & Installation

- **Windows**: `install.ps1` automatically configures `EveryCliDaemon` as a native Windows Service with auto-elevation, or falls back to user Startup directory (`-NoService`).
- **Linux / macOS**: Native standalone process managed via `install.sh`.
- **Self-contained Release**: Release bundles package `everycli.exe`, `everycli-daemon.exe`, `model.onnx`, `tokenizer.json` and `onnxruntime.dll` for zero-setup installation.
