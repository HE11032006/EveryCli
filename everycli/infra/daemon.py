"""
EveryCLI Daemon — serveur TCP léger qui garde le modèle en mémoire.

Architecture (Hexagonal / Ports & Adapters) :
  Port entrant  : connexion TCP JSON (query → résultats)
  Port sortant  : SearchEngine (loader + matcher + os_resolver)

Gestion d'erreurs : Result-type interne, jamais de crash silencieux.
Perf : asyncio mono-thread, <10 Mo RAM hors modèle sémantique.
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Configuration ──────────────────────────────────────────────────────────────

EVERYCLI_DIR = Path.home() / ".everycli"
PID_FILE     = EVERYCLI_DIR / "daemon.pid"
LOG_FILE     = EVERYCLI_DIR / "daemon.log"
SOCKET_HOST  = "127.0.0.1"
SOCKET_PORT  = int(os.environ.get("EVERYCLI_PORT", "51821"))
DEBUG        = os.environ.get("EVERYCLI_DEBUG", "").lower() in ("1", "true", "yes")


# ── Logging ────────────────────────────────────────────────────────────────────

def _build_logger(debug: bool = False) -> logging.Logger:
    EVERYCLI_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("everycli.daemon")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers.clear()

    # Rotation : 1 Mo max, 3 fichiers gardés
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter("[daemon] %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger = _build_logger(DEBUG)


# ── Result type — pas de crash silencieux ─────────────────────────────────────

@dataclass
class Ok:
    value: Any


@dataclass
class Err:
    message: str
    code: str = "INTERNAL_ERROR"


# ── PID — singleton strict ────────────────────────────────────────────────────

def _write_pid() -> None:
    EVERYCLI_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    logger.debug(f"PID {os.getpid()} écrit dans {PID_FILE}")


def _clear_pid() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Impossible de supprimer {PID_FILE} : {e}")


def read_pid() -> int | None:
    """Lit le PID depuis le fichier. Retourne None si absent ou invalide."""
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_running(pid: int) -> bool:
    """Vérifie si un process avec ce PID est vivant (cross-platform)."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except Exception:
        return False


def check_singleton() -> Ok | Err:
    """
    Vérifie qu'aucun daemon ne tourne déjà.
    Nettoie le PID file si le process précédent est mort.
    """
    pid = read_pid()
    if pid is None:
        return Ok(None)

    if is_running(pid):
        return Err(
            f"Le daemon tourne déjà (PID {pid}). Lance 'everycli daemon --stop' d'abord.",
            code="ALREADY_RUNNING",
        )

    # Process mort mais fichier orphelin — on nettoie
    logger.warning(f"PID file orphelin (PID {pid} mort) — nettoyage.")
    _clear_pid()
    return Ok(None)


# ── SearchEngine — chargé une seule fois ─────────────────────────────────────

def _build_engine():
    """Construit et boot le SearchEngine. Lève une exception si ça échoue."""
    from pathlib import Path as _Path
    from everycli.core.search_engine import SearchEngine
    from everycli.infra.os_resolver import OSResolver
    from everycli.infra.yaml_loader import YamlLoader
    from everycli.infra.hybrid_matcher import HybridMatcher

    data_dir = _Path(__file__).parent.parent / "data" / "commands"
    engine = SearchEngine(
        loader=YamlLoader(data_dir),
        matcher=HybridMatcher(semantic_weight=0.6),
        os_resolver=OSResolver(),
    )
    engine.boot()
    return engine


# ── Handlers TCP ──────────────────────────────────────────────────────────────

async def _handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    engine,
) -> None:
    """
    Protocole JSON minimaliste :
      requête  → {"action": "search", "query": "...", "top_k": 3}
               | {"action": "reload"}
               | {"action": "ping"}
      réponse  → {"ok": true,  "results": [...]}
               | {"ok": false, "error": "...", "code": "..."}
    """
    peer = writer.get_extra_info("peername", "?")
    try:
        raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not raw:
            return

        try:
            request = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            await _send(writer, {"ok": False, "error": str(e), "code": "BAD_JSON"})
            return

        action = request.get("action", "")
        logger.debug(f"{peer} → action={action}")

        if action == "ping":
            await _send(writer, {"ok": True, "pong": True})

        elif action == "search":
            result = _do_search(engine, request)
            await _send(writer, result)

        elif action == "reload":
            result = _do_reload(engine)
            await _send(writer, result)

        else:
            await _send(writer, {
                "ok": False,
                "error": f"Action inconnue : '{action}'",
                "code": "UNKNOWN_ACTION",
            })

    except asyncio.TimeoutError:
        logger.warning(f"{peer} timeout lecture")
        await _send(writer, {"ok": False, "error": "Timeout", "code": "TIMEOUT"})
    except Exception as e:
        logger.exception(f"{peer} erreur inattendue")
        await _send(writer, {"ok": False, "error": str(e), "code": "INTERNAL_ERROR"})
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _send(writer: asyncio.StreamWriter, payload: dict) -> None:
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    writer.write(line.encode("utf-8"))
    await writer.drain()


def _do_search(engine, request: dict) -> dict:
    query = request.get("query", "").strip()
    top_k = int(request.get("top_k", 1))

    if not query:
        return {"ok": False, "error": "'query' est vide.", "code": "EMPTY_QUERY"}

    try:
        results = engine.search(query, top_k=top_k)
        return {
            "ok": True,
            "results": [
                {
                    "id":          r.scenario.id,
                    "description": r.scenario.description,
                    "command":     r.resolved_command,
                    "explanation": r.scenario.explanation,
                    "warning":     r.scenario.warning,
                    "score":       r.score,
                    "tags":        r.scenario.tags,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.exception("Erreur pendant la recherche")
        return {"ok": False, "error": str(e), "code": "SEARCH_ERROR"}


def _do_reload(engine) -> dict:
    try:
        engine.boot()
        logger.info("Base rechargée avec succès.")
        return {"ok": True, "reloaded": True}
    except Exception as e:
        logger.exception("Erreur pendant le reload")
        return {"ok": False, "error": str(e), "code": "RELOAD_ERROR"}


# ── Serveur principal ─────────────────────────────────────────────────────────

async def _serve(engine) -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(*_):
        logger.info("Signal reçu — arrêt du daemon.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            # Windows ne supporte pas add_signal_handler
            signal.signal(sig, _shutdown)

    server = await asyncio.start_server(
        lambda r, w: _handle_client(r, w, engine),
        host=SOCKET_HOST,
        port=SOCKET_PORT,
    )

    logger.info(f"Daemon prêt sur {SOCKET_HOST}:{SOCKET_PORT} (PID {os.getpid()})")
    _write_pid()

    async with server:
        await stop_event.wait()

    logger.info("Daemon arrêté proprement.")


# ── Points d'entrée publics ───────────────────────────────────────────────────

def start_daemon(debug: bool = False) -> None:
    """
    Vérifie le singleton, charge le moteur, lance la boucle asyncio.
    Appelé par `everycli daemon --start`.
    """
    global logger
    logger = _build_logger(debug)

    result = check_singleton()
    if isinstance(result, Err):
        print(f"[daemon] {result.message}")
        sys.exit(1)

    logger.info("Chargement du moteur de recherche...")
    try:
        engine = _build_engine()
    except Exception as e:
        logger.error(f"Impossible de charger le moteur : {e}")
        sys.exit(1)

    logger.info("Moteur prêt.")

    try:
        asyncio.run(_serve(engine))
    except KeyboardInterrupt:
        pass
    finally:
        _clear_pid()
        logger.info("PID file supprimé. Bye.")


def stop_daemon() -> None:
    """Envoie SIGTERM au daemon et attend sa mort."""
    pid = read_pid()
    if pid is None:
        print("[daemon] Aucun daemon en cours.")
        return

    if not is_running(pid):
        print(f"[daemon] PID {pid} introuvable — nettoyage du fichier orphelin.")
        _clear_pid()
        return

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"[daemon] SIGTERM envoyé (PID {pid}).")
    except Exception as e:
        print(f"[daemon] Impossible d'arrêter le daemon : {e}")


def status_daemon() -> None:
    """Affiche l'état du daemon."""
    pid = read_pid()
    if pid is None:
        print("[daemon] Arrêté (pas de PID file).")
        return
    if is_running(pid):
        print(f"[daemon] Actif — PID {pid} — port {SOCKET_PORT}")
    else:
        print(f"[daemon] PID file présent ({pid}) mais process mort — lancer --start.")


def show_logs() -> None:
    """Affiche le contenu du log."""
    if not LOG_FILE.exists():
        print("[daemon] Aucun log pour l'instant.")
        return
    print(LOG_FILE.read_text(encoding="utf-8"))
