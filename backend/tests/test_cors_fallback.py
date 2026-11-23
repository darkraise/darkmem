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


def _cors_origins(origins: list[str]):
    """The CORS entry rebuilt with ``origins``; the stack is rebuilt again on
    the way out, so no later test sees this one's origins."""
    import contextlib

    @contextlib.contextmanager
    def patched():
        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(_cors_entry().kwargs, "allow_origins", origins)
            mp.setattr(app, "middleware_stack", None)
            try:
                yield
            finally:
                app.middleware_stack = None
        app.middleware_stack = None

    return patched()


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:5173"])
async def test_unset_cors_origins_allows_no_origin(client, origin):
    assert settings.cors_origins == []

    with _cors_origins([]):
        r = await client.get("/api/v1/auth/me", headers={"Origin": origin})
        pre = await client.options(
            "/api/v1/auth/me",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )

    assert "access-control-allow-origin" not in r.headers
    assert "access-control-allow-origin" not in pre.headers


@pytest.mark.asyncio
async def test_configured_origin_is_still_allowed(client):
    with _cors_origins(["https://mem.example"]):
        r = await client.get("/api/v1/auth/me", headers={"Origin": "https://mem.example"})

    assert r.headers.get("access-control-allow-origin") == "https://mem.example"
    assert r.headers.get("access-control-allow-credentials") == "true"
