"""The unified graph at scale: selection order, counts, clustering and cache."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table

FINGERPRINT = "graph-scale-embedder|4"
DIMS = 4
SCOPE = MemoryFilter(project="alpha", statuses=("active",))
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": FINGERPRINT.split("|")[0], "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, *, vector: list[float] | None = None, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="graph scale memory",
        source="test",
        memory_type="fact",
        importance=0.5,
        metadata_={},
        project="alpha",
        status="active",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()
    if vector is not None:
        child = child_table("memory_embeddings", FINGERPRINT)
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
            ),
            {
                "mid": base["id"],
                "fp": FINGERPRINT,
                "vec": str(vector),
                "payload": '{"content": "%s", "source": "test", "tags": []}' % base["content"],
            },
        )
        await session.flush()
    return memory


@pytest.mark.asyncio
async def test_bulk_read_is_newest_first(session):
    await _seed_partition(session)
    old = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], created_at=BASE)
    new = await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0], created_at=BASE + timedelta(days=2))
    mid = await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.0], created_at=BASE + timedelta(days=1))

    points = await PostgresVectorRepository(session).get_all_vectors(FINGERPRINT, limit=2, filters=SCOPE)

    assert [p["memory_id"] for p in points] == [new.id, mid.id]
    assert old.id not in {p["memory_id"] for p in points}


@pytest.mark.asyncio
async def test_bulk_read_returns_native_floats_and_importance(session, monkeypatch):
    await _seed_partition(session)
    await _add_memory(session, vector=[0.5, 0.25, 0.0, 1.0], importance=0.9)

    def _no_text_parsing(raw):
        raise AssertionError("the bulk read must not parse the text form")

    monkeypatch.setattr(PostgresVectorRepository, "_parse_vector", staticmethod(_no_text_parsing))
    [point] = await PostgresVectorRepository(session).get_all_vectors(FINGERPRINT, limit=10, filters=SCOPE)

    assert point["vector"] == pytest.approx([0.5, 0.25, 0.0, 1.0])
    assert all(isinstance(v, float) for v in point["vector"])
    assert point["importance"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_vector_matrix_matches_the_bulk_read(session):
    await _seed_partition(session)
    for i in range(3):
        await _add_memory(session, vector=[1.0, float(i), 0.0, 0.5], created_at=BASE + timedelta(days=i))
    repo = PostgresVectorRepository(session)

    points = await repo.get_all_vectors(FINGERPRINT, limit=10, filters=SCOPE)
    matrix_points, matrix = await repo.get_vector_matrix(FINGERPRINT, limit=10, filters=SCOPE)

    assert [p["memory_id"] for p in matrix_points] == [p["memory_id"] for p in points]
    assert matrix.dtype == np.float32
    assert matrix.shape == (3, 4)
    assert np.allclose(matrix, [p["vector"] for p in points])
    assert "vector" not in matrix_points[0]
    assert matrix_points[0]["project"] == "alpha"


@pytest.mark.asyncio
async def test_vector_matrix_of_an_empty_scope(session):
    await _seed_partition(session)
    points, matrix = await PostgresVectorRepository(session).get_vector_matrix(FINGERPRINT, filters=SCOPE)
    assert points == []
    assert matrix.shape == (0, 0)


@pytest.mark.asyncio
async def test_scope_stamp_counts_the_readable_set(session):
    await _seed_partition(session)
    await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], updated_at=BASE)
    newest = BASE + timedelta(hours=3)
    await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0], updated_at=newest)
    await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.0], project="beta")
    await _add_memory(session)  # no vector: not readable

    repo = PostgresVectorRepository(session)
    count, last_updated = await repo.scope_stamp(FINGERPRINT, SCOPE)

    assert count == 2
    assert last_updated == newest

    await _add_memory(session, vector=[0.0, 0.0, 0.0, 1.0], updated_at=BASE)
    assert (await repo.scope_stamp(FINGERPRINT, SCOPE))[0] == 3
