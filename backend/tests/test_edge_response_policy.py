"""The response duties the app absorbed when nginx left the shipped topology.

Security headers, gzip and the request-body cap were nginx's, and their
values must not drift: the nginx-in-image fallback and the app-as-edge build
have to present the same policy, so the CSP here is compared against
``frontend/nginx.conf`` itself rather than against the app's own constant.

The exclusion of /mcp is asserted as hard as the inclusion is. The
middlewares are global by default, so the excluded surface is the one that
regresses silently — nginx never fronted /mcp, and a global body cap would
newly bound MCP ingestion.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from starlette.routing import Mount

from app.api.spa import mount_spa
from app.main import (
    MAX_REQUEST_BODY_BYTES,
    RequestBodyLimitMiddleware,
    ScopedGZipMiddleware,
    SecurityHeadersMiddleware,
    app,
)

NGINX_CONF = Path(__file__).resolve().parent.parent.parent / "frontend" / "nginx.conf"

INDEX_BODY = "<!doctype html><html><body><div id=\"root\"></div></body></html>"


def _nginx_headers() -> dict[str, str]:
    pattern = re.compile(r'^\s*add_header\s+(\S+)\s+"(.*)"\s+always;\s*$', re.MULTILINE)
    return {
        name.lower(): value
        for name, value in pattern.findall(NGINX_CONF.read_text())
    }


@pytest.fixture
def mounted(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX_BODY)
    assert mount_spa(app, tmp_path) is True
    try:
        yield tmp_path
    finally:
        app.router.routes[:] = [
            route for route in app.router.routes
            if not (isinstance(route, Mount) and route.name == "spa")
        ]


# ── The four security headers, at nginx's values ──────────────────────


async def test_nginx_conf_still_declares_the_four_headers():
    """Guards the comparison below: if nginx.conf stops declaring them, the
    equality tests would pass by comparing nothing."""
    declared = _nginx_headers()
    assert set(declared) == {
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "content-security-policy",
    }


async def test_security_headers_on_an_api_response(client):
    response = await client.get("/health")
    for name, value in _nginx_headers().items():
        assert response.headers[name] == value


async def test_security_headers_on_an_spa_response(client, mounted):
    """nginx never emitted these on the SPA's own HTML document, where a CSP
    is the only place it does anything. The app does."""
    response = await client.get("/")
    assert response.text == INDEX_BODY
    for name, value in _nginx_headers().items():
        assert response.headers[name] == value


async def test_csp_matches_nginx_character_for_character(client):
    response = await client.get("/health")
    assert (
        response.headers["content-security-policy"]
        == _nginx_headers()["content-security-policy"]
    )


# ── gzip, at nginx's threshold ────────────────────────────────────────


async def test_large_response_is_gzipped(client):
    response = await client.get("/openapi.json", headers={"accept-encoding": "gzip"})
    assert response.status_code == 200
    assert int(response.headers["content-length"]) > 1024
    assert response.headers["content-encoding"] == "gzip"


async def test_small_response_is_not_gzipped(client):
    response = await client.get("/health", headers={"accept-encoding": "gzip"})
    assert len(response.content) < 1024
    assert "content-encoding" not in response.headers


# ── The 25 MB request-body cap ────────────────────────────────────────


async def test_oversized_declared_body_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/login",
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1), "content-type": "application/json"},
        content=b"",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_body_under_the_cap_reaches_its_handler(client):
    response = await client.post(
        "/api/v1/auth/login",
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES - 1)},
        json={"password": "not-the-admin-password"},
    )
    assert response.status_code != 413
    assert response.json().get("error", {}).get("code") != "payload_too_large"


# ── /mcp is excluded from all three, exactly as nginx left it ─────────


async def _asgi_call(middleware, path, *, headers=(), inner=None):
    """Drive one middleware over a stub inner app and collect its messages."""
    sent: list[dict] = []

    async def default_inner(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": b"x" * 4096})

    middleware.app = inner or default_inner
    if isinstance(middleware, ScopedGZipMiddleware):
        middleware.gzip.app = inner or default_inner

    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "query_string": b"",
        "root_path": "",
        "headers": [(k.encode(), v.encode()) for k, v in headers],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)
    return sent


def _start_headers(messages):
    start = next(m for m in messages if m["type"] == "http.response.start")
    return {k.decode().lower(): v.decode() for k, v in start["headers"]}


@pytest.mark.parametrize("path", ["/mcp", "/mcp/", "/mcp/messages"])
async def test_mcp_carries_no_security_headers(path):
    messages = await _asgi_call(SecurityHeadersMiddleware(None), path)
    headers = _start_headers(messages)
    for name in _nginx_headers():
        assert name not in headers


async def test_non_mcp_paths_still_get_the_headers_through_the_same_predicate():
    messages = await _asgi_call(SecurityHeadersMiddleware(None), "/mcpx/tool")
    headers = _start_headers(messages)
    for name in _nginx_headers():
        assert name in headers


async def test_mcp_is_not_gzipped():
    messages = await _asgi_call(
        ScopedGZipMiddleware(None), "/mcp/messages",
        headers=[("accept-encoding", "gzip")],
    )
    assert "content-encoding" not in _start_headers(messages)


async def test_non_mcp_json_is_gzipped_through_the_same_middleware():
    messages = await _asgi_call(
        ScopedGZipMiddleware(None), "/api/v1/anything",
        headers=[("accept-encoding", "gzip")],
    )
    assert _start_headers(messages)["content-encoding"] == "gzip"


async def test_sse_is_never_gzipped():
    """Starlette excludes text/event-stream by content type; asserted here
    because a compressed event stream stalls rather than fails."""
    async def sse_inner(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/event-stream")],
        })
        await send({"type": "http.response.body", "body": b"data: x\n\n" * 500})

    messages = await _asgi_call(
        ScopedGZipMiddleware(None), "/api/v1/chat/completions",
        headers=[("accept-encoding", "gzip")], inner=sse_inner,
    )
    assert "content-encoding" not in _start_headers(messages)


async def test_mcp_body_is_not_capped():
    """nginx's client_max_body_size never applied to /mcp, so the app must not
    newly bound MCP ingestion. /mcp answers with its own transport error for a
    malformed body — assert only that it is not this middleware's 413."""
    messages = await _asgi_call(
        RequestBodyLimitMiddleware(None), "/mcp/messages",
        headers=[("content-length", str(MAX_REQUEST_BODY_BYTES + 1))],
    )
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] != 413
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    assert b"payload_too_large" not in body


async def test_non_mcp_body_is_capped_through_the_same_predicate():
    messages = await _asgi_call(
        RequestBodyLimitMiddleware(None), "/api/v1/memories",
        headers=[("content-length", str(MAX_REQUEST_BODY_BYTES + 1))],
    )
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 413
