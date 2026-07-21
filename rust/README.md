# EveryCli Rust fast path

This workspace is the native client half of the performance migration, not a
replacement of the Python daemon. `everycli-rs search` talks to the existing
Python daemon (the one keeping `paraphrase-multilingual-MiniLM-L12-v2` resident
in RAM) over its TCP/JSON protocol on `127.0.0.1:51821`, and only falls back to
a dependency-free, deterministic local lexical search over
`everycli/data/commands/*.yaml` when the daemon can't be reached — the same
fallback shape as the Python CLI's `--no-daemon` path.

```powershell
cargo test --manifest-path rust/Cargo.toml
cargo run --manifest-path rust/Cargo.toml -p everycli-rs -- search "docker build an image"
```

## Daemon-first search, with automatic fallback

By default `search` pings the daemon, sends the query, and prints whatever the
daemon (semantic + lexical hybrid) returns. If the daemon isn't running, it
spawns `python -m everycli.infra.daemon_runner` detached, waits up to 10s for
it to answer a ping, retries once, and — if that also fails — falls back to
the local lexical search built into `everycli-core`, printing one line to
stderr explaining why. Pass `--no-daemon` to skip the daemon entirely and go
straight to the local search.

Environment overrides: `EVERYCLI_PORT` (default `51821`), `EVERYCLI_TIMEOUT`
(default `1.0` seconds), `EVERYCLI_DATA_DIR` (corpus directory).

## `search` options

| Flag | Effect |
| --- | --- |
| `--top N`, `-t N` | Number of results to show (default 1). |
| `--platform linux\|windows\|macos` | Resolve the platform-specific command. |
| `--data DIR` | Corpus directory override. |
| `--json` | Machine-readable output, including `tags` and `warning`. |
| `--error MSG`, `-e MSG` | Look up a matching error hint (`cause`/`fix`) for the top result. |
| `--env NAME` | Keep only results tagged with `NAME`. |
| `--copy`, `-c` | Copy the resolved command to the clipboard (`clip` / `pbcopy` / `xclip`+`xsel`). |
| `--run`, `-r` | Prompt for confirmation, then execute the resolved command. |
| `--interactive`, `-i` | Pick a result from a plain numbered list (not a `pick`-style TUI). |
| `--shell`, `-s` | Print only the resolved command to stdout; everything else goes to stderr. Requires `--top 1` and a non-empty query; incompatible with `-i`/`--run`/`--copy`/`--error`. |
| `--no-daemon` | Skip the daemon and search the local corpus directly. |

Auto-disambiguation mirrors the Python CLI: when the top two results score
within 5% of each other, you're prompted to pick one instead of getting the
higher-scored (but uncertain) result silently.

## Download a prebuilt binary

Every tagged release (`v*`) publishes a native, dependency-free
`everycli-rs` binary for Linux, macOS, and Windows, plus `everycli-data.zip`
(the corpus) — see the repo's Releases page. Unlike the Full/Lite Python
builds, this download has no bundled model: it's the fastest possible
cold-start option and gets full semantic search automatically if a Full/Lite
daemon happens to be running locally, otherwise it uses the local lexical
fallback.

```bash
# Linux/macOS
unzip everycli-data.zip -d .
chmod +x everycli-rs-linux   # or everycli-rs-macos
./everycli-rs-linux search "docker build an image" --data ./commands
```

```powershell
# Windows
Expand-Archive everycli-data.zip .
.\everycli-rs-windows.exe search "docker build an image" --data .\commands
```

Set `EVERYCLI_DATA_DIR` instead of `--data` to avoid repeating the flag.

## What's intentionally not here yet

Only `search` exists — `plan`, `daemon`, `add`, `list`, `export`, `import`,
`update`, and `history` stay Python-only for now. `--interactive` is a plain
stdin picker rather than `pick`'s arrow-key TUI, since pulling in a TUI crate
for one flag isn't worth it yet. The next migration step is parity evaluation
against `eval/confusion_set.yaml`.
