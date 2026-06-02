"""/refresh must rotate: the presented token is revoked when a new one issues.

Without blocklisting the old jti, refresh is non-rotating — both the old and
new tokens stay valid until the old one's 24h exp, so a captured pre-refresh
token keeps working for up to a day. Unlike change-password, refresh has no
epoch backstop, so the jti blocklist is the only revocation path.
"""
from __future__ import annotations

import pytest

from app.api.auth import create_access_token, hash_password
from app.models.config import Config


@pytest.mark.asyncio
async def test_refresh_revokes_the_presented_token(client, session):
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("pw")}))
    await session.flush()

    old_token = create_access_token({"sub": "admin"})

    # Sanity: the token is valid before refresh.
    client.cookies.clear()
    pre = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert pre.status_code == 200

    refreshed = await client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert refreshed.status_code == 200

    # The old token must now be revoked (blocklisted).
    client.cookies.clear()
    post = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert post.status_code == 401
    assert "revoked" in post.json()["detail"].lower()
