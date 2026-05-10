"""
Tests pour infra/daemon_client.py

Couvre : ping, _send_request (timeout/refus), search (ok/fallback),
         send_reload, respawn.
Zéro connexion réseau réelle — tout est mocké via unittest.mock.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from everycli.infra.daemon_client import (
    DaemonError,
    DaemonResult,
    ping,
    search,
    send_reload,
    _send_request,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_response(**kwargs) -> bytes:
    """Encode un dict en ligne JSON comme le ferait le daemon."""
    return (json.dumps(kwargs) + "\n").encode("utf-8")


# ── Tests : _send_request ─────────────────────────────────────────────────────

class TestSendRequest:
    def test_returns_none_on_connection_refused(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            result = _send_request({"action": "ping"})
        assert result is None

    def test_returns_none_on_timeout(self):
        with patch("socket.create_connection", side_effect=TimeoutError):
            result = _send_request({"action": "ping"})
        assert result is None

    def test_returns_none_on_bad_json(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"not json\n"
        with patch("socket.create_connection", return_value=mock_sock):
            result = _send_request({"action": "ping"})
        assert result is None

    def test_returns_dict_on_valid_response(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.side_effect = [_make_response(ok=True, pong=True), b""]
        with patch("socket.create_connection", return_value=mock_sock):
            result = _send_request({"action": "ping"})
        assert result == {"ok": True, "pong": True}


# ── Tests : ping ──────────────────────────────────────────────────────────────

class TestPing:
    def test_returns_true_when_daemon_responds(self):
        with patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": True, "pong": True}):
            assert ping() is True

    def test_returns_false_when_daemon_absent(self):
        with patch("everycli.infra.daemon_client._send_request", return_value=None):
            assert ping() is False

    def test_returns_false_when_ok_is_false(self):
        with patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": False}):
            assert ping() is False


# ── Tests : search ────────────────────────────────────────────────────────────

FAKE_RESULT = {
    "id": "git_test",
    "description": "Tester git",
    "command": "git test",
    "explanation": "Test.",
    "warning": "",
    "score": 0.9,
    "tags": ["git"],
}


class TestSearch:
    def test_returns_daemon_result_when_daemon_alive(self):
        with patch("everycli.infra.daemon_client.ping", return_value=True), \
             patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": True, "results": [FAKE_RESULT]}):
            result = search("tester git", top_k=1)
        assert isinstance(result, DaemonResult)
        assert len(result.results) == 1
        assert result.results[0]["id"] == "git_test"

    def test_attempts_respawn_when_daemon_absent(self):
        with patch("everycli.infra.daemon_client.ping", return_value=False), \
             patch("everycli.infra.daemon_client._respawn_daemon", return_value=False) as mock_respawn:
            result = search("test")
        mock_respawn.assert_called_once()
        assert isinstance(result, DaemonError)
        assert result.code == "RESPAWN_FAILED"

    def test_returns_daemon_result_after_successful_respawn(self):
        with patch("everycli.infra.daemon_client.ping", return_value=False), \
             patch("everycli.infra.daemon_client._respawn_daemon", return_value=True), \
             patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": True, "results": [FAKE_RESULT]}):
            result = search("test")
        assert isinstance(result, DaemonResult)

    def test_returns_daemon_error_on_timeout(self):
        with patch("everycli.infra.daemon_client.ping", return_value=True), \
             patch("everycli.infra.daemon_client._send_request", return_value=None):
            result = search("test")
        assert isinstance(result, DaemonError)
        assert result.code == "TIMEOUT"

    def test_returns_daemon_error_when_ok_false(self):
        with patch("everycli.infra.daemon_client.ping", return_value=True), \
             patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": False, "error": "SEARCH_ERROR", "code": "SEARCH_ERROR"}):
            result = search("test")
        assert isinstance(result, DaemonError)
        assert result.code == "SEARCH_ERROR"

    def test_empty_results_list_is_valid(self):
        with patch("everycli.infra.daemon_client.ping", return_value=True), \
             patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": True, "results": []}):
            result = search("rien du tout")
        assert isinstance(result, DaemonResult)
        assert result.results == []


# ── Tests : send_reload ───────────────────────────────────────────────────────

class TestSendReload:
    def test_returns_true_on_success(self):
        with patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": True, "reloaded": True}):
            assert send_reload() is True

    def test_returns_false_when_daemon_absent(self):
        with patch("everycli.infra.daemon_client._send_request", return_value=None):
            assert send_reload() is False

    def test_returns_false_on_reload_error(self):
        with patch("everycli.infra.daemon_client._send_request",
                   return_value={"ok": False, "code": "RELOAD_ERROR"}):
            assert send_reload() is False
