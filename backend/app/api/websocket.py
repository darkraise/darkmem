import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

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
        message = json.dumps({"event": event_type, "data": data})
        for ws in self.connections[:]:
            try:
                await ws.send_text(message)
            except Exception:
                self.connections.remove(ws)


event_manager = EventManager()


async def websocket_endpoint(ws: WebSocket):
    await event_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(ws)
