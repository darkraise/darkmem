"""The triple-embeddings family is gone, and revision 0005 drops its tables.

The revision tests run on a private ``<worker database>_rev`` database created
once per run and dropped after it: the shared worker database is migrated to
head and is never downgraded.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.services.embedder_registry import (
    _AUX_INDEXES,
    _TABLE_TEMPLATES,
    _partition_slug,
    embedder_registry,
    ensure_registered,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]

_WORKER_URL = make_url(os.environ["TEST_DATABASE_URL"])
REV_DB = f"{_WORKER_URL.database}_rev"
REV_URL = _WORKER_URL.set(database=REV_DB).render_as_string(hide_password=False)
_ASYNCPG = _WORKER_URL.set(drivername="postgresql")
ADMIN_DSN = _ASYNCPG.set(database="postgres").render_as_string(hide_password=False)
REV_DSN = _ASYNCPG.set(database=REV_DB).render_as_string(hide_password=False)

PROBE_FINGERPRINT = "rev-probe|3"


async def _execute(dsn: str, *statements: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        for statement in statements:
            await conn.execute(statement)
    finally:
        await conn.close()


async def _fetch(dsn: str, query: str) -> list:
    conn = await asyncpg.connect(dsn)
    try:
        return [tuple(row) for row in await conn.fetch(query)]
    finally:
        await conn.close()


def _drop_rev_database() -> None:
    asyncio.run(_execute(
        ADMIN_DSN,
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{REV_DB}' AND pid <> pg_backend_pid()",
        f'DROP DATABASE IF EXISTS "{REV_DB}"',
    ))


def _alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env={**os.environ, "DATABASE_URL": REV_URL},
        capture_output=True,
        text=True,
        timeout=300,
    )


def _triple_tables() -> list[str]:
    rows = asyncio.run(_fetch(
        REV_DSN,
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
        "AND tablename LIKE 'triple\\_embeddings\\_\\_%' ORDER BY tablename",
    ))
    return [name for (name,) in rows]


def _create_triple_table(name: str) -> None:
    """The child shape the removed template created, written by hand."""
    asyncio.run(_execute(
        REV_DSN,
        f"CREATE TABLE {name} ("
        " fact_id UUID NOT NULL,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector(3) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (fact_id, fingerprint))",
        f"CREATE INDEX ix_{name}_fact_id ON {name} (fact_id)",
    ))


@pytest.fixture(scope="module")
def rev_database():
    _drop_rev_database()
    asyncio.run(_execute(ADMIN_DSN, f'CREATE DATABASE "{REV_DB}"'))
    try:
        yield
    finally:
        _drop_rev_database()


@pytest.fixture
def at_0004(rev_database):
    """The scratch database at revision 0004 with no triple tables left over."""
    for args in (("upgrade", "0004"), ("downgrade", "0004")):
        result = _alembic(*args)
        assert result.returncode == 0, result.stderr
    for name in _triple_tables():
        asyncio.run(_execute(REV_DSN, f"DROP TABLE {name}"))
    asyncio.run(_execute(
        REV_DSN,
        "INSERT INTO embedders (fingerprint, model_id, dims, source) "
        f"VALUES ('{PROBE_FINGERPRINT}', 'rev-probe', 3, 'llm') "
        "ON CONFLICT (fingerprint) DO NOTHING",
    ))


@pytest.mark.asyncio
async def test_registration_creates_no_triple_table(session):
    assert "triple_embeddings" not in _TABLE_TEMPLATES
    assert "triple_embeddings" not in _AUX_INDEXES

    fingerprint = f"no-triple-{uuid4().hex[:8]}|4"
    try:
        await ensure_registered(session, fingerprint)
        slug = _partition_slug(fingerprint)
        memory_child = (await session.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.memory_embeddings__{slug}"}
        )).scalar()
        triple_child = (await session.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.triple_embeddings__{slug}"}
        )).scalar()
    finally:
        embedder_registry.forget(fingerprint)
    assert memory_child is not None
    assert triple_child is None


def test_revision_drops_empty_tables_and_keeps_a_populated_one(at_0004):
    empty, populated = "triple_embeddings__rev_empty_3", "triple_embeddings__rev_full_3"
    _create_triple_table(empty)
    _create_triple_table(populated)
    asyncio.run(_execute(
        REV_DSN,
        f"INSERT INTO {populated} (fact_id, fingerprint, embedding) "
        f"VALUES ('{uuid4()}', '{PROBE_FINGERPRINT}', '[1,0,0]')",
    ))

    result = _alembic("upgrade", "0005")

    assert result.returncode == 0, result.stderr
    assert _triple_tables() == [populated]
    assert f"kept {populated} rows=1" in result.stderr
    assert empty not in result.stderr


def test_revision_is_a_no_op_without_such_tables(at_0004):
    assert _triple_tables() == []

    result = _alembic("upgrade", "0005")

    assert result.returncode == 0, result.stderr
    assert _triple_tables() == []
    version = asyncio.run(_fetch(REV_DSN, "SELECT version_num FROM alembic_version"))
    assert version == [("0005",)]


def test_module_is_gone():
    assert importlib.util.find_spec("app.services.triple_embeddings") is None
