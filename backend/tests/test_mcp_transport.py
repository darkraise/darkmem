"""Transport-level guards on /mcp, pinned across the SDK v2 migration.

These assert the Host allowlist's shape, not the SDK's internals, so they
must read identically before and after the migration.
"""
from app.api.mcp.server import build_transport_security


def test_localhost_is_always_allowed():
    s = build_transport_security("")
    assert s.enable_dns_rebinding_protection is True
    assert "localhost" in s.allowed_hosts
    assert "127.0.0.1" in s.allowed_hosts


def test_configured_lan_host_is_added():
    s = build_transport_security("192.168.0.195:8000")
    assert "192.168.0.195:8000" in s.allowed_hosts
    assert "http://192.168.0.195:8000" in s.allowed_origins
    assert "https://192.168.0.195:8000" in s.allowed_origins


def test_star_disables_the_check_wholesale():
    s = build_transport_security("*")
    assert s.enable_dns_rebinding_protection is False


def test_blank_entries_are_ignored():
    s = build_transport_security(" , ,192.168.0.7:8000, ")
    assert "192.168.0.7:8000" in s.allowed_hosts
    assert "" not in s.allowed_hosts


def test_default_host_and_origin_lists_are_exact():
    s = build_transport_security("")
    assert s.allowed_hosts == ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]
    assert s.allowed_origins == [
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*",
        "https://localhost",
        "https://localhost:*",
        "https://127.0.0.1",
        "https://127.0.0.1:*",
    ]


def test_star_opt_out_leaves_host_and_origin_lists_empty():
    s = build_transport_security("*")
    assert s.allowed_hosts == []
    assert s.allowed_origins == []


def test_star_opt_out_wins_even_alongside_other_hosts():
    s = build_transport_security("192.168.0.195:8000,*")
    assert s.enable_dns_rebinding_protection is False
    assert s.allowed_hosts == []
    assert s.allowed_origins == []
