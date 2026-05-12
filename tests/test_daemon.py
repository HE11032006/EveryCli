"""
Tests pour infra/daemon.py

Couvre : singleton PID, lecture/écriture PID, check_singleton,
         _do_search, _do_reload, protocole JSON.
Zéro I/O réseau réel — tout est mocké.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from everycli.infra.daemon import (
    check_singleton,
    is_running,
    read_pid,
    _do_search,
    _do_reload,
)
from everycli.core.models import Command, Scenario, SearchResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_pid_file(tmp_path, monkeypatch):
    """Redirige PID_FILE vers un fichier temporaire."""
    pid_file = tmp_path / "daemon.pid"
    monkeypatch.setattr("everycli.infra.daemon.PID_FILE", pid_file)
    return pid_file


@pytest.fixture
def fake_scenario():
    return Scenario(
        id="git_test",
        description="Tester git",
        tags=["git", "test"],
        command=Command(linux="git test", windows="git test"),
        explanation="Juste un test.",
        warning="",
    )


@pytest.fixture
def fake_engine(fake_scenario):
    result = SearchResult(
        scenario=fake_scenario,
        resolved_command="git test",
        score=0.95,
    )
    engine = MagicMock()
    engine.search.return_value = [result]
    return engine


# ── Tests : is_running ────────────────────────────────────────────────────────

class TestIsRunning:
    def test_current_process_is_running(self):
        assert is_running(os.getpid()) is True

    def test_dead_pid_returns_false(self):
        # PID 999999 quasi certainement inexistant
        assert is_running(999999) is False


# ── Tests : read_pid ──────────────────────────────────────────────────────────

class TestReadPid:
    def test_returns_none_when_file_absent(self, tmp_pid_file):
        assert read_pid() is None

    def test_returns_pid_when_file_present(self, tmp_pid_file):
        tmp_pid_file.write_text("1234", encoding="utf-8")
        assert read_pid() == 1234

    def test_returns_none_on_invalid_content(self, tmp_pid_file):
        tmp_pid_file.write_text("not_a_number", encoding="utf-8")
        assert read_pid() is None


# ── Tests : check_singleton ───────────────────────────────────────────────────

class TestCheckSingleton:
    def test_ok_when_no_pid_file(self, tmp_pid_file):
        from everycli.infra.daemon import Ok
        result = check_singleton()
        assert isinstance(result, Ok)

    def test_err_when_daemon_already_running(self, tmp_pid_file):
        from everycli.infra.daemon import Err
        # PID du process courant = vivant
        tmp_pid_file.write_text(str(os.getpid()), encoding="utf-8")
        result = check_singleton()
        assert isinstance(result, Err)
        assert result.code == "ALREADY_RUNNING"

    def test_ok_and_cleans_orphan_pid(self, tmp_pid_file):
        from everycli.infra.daemon import Ok
        # PID mort (999999)
        tmp_pid_file.write_text("999999", encoding="utf-8")
        result = check_singleton()
        assert isinstance(result, Ok)
        # Le fichier orphelin doit avoir été supprimé
        assert not tmp_pid_file.exists()


# ── Tests : _do_search ────────────────────────────────────────────────────────

class TestDoSearch:
    def test_returns_ok_with_results(self, fake_engine):
        resp = _do_search(fake_engine, {"query": "tester git", "top_k": 1})
        assert resp["ok"] is True
        assert len(resp["results"]) == 1
        assert resp["results"][0]["id"] == "git_test"
        assert resp["results"][0]["command"] == "git test"
        assert resp["results"][0]["score"] == 0.95

    def test_returns_error_on_empty_query(self, fake_engine):
        resp = _do_search(fake_engine, {"query": "", "top_k": 1})
        assert resp["ok"] is False
        assert resp["code"] == "EMPTY_QUERY"

    def test_returns_error_on_whitespace_query(self, fake_engine):
        resp = _do_search(fake_engine, {"query": "   ", "top_k": 1})
        assert resp["ok"] is False
        assert resp["code"] == "EMPTY_QUERY"

    def test_handles_engine_exception(self, fake_engine):
        fake_engine.search.side_effect = RuntimeError("moteur cassé")
        resp = _do_search(fake_engine, {"query": "test", "top_k": 1})
        assert resp["ok"] is False
        assert resp["code"] == "SEARCH_ERROR"
        assert "moteur cassé" in resp["error"]

    def test_default_top_k_is_1(self, fake_engine):
        resp = _do_search(fake_engine, {"query": "test"})
        assert resp["ok"] is True
        fake_engine.search.assert_called_once_with("test", top_k=1)

    def test_result_contains_all_fields(self, fake_engine):
        resp = _do_search(fake_engine, {"query": "test", "top_k": 1})
        result = resp["results"][0]
        for field in ("id", "description", "command", "explanation", "warning", "score", "tags"):
            assert field in result


# ── Tests : _do_reload ────────────────────────────────────────────────────────

class TestDoReload:
    def test_returns_ok_on_success(self, fake_engine):
        resp = _do_reload(fake_engine)
        assert resp["ok"] is True
        assert resp["reloaded"] is True
        fake_engine.boot.assert_called_once()

    def test_returns_error_on_engine_failure(self, fake_engine):
        fake_engine.boot.side_effect = RuntimeError("impossible de charger")
        resp = _do_reload(fake_engine)
        assert resp["ok"] is False
        assert resp["code"] == "RELOAD_ERROR"
        assert "impossible de charger" in resp["error"]
