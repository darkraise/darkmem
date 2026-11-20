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


# ── Revalidation from memory ─────────────────────────────────────────────

import time
import uuid
from contextlib import contextmanager

import jwt
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.api import auth as auth_module
from app.api import websocket
from app.api.auth import ALGORITHM, COOKIE_NAME
from app.config import settings

INTERVAL = 0.05


def _token(*, iat_ago: float = 0.0, ttl: float = 3600.0) -> str:
    now = time.time()
    return jwt.encode(
        {"sub": "admin", "iat": int(now - iat_ago), "exp": int(now + ttl), "jti": uuid.uuid4().hex},
        settings.jwt_secret, algorithm=ALGORITHM,
    )


class _Socket:
    def __init__(self, token: str):
        self.cookies = {COOKIE_NAME: token}
        self.accepted = asyncio.Event()
        self.closed = asyncio.Event()
        self.close_reason = None
        self.sent: list[str] = []

    async def accept(self):
        self.accepted.set()

    async def receive_text(self):
        await asyncio.Event().wait()

    async def send_text(self, data):
        self.sent.append(data)

    async def close(self, code=1000, reason=None):
        self.close_reason = reason
        self.closed.set()


@contextmanager
def _statements():
    seen: list[str] = []

    def capture(conn, cursor, statement, *args):
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", capture)
    try:
        yield seen
    finally:
        event.remove(Engine, "before_cursor_execute", capture)


@pytest.fixture
def manager(monkeypatch, setup_database):
    fresh = websocket.EventManager()
    monkeypatch.setattr(websocket, "event_manager", fresh)
    monkeypatch.setattr(websocket, "AUTH_CHECK_INTERVAL_SECONDS", INTERVAL)
    return fresh


async def _open(token: str) -> tuple[_Socket, asyncio.Task]:
    socket = _Socket(token)
    task = asyncio.create_task(websocket.websocket_endpoint(socket))
    await asyncio.wait_for(socket.accepted.wait(), 5)
    return socket, task


async def _shut(*tasks):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def test_idle_socket_revalidates_without_a_query(manager):
    socket, task = await _open(_token())
    try:
        await asyncio.sleep(INTERVAL)
        with _statements() as seen:
            await asyncio.sleep(INTERVAL * 4)
        assert not socket.closed.is_set()
        assert seen == []
    finally:
        await _shut(task)


async def test_logout_closes_the_socket_within_two_seconds(manager, client):
    token = _token()
    socket, task = await _open(token)
    try:
        answer = await client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"},
        )
        assert answer.status_code == 200
        await asyncio.wait_for(socket.closed.wait(), 2)
        assert socket.close_reason == "Session expired or revoked"
    finally:
        await _shut(task)


async def test_password_change_closes_other_sessions_sockets(manager, client, auth_headers):
    other, task = await _open(_token(iat_ago=30))
    try:
        answer = await client.post(
            "/api/v1/auth/change-password", headers=auth_headers,
            json={"current_password": "test-admin-password", "new_password": "a-new-password-9"},
        )
        assert answer.status_code == 200, answer.text
        await asyncio.wait_for(other.closed.wait(), 2)
        assert other.close_reason == "Session expired or revoked"
    finally:
        await _shut(task)


async def test_expiry_closes_the_socket_without_a_query(manager):
    socket, task = await _open(_token(ttl=1.0))
    try:
        with _statements() as seen:
            await asyncio.wait_for(socket.closed.wait(), 3)
        assert socket.close_reason == "Session expired or revoked"
        assert seen == []
    finally:
        await _shut(task)


async def test_broadcast_does_not_wait_on_revalidation(manager, monkeypatch):
    opened = [await _open(_token()) for _ in range(10)]

    async def slow(*args, **kwargs):
        await asyncio.sleep(1)
        return False

    monkeypatch.setattr(auth_module, "is_token_revoked", slow)
    monkeypatch.setattr(auth_module, "_password_changed_after", slow)
    try:
        started = time.monotonic()
        with _statements() as seen:
            await asyncio.wait_for(manager.broadcast("unknown.test", {"n": 1}), 0.5)
        assert time.monotonic() - started < 0.5
        assert seen == []
        assert all(len(socket.sent) == 1 for socket, _ in opened)
    finally:
        await _shut(*(task for _, task in opened))


async def test_a_socket_revoked_while_the_broadcast_waits_gets_nothing(manager):
    token = _token()
    socket, task = await _open(token)
    claims = jwt.decode(token, options={"verify_signature": False})
    try:
        async with manager._send_lock:
            pending = asyncio.create_task(manager.broadcast("unknown.test", {"n": 1}))
            await asyncio.sleep(0.01)
            websocket.session_revocations.revoke(claims["jti"], float(claims["exp"]))
        await asyncio.wait_for(pending, 1)
        assert socket.sent == []
        assert socket.close_reason == "Session expired or revoked"
    finally:
        await _shut(task)
