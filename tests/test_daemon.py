"""Tests for the daemon lifecycle and protocol after the daemon refactor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from everycli.core.models import Command, Scenario, SearchResult
from everycli.infra.daemon_manager import DaemonManager
from everycli.infra.daemon_server import DaemonServer


def _server() -> tuple[DaemonServer, MagicMock]:
    scenario = Scenario(
        id="git_status",
        description="Show repository status",
        tags=["git", "status"],
        command=Command(linux="git status", windows="git status"),
        explanation="Displays the working tree status.",
        warning="",
        namespace="git",
    )
    engine = MagicMock()
    engine.search.return_value = [
        SearchResult(scenario=scenario, resolved_command="git status", score=0.95)
    ]
    return DaemonServer(engine), engine


def test_daemon_manager_reads_writes_and_clears_pid(tmp_path):
    manager = DaemonManager(tmp_path / "runtime" / "daemon.pid")
    manager.write_pid(1234)
    assert manager.read_pid() == 1234
    manager.clear_pid()
    assert manager.read_pid() is None


def test_daemon_manager_cleans_orphaned_pid(tmp_path):
    manager = DaemonManager(tmp_path / "daemon.pid")
    manager.write_pid(999999)
    with patch("everycli.infra.daemon_manager.os.kill", side_effect=ProcessLookupError):
        assert manager.stop() is False
    assert manager.read_pid() is None


def test_search_returns_complete_protocol_payload():
    server, engine = _server()
    response = server._do_search({"query": "repository status", "top_k": 1, "context": ["git"]})

    assert response["ok"] is True
    result = response["results"][0]
    assert result["tags"] == ["git", "status"]
    assert result["namespace"] == "git"
    engine.search.assert_called_once_with("repository status", top_k=1, context_override=["git"])


def test_search_rejects_an_empty_query():
    server, _ = _server()
    assert server._do_search({"query": "   "})["code"] == "EMPTY_QUERY"


def test_search_rejects_invalid_top_k():
    server, _ = _server()
    assert server._do_search({"query": "status", "top_k": "many"})["code"] == "INVALID_TOP_K"


def test_search_reports_engine_failures():
    server, engine = _server()
    engine.search.side_effect = RuntimeError("engine failed")
    response = server._do_search({"query": "status"})
    assert response == {"ok": False, "code": "SEARCH_ERROR", "error": "engine failed"}
