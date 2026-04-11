import json
import logging

import jwt
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import settings
from app.schemas.events import EVENT_SCHEMAS

logger = logging.getLogger(__name__)


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

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
        for ws in list(self.connections):
            try:
                await ws.send_text(message)
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
        event_manager.disconnect(ws)
