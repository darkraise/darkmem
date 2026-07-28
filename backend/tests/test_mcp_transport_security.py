"""MCP DNS-rebinding host allowlist (config-driven)."""
from __future__ import annotations

import httpx
import pytest

from app.api.mcp.server import build_transport_security


def test_default_allows_localhost_only():
    s = build_transport_security("")
    assert s.enable_dns_rebinding_protection is True
    assert "localhost:*" in s.allowed_hosts
    assert "127.0.0.1:*" in s.allowed_hosts
    assert not any("192.168" in h for h in s.allowed_hosts)


def test_configured_hosts_are_allowed_and_keep_localhost():
    s = build_transport_security("192.168.0.195:8000, 10.0.0.5:*")
    assert s.enable_dns_rebinding_protection is True
    assert "192.168.0.195:8000" in s.allowed_hosts
    assert "10.0.0.5:*" in s.allowed_hosts
    assert "localhost:*" in s.allowed_hosts
    assert "http://192.168.0.195:8000" in s.allowed_origins


def test_wildcard_disables_protection():
    s = build_transport_security("*")
    assert s.enable_dns_rebinding_protection is False


@pytest.mark.asyncio
async def test_default_mcp_rejects_foreign_host_allows_localhost(mcp_streamable_app):
    """With the default (empty) allowlist, localhost is accepted and a LAN host
    is rejected with 421 — proving rebinding protection is on by default."""
    payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "1"}},
    }
    transport = httpx.ASGITransport(app=mcp_streamable_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        ok = await c.post("/", json=payload, headers={
            "Accept": "application/json, text/event-stream", "Host": "localhost:8000"})
        foreign = await c.post("/", json=payload, headers={
            "Accept": "application/json, text/event-stream", "Host": "192.168.0.195:8000"})
    assert ok.status_code == 200
    assert foreign.status_code == 421


def test_wildcard_stays_available_as_an_explicit_opt_out():
    """`*` disables the Host check, and that is deliberate (doc 12 section 6).

    The rule that a LAN 421 is fixed by extending the allowlist rather than by
    reaching for `*` is operator discipline for a fully-trusted isolated
    network, not something the code makes impossible. A change that removes
    the opt-out is a contract change, not a hardening.
    """
    s = build_transport_security("*")
    assert s.enable_dns_rebinding_protection is False

    # It is the whole-allowlist wildcard that opts out, not a wildcard that
    # merely appears alongside real hosts.
    mixed = build_transport_security("192.168.0.195:8000, *")
    assert mixed.enable_dns_rebinding_protection is False


def test_an_unconfigured_host_is_not_reachable_by_accident():
    """The default allowlist admits localhost and nothing else.

    Stated as an exclusion rather than an inclusion: a bug that widened the
    allowlist (an empty CSV parsed into a bare "", a stray wildcard entry)
    would still satisfy an inclusion-only assertion while silently admitting
    every Host.
    """
    s = build_transport_security("")
    assert s.enable_dns_rebinding_protection is True
    assert set(s.allowed_hosts) == {"localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"}
    assert "" not in s.allowed_hosts
    assert "*" not in s.allowed_hosts


@pytest.mark.asyncio
async def test_browser_origins_are_allowlisted_to_the_same_hosts(mcp_streamable_app):
    """A browser Origin is checked against the same host set (403 when foreign).

    Agents send no Origin at all, so this gate exists purely for the browser
    case: without it a page on any origin could drive the unauthenticated tool
    surface from a victim's machine, which is the attack the Host check alone
    does not cover.
    """
    payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "1"}},
    }
    headers = {"Accept": "application/json, text/event-stream", "Host": "localhost:8000"}
    transport = httpx.ASGITransport(app=mcp_streamable_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        none_sent = await c.post("/", json=payload, headers=headers)
        allowed = await c.post("/", json=payload, headers={
            **headers, "Origin": "http://localhost:3636"})
        foreign = await c.post("/", json=payload, headers={
            **headers, "Origin": "http://attacker.example"})

    assert none_sent.status_code == 200
    assert allowed.status_code == 200
    assert foreign.status_code == 403
