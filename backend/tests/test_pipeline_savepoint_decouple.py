"""A graph-write failure must not discard the already-successful embedding.

Phase 5 wrote the content vector and the entity/relation graph inside ONE
``begin_nested()`` savepoint, and the single ``except`` set both ``vector`` and
``graph`` to error. So any failure in ``create_relationship`` / supersession
rolled back the embedding too, leaving the memory unsearchable and
mis-attributing the failure to the vector step. The vector upsert must commit in
its own savepoint that survives a graph failure.

``_write_memory`` opens and commits its OWN session via ``session_factory`` and
nests savepoints inside it, so it cannot run on the conftest ``session`` fixture
(which already holds a restarting nested savepoint). This test drives it against
a real committing factory bound to ``test_engine`` and tears the seeded rows down
explicitly; the session-end schema reset is the backstop for any leak.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.pipeline import ProcessingPipeline
from tests.conftest import test_engine

FP = "savepoint-decouple|4"


@pytest.mark.asyncio
async def test_graph_failure_keeps_embedding_and_records_graph_step(setup_database, monkeypatch):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    child = child_table("memory_embeddings", FP)
    mem_id = uuid.uuid4()

    async with factory() as s:
        await s.execute(
            text("INSERT INTO embedders (fingerprint, model_id, dims, source) "
                 "VALUES (:fp, 'm', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"),
            {"fp": FP},
        )
        await s.execute(text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            " embedding vector(4) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " PRIMARY KEY (memory_id, fingerprint))"
        ))
        s.add(Memory(id=mem_id, content="pgvector replaces faiss", source="api",
                     importance=0.5, metadata_={}))
        await s.commit()

    try:
        async def _boom(self, *a, **k):
            raise RuntimeError("graph boom")

        monkeypatch.setattr(PostgresGraphRepository, "create_relationship", _boom)

        pipe = ProcessingPipeline(object(), factory)
        extraction = {
            "entities": [{"name": "pgvector", "type": "tool"}],
            "relationships": [
                {"source": "pgvector", "target": "faiss", "type": "REPLACES", "weight": 0.9},
            ],
        }
        entry = {"memory_id": mem_id, "content": "pgvector replaces faiss", "source": "api"}

        status = await pipe._write_memory(
            entry, [0.1, 0.2, 0.3, 0.4], FP, FP, extraction, None, {}, {}, {},
        )

        # The embedding succeeded and must be reported as such; only the graph failed.
        assert status["embed"] == "ok"
        assert status["vector"] == "ok"
        assert status["graph"] == "error"

        # And the embedding row must survive the graph rollback.
        async with factory() as s:
            row = (await s.execute(
                text(f"SELECT 1 FROM {child} WHERE memory_id = :m"), {"m": str(mem_id)},
            )).first()
        assert row is not None
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(mem_id)})
            await s.execute(text(f"DROP TABLE IF EXISTS {child}"))
            await s.execute(text("DELETE FROM embedders WHERE fingerprint = :fp"), {"fp": FP})
            await s.commit()
