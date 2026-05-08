"""
WebSocket connection manager.
Handles active connections and broadcasts progress events to clients.
"""

import json
import asyncio
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

# Active WebSocket connections keyed by session_id
_connections: dict[str, WebSocket] = {}


async def connect(session_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    _connections[session_id] = websocket
    logger.info("ws_connected", session_id=session_id)


def disconnect(session_id: str) -> None:
    _connections.pop(session_id, None)
    logger.info("ws_disconnected", session_id=session_id)


async def emit(session_id: str, event: str, data: dict) -> None:
    """
    Send a progress event to the client.
    Silently ignores if client is not connected (they'll recover via polling).
    """
    ws = _connections.get(session_id)
    if ws is None:
        return

    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        disconnect(session_id)


async def heartbeat_loop(session_id: str, interval: int = 10) -> None:
    """
    Send a ping every `interval` seconds while the session is active.
    Prevents client-side WebSocket timeout on slow connections.
    """
    while session_id in _connections:
        await asyncio.sleep(interval)
        ws = _connections.get(session_id)
        if ws is None:
            break
        try:
            await ws.send_text(json.dumps({"event": "ping"}))
        except Exception:
            disconnect(session_id)
            break
