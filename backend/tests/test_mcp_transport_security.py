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
