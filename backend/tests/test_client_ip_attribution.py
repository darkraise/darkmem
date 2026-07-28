"""Which address the login rate limiter keys on, in both postures.

The property the app-as-edge posture must hold is that the client-supplied
leftmost X-Forwarded-For entry is read in NO posture -- an attacker who can
name their own IP rotates the bucket per guess and never locks out.

Asserting only that is not enough, and this is the trap the matrix exists to
avoid: with trust off the function ignores headers entirely, so "the leftmost
value was not returned" passes vacuously, and would still pass with the whole
posture switch deleted. So every row carries a positive assertion of the value
that MUST come back alongside the negatives, and four distinct addresses are
used rather than three -- X-Real-IP gets its own, so a row that reads
X-Real-IP is distinguishable from one that fell through to the rightmost hop.
"""
from types import SimpleNamespace

import pytest

from app.api.routes.auth import _client_ip
from app.config import settings

LEFTMOST_XFF = "203.0.113.9"    # client-supplied; must never be returned
RIGHTMOST_XFF = "198.51.100.4"  # the hop a trusted proxy appended
X_REAL_IP = "192.0.2.7"         # what the trusted proxy itself observed
SOCKET_PEER = "10.0.0.5"        # the transport peer

BOTH_HEADERS = {
    "x-forwarded-for": f"{LEFTMOST_XFF}, {RIGHTMOST_XFF}",
    "x-real-ip": X_REAL_IP,
}
XFF_ONLY = {"x-forwarded-for": f"{LEFTMOST_XFF}, {RIGHTMOST_XFF}"}


class _FakeRequest:
    def __init__(self, headers: dict, client_host: str = SOCKET_PEER) -> None:
        self.headers = headers
        self.client = SimpleNamespace(host=client_host)


@pytest.mark.parametrize(
    "trust,headers,expected,rejected",
    [
        pytest.param(
            True, BOTH_HEADERS, X_REAL_IP, (LEFTMOST_XFF, RIGHTMOST_XFF, SOCKET_PEER),
            id="trusted-prefers-x-real-ip-over-every-xff-hop",
        ),
        pytest.param(
            True, XFF_ONLY, RIGHTMOST_XFF, (LEFTMOST_XFF, SOCKET_PEER),
            id="trusted-falls-back-to-the-rightmost-hop",
        ),
        pytest.param(
            False, BOTH_HEADERS, SOCKET_PEER, (LEFTMOST_XFF, RIGHTMOST_XFF, X_REAL_IP),
            id="untrusted-reads-the-transport-peer-and-no-header",
        ),
        pytest.param(
            False, {}, SOCKET_PEER, (),
            id="untrusted-with-no-headers-at-all",
        ),
    ],
)
def test_client_ip_attribution(monkeypatch, trust, headers, expected, rejected):
    monkeypatch.setattr(settings, "trust_proxy_headers", trust)
    resolved = _client_ip(_FakeRequest(headers))
    assert resolved == expected
    for value in rejected:
        assert resolved != value


def test_the_leftmost_xff_is_read_in_no_posture(monkeypatch):
    for trust in (True, False):
        monkeypatch.setattr(settings, "trust_proxy_headers", trust)
        assert _client_ip(_FakeRequest(BOTH_HEADERS)) != LEFTMOST_XFF
        assert _client_ip(_FakeRequest(XFF_ONLY)) != LEFTMOST_XFF


def test_falls_back_to_unknown_without_a_transport_peer(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    request = _FakeRequest({})
    request.client = None
    assert _client_ip(request) == "unknown"
