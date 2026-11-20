"""Concurrent logins are gated before the first await, and bcrypt runs off the loop."""
from __future__ import annotations

import asyncio
import threading

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import create_access_token, hash_password
from app.api.routes import auth as auth_routes
from app.database import get_session
from app.main import app
from app.models.config import Config
from app.services.login_rate_limit import LoginRateLimiter


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _StubResult:
    def __init__(self, row: Config) -> None:
        self._row = row

    def scalar_one_or_none(self) -> Config:
        return self._row


class _StubSession:
    """Answers the hash lookup after a real suspension point, with no database:
    twenty concurrent requests on the shared test session would collide, and on
    real sessions they exhaust the pool."""

    def __init__(self, row: Config) -> None:
        self._row = row

    async def execute(self, _statement):
        await asyncio.sleep(0.01)
        return _StubResult(self._row)


@pytest.mark.asyncio
async def test_concurrent_wrong_passwords_verify_at_most_five(monkeypatch):
    monkeypatch.setattr(auth_routes, "login_rate_limiter", LoginRateLimiter(max_failures=5))

    async def no_audit(action: str, details: dict) -> None:
        return None

    monkeypatch.setattr(auth_routes, "_record_audit", no_audit)

    calls = 0

    def counting_verify(password: str, hashed: str) -> bool:
        nonlocal calls
        calls += 1
        return False

    monkeypatch.setattr(auth_routes, "verify_password", counting_verify)
    row = Config(key="admin_password_hash", value={"hash": "unused"})

    async def stub_session():
        yield _StubSession(row)

    app.dependency_overrides[get_session] = stub_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            responses = await asyncio.gather(*(
                c.post("/api/v1/auth/login", json={"password": "wrong"}) for _ in range(20)
            ))
    finally:
        app.dependency_overrides.clear()

    codes = sorted(r.status_code for r in responses)
    assert 1 <= calls <= 5
    assert codes.count(401) == calls
    assert codes.count(429) == 20 - calls


@pytest.mark.asyncio
async def test_password_hashing_runs_off_the_event_loop(client, session, monkeypatch):
    from tests.conftest import test_engine

    monkeypatch.setattr(
        auth_routes, "async_session_factory",
        async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False),
    )
    loop_thread = threading.get_ident()
    seen: list[int] = []
    real_verify = auth_routes.verify_password

    def recording_verify(password: str, hashed: str) -> bool:
        seen.append(threading.get_ident())
        return real_verify(password, hashed)

    monkeypatch.setattr(auth_routes, "verify_password", recording_verify)
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.flush()

    r = await client.post("/api/v1/auth/login", json={"password": "correct"})
    assert r.status_code == 200
    assert seen and all(t != loop_thread for t in seen)


@pytest.mark.asyncio
async def test_password_hashing_runs_off_the_event_loop_on_change_password(
    client, session, monkeypatch,
):
    loop_thread = threading.get_ident()
    seen: list[int] = []
    real_hash = auth_routes.hash_password

    def recording_hash(password: str) -> str:
        seen.append(threading.get_ident())
        return real_hash(password)

    monkeypatch.setattr(auth_routes, "hash_password", recording_hash)
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("old-password")}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "old-password", "new_password": "brand-new-pw-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert seen and all(t != loop_thread for t in seen)


@pytest.mark.asyncio
async def test_in_flight_slot_is_released_on_error(client, session, monkeypatch):
    clock = _Clock()
    limiter = LoginRateLimiter(max_failures=5, lockout_seconds=300, clock=clock)
    monkeypatch.setattr(auth_routes, "login_rate_limiter", limiter)

    def exploding_verify(password: str, hashed: str) -> bool:
        raise RuntimeError("verify blew up")

    monkeypatch.setattr(auth_routes, "verify_password", exploding_verify)
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.flush()

    for _ in range(5):
        with pytest.raises(RuntimeError):
            await client.post("/api/v1/auth/login", json={"password": "wrong"})

    clock.now += 301
    assert limiter.in_flight("127.0.0.1") == 0
