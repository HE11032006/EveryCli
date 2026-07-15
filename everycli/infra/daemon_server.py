"""
DaemonServer — serveur TCP asynchrone pour EveryCli.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Optional
from everycli.core.search_engine import SearchEngine

logger = logging.getLogger("everycli.daemon")

class DaemonServer:
    def __init__(self, engine: SearchEngine, host: str = "127.0.0.1", port: int = 51821):
        self.engine = engine
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None

    async def start(self):
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                host=self.host,
                port=self.port,
            )
            logger.info(f"Serveur TCP prêt sur {self.host}:{self.port}")
            async with self._server:
                await self._server.serve_forever()
        except OSError as e:
            logger.error(f"Erreur serveur (port {self.port}) : {e}")
            raise

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername", "?")
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not raw: return

            request = json.loads(raw.decode("utf-8"))
            action = request.get("action", "")

            if action == "search":
                response = self._do_search(request)
            elif action == "ping":
                response = {"ok": True, "pong": True}
            elif action == "reload":
                self.engine.boot()
                response = {"ok": True, "reloaded": True}
            else:
                response = {"ok": False, "error": "Action inconnue"}

            writer.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
            await writer.drain()

        except Exception as e:
            logger.error(f"Erreur client {peer} : {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    def _do_search(self, request: dict) -> dict:
        query = request.get("query", "").strip()
        top_k = int(request.get("top_k", 1))
        # Le daemon est un process résident: son propre cwd n'a aucun rapport
        # avec le dossier où l'utilisateur tape sa commande. Le client détecte
        # le contexte (composer.json, .git, ...) dans SON cwd et le transmet
        # ici — voir daemon_client.py.
        context = request.get("context", None)

        try:
            results = self.engine.search(query, top_k=top_k, context_override=context)
            return {
                "ok": True,
                "results": [
                    {
                        "id": r.scenario.id,
                        "description": r.scenario.description,
                        "command": r.resolved_command,
                        "explanation": r.scenario.explanation,
                        "namespace": r.scenario.namespace,
                        "score": r.score,
                    } for r in results
                ]
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}