import asyncio
import json
import logging

import jwt
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import settings
from app.schemas.events import EVENT_SCHEMAS

logger = logging.getLogger(__name__)

# A frozen/backgrounded browser tab stops draining its socket; without a cap a
# producer awaiting the broadcast (the indexing / memory pipeline) would block
# on TCP backpressure behind the slowest consumer.
SEND_TIMEOUT_SECONDS = 5.0


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        # Serialize the per-connection send fan-out: broadcast() is awaited from
        # many concurrent coroutines (pipeline fan-out, indexing, jobs, reembed)
        # and Starlette's WebSocket.send is not safe for concurrent senders on
        # one socket — interleaved ASGI sends raise and kill the connection.
        self._send_lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, event_type: str, data: dict):
        schema = EVENT_SCHEMAS.get(event_type)
        if schema:
            try:
                schema.model_validate(data)
            except ValidationError as e:
                logger.warning("Event '%s' data does not match schema: %s", event_type, e)
        message = json.dumps({"event": event_type, "data": data})
        dead: list[WebSocket] = []
        async with self._send_lock:
            for ws in list(self.connections):
                try:
                    await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)


event_manager = EventManager()


async def websocket_endpoint(ws: WebSocket):
    from app.api.auth import COOKIE_NAME
    token = ws.cookies.get(COOKIE_NAME)
    if not token:
        await ws.close(code=1008, reason="Unauthorized")
        return
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        await ws.close(code=1008, reason="Unauthorized")
        return

    jti = payload.get("jti")
    if not jti:
        await ws.close(code=1008, reason="Invalid token")
        return
    from app.api.auth import is_token_revoked
    from app.database import async_session_factory
    async with async_session_factory() as session:
        if await is_token_revoked(jti, session):
            await ws.close(code=1008, reason="Token revoked")
            return
    await event_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other receive error (e.g. the socket was already torn down by a
        # failed broadcast send) must still evict the connection so the list
        # self-heals instead of leaking a dead socket.
        logger.debug("WebSocket receive loop ended abnormally", exc_info=True)
    finally:
        event_manager.disconnect(ws)
