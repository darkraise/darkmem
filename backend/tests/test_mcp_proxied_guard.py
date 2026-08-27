"""`/mcp` must not be reachable through the proxy (T4.17).

The E4 epic review's I3. At the time this guard was built, `/mcp` was
unauthenticated by design — the local-network trust model — and the runbook
told the operator not to route it publicly on that basis. **Every `/mcp` call
has required a bearer key since doc 18 §5's second activation (2026-08-26)**,
which closes the "any LAN peer reaches any tool" gap this guard's original
premise rested on — but the guard is not thereby redundant: it answers "did
this arrive from outside the trusted network", which a valid key does not
answer, and MCP auth carries no rate limiting, so a leaked or guessed
credential arriving from outside is still not something the runbook should
treat as safe. The objection to leaving the guard unenforced: the gap was
**one allowlist entry from armed**, and the standing advice for a LAN `421` is
"extend the allowlist", which points at exactly that entry. An operator
following correct advice about a different guard could open this one.

The guard closes it in the only direction that cannot cost anything: it is
inert unless the exposed switch is on, and even then it refuses only requests
that arrived through the proxy. Both halves are asserted below, because a
guard that refused everything would satisfy the headline and break every LAN
agent.

This is deliberately **not** the Host allowlist. That one asks "is this Host
one I serve" and answers `421`, fixed by extending the allowlist; this one asks
"did this arrive from outside" and extending the allowlist does not fix it.
"""
from __future__ import annotations

import pytest

from app.config import settings

pytestmark = pytest.mark.asyncio

PROXIED = {"x-forwarded-for": "203.0.113.9", "x-real-ip": "198.51.100.4"}


async def _mcp_status(client, headers: dict) -> int:
    response = await client.post("/mcp/", json={}, headers=headers)
    return response.status_code


async def _guard_passes_through(path: str, headers: dict) -> bool:
    """Whether the middleware handed the request on to the app beneath it.

    Asserted against the middleware rather than end to end, because a request
    the guard *allows* reaches the real MCP mount, whose session manager is not
    running in-process — so "it was allowed" would be observable only as an SDK
    internal error, and the test would be pinned to that error's identity
    rather than to the decision it is about.
    """
    from app.main import ProxiedMcpGuardMiddleware

    reached = False

    async def _inner(scope, receive, send):
        nonlocal reached
        reached = True

    scope = {
        "type": "http",
        "path": path,
        "method": "POST",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
    }
    await ProxiedMcpGuardMiddleware(_inner)(scope, None, None)
    return reached


async def test_a_proxied_request_is_refused_in_the_exposed_posture(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    response = await client.post("/mcp/", json={}, headers=PROXIED)

    assert response.status_code == 403
    body = response.json()
    assert "mcp_not_exposed" in str(body)
    assert "runbook-exposed-deployment" in str(body)


async def test_a_direct_request_is_untouched_in_the_exposed_posture(monkeypatch):
    """The half that keeps a LAN agent working while the box is exposed: no
    proxy headers means the request did not come through the proxy, and the
    guard has nothing to say about it."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert await _guard_passes_through("/mcp/", {}) is True


async def test_the_guard_is_inert_in_the_lan_posture(monkeypatch):
    """With the exposed switch off the middleware must not fire at all, even on
    a request carrying forwarded headers — in that posture those headers are
    attacker-writable noise, and refusing on them would let any client take
    `/mcp` away from every other client."""
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    assert await _guard_passes_through("/mcp/", PROXIED) is True


@pytest.mark.parametrize("marker", ["x-forwarded-for", "x-real-ip", "x-forwarded-proto"])
async def test_each_forwarded_marker_alone_is_enough(client, monkeypatch, marker):
    """A proxy that sets only one of the three still means "from outside"."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert await _mcp_status(client, {marker: "203.0.113.9"}) == 403


async def test_the_guard_does_not_touch_the_api_surface(client, monkeypatch):
    """Only `/mcp` — the API is the surface the proxy exists to serve, and
    refusing proxied `/api/v1` requests would make the exposed posture
    unusable."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    response = await client.get("/api/v1/auth/me", headers=PROXIED)
    assert response.status_code != 403
