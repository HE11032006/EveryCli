"""
Tests d'intégration daemon — test end-to-end complet.

Lance un vrai daemon sur un port éphémère, fait de vraies requêtes TCP,
vérifie les réponses, puis l'arrête proprement.

Nécessite que le SearchEngine puisse se booter (fichiers YAML présents).
Ces tests sont plus lents (~5s au premier run à cause du modèle sémantique).
"""

import asyncio
import json
import os
import socket
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tcp_send(port: int, payload: dict, timeout: float = 5.0) -> dict | None:
    """Envoie une requête JSON au daemon et retourne la réponse."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
            sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            data = b""
            sock.settimeout(timeout)
            while not data.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return json.loads(data.decode("utf-8").strip())
    except Exception:
        return None


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    """Attend que le port TCP soit disponible."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.2)
    return False


# ── Fixture : daemon sur port éphémère ───────────────────────────────────────

TEST_PORT = 51899   # Port dédié aux tests, différent du port prod (51821)


@pytest.fixture(scope="module")
def running_daemon():
    """
    Lance un vrai daemon en arrière-plan pour toute la suite de tests.
    L'arrête proprement à la fin via SIGTERM.
    """
    import threading
    from everycli.infra import daemon as daemon_mod

    # Redirige le port et les fichiers vers des chemins de test
    original_port = daemon_mod.SOCKET_PORT
    daemon_mod.SOCKET_PORT = TEST_PORT

    stop_event = threading.Event()
    daemon_thread = None

    def _run():
        from everycli.infra.daemon import _build_engine, _serve, _write_pid, _clear_pid
        import asyncio

        engine = _build_engine()
        _write_pid()

        async def _run_async():
            server = await asyncio.start_server(
                lambda r, w: daemon_mod._handle_client(r, w, engine),
                host="127.0.0.1",
                port=TEST_PORT,
            )
            async with server:
                # Tourne jusqu'à ce que stop_event soit set
                while not stop_event.is_set():
                    await asyncio.sleep(0.1)

        asyncio.run(_run_async())
        _clear_pid()

    daemon_thread = threading.Thread(target=_run, daemon=True)
    daemon_thread.start()

    # Attendre que le port soit prêt
    ready = _wait_for_port(TEST_PORT, timeout=15.0)
    if not ready:
        pytest.skip("Daemon non prêt dans les temps — modèle trop lent ?")

    yield TEST_PORT

    # Teardown
    stop_event.set()
    daemon_thread.join(timeout=3.0)
    daemon_mod.SOCKET_PORT = original_port


# ── Tests d'intégration ───────────────────────────────────────────────────────

class TestDaemonIntegration:
    def test_ping_returns_pong(self, running_daemon):
        resp = _tcp_send(running_daemon, {"action": "ping"})
        assert resp is not None
        assert resp["ok"] is True
        assert resp["pong"] is True

    def test_search_returns_results(self, running_daemon):
        resp = _tcp_send(running_daemon, {
            "action": "search",
            "query": "modifier message dernier commit",
            "top_k": 1,
        })
        assert resp is not None
        assert resp["ok"] is True
        assert len(resp["results"]) >= 1
        result = resp["results"][0]
        assert "command" in result
        assert "description" in result
        assert "score" in result

    def test_search_empty_query_returns_error(self, running_daemon):
        resp = _tcp_send(running_daemon, {"action": "search", "query": ""})
        assert resp is not None
        assert resp["ok"] is False
        assert resp["code"] == "EMPTY_QUERY"

    def test_unknown_action_returns_error(self, running_daemon):
        resp = _tcp_send(running_daemon, {"action": "does_not_exist"})
        assert resp is not None
        assert resp["ok"] is False
        assert resp["code"] == "UNKNOWN_ACTION"

    def test_bad_json_returns_error(self, running_daemon):
        try:
            with socket.create_connection(("127.0.0.1", running_daemon), timeout=3.0) as sock:
                sock.sendall(b"not valid json\n")
                data = sock.recv(4096)
                resp = json.loads(data.decode("utf-8").strip())
            assert resp["ok"] is False
            assert resp["code"] == "BAD_JSON"
        except Exception as e:
            pytest.fail(f"Connexion échouée : {e}")

    def test_reload_returns_ok(self, running_daemon):
        resp = _tcp_send(running_daemon, {"action": "reload"})
        assert resp is not None
        assert resp["ok"] is True
        assert resp["reloaded"] is True

    def test_concurrent_requests(self, running_daemon):
        """Vérifie que le daemon gère plusieurs requêtes simultanées."""
        import threading

        responses = []
        errors = []

        def _do_request():
            resp = _tcp_send(running_daemon, {
                "action": "search",
                "query": "lister les fichiers",
                "top_k": 1,
            })
            if resp is None:
                errors.append("no response")
            else:
                responses.append(resp)

        threads = [threading.Thread(target=_do_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Erreurs : {errors}"
        assert len(responses) == 5
        assert all(r["ok"] for r in responses)

    def test_search_git_commit_message(self, running_daemon):
        """Test fonctionnel : la query emblématique du projet doit trouver un résultat."""
        resp = _tcp_send(running_daemon, {
            "action": "search",
            "query": "comment modifier un message dans tous mes commits",
            "top_k": 1,
        })
        assert resp is not None
        assert resp["ok"] is True
        assert len(resp["results"]) == 1
        # Le résultat doit être lié à git
        assert "git" in resp["results"][0]["tags"]
