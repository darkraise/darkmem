"""Dedicated e2e-database lifecycle.

Mirrors ``backend/scripts/benchlib/bench_db.py``'s reset discipline against a
third, separate database (``darkmem_e2e`` by default, overridable via
``TEST_DATABASE_URL``) so the API e2e suite never touches ``darkmem``,
``darkmem_bench`` or pytest's ``darkmem_test``, which conftest drops and
re-migrates under a running stack. Importing this module overrides
``DATABASE_URL``, so it MUST be imported before any other ``app.*`` import in
an e2e process.

Create the database once:
  docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_e2e;"
"""
import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_e2e",
)
# Override BEFORE importing app.database (it builds its engine at import time).
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend

engine = create_async_engine(TEST_DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


DISPOSABLE_NAME = re.compile(r"darkmem_(test|e2e)(_[a-z0-9_]+)?")
PRODUCTION_PORT = 5432
ALEMBIC_TIMEOUT_SECONDS = 600


class NotADisposableDatabase(RuntimeError):
    pass


def _is_this_host(host: str) -> bool:
    if host in {"", "localhost"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def assert_disposable_target(url: str) -> None:
    """Refuse a reset of anything but a suite database off the production port.

    The CI service container answers on its own host's 5432, so the port is
    refused only on an address of this host (``localhost``, the empty host,
    any loopback or unspecified address), where 5432 is production.
    """
    parts = urlsplit(url)
    name = parts.path.lstrip("/")
    if not DISPOSABLE_NAME.fullmatch(name):
        raise NotADisposableDatabase(
            f"refusing to reset {name!r}: the e2e reset only drops a darkmem_test* or darkmem_e2e* database"
        )
    host = (parts.hostname or "").lower()
    if _is_this_host(host) and (parts.port or PRODUCTION_PORT) == PRODUCTION_PORT:
        raise NotADisposableDatabase(
            f"refusing to reset {name!r} on {host or 'localhost'}:5432, the production port on this host"
        )


async def _reset_schema() -> None:
    assert_disposable_target(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic_upgrade() -> None:
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
        timeout=ALEMBIC_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed for the e2e database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


async def reset_e2e_db() -> None:
    """Drop + recreate the public schema, then migrate to head.

    Disposing the pool and forgetting registered embedders mirrors
    ``bench_db.reset_bench_db`` — see that module's docstring for the two
    process-lifetime caches (asyncpg's prepared-statement OID cache and
    ``embedder_registry``'s known-fingerprint set) that go stale across a
    schema reset otherwise.
    """
    await _reset_schema()
    await engine.dispose()
    _run_alembic_upgrade()
    _forget_registered_embedders()


def _forget_registered_embedders() -> None:
    from app.services.embedder_registry import embedder_registry
    for fingerprint in list(embedder_registry._known):
        embedder_registry.forget(fingerprint)
