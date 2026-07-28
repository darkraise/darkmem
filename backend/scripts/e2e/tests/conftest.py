"""Shared fixtures for the API e2e suite.

Requires ``E2E_BASE_URL`` and ``E2E_ADMIN_PASSWORD`` — set by
``scripts/e2e/run_e2e.py`` after it boots a disposable stack (see
``scripts/e2e/stack.py``). Running this directory directly without those set
is a configuration error, not something to soft-skip: the suite's one
documented entry point is ``run_e2e.py``, and a bare
``pytest scripts/e2e/tests`` without it is not a supported invocation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from e2e import e2e_db  # noqa: E402,F401  (ensures DATABASE_URL override)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set — run this suite through "
            "`python scripts/e2e/run_e2e.py`, which boots a stack and sets it."
        )
    return value


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    return _require_env("E2E_BASE_URL")


@pytest.fixture(scope="session")
def e2e_admin_password() -> str:
    return _require_env("E2E_ADMIN_PASSWORD")


@pytest.fixture
async def api_client(e2e_base_url, e2e_admin_password):
    """A logged-in httpx client against the booted stack.

    One client per test (not session-scoped) so each test's cookie jar is
    independent; login itself is cheap against a local, freshly-booted
    stack.
    """
    async with httpx.AsyncClient(base_url=e2e_base_url, timeout=30.0) as client:
        resp = await client.post(
            "/api/v1/auth/login", json={"password": e2e_admin_password},
        )
        assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
        yield client


@pytest.fixture
async def db_session():
    """A direct DB session against the e2e database.

    For assertions neither door's response ever carries — ``origin_key``
    chief among them (T1.64 plan §2.5: no response schema echoes the
    column) — and for reading ``pipeline_failures`` rows the API never
    surfaces per-memory.
    """
    async with e2e_db.session_factory() as session:
        yield session
