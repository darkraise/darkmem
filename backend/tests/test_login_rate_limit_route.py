"""auth_login must lock out an IP after repeated failures."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import hash_password
from app.api.routes import auth as auth_routes
from app.models.config import Config
from app.services.login_rate_limit import LoginRateLimiter


@pytest.mark.asyncio
async def test_login_locks_out_after_repeated_failures(client, session, monkeypatch):
    from tests.conftest import test_engine

    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(auth_routes, "async_session_factory", test_factory)
    monkeypatch.setattr(
        auth_routes, "login_rate_limiter",
        LoginRateLimiter(max_failures=2, lockout_seconds=300),
    )

    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.commit()

    for _ in range(2):
        r = await client.post("/api/v1/auth/login", json={"password": "wrong"})
        assert r.status_code == 401

    # Third attempt is locked out, even before checking the password.
    r = await client.post("/api/v1/auth/login", json={"password": "wrong"})
    assert r.status_code == 429
    assert r.headers.get("Retry-After")

    # The committed failed-login audit rows live outside the fixture rollback;
    # clean them up so they don't leak into other tests.
    async with AsyncSession(test_engine) as vs:
        await vs.execute(
            text("DELETE FROM events WHERE event_type = 'auth_login_failed'")
        )
        await vs.commit()
