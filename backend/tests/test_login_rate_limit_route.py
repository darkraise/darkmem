"""auth_login must lock out an IP after repeated failures."""
from __future__ import annotations

import pytest
from sqlalchemy import text
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

    # The committed failed-login audit rows outlive the fixture rollback and
    # cannot be cleaned up: `events` is append-only (T1.06), so a DELETE here is
    # refused by the forbid-trigger. Readers must tolerate them.


@pytest.mark.asyncio
async def test_lockout_transition_is_journaled(client, session, monkeypatch):
    """T2.103 — the failure that actually crosses the threshold journals a
    distinct `auth_lockout` row (not just another `auth_login_failed`), so
    the security audit trail can tell "one more bad guess" from "this IP
    just got locked out" apart. Proves the emitter fires at the real
    transition, not merely that the value exists somewhere in the vocabulary.

    Counts are taken relative to a baseline read at the start of the test,
    not asserted as absolute zero/one: `events` is append-only, so sibling
    tests in this file (this suite's own lockout test above included) leave
    `auth_lockout` rows behind that this test cannot and must not try to
    clean up.
    """
    from tests.conftest import test_engine

    async def _lockout_row_count() -> int:
        async with AsyncSession(test_engine) as verify_session:
            rows = (await verify_session.execute(
                text("SELECT id FROM events WHERE event_type = 'auth_lockout'")
            )).all()
            return len(rows)

    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(auth_routes, "async_session_factory", test_factory)
    monkeypatch.setattr(
        auth_routes, "login_rate_limiter",
        LoginRateLimiter(max_failures=2, lockout_seconds=300),
    )

    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.commit()

    baseline = await _lockout_row_count()

    # First failure: below threshold, no new lockout row yet.
    r = await client.post("/api/v1/auth/login", json={"password": "wrong"})
    assert r.status_code == 401
    assert await _lockout_row_count() == baseline

    # Second failure: crosses max_failures=2, must journal the transition.
    r = await client.post("/api/v1/auth/login", json={"password": "wrong"})
    assert r.status_code == 401
    assert await _lockout_row_count() == baseline + 1

    # A third attempt, now locked out at the door, must not journal a
    # second lockout row for the same lockout window.
    r = await client.post("/api/v1/auth/login", json={"password": "wrong"})
    assert r.status_code == 429
    assert await _lockout_row_count() == baseline + 1
