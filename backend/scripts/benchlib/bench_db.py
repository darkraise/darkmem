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

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend

engine = create_async_engine(BENCH_DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic_upgrade() -> None:
    env = {**os.environ, "DATABASE_URL": BENCH_DATABASE_URL}
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
    """Drop + recreate the public schema, then migrate to head."""
    await _reset_schema()
    _run_alembic_upgrade()
