import asyncio
import json
import logging

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.events import EVENT_SCHEMAS

logger = logging.getLogger(__name__)

# A frozen/backgrounded browser tab stops draining its socket; without a cap a
# producer awaiting the broadcast (the indexing / memory pipeline) would block
# on TCP backpressure behind the slowest consumer.
SEND_TIMEOUT_SECONDS = 5.0
AUTH_CHECK_INTERVAL_SECONDS = 1.0


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self._validators = {}
        # Serialize the per-connection send fan-out: broadcast() is awaited from
        # many concurrent coroutines (pipeline fan-out, indexing, jobs, reembed)
        # and Starlette's WebSocket.send is not safe for concurrent senders on
        # one socket — interleaved ASGI sends raise and kill the connection.
        self._send_lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, validator=None):
        await ws.accept()
        self.connections.append(ws)
        if validator is not None:
            self._validators[ws] = validator

    def disconnect(self, ws: WebSocket):
        self._validators.pop(ws, None)
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, event_type: str, data: dict):
        schema = EVENT_SCHEMAS.get(event_type)
        if schema:
            try:
                schema.model_validate(data)
            except ValidationError as e:
                # Send anyway (clients tolerate extra/missing fields), but make
                # it loud that the payload diverged from the declared schema —
                # this usually means a producer drifted from schemas/events.py.
                logger.warning(
                    "Broadcasting event '%s' whose payload failed schema "
                    "validation (sent regardless): %s",
                    event_type,
                    e,
                )
        message = json.dumps({"event": event_type, "data": data})
        dead: list[WebSocket] = []
        async with self._send_lock:
            for ws in list(self.connections):
                try:
                    validator = self._validators.get(ws)
                    if validator is not None:
                        try:
                            await validator()
                        except HTTPException:
                            await ws.close(code=1008, reason="Session expired or revoked")
                            dead.append(ws)
                            continue
                    await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)


event_manager = EventManager()


async def websocket_endpoint(ws: WebSocket):
    from app.api.auth import COOKIE_NAME, validate_session_token
    from app.database import async_session_factory

    token = ws.cookies.get(COOKIE_NAME)
    if not token:
        await ws.close(code=1008, reason="Unauthorized")
        return
    try:
        async with async_session_factory() as session:
            await validate_session_token(token, session)
    except HTTPException:
        await ws.close(code=1008, reason="Unauthorized")
        return

    async def validate():
        async with async_session_factory() as session:
            await validate_session_token(token, session)

    await event_manager.connect(ws, validate)
    receive_task = asyncio.create_task(ws.receive_text())
    try:
        while True:
            done, _pending = await asyncio.wait(
                {receive_task}, timeout=AUTH_CHECK_INTERVAL_SECONDS,
            )
            await validate()
            if done:
                receive_task.result()
                receive_task = asyncio.create_task(ws.receive_text())
    except HTTPException:
        await ws.close(code=1008, reason="Session expired or revoked")
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other receive error (e.g. the socket was already torn down by a
        # failed broadcast send) must still evict the connection so the list
        # self-heals instead of leaking a dead socket.
        logger.debug("WebSocket receive loop ended abnormally", exc_info=True)
    finally:
        event_manager.disconnect(ws)
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)
