"""Verified API keys are cached for 60 seconds, and revocation and expiry still bite."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import create_access_token
from app.database import get_session
from app.main import app
from app.services import api_keys
from tests.conftest import test_engine
from tests.test_mcp_auth import door, mint_key  # noqa: F401 — fixtures

pytestmark = pytest.mark.asyncio


class _Clock:
    def __init__(self) -> None:
        self.now = 5000.0

    def __call__(self) -> float:
        return self.now


def _clear_caches() -> None:
    api_keys._verified.clear()
    api_keys._revoked_ids.clear()
    api_keys._last_marked.clear()


@pytest.fixture(autouse=True)
def _fresh_caches():
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def bcrypt_calls(monkeypatch):
    calls = {"n": 0}
    real = api_keys.verify_secret

    def counting(secret, key_hash):
        calls["n"] += 1
        return real(secret, key_hash)

    monkeypatch.setattr(api_keys, "verify_secret", counting)
    return calls


@pytest.fixture
def cache_clock(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(api_keys, "_cache_clock", clock)
    return clock


async def _tools_list(client, credential):
    return await client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers={"Authorization": f"Bearer {credential}"},
    )


async def _authenticate(credential, **kw):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        return await api_keys.authenticate(s, credential, **kw)


async def test_second_call_within_window_verifies_no_bcrypt(door, mint_key, bcrypt_calls):
    _row_id, credential = await mint_key(scopes=["read"])

    first = await _tools_list(door, credential)
    second = await _tools_list(door, credential)

    assert first.status_code == 200
    assert second.status_code == 200
    assert bcrypt_calls["n"] == 1


async def test_entry_expires_after_sixty_seconds(mint_key, bcrypt_calls, cache_clock):
    _row_id, credential = await mint_key(scopes=["read"])

    assert await _authenticate(credential) is not None
    cache_clock.now += 61
    assert await _authenticate(credential) is not None

    assert bcrypt_calls["n"] == 2


async def test_revoked_key_is_refused_on_next_call(door, mint_key, bcrypt_calls):
    row_id, credential = await mint_key(scopes=["read"])
    assert (await _tools_list(door, credential)).status_code == 200
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def real_session():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = real_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(
                f"/api/v1/api-keys/{row_id}",
                headers={"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 204

    before = bcrypt_calls["n"]
    refused = await _tools_list(door, credential)

    assert refused.status_code == 401
    assert bcrypt_calls["n"] == before


async def test_expired_key_is_refused_on_a_cache_hit(door, mint_key, bcrypt_calls, monkeypatch):
    row_id, credential = await mint_key(
        scopes=["read"], expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    assert (await _tools_list(door, credential)).status_code == 200
    verified = bcrypt_calls["n"]

    later = datetime.now(timezone.utc) + timedelta(seconds=45)

    class _Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return later if tz is not None else later.replace(tzinfo=None)

    monkeypatch.setattr(api_keys, "datetime", _Later)
    refused = await _tools_list(door, credential)

    assert refused.status_code == 401
    assert bcrypt_calls["n"] == verified


async def test_verify_in_flight_during_revoke_caches_nothing(mint_key, monkeypatch):
    row_id, credential = await mint_key(scopes=["read"])
    real = api_keys.verify_secret
    revoked_mid_verify = False

    def verify_then_revoke(secret, key_hash):
        nonlocal revoked_mid_verify
        result = real(secret, key_hash)
        api_keys.forget_revoked_key(row_id)
        revoked_mid_verify = True
        return result

    monkeypatch.setattr(api_keys, "verify_secret", verify_then_revoke)
    first = await _authenticate(credential)
    monkeypatch.setattr(api_keys, "verify_secret", real)

    assert revoked_mid_verify
    assert first is not None
    assert not any(p.api_key_id == row_id for p, _e, _c in api_keys._verified.values())

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        await api_keys.revoke_key(s, row_id)
        await s.commit()
    assert await _authenticate(credential) is None


async def test_cache_key_is_a_digest(mint_key):
    _row_id, credential = await mint_key(scopes=["read"])
    _key_id, secret = api_keys.parse_credential(credential)

    assert await _authenticate(credential) is not None

    assert api_keys._verified
    for key, value in api_keys._verified.items():
        assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)
        blob = f"{key}{value!r}"
        assert credential not in blob
        assert secret not in blob


async def test_wrong_secret_for_cached_key_id_is_refused(door, mint_key):
    _row_id, credential = await mint_key(scopes=["read"])
    assert (await _tools_list(door, credential)).status_code == 200

    prefix, key_id, secret = credential.split("_")
    other = "a" * len(secret) if secret != "a" * len(secret) else "b" * len(secret)
    forged = f"{prefix}_{key_id}_{other}"

    assert (await _tools_list(door, forged)).status_code == 401
