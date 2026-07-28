"""Tests for the simplified single-LXC config surface.

Covers three behavior changes made so a same-host, same-origin deployment
needs only the three per-deploy secrets in its environment:

1. ``DATABASE_URL`` is derived from ``DB_PASSWORD`` (and the constant
   host/port/db/user) when not given explicitly; an explicit value still
   wins (external Postgres, bare-host runs).
2. ``trust_proxy_headers`` defaults to False — the app is the network edge,
   so the transport peer decides the rate-limit bucket and no request header
   can move it. Flipping it on is how a deployment with a genuinely trusted
   proxy in front opts back into the header strategy.
3. ``cookie_secure`` decouples the session-cookie Secure flag from
   ``environment`` so the stack can run production validators while still
   serving login over plain HTTP on a trusted LAN.
"""
from __future__ import annotations

import pytest
from starlette.responses import JSONResponse

from app.api.auth import set_auth_cookie
from app.config import Settings, settings

_DB_VARS = ["DATABASE_URL", "DB_PASSWORD", "DB_USER", "DB_HOST", "DB_PORT", "DB_NAME"]


def _clear(monkeypatch, *names):
    for name in names:
        monkeypatch.delenv(name, raising=False)


# A valid JWT secret so constructing a production Settings does not trip the
# JWT validator — that validator is exercised elsewhere.
_PROD = {"jwt_secret": "x" * 32}


# ── DATABASE_URL derivation ───────────────────────────────────────────


def test_database_url_derived_from_components_defaults(monkeypatch):
    _clear(monkeypatch, *_DB_VARS)
    s = Settings(_env_file=None, db_password="s3cret")
    assert s.database_url == "postgresql+asyncpg://darkmem:s3cret@localhost:5432/darkmem"


def test_database_url_honors_db_host_override(monkeypatch):
    _clear(monkeypatch, *_DB_VARS)
    s = Settings(_env_file=None, db_password="pw", db_host="postgres", db_port=6000)
    assert s.database_url == "postgresql+asyncpg://darkmem:pw@postgres:6000/darkmem"


def test_database_url_encodes_special_chars_in_credentials(monkeypatch):
    """A password with URL-significant chars (@ : /) must not corrupt the host."""
    from sqlalchemy import make_url

    _clear(monkeypatch, *_DB_VARS)
    s = Settings(_env_file=None, db_user="dark@user", db_password="Qu@ng:01/77", db_host="localhost")
    u = make_url(s.database_url)
    assert u.host == "localhost"
    assert u.username == "dark@user"
    assert u.password == "Qu@ng:01/77"


def test_explicit_database_url_overrides_components(monkeypatch):
    _clear(monkeypatch, *_DB_VARS)
    explicit = "postgresql+asyncpg://u:p@db.example:6543/other"
    s = Settings(_env_file=None, database_url=explicit, db_password="ignored")
    assert s.database_url == explicit


def test_database_url_components_are_overridable(monkeypatch):
    _clear(monkeypatch, *_DB_VARS)
    s = Settings(
        _env_file=None,
        db_password="pw",
        db_host="localhost",
        db_port=5433,
        db_name="darkmem_test",
    )
    assert s.database_url == "postgresql+asyncpg://darkmem:pw@localhost:5433/darkmem_test"


# ── trust_proxy_headers default ───────────────────────────────────────


def test_trust_proxy_headers_defaults_false(monkeypatch):
    _clear(monkeypatch, "TRUST_PROXY_HEADERS")
    s = Settings(_env_file=None)
    assert s.trust_proxy_headers is False


# ── cookie_secure resolution ──────────────────────────────────────────


def test_cookie_secure_follows_production_when_unset(monkeypatch):
    _clear(monkeypatch, "COOKIE_SECURE")
    prod = Settings(_env_file=None, environment="production", **_PROD)
    assert prod.session_cookie_secure is True
    assert Settings(_env_file=None, environment="development").session_cookie_secure is False


def test_cookie_secure_explicit_override_wins(monkeypatch):
    _clear(monkeypatch, "COOKIE_SECURE")
    s = Settings(_env_file=None, environment="production", cookie_secure=False, **_PROD)
    assert s.session_cookie_secure is False


# ── set_auth_cookie honors the resolved flag ──────────────────────────


def test_set_auth_cookie_secure_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "cookie_secure", None)
    resp = set_auth_cookie(JSONResponse(content={}), "tok")
    assert "secure" in resp.headers["set-cookie"].lower()


def test_set_auth_cookie_insecure_when_overridden(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "cookie_secure", False)
    resp = set_auth_cookie(JSONResponse(content={}), "tok")
    assert "secure" not in resp.headers["set-cookie"].lower()
