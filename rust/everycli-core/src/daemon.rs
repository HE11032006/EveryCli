//! TCP client for the EveryCli Python daemon's newline-delimited JSON protocol.
//! See `everycli/infra/daemon_client.py` and `everycli/infra/daemon_server.py`.

use std::io::{BufRead, BufReader, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use serde::Deserialize;
use serde_json::{Value, json};

#[derive(Clone, Copy, Debug)]
pub struct DaemonConfig {
    pub host: &'static str,
    pub port: u16,
    pub timeout: Duration,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        let port = std::env::var("EVERYCLI_PORT")
            .ok()
            .and_then(|value| value.parse().ok())
            .unwrap_or(51821);
        let timeout = std::env::var("EVERYCLI_TIMEOUT")
            .ok()
            .and_then(|value| value.parse::<f64>().ok())
            .map(Duration::from_secs_f64)
            .unwrap_or(Duration::from_secs(1));
        Self {
            host: "127.0.0.1",
            port,
            timeout,
        }
    }
}

#[derive(Debug, Deserialize, PartialEq)]
pub struct DaemonSearchHit {
    pub id: String,
    pub description: String,
    pub command: String,
    pub explanation: String,
    #[serde(default)]
    pub explanation_en: String,
    #[serde(default)]
    pub warning: String,
    #[serde(default)]
    pub warning_en: String,
    #[serde(default)]
    pub tags: Vec<String>,
    pub namespace: String,
    pub score: f32,
}

#[derive(Debug, PartialEq)]
pub enum DaemonError {
    Unavailable,
    RespawnFailed,
    Timeout,
    Server { code: String, message: String },
}

fn send_request(config: &DaemonConfig, payload: &Value) -> Option<Value> {
    let addr = (config.host, config.port).to_socket_addrs().ok()?.next()?;
    let mut stream = TcpStream::connect_timeout(&addr, config.timeout).ok()?;
    stream.set_read_timeout(Some(config.timeout)).ok()?;
    stream.set_write_timeout(Some(config.timeout)).ok()?;

    let mut line = serde_json::to_string(payload).ok()?;
    line.push('\n');
    stream.write_all(line.as_bytes()).ok()?;

    let mut reader = BufReader::new(stream);
    let mut response = String::new();
    reader.read_line(&mut response).ok()?;
    serde_json::from_str(response.trim_end()).ok()
}

pub fn ping(config: &DaemonConfig) -> bool {
    match send_request(config, &json!({"action": "ping"})) {
        Some(response) => response.get("ok").and_then(Value::as_bool) == Some(true),
        None => false,
    }
}

/// Send one `search` request. Does not ping first and never respawns the
/// daemon — callers that want the ping-then-respawn-then-retry flow should
/// use [`search`].
fn search_once_no_ping(
    config: &DaemonConfig,
    query: &str,
    top_k: usize,
) -> Result<Vec<DaemonSearchHit>, DaemonError> {
    let payload = json!({"action": "search", "query": query, "top_k": top_k, "context": null});
    let response = send_request(config, &payload).ok_or(DaemonError::Timeout)?;

    let ok = response.get("ok").and_then(Value::as_bool).unwrap_or(false);
    if !ok {
        let code = response
            .get("code")
            .and_then(Value::as_str)
            .unwrap_or("DAEMON_ERROR")
            .to_owned();
        let message = response
            .get("error")
            .and_then(Value::as_str)
            .unwrap_or("Erreur inconnue")
            .to_owned();
        return Err(DaemonError::Server { code, message });
    }

    let results = response.get("results").cloned().unwrap_or(Value::Null);
    serde_json::from_value(results).map_err(|_| DaemonError::Timeout)
}

/// Ask the daemon to reload its corpus. Silently returns `false` if the
/// daemon is unreachable, matching `daemon_client.py::send_reload`.
pub fn reload(config: &DaemonConfig) -> bool {
    match send_request(config, &json!({"action": "reload"})) {
        Some(response) => response.get("ok").and_then(Value::as_bool) == Some(true),
        None => false,
    }
}

/// Ping the daemon, then send one `search` request. Returns
/// [`DaemonError::Unavailable`] without attempting the search if the ping
/// fails (mirrors `everycli/infra/daemon_client.py`'s ping-before-search
/// guard, minus the respawn step — see [`search`] for that).
pub fn search_once(
    config: &DaemonConfig,
    query: &str,
    top_k: usize,
) -> Result<Vec<DaemonSearchHit>, DaemonError> {
    if !ping(config) {
        return Err(DaemonError::Unavailable);
    }
    search_once_no_ping(config, query, top_k)
}

/// [`search_once`], but on [`DaemonError::Unavailable`] calls `respawn` once
/// and retries. `respawn` is injected so the polling/process-spawn strategy
/// (real implementation: [`respawn_daemon`]) stays out of this decision logic.
fn search_with(
    config: &DaemonConfig,
    query: &str,
    top_k: usize,
    respawn: impl FnOnce() -> bool,
) -> Result<Vec<DaemonSearchHit>, DaemonError> {
    match search_once(config, query, top_k) {
        Err(DaemonError::Unavailable) => {
            if respawn() {
                // The very first real search right after a cold respawn
                // commonly needs several seconds (semantic model load is
                // deferred to the first query — see POST_RESPAWN_SEARCH_TIMEOUT)
                // — governing it by the caller's normal steady-state
                // per-request timeout would report a spurious failure even
                // though the daemon is genuinely up and about to answer.
                let mut warm_config = *config;
                warm_config.timeout = POST_RESPAWN_SEARCH_TIMEOUT;
                search_once_no_ping(&warm_config, query, top_k)
            } else {
                Err(DaemonError::RespawnFailed)
            }
        }
        other => other,
    }
}

/// Call `is_ready` every `interval` until it returns `true` or `timeout`
/// elapses.
fn poll_until_ready(
    mut is_ready: impl FnMut() -> bool,
    interval: Duration,
    timeout: Duration,
) -> bool {
    let deadline = std::time::Instant::now() + timeout;
    loop {
        if is_ready() {
            return true;
        }
        if std::time::Instant::now() >= deadline {
            return false;
        }
        std::thread::sleep(interval);
    }
}

const RESPAWN_POLL_INTERVAL: Duration = Duration::from_millis(200);
const RESPAWN_TIMEOUT: Duration = Duration::from_secs(10);
// The daemon defers loading the actual ML model until the first real query
// (see semantic_matcher.py's `fit()` — a corpus-embeddings cache hit skips
// `_load_model()` entirely, so `ping` succeeding is not a signal that the
// model itself is ready). That first-query model load is normally ~3s but
// can take much longer depending on the machine (disk/AV scanning torch's
// files for the first time) — 30s gives real headroom without hanging the
// CLI indefinitely if the daemon is genuinely broken.
const POST_RESPAWN_SEARCH_TIMEOUT: Duration = Duration::from_secs(30);

/// Conventional sibling binary names to look for next to the running
/// `everycli-rs` exe. Includes both the generic names (matching
/// `everycli-daemon.spec`'s raw output name, useful if someone renames a
/// download to the simple convention already documented in `bin/everycli`)
/// and the actual OS-prefixed names `build.yml`'s release job really ships
/// (`everycli-windows-full.exe`, `everycli-linux-full`,
/// `everycli-macos-full`, and their `-lite` counterparts) — a real,
/// as-downloaded release asset only ever matches the latter.
const SIBLING_DAEMON_NAMES: &[&str] = &[
    "everycli-daemon",
    "everycli-full",
    "everycli-lite",
    "everycli-windows-full",
    "everycli-windows-lite",
    "everycli-linux-full",
    "everycli-linux-lite",
    "everycli-macos-full",
    "everycli-macos-lite",
];

/// Sentinel argument recognized by `everycli.everycli:main` before Typer/
/// Click or Rich ever run — must match `daemon_client.DAEMON_RUNNER_ARG`
/// exactly. A fully detached process (no console at all) with stdio
/// redirected to null crashes the instant Rich's `console.print` tries to
/// probe terminal capabilities; `start_daemon()`'s plain `print()` calls
/// don't have that problem, so respawn must reach it directly rather than
/// going through the normal `daemon --start` Typer subcommand.
const DAEMON_RUNNER_ARG: &str = "__internal_daemon_runner__";

/// Binaries to try spawning as `<candidate> <DAEMON_RUNNER_ARG>`, in priority
/// order: an explicit override (`EVERYCLI_DAEMON_BIN`, mirrors
/// `bin/everycli`'s `DAEMON_BIN` and `everycli.ps1`'s `$env:EVERYCLI_BIN`),
/// then conventional sibling names in `dir` (the directory the current
/// `everycli-rs` exe lives in). Only entries that exist on disk are kept —
/// a caller who downloaded only the Rust binary correctly gets an empty
/// list rather than attempting to spawn a nonexistent file.
fn daemon_binary_candidates(dir: &Path, env_override: Option<&str>) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    if let Some(value) = env_override.filter(|value| !value.is_empty()) {
        candidates.push(PathBuf::from(value));
    }
    for name in SIBLING_DAEMON_NAMES {
        let file_name = if cfg!(windows) {
            format!("{name}.exe")
        } else {
            (*name).to_owned()
        };
        candidates.push(dir.join(file_name));
    }
    candidates.into_iter().filter(|path| path.is_file()).collect()
}

/// Spawn `program` with `args`, detached from this process on every OS —
/// mirrors `daemon_client.py::_respawn_daemon`'s `subprocess.Popen(...)`.
fn spawn_detached(program: &Path, args: &[&str]) -> std::io::Result<std::process::Child> {
    let mut command = Command::new(program);
    command.args(args);
    spawn_detached_with(&mut command)
}

/// Start the daemon detached from this process, trying (in order): a
/// sibling Full/Lite binary next to the current `everycli-rs` exe, then
/// `python`/`python3` on PATH running `-m everycli.everycli
/// <DAEMON_RUNNER_ARG>` (dev/source installs) — mirrors
/// `daemon_client.py::_respawn_command`.
///
/// Windows tries `python` first: `python3` there is frequently just the
/// App Execution Alias stub, which spawns "successfully" (so `spawn()`
/// returns `Ok`) but exits immediately without starting anything.
fn spawn_daemon_process(repo_root: &Path) -> bool {
    if let Ok(current_exe) = std::env::current_exe()
        && let Some(exe_dir) = current_exe.parent()
    {
        let env_override = std::env::var("EVERYCLI_DAEMON_BIN").ok();
        for candidate in daemon_binary_candidates(exe_dir, env_override.as_deref()) {
            if spawn_detached(&candidate, &[DAEMON_RUNNER_ARG]).is_ok() {
                return true;
            }
        }
    }

    let candidates: &[&str] = if cfg!(windows) {
        &["python", "python3"]
    } else {
        &["python3", "python"]
    };
    for python in candidates {
        let mut command = Command::new(python);
        command
            .args(["-m", "everycli.everycli", DAEMON_RUNNER_ARG])
            .env("PYTHONPATH", repo_root);
        if spawn_detached_with(&mut command).is_ok() {
            return true;
        }
    }
    false
}

/// Apply detachment settings to an already-configured [`Command`] and spawn
/// it. Shared by [`spawn_detached`] and the `python`/`python3` fallback,
/// which additionally needs `PYTHONPATH` set on the command before spawning.
fn spawn_detached_with(command: &mut Command) -> std::io::Result<std::process::Child> {
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const DETACHED_PROCESS: u32 = 0x0000_0008;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
        command.creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP);
    }

    command.spawn()
}

/// Spawn the daemon and wait (up to [`RESPAWN_TIMEOUT`]) until it answers a
/// ping — mirrors `daemon_client.py::_respawn_daemon`.
pub fn respawn_daemon(config: &DaemonConfig, repo_root: &Path) -> bool {
    if !spawn_daemon_process(repo_root) {
        return false;
    }
    poll_until_ready(|| ping(config), RESPAWN_POLL_INTERVAL, RESPAWN_TIMEOUT)
}

/// Search the daemon, respawning it once if it isn't running.
/// Mirrors the client-side flow in `everycli/infra/daemon_client.py::search`.
pub fn search(
    config: &DaemonConfig,
    repo_root: &Path,
    query: &str,
    top_k: usize,
) -> Result<Vec<DaemonSearchHit>, DaemonError> {
    search_with(config, query, top_k, || respawn_daemon(config, repo_root))
}

#[cfg(test)]
mod tests {
    use std::io::{BufRead, BufReader, Write};
    use std::net::TcpListener;
    use std::thread;
    use std::time::Duration;

    fn mock_daemon(reply: &'static str) -> super::DaemonConfig {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
        let port = listener.local_addr().unwrap().port();
        thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let mut request = String::new();
                let _ = reader.read_line(&mut request);
                let _ = stream.write_all(format!("{reply}\n").as_bytes());
            }
        });
        super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(500),
        }
    }

    #[test]
    fn ping_returns_true_when_daemon_replies_ok() {
        let config = mock_daemon(r#"{"ok":true,"pong":true}"#);
        assert!(super::ping(&config));
    }

    fn touch(dir: &std::path::Path, name: &str) {
        std::fs::write(dir.join(name), b"").expect("write dummy sibling binary");
    }

    fn tempdir() -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "everycli-daemon-candidates-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).expect("create tempdir");
        dir
    }

    #[test]
    fn daemon_binary_candidates_prefers_the_env_override_when_it_exists() {
        let dir = tempdir();
        touch(&dir, "custom-daemon");
        touch(&dir, "everycli-daemon");
        let override_path = dir.join("custom-daemon");
        let candidates =
            super::daemon_binary_candidates(&dir, Some(override_path.to_str().unwrap()));
        assert_eq!(candidates.first(), Some(&override_path));
    }

    #[test]
    fn daemon_binary_candidates_falls_back_to_a_conventional_sibling_name() {
        let dir = tempdir();
        let sibling_name = if cfg!(windows) {
            "everycli-full.exe"
        } else {
            "everycli-full"
        };
        touch(&dir, sibling_name);
        let candidates = super::daemon_binary_candidates(&dir, None);
        assert_eq!(candidates, vec![dir.join(sibling_name)]);
    }

    #[test]
    fn daemon_binary_candidates_is_empty_when_nothing_exists() {
        let dir = tempdir();
        assert!(super::daemon_binary_candidates(&dir, None).is_empty());
    }

    #[test]
    fn daemon_binary_candidates_recognizes_the_real_os_prefixed_release_asset_name() {
        // build.yml's release job actually ships `everycli-windows-full.exe`,
        // `everycli-linux-full`, `everycli-macos-full` (and `-lite` variants)
        // — not the unprefixed `everycli-full` name. A user who downloads the
        // release as-is, without renaming anything, must still be found.
        let dir = tempdir();
        let os_prefix = if cfg!(target_os = "windows") {
            "windows"
        } else if cfg!(target_os = "macos") {
            "macos"
        } else {
            "linux"
        };
        let sibling_name = if cfg!(windows) {
            format!("everycli-{os_prefix}-full.exe")
        } else {
            format!("everycli-{os_prefix}-full")
        };
        touch(&dir, &sibling_name);
        let candidates = super::daemon_binary_candidates(&dir, None);
        assert_eq!(candidates, vec![dir.join(&sibling_name)]);
    }

    #[test]
    fn ping_returns_false_when_nothing_listens() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };
        assert!(!super::ping(&config));
    }

    /// Serves one canned reply per accepted connection, cycling through
    /// `replies` in order (search_once makes a ping connection then a
    /// search connection, exactly like the Python client).
    fn mock_daemon_sequence(replies: &'static [&'static str]) -> super::DaemonConfig {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
        let port = listener.local_addr().unwrap().port();
        thread::spawn(move || {
            for reply in replies {
                if let Ok((mut stream, _)) = listener.accept() {
                    let mut reader = BufReader::new(stream.try_clone().unwrap());
                    let mut request = String::new();
                    let _ = reader.read_line(&mut request);
                    let _ = stream.write_all(format!("{reply}\n").as_bytes());
                }
            }
        });
        super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(500),
        }
    }

    #[test]
    fn search_once_returns_hits_on_success() {
        let config = mock_daemon_sequence(&[
            r#"{"ok":true,"pong":true}"#,
            r#"{"ok":true,"results":[{"id":"docker_build_image","description":"Build an image","command":"docker build -t app .","explanation":"Builds it","warning":"","tags":["docker"],"namespace":"docker","score":0.91}]}"#,
        ]);
        let hits = super::search_once(&config, "docker build", 1).expect("search should succeed");
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].id, "docker_build_image");
        assert_eq!(hits[0].command, "docker build -t app .");
        assert_eq!(hits[0].tags, vec!["docker".to_owned()]);
        assert!((hits[0].score - 0.91).abs() < 1e-6);
    }

    #[test]
    fn search_once_maps_server_error_response() {
        let config = mock_daemon_sequence(&[
            r#"{"ok":true,"pong":true}"#,
            r#"{"ok":false,"code":"EMPTY_QUERY","error":"La requete ne peut pas etre vide"}"#,
        ]);
        let error = super::search_once(&config, "", 1).unwrap_err();
        assert_eq!(
            error,
            super::DaemonError::Server {
                code: "EMPTY_QUERY".to_owned(),
                message: "La requete ne peut pas etre vide".to_owned(),
            }
        );
    }

    #[test]
    fn reload_returns_true_when_daemon_confirms() {
        let config = mock_daemon(r#"{"ok":true,"reloaded":true}"#);
        assert!(super::reload(&config));
    }

    #[test]
    fn reload_returns_false_when_daemon_is_down() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };
        assert!(!super::reload(&config));
    }

    #[test]
    fn search_once_is_unavailable_when_daemon_is_down() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };
        assert_eq!(
            super::search_once(&config, "docker build", 1).unwrap_err(),
            super::DaemonError::Unavailable
        );
    }

    #[test]
    fn search_with_retries_after_successful_respawn() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener); // nothing listens yet: the first ping must fail

        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };

        let hits = super::search_with(&config, "docker build", 1, || {
            // Simulates the daemon coming up as a side effect of respawning.
            // search_with only makes one more connection after a successful
            // respawn (search_once_no_ping — no extra ping), so serve one reply.
            let listener = TcpListener::bind(("127.0.0.1", port)).unwrap();
            thread::spawn(move || {
                if let Ok((mut stream, _)) = listener.accept() {
                    let mut reader = BufReader::new(stream.try_clone().unwrap());
                    let mut request = String::new();
                    let _ = reader.read_line(&mut request);
                    let reply = r#"{"ok":true,"results":[{"id":"docker_build_image","description":"Build","command":"docker build .","explanation":"e","warning":"","tags":[],"namespace":"docker","score":0.5}]}"#;
                    let _ = stream.write_all(format!("{reply}\n").as_bytes());
                }
            });
            true
        })
        .expect("search should succeed after respawn");

        assert_eq!(hits[0].id, "docker_build_image");
    }

    #[test]
    fn search_with_uses_a_longer_timeout_for_the_first_search_after_respawn() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        // The passed-in config's timeout (200ms) is deliberately too short
        // for the 600ms-delayed reply below — the very first real search
        // right after a cold respawn commonly needs several seconds
        // (semantic model warm-up), so it must not be governed by the
        // caller's normal steady-state per-request timeout.
        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };

        let hits = super::search_with(&config, "docker build", 1, || {
            let listener = TcpListener::bind(("127.0.0.1", port)).unwrap();
            thread::spawn(move || {
                if let Ok((mut stream, _)) = listener.accept() {
                    let mut reader = BufReader::new(stream.try_clone().unwrap());
                    let mut request = String::new();
                    let _ = reader.read_line(&mut request);
                    thread::sleep(Duration::from_millis(600));
                    let reply = r#"{"ok":true,"results":[{"id":"docker_build_image","description":"Build","command":"docker build .","explanation":"e","warning":"","tags":[],"namespace":"docker","score":0.5}]}"#;
                    let _ = stream.write_all(format!("{reply}\n").as_bytes());
                }
            });
            true
        })
        .expect("search should still succeed despite a slow first reply after respawn");

        assert_eq!(hits[0].id, "docker_build_image");
    }

    #[test]
    fn search_with_reports_respawn_failed_when_respawn_fails() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let config = super::DaemonConfig {
            host: "127.0.0.1",
            port,
            timeout: Duration::from_millis(200),
        };

        let error = super::search_with(&config, "docker build", 1, || false).unwrap_err();
        assert_eq!(error, super::DaemonError::RespawnFailed);
    }

    #[test]
    fn search_with_does_not_respawn_on_a_server_error() {
        let config = mock_daemon_sequence(&[
            r#"{"ok":true,"pong":true}"#,
            r#"{"ok":false,"code":"EMPTY_QUERY","error":"vide"}"#,
        ]);
        let mut respawn_called = false;
        let error = super::search_with(&config, "", 1, || {
            respawn_called = true;
            true
        })
        .unwrap_err();
        assert!(!respawn_called);
        assert_eq!(
            error,
            super::DaemonError::Server {
                code: "EMPTY_QUERY".to_owned(),
                message: "vide".to_owned(),
            }
        );
    }

    #[test]
    fn poll_until_ready_returns_true_once_the_check_passes() {
        use std::sync::atomic::{AtomicUsize, Ordering};
        let calls = AtomicUsize::new(0);
        let ready = super::poll_until_ready(
            || calls.fetch_add(1, Ordering::SeqCst) >= 2,
            Duration::from_millis(1),
            Duration::from_secs(1),
        );
        assert!(ready);
    }

    #[test]
    fn poll_until_ready_gives_up_after_the_timeout() {
        let ready = super::poll_until_ready(
            || false,
            Duration::from_millis(1),
            Duration::from_millis(20),
        );
        assert!(!ready);
    }
}
