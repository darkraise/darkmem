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
        self.close_code = None
        self.close_reason = None
        self.sent: list[str] = []

    async def accept(self):
        self.accepted.set()

    async def receive_text(self):
        await asyncio.Event().wait()

    async def send_text(self, data):
        self.sent.append(data)

    async def close(self, code=1000, reason=None):
        if self.closed.is_set():
            raise RuntimeError("close after close")
        self.close_code = code
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


# ── Rotation closes the presented token's sockets first ──────────────────

RENEWED = "Session renewed"


def _presented(auth_headers) -> str:
    return auth_headers["Authorization"].removeprefix("Bearer ")


@contextmanager
def _held_commit(session):
    """The request session's commit waits until released, so a test can see
    what the socket received before the blocklist write committed."""
    entered = asyncio.Event()
    release = asyncio.Event()
    original = session.commit

    async def commit():
        entered.set()
        await release.wait()
        return await original()

    session.commit = commit
    try:
        yield entered, release
    finally:
        session.commit = original


async def test_refresh_closes_the_presented_tokens_socket_with_4001_first(
    manager, client, auth_headers, session,
):
    socket, task = await _open(_presented(auth_headers))
    try:
        with _held_commit(session) as (entered, release):
            answer = asyncio.create_task(
                client.post("/api/v1/auth/refresh", headers=auth_headers)
            )
            await asyncio.wait_for(entered.wait(), 5)
            assert socket.closed.is_set(), "the socket was not closed before the commit"
            assert (socket.close_code, socket.close_reason) == (4001, RENEWED)
            release.set()
            assert (await answer).status_code == 200
        await asyncio.sleep(INTERVAL * 4)
        assert task.done()
        assert task.exception() is None
        assert manager.connections == []
    finally:
        await _shut(task)


async def test_password_change_closes_own_socket_4001_and_others_as_revoked(
    manager, client, auth_headers,
):
    own, own_task = await _open(_presented(auth_headers))
    other, other_task = await _open(_token(iat_ago=30))
    try:
        answer = await client.post(
            "/api/v1/auth/change-password", headers=auth_headers,
            json={"current_password": "test-admin-password", "new_password": "a-new-password-9"},
        )
        assert answer.status_code == 200, answer.text
        await asyncio.wait_for(other.closed.wait(), 2)
        assert (own.close_code, own.close_reason) == (4001, RENEWED)
        assert other.close_reason == "Session expired or revoked"
        assert other.close_code != 4001
    finally:
        await _shut(own_task, other_task)


async def test_read_only_refresh_also_closes_with_4001(
    manager, client, auth_headers, monkeypatch,
):
    monkeypatch.setattr(settings, "read_only", True)
    socket, task = await _open(_presented(auth_headers))
    try:
        answer = await client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert answer.status_code == 200
        await asyncio.wait_for(socket.closed.wait(), 2)
        assert (socket.close_code, socket.close_reason) == (4001, RENEWED)
    finally:
        await _shut(task)


async def test_a_new_socket_with_the_new_cookie_connects(manager, client, auth_headers):
    presented = _presented(auth_headers)
    first, first_task = await _open(presented)
    renewed_task = None
    try:
        answer = await client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert answer.status_code == 200
        issued = answer.cookies.get(COOKIE_NAME)
        assert issued

        renewed, renewed_task = await _open(issued)
        stale = _Socket(presented)
        await asyncio.wait_for(websocket.websocket_endpoint(stale), 5)
        assert not stale.accepted.is_set()
        assert stale.close_reason == "Unauthorized"

        await manager.broadcast("unknown.test", {"n": 1})
        assert len(renewed.sent) == 1
        assert not renewed.closed.is_set()
    finally:
        await _shut(first_task)
        if renewed_task is not None:
            await _shut(renewed_task)


async def test_a_socket_opened_inside_the_rotation_window_is_told_renewed(
    manager, client, auth_headers, session,
):
    presented = _presented(auth_headers)
    with _held_commit(session) as (entered, release):
        answer = asyncio.create_task(
            client.post("/api/v1/auth/refresh", headers=auth_headers)
        )
        await asyncio.wait_for(entered.wait(), 5)
        late = _Socket(presented)
        await asyncio.wait_for(websocket.websocket_endpoint(late), 5)
        assert (late.close_code, late.close_reason) == (4001, RENEWED)
        assert manager.connections == []
        release.set()
        assert (await answer).status_code == 200


async def test_a_rotation_whose_commit_fails_keeps_the_token_usable(
    manager, client, auth_headers, session,
):
    presented = _presented(auth_headers)
    original = session.commit

    async def refuse():
        raise RuntimeError("commit refused")

    session.commit = refuse
    try:
        with pytest.raises(RuntimeError):
            await client.post("/api/v1/auth/refresh", headers=auth_headers)
    finally:
        session.commit = original

    socket, task = await _open(presented)
    try:
        await asyncio.sleep(INTERVAL * 4)
        assert not socket.closed.is_set()
    finally:
        await _shut(task)


async def test_a_frozen_tab_cannot_hold_a_rotation_on_its_close(monkeypatch):
    monkeypatch.setattr(websocket, "SEND_TIMEOUT_SECONDS", 0.05)
    manager = websocket.EventManager()

    class _FrozenSocket(_Socket):
        async def close(self, code=1000, reason=None):
            await asyncio.Event().wait()

    frozen = _FrozenSocket(_token())
    healthy = _Socket(_token())
    await manager.connect(frozen, token_id="rotated")
    await manager.connect(healthy)

    await asyncio.wait_for(manager.close_token("rotated", 4001, "Session renewed"), 1)
    await asyncio.wait_for(manager.broadcast("memory.created", {"id": "m1"}), 1)

    assert frozen not in manager.connections
    assert len(healthy.sent) == 1


# ── The in-process copy is re-read from the database ─────────────────────


async def test_an_out_of_band_revocation_closes_the_socket_after_reload(manager, monkeypatch):
    from datetime import datetime, timezone

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    clock = [1000.0]
    monkeypatch.setattr(websocket, "_now", lambda: clock[0], raising=False)
    token = _token()
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    socket, task = await _open(token)
    try:
        async with factory() as s:
            await s.execute(
                text("INSERT INTO token_blocklist (id, jti, expires_at) "
                     "VALUES (gen_random_uuid(), :jti, :exp)"),
                {"jti": claims["jti"], "exp": datetime.fromtimestamp(claims["exp"], tz=timezone.utc)},
            )
            await s.commit()
        await asyncio.sleep(INTERVAL * 4)
        assert not socket.closed.is_set()

        clock[0] += 61
        await asyncio.wait_for(socket.closed.wait(), 2)
        assert socket.close_reason == "Session expired or revoked"
    finally:
        await _shut(task)
        async with factory() as s:
            await s.execute(text("DELETE FROM token_blocklist WHERE jti = :jti"), {"jti": claims["jti"]})
            await s.commit()


async def test_reload_is_single_flight_merges_and_survives_a_failed_read(
    monkeypatch, caplog, setup_database,
):
    import logging
    from contextlib import asynccontextmanager

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    clock = [1000.0]
    monkeypatch.setattr(websocket, "_now", lambda: clock[0], raising=False)
    real = async_sessionmaker(test_engine, expire_on_commit=False)
    revocations = websocket.SessionRevocations()
    await revocations.load(real)
    clock[0] += 61

    reads = 0
    gate = asyncio.Event()

    @asynccontextmanager
    async def counting_factory():
        nonlocal reads
        reads += 1
        await gate.wait()
        async with real() as s:
            yield s

    calls = [asyncio.create_task(revocations.refresh_if_stale(counting_factory)) for _ in range(20)]
    await asyncio.sleep(0.05)
    revocations.revoke("revoked-during-the-read", time.time() + 3600)
    gate.set()
    await asyncio.gather(*calls)
    assert reads == 1
    assert "revoked-during-the-read" in revocations._revoked

    @asynccontextmanager
    async def failing_factory():
        raise RuntimeError("database down")
        yield

    caplog.set_level(logging.WARNING, logger="app.api.websocket")
    for _ in range(2):
        clock[0] += 61
        await revocations.refresh_if_stale(failing_factory)
    assert "revoked-during-the-read" in revocations._revoked
    warnings = [
        r for r in caplog.records if r.name == "app.api.websocket" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]


async def test_a_cancelled_refresh_forgets_the_renewed_mark(manager, client, auth_headers):
    presented = _presented(auth_headers)
    jti = jwt.decode(presented, settings.jwt_secret, algorithms=[ALGORITHM])["jti"]
    socket, task = await _open(presented)
    try:
        async with manager._send_lock:
            answer = asyncio.create_task(client.post("/api/v1/auth/refresh", headers=auth_headers))
            for _ in range(200):
                if jti in websocket.session_revocations._renewed:
                    break
                await asyncio.sleep(0.01)
            assert jti in websocket.session_revocations._renewed
            answer.cancel()
            await asyncio.gather(answer, return_exceptions=True)
        assert jti not in websocket.session_revocations._renewed
    finally:
        await _shut(task)
