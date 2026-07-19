"""
EveryCLI Daemon Client — côté CLI.

Responsabilité unique : envoyer une requête au daemon et retourner
la réponse, ou signaler proprement que le daemon est indisponible.

Gestion d'erreurs (error-handling-patterns) :
  - Result-type explicite : DaemonResult (ok) | DaemonError (ko)
  - Fallback automatique si le daemon est absent ou lent
  - Respawn silencieux si le daemon est mort
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SOCKET_HOST  = "127.0.0.1"
SOCKET_PORT  = int(os.environ.get("EVERYCLI_PORT", "51821"))
TIMEOUT      = float(os.environ.get("EVERYCLI_TIMEOUT", "1.0"))
RESPAWN_WAIT = 10.0   # secondes max pour attendre le daemon après respawn


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class DaemonResult:
    """Réponse valide du daemon."""
    results: list[dict] = field(default_factory=list)


@dataclass
class DaemonError:
    """Erreur daemon — le caller doit basculer en fallback."""
    reason: str
    code: str = "DAEMON_UNAVAILABLE"


# ── Communication bas-niveau ──────────────────────────────────────────────────

def _send_request(payload: dict) -> dict | None:
    """
    Ouvre une connexion TCP, envoie le payload JSON, lit la réponse.
    Retourne None si le daemon est injoignable ou timeout.
    """
    try:
        with socket.create_connection((SOCKET_HOST, SOCKET_PORT), timeout=TIMEOUT) as sock:
            sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            # Lecture ligne par ligne (la réponse tient sur une ligne)
            data = b""
            sock.settimeout(TIMEOUT)
            while not data.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return json.loads(data.decode("utf-8").strip())
    except (ConnectionRefusedError, OSError, TimeoutError, json.JSONDecodeError):
        return None


def ping() -> bool:
    """Retourne True si le daemon répond au ping."""
    resp = _send_request({"action": "ping"})
    return resp is not None and resp.get("ok") is True


# ── Respawn automatique ───────────────────────────────────────────────────────

def _respawn_daemon() -> bool:
    """
    Lance le daemon en arrière-plan et attend qu'il soit prêt.
    Retourne True si le daemon répond dans RESPAWN_WAIT secondes.
    """
    try:
        subprocess.Popen(
            [sys.executable, "-m", "everycli.infra.daemon_runner"],
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent.parent)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,   # Détache du terminal courant
        )
    except Exception:
        return False

    deadline = time.monotonic() + RESPAWN_WAIT
    while time.monotonic() < deadline:
        time.sleep(0.2)
        if ping():
            return True
    return False


# ── API publique ──────────────────────────────────────────────────────────────

# def search(query: str, top_k: int = 1) -> DaemonResult | DaemonError:
#     """
#     Envoie une requête de recherche au daemon.

#     Comportement :
#       1. Ping rapide → daemon vivant → search direct
#       2. Daemon absent → respawn silencieux → search
#       3. Respawn échoue → DaemonError (caller bascule en fallback)
#     """
#     if not ping():
#         # Daemon absent — on tente un respawn silencieux
#         import sys as _sys
#         from rich.console import Console
#         Console().print(
#             "  [yellow]⚡ Daemon absent — démarrage automatique...[/yellow]",
#             highlight=False,
#         )
#         ok = _respawn_daemon()
#         if not ok:
#             return DaemonError(
#                 reason=(
#                     "Impossible de démarrer le daemon automatiquement. "
#                     "Lance 'everycli daemon --start' pour l'activer."
#                 ),
#                 code="RESPAWN_FAILED",
#             )

#     resp = _send_request({"action": "search", "query": query, "top_k": top_k})

#     if resp is None:
#         return DaemonError(
#             reason="Le daemon ne répond pas (timeout).",
#             code="TIMEOUT",
#         )

#     if not resp.get("ok"):
#         return DaemonError(
#             reason=resp.get("error", "Erreur inconnue"),
#             code=resp.get("code", "DAEMON_ERROR"),
#         )

#     return DaemonResult(results=resp.get("results", []))

def search(query: str, top_k: int = 1, console=None) -> DaemonResult | DaemonError:
    from everycli.infra.context_detector import ProjectContextDetector
    # Détecté ICI, côté client, car c'est le seul endroit où le cwd correspond
    # réellement au dossier de l'utilisateur au moment de cette requête précise.
    context = ProjectContextDetector().detect()
    payload = {"action": "search", "query": query, "top_k": top_k, "context": context}

    # 1. Ping rapide — si le daemon est absent on tente un respawn avant d'envoyer
    if not ping():
        (console or __import__("rich.console", fromlist=["Console"]).Console()).print(
            "  [yellow]⚡ Daemon absent — démarrage automatique...[/yellow]",
            highlight=False,
        )
        ok = _respawn_daemon()
        if not ok:
            return DaemonError(
                reason="Impossible de démarrer le daemon. Lance 'everycli daemon --start'.",
                code="RESPAWN_FAILED",
            )

    resp = _send_request(payload)

    if resp is None:
        return DaemonError(reason="Le daemon ne répond pas (timeout).", code="TIMEOUT")

    if not resp.get("ok"):
        return DaemonError(
            reason=resp.get("error", "Erreur inconnue"),
            code=resp.get("code", "DAEMON_ERROR"),
        )

    return DaemonResult(results=resp.get("results", []))

def send_reload() -> bool:
    """
    Demande au daemon de recharger la base de scénarios.
    Appelé par `everycli add` après l'écriture YAML.
    Silencieux si le daemon est absent (pas critique).
    """
    resp = _send_request({"action": "reload"})
    return resp is not None and resp.get("ok") is True