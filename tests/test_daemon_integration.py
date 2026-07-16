"""TCP-level daemon tests using a fake search engine, without model downloads."""

import asyncio
import json
from unittest.mock import MagicMock

from everycli.infra.daemon_server import DaemonServer


def _request(payload: bytes, engine: MagicMock | None = None) -> dict:
    async def run() -> dict:
        server_impl = DaemonServer(engine or MagicMock())
        tcp_server = await asyncio.start_server(server_impl._handle_client, "127.0.0.1", 0)
        port = tcp_server.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(payload)
            await writer.drain()
            response = await reader.readline()
            writer.close()
            await writer.wait_closed()
            return json.loads(response.decode("utf-8"))
        finally:
            tcp_server.close()
            await tcp_server.wait_closed()

    return asyncio.run(run())


def test_ping_round_trip():
    assert _request(b'{"action":"ping"}\n') == {"ok": True, "pong": True}


def test_unknown_action_returns_a_protocol_error():
    response = _request(b'{"action":"nope"}\n')
    assert response["code"] == "UNKNOWN_ACTION"


def test_invalid_json_returns_a_protocol_error():
    response = _request(b'not json\n')
    assert response["code"] == "BAD_JSON"


def test_reload_boots_the_engine():
    engine = MagicMock()
    assert _request(b'{"action":"reload"}\n', engine) == {"ok": True, "reloaded": True}
    engine.boot.assert_called_once()
