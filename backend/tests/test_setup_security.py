"""Pre-setup endpoints are open trust-on-first-use (no SETUP_SECRET).

Before an admin password exists, the wizard's fs-browse and model-probe
endpoints are reachable by any network peer — gated only by
``require_uninitialized``. This is the accepted local/LAN trust-on-first-use
model: the first caller to finish /setup claims admin and closes the window.
There is no setup-secret layer.
"""
from __future__ import annotations

import pytest

from app.api.auth import hash_password
from app.models.config import Config


@pytest.mark.asyncio
async def test_fs_roots_open_before_setup(client):
    r = await client.get("/api/v1/setup/fs/roots")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_fs_roots_blocked_after_admin_exists(client, session):
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("pw-12345678")}))
    await session.flush()
    r = await client.get("/api/v1/setup/fs/roots")
    assert r.status_code == 403
