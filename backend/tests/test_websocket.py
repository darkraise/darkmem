import asyncio

from app.api.websocket import EventManager


async def test_event_manager_broadcast():
    manager = EventManager()

    received = []

    class MockWS:
        async def accept(self):
            pass
        async def send_text(self, data):
            received.append(data)

    ws = MockWS()
    await manager.connect(ws)
    await manager.broadcast("memory.created", {"id": "123"})

    assert len(received) == 1
    assert "memory.created" in received[0]


async def test_event_manager_disconnect():
    manager = EventManager()

    class MockWS:
        async def accept(self):
            pass
        async def send_text(self, data):
            pass

    ws = MockWS()
    await manager.connect(ws)
    assert len(manager.connections) == 1

    manager.disconnect(ws)
    assert len(manager.connections) == 0
