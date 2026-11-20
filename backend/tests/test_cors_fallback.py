"""CORS allows exactly the configured origins, with no built-in fallback."""
from __future__ import annotations

import pytest
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.main import app


def _cors_entry():
    entries = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert len(entries) == 1
    return entries[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:5173"])
async def test_unset_cors_origins_allows_no_origin(client, origin):
    assert settings.cors_origins == []

    r = await client.get("/api/v1/auth/me", headers={"Origin": origin})
    assert "access-control-allow-origin" not in r.headers

    pre = await client.options(
        "/api/v1/auth/me",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in pre.headers


@pytest.mark.asyncio
async def test_configured_origin_is_still_allowed(client, monkeypatch):
    entry = _cors_entry()
    monkeypatch.setitem(entry.kwargs, "allow_origins", ["https://mem.example"])
    monkeypatch.setattr(app, "middleware_stack", None)
    try:
        r = await client.get("/api/v1/auth/me", headers={"Origin": "https://mem.example"})
    finally:
        monkeypatch.undo()
        app.middleware_stack = None

    assert r.headers.get("access-control-allow-origin") == "https://mem.example"
    assert r.headers.get("access-control-allow-credentials") == "true"
