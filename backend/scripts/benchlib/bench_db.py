"""Dedicated bench-database lifecycle.

Mirrors backend/tests/conftest.py's reset discipline but against a SEPARATE
database (darkmem_bench) so bench runs never touch the real or darkmem_test
database. Importing this module overrides DATABASE_URL to the bench URL, so it
MUST be imported before any other app.* import in a bench process.

Create the database once:
  psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_bench;"
"""
import os
import subprocess
import sys
from pathlib import Path

BENCH_DATABASE_URL = os.environ.get(
    "BENCH_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench",
)
# Override BEFORE importing app.database (it builds its engine at import time).
os.environ["DATABASE_URL"] = BENCH_DATABASE_URL

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from benchlib.db_target import (  # noqa: E402
    assert_destructive_target_allowed,
    resolved_database_name,
)

# Re-exported so the historical import site keeps working; the rule itself
# lives in db_target, which has no import-time side effects.
__all__ = ["assert_destructive_target_allowed", "resolved_database_name"]

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend

engine = create_async_engine(BENCH_DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _reset_schema(target_engine=None) -> None:
    """Drop and recreate ``public`` on a pool with nothing else in it.

    **The dispose before the drop is load-bearing and is not the one the
    callers do afterwards.** ``DROP SCHEMA ... CASCADE`` needs an
    AccessExclusiveLock on every object it removes, and a pooled connection
    left idle-in-transaction from an earlier test still holds AccessShareLock
    on those same relations. Postgres then has the drop waiting on the reader
    and the reader waiting on the drop, and resolves it by killing one —
    surfacing as ``DeadlockDetectedError`` on ``DROP SCHEMA IF EXISTS public
    CASCADE`` rather than as anything resembling its cause.

    It is timing-dependent, so it fails only under load: twice on 2026-08-09,
    both times with the machine busy, and never in a quiet run of the same
    suite. That profile is the hazard, not a mitigation of it — an
    intermittently red gate teaches its readers to re-run until green, which
    is exactly how a real regression gets waved through.

    The callers' own ``dispose()`` *after* the drop stays where it is and is a
    different concern: asyncpg caches prepared-statement plans against object
    OIDs, which the drop invalidates.
    """
    target = target_engine or engine
    await target.dispose()
    async with target.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic_upgrade(url: str = BENCH_DATABASE_URL) -> None:
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed for the bench database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


async def reset_bench_db() -> None:
    """Drop + recreate the public schema, then migrate to head.

    Safe to call more than once in the same process -- run_smoke.py's
    two-pass affordability gate resets between passes deliberately. Two
    process-lifetime caches would otherwise go stale across that second
    reset and neither announces itself as a caching problem when it does:

    - asyncpg caches a prepared statement's plan against the object OIDs
      it referenced at prepare time. DROP SCHEMA CASCADE recreates those
      objects (and their implicit types) under new OIDs, so a pooled
      connection reused after the reset can hit
      ``cache lookup failed for type/relation <oid>`` on a query it had
      already prepared before the drop. Disposing the pool forces fresh
      connections with an empty statement cache.
    - app.services.embedder_registry.embedder_registry is a process-wide
      singleton that marks a fingerprint "known" and never re-checks the
      DB, so its per-fingerprint partition tables silently stop being
      recreated on a later reset unless forgotten explicitly (see
      backend/tests/test_pipeline_process_batch.py's docstring for the
      same gotcha in the main test suite).
    """
    assert_destructive_target_allowed(BENCH_DATABASE_URL, actor="reset_bench_db")
    await _reset_schema()
    await engine.dispose()
    _run_alembic_upgrade()
    _forget_registered_embedders()


def _forget_registered_embedders() -> None:
    from app.services.embedder_registry import embedder_registry
    for fingerprint in list(embedder_registry._known):
        embedder_registry.forget(fingerprint)


class BenchDatabase:
    """A bench database chosen by URL rather than by ambient environment.

    Exists so a test whose whole purpose is an in-process double run (the
    T2.54 harvest reproducibility check) can select its own disposable
    database instead of inheriting whatever ``BENCH_DATABASE_URL`` happens
    to be exported -- the module-level default above is pinned at import
    time and points at the shared unnumbered ``darkmem_bench`` under
    ``./scripts/gate.sh``, which is exactly the database a self-sufficient
    test must not clobber. The full ingest pipeline is session-factory
    driven end to end, so handing ``session_factory`` down is sufficient
    to redirect every write.
    """

    def __init__(self, url: str):
        assert_destructive_target_allowed(url, actor="BenchDatabase")
        self.url = url
        self.database = resolved_database_name(url)
        self.engine = create_async_engine(url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def ensure_created(self) -> None:
        """CREATE DATABASE if missing, via the server's ``postgres``
        maintenance database (CREATE DATABASE cannot run in a transaction,
        hence AUTOCOMMIT). Concurrent creators race benignly: the loser's
        'already exists' is swallowed."""
        if not self.database.replace("_", "").isalnum():
            raise ValueError(f"unsafe database name {self.database!r}")
        maintenance_url = self.url.rsplit("/", 1)[0] + "/postgres"
        maintenance = create_async_engine(
            maintenance_url, isolation_level="AUTOCOMMIT"
        )
        try:
            async with maintenance.connect() as conn:
                exists = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": self.database},
                )
                if exists.scalar_one_or_none() is None:
                    try:
                        await conn.execute(text(f'CREATE DATABASE "{self.database}"'))
                    except Exception as exc:  # noqa: BLE001
                        if "already exists" not in str(exc):
                            raise
        finally:
            await maintenance.dispose()

    async def reset(self) -> None:
        """Mirror of ``reset_bench_db`` against this target: create if
        missing, drop + recreate the schema, dispose the pool (stale
        prepared-statement OIDs), migrate to head, forget embedders."""
        await self.ensure_created()
        await _reset_schema(self.engine)
        await self.engine.dispose()
        _run_alembic_upgrade(self.url)
        _forget_registered_embedders()

    async def dispose(self) -> None:
        await self.engine.dispose()
