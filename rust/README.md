# EveryCli Rust fast path

This workspace is the start of the performance migration, not a replacement of
the Python hybrid engine yet. It reads the same `everycli/data/commands/*.yaml`
files and uses a dependency-free, deterministic lexical retriever with explicit
ecosystem routing. That makes its latency and behavior easy to benchmark while
the semantic reranker is evaluated separately.

```powershell
cargo test --manifest-path rust/Cargo.toml
cargo run --manifest-path rust/Cargo.toml -p everycli-rs -- search "docker build an image"
```

Useful options: `--top N`, `--platform windows|linux|macos`, `--data DIR`, and
`--json`. The next migration step is parity evaluation against
`eval/confusion_set.yaml`, then a semantic reranking adapter only if it improves
accuracy without compromising the Rust fast path.
