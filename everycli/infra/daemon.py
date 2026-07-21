"""
EveryCLI Daemon — Point d'entrée haute performance.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

from everycli.infra.daemon_manager import DaemonManager
from everycli.infra.daemon_server import DaemonServer

logger = logging.getLogger("everycli.daemon")


def _daemon_port() -> int:
    """Read fresh at call time (not module import time) so tests and a
    changed environment both see the current value, matching the client's
    own `EVERYCLI_PORT` convention (`daemon_client.SOCKET_PORT`)."""
    return int(os.environ.get("EVERYCLI_PORT", "51821"))


def _build_engine():
    from everycli.core.search_engine import SearchEngine
    from everycli.infra.os_resolver import OSResolver
    from everycli.infra.yaml_loader import YamlLoader
    from everycli.infra.hybrid_matcher import HybridMatcher

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        data_dir = Path(sys._MEIPASS) / "everycli" / "data" / "commands"
    else:
        data_dir = Path(__file__).parent.parent / "data" / "commands"

    # Pas de ContextDetector injecté ici : le daemon est un process résident
    # dont le cwd ne reflète pas le dossier réel de l'utilisateur au moment
    # de chaque requête. Le contexte est détecté côté client et transmis
    # dans le payload (voir daemon_client.py / daemon_server.py).
    return SearchEngine(
        loader=YamlLoader(data_dir),
        matcher=HybridMatcher(semantic_weight=0.6),
        os_resolver=OSResolver(),
    )

def start_daemon(debug: bool = False):
    manager = DaemonManager()
    if manager.is_running():
        print(f"[daemon] Le daemon tourne déjà (PID {manager.read_pid()}).")
        return

    print("[daemon] Chargement de l'intelligence artificielle...")
    engine = _build_engine()
    engine.boot()

    server = DaemonServer(engine, port=_daemon_port())
    
    manager.write_pid(os.getpid())
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
    finally:
        manager.clear_pid()

def stop_daemon():
    manager = DaemonManager()
    if manager.stop():
        print("[daemon] Signal d'arrêt envoyé.")
    else:
        print("[daemon] Aucun daemon en cours d'exécution.")

def status_daemon():
    manager = DaemonManager()
    if manager.is_running():
        print(f"[daemon] Actif (PID {manager.read_pid()})")
    else:
        print("[daemon] Arrêté.")

def show_logs():
    from everycli.infra.daemon import LOG_FILE
    if LOG_FILE.exists():
        print(LOG_FILE.read_text())
    else:
        print("[daemon] Aucun log trouvé.")

def install_systemd_service():
    # Garder la logique systemd ici ou la déplacer dans un script utilitaire
    pass