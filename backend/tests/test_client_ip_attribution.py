"""Login rate-limiter IP attribution behind a trusted proxy.

Regression guard for the X-Forwarded-For spoof: the limiter must key on the
address the trusted proxy observed, never the client-supplied leftmost XFF entry
(which an attacker rotates per request to defeat the per-IP lockout)."""
from types import SimpleNamespace

from app.api.routes.auth import _client_ip
from app.config import settings


class _FakeRequest:
    def __init__(self, headers: dict, client_host: str = "10.9.9.9") -> None:
        self.headers = headers
        self.client = SimpleNamespace(host=client_host)


def test_prefers_xrealip_over_spoofable_leftmost_xff(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    # Attacker spoofs the leftmost XFF; nginx overwrites X-Real-IP with the hop.
    req = _FakeRequest({
        "x-forwarded-for": "1.2.3.4, 203.0.113.7",
        "x-real-ip": "203.0.113.7",
    })
    assert _client_ip(req) == "203.0.113.7"


def test_falls_back_to_rightmost_xff_when_no_xrealip(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    # No X-Real-IP: use the rightmost hop the trusted proxy appended, never the
    # spoofable leftmost value the client supplied.
    req = _FakeRequest({"x-forwarded-for": "1.2.3.4, 203.0.113.7"})
    assert _client_ip(req) == "203.0.113.7"


def test_ignores_proxy_headers_when_untrusted(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    req = _FakeRequest(
        {"x-real-ip": "1.2.3.4", "x-forwarded-for": "1.2.3.4"},
        client_host="10.9.9.9",
    )
    assert _client_ip(req) == "10.9.9.9"
