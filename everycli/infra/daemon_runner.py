"""
everycli/infra/daemon_runner.py

Point d'entrée minimal pour lancer le daemon via :
    python -m everycli.infra.daemon_runner

Utilisé par daemon_client._respawn_daemon() pour le démarrage automatique.
"""

from everycli.infra.daemon import start_daemon

if __name__ == "__main__":
    start_daemon()
