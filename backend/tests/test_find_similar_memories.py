"""Characterization test for find_similar_memories (crossref neighbor lookup).

The query is being refactored to drive the ANN probe from a literal vector (so
the HNSW index can serve it) instead of a column-vs-column self-join. Results
must be identical: nearest neighbors above the threshold, excluding self.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.vector import PostgresVectorRepository
from app.services.embedder_registry import child_table

FP = "fake-embedder|4"


async def _seed_partition(session) -> str:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'm', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FP},
    )
    child = child_table("memory_embeddings", FP)
    await session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            " embedding vector(4) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " PRIMARY KEY (memory_id, fingerprint))"
        )
    )
    return child


def _mem(**ov) -> Memory:
    base = dict(id=uuid.uuid4(), content="c", source="t", importance=0.5, metadata_={})
    base.update(ov)
    return Memory(**base)


@pytest.mark.asyncio
async def test_find_similar_memories_returns_nearest_excluding_self(session):
    child = await _seed_partition(session)
    q, near, far = _mem(content="q"), _mem(content="near"), _mem(content="far")
    session.add_all([q, near, far])
    await session.flush()

    vecs = {q.id: "[1,0,0,0]", near.id: "[0.9,0.1,0,0]", far.id: "[0,0,0,1]"}
    for mid, v in vecs.items():
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding) "
                "VALUES (:m, :fp, CAST(:v AS vector))"
            ),
            {"m": mid, "fp": FP, "v": v},
        )

    repo = PostgresVectorRepository(session)
    res = await repo.find_similar_memories(q.id, fingerprint=FP, top_k=5, min_score=0.4)
    ids = [r["memory_id"] for r in res]

    assert str(q.id) not in ids        # self excluded
    assert str(near.id) in ids         # near neighbor present (cosine ~0.99)
    assert str(far.id) not in ids      # orthogonal vector (cosine 0) below 0.4
    # scores are descending similarity
    assert all(0.0 <= r["score"] <= 1.0 for r in res)
