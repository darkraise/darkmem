"""Pre-setup fs-browse and model-probe endpoints must honour SETUP_SECRET.

Before the admin password exists, fs/roots, fs/list and probe-models are
reachable by any network peer (gated only by require_uninitialized).
_enforce_setup_secret was applied only inside setup_finalize, so even a
configured secret left these open: fs/* leaks the host filesystem and
probe-models is a server-side request-forgery primitive. When a secret is
configured, every pre-setup endpoint must require it.
"""
from __future__ import annotations

import pytest

from app.config import settings


@pytest.mark.asyncio
async def test_fs_roots_rejected_without_secret_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "setup_secret", "topsecret")
    r = await client.get("/api/v1/setup/fs/roots")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_fs_roots_allowed_with_correct_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "setup_secret", "topsecret")
    r = await client.get("/api/v1/setup/fs/roots", headers={"X-Setup-Secret": "topsecret"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_probe_models_rejected_without_secret_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "setup_secret", "topsecret")
    r = await client.post(
        "/api/v1/setup/probe-models",
        json={"api_kind": "openai", "base_url": "https://api.openai.com/v1", "api_key": "sk"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_fs_roots_open_when_no_secret_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "setup_secret", None)
    r = await client.get("/api/v1/setup/fs/roots")
    assert r.status_code == 200
