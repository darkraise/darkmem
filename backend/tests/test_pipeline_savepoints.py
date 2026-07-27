"""Phase 5 — the two-savepoint write (doc 05 §8).

Savepoint A lands the content vector and the memory-row enrichment; savepoint B
lands the graph strip, the entity/relation graph, the ``technologies`` denorm and
supersession. The split is load-bearing: a graph failure must roll back only the
graph, leaving the memory embedded, searchable, and reported as ``graph=error``
rather than ``vector=error``.

``_write_memory`` opens and commits its OWN session through ``session_factory``
and nests savepoints inside it, so it cannot run on the conftest ``session``
fixture (which already holds a restarting nested savepoint). Every test here
drives it against a real committing ``async_sessionmaker(test_engine)`` and tears
its rows, child tables and registry cache entries down by hand. Rows in
``events`` are deliberately left behind: that table is append-only by trigger, so
the session-end schema reset is its only cleanup.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import FakeEmbedder, cleanup, seed_memories

VECTOR = [0.1, 0.2, 0.3, 0.4]

EXTRACTION = {
    "entities": [
        {"name": "Pgvector", "type": "tool"},
        {"name": "faiss", "type": "tool"},
    ],
    "relationships": [
        {"source": "pgvector", "target": "faiss", "type": "REPLACES", "weight": 0.9},
    ],
    "memory_type": "fact",
}

EXTRACTION_ENTITY_NAMES = ("pgvector", "faiss")


@dataclass
class Bed:
    """One seeded memory, one registered fingerprint, one pipeline over both."""

    factory: async_sessionmaker
    pipe: ProcessingPipeline
    memory_ids: list[uuid.UUID]
    fingerprint: str
    broadcasts: list[tuple[str, dict]] = field(default_factory=list)

    @property
    def memory_id(self) -> uuid.UUID:
        return self.memory_ids[0]

    def entry(self, index: int = 0, content: str | None = None) -> dict:
        return {
            "memory_id": self.memory_ids[index],
            "content": content or f"savepoint memory {index}",
            "source": "api",
            "tags": [],
            "memory_type": None,
            "created_at": "",
        }

    async def embedding_rows(self, index: int = 0) -> int:
        table = child_table("memory_embeddings", self.fingerprint)
        async with self.factory() as s:
            return (await s.execute(
                text(f"SELECT count(*) FROM {table} "
                     "WHERE memory_id = CAST(:m AS uuid)"),
                {"m": str(self.memory_ids[index])},
            )).scalar_one()

    async def entity_names(self, index: int = 0) -> set[str]:
        async with self.factory() as s:
            rows = (await s.execute(
                text("SELECT name FROM entities "
                     "WHERE CAST(:m AS uuid) = ANY(memory_ids)"),
                {"m": str(self.memory_ids[index])},
            )).scalars().all()
        return set(rows)

    async def relation_types(self, index: int = 0) -> set[str]:
        async with self.factory() as s:
            rows = (await s.execute(
                text("SELECT rel_type FROM entity_relations "
                     "WHERE CAST(:m AS uuid) = ANY(memory_ids)"),
                {"m": str(self.memory_ids[index])},
            )).scalars().all()
        return set(rows)

    async def technologies(self, index: int = 0) -> list[str]:
        async with self.factory() as s:
            return (await s.execute(
                text("SELECT technologies FROM memories WHERE id = CAST(:m AS uuid)"),
                {"m": str(self.memory_ids[index])},
            )).scalar_one() or []


@asynccontextmanager
async def savepoint_bed(
    contents: list[str],
    fingerprint: str,
    entity_names: tuple[str, ...] = EXTRACTION_ENTITY_NAMES,
    extraction: dict | None = None,
):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    bed = Bed(
        factory=factory,
        pipe=ProcessingPipeline(FakeEmbedder([fingerprint]), factory),
        memory_ids=[],
        fingerprint=fingerprint,
    )

    async def _capture(event_type: str, payload: dict) -> None:
        bed.broadcasts.append((event_type, payload))

    bed.pipe._broadcast = _capture

    async def _extract(content, system_prompt=None, **kwargs):
        return dict(extraction if extraction is not None else EXTRACTION)

    async def _resolve():
        return bed.pipe.classification

    bed.pipe.extraction.extract = _extract  # type: ignore[method-assign]
    bed.pipe._resolve_classifier = _resolve  # type: ignore[method-assign]

    await bed.pipe._register_fingerprint(fingerprint)
    bed.memory_ids = await seed_memories(factory, contents)
    try:
        yield bed
    finally:
        await cleanup(factory, bed.memory_ids, [fingerprint], entity_names)


@pytest.mark.asyncio
async def test_graph_failure_keeps_embedding_and_records_graph_step(
    setup_database, monkeypatch
):
    """A graph-write failure must not discard the already-successful embedding.

    Phase 5 used to write the content vector and the graph inside ONE
    ``begin_nested()``, and a single ``except`` set both ``vector`` and ``graph``
    to error — so a failure in ``create_relationship`` rolled the embedding back
    too, leaving the memory unsearchable and mis-attributing the failure to the
    vector step.
    """
    async with savepoint_bed(["pgvector replaces faiss"], "savepoint-rel|4") as bed:
        async def _boom(self, *a, **k):
            raise RuntimeError("graph boom")

        monkeypatch.setattr(PostgresGraphRepository, "create_relationship", _boom)

        status = await bed.pipe._write_memory(
            bed.entry(content="pgvector replaces faiss"),
            VECTOR, bed.fingerprint, bed.fingerprint,
            dict(EXTRACTION), None, {}, {},
        )

        assert status["embed"] == "ok"
        assert status["vector"] == "ok"
        assert status["graph"] == "error"
        assert await bed.embedding_rows() == 1


@pytest.mark.asyncio
async def test_supersession_failure_still_commits_the_vector_write(
    setup_database, monkeypatch
):
    """A savepoint-B rollback must not take the whole transaction down with it.

    ``technologies`` is assigned onto ``mem_record`` inside savepoint B, so a
    rollback of B expires the ORM object. Every attribute read after the
    savepoints therefore has to come from a plain local captured before B — an
    expired attribute read on an ``AsyncSession`` outside an ``await`` triggers a
    synchronous lazy load, raises ``MissingGreenlet`` *before* ``session.commit()``
    is reached, and takes the embedding row, the enrichment, the journal row and
    the broadcast down with it.
    """
    import app.services.pipeline as pipeline_module

    async def _boom(*a, **k):
        raise RuntimeError("supersession boom")

    async with savepoint_bed(["pgvector replaces faiss"], "savepoint-super|4") as bed:
        monkeypatch.setattr(pipeline_module, "detect_supersessions", _boom)

        results = await bed.pipe.process_batch(
            [bed.entry(content="pgvector replaces faiss")]
        )

        assert len(results) == 1
        status = results[0]
        assert status["vector"] == "ok"
        assert status["graph"] == "error"
        assert await bed.embedding_rows() == 1
        assert [e for e, _ in bed.broadcasts] == ["pipeline.partial"]

        async with bed.factory() as s:
            journalled = (await s.execute(
                text("SELECT payload->>'outcome' FROM events "
                     "WHERE event_type = 'extracted' "
                     "AND object_id = CAST(:m AS uuid)"),
                {"m": str(bed.memory_id)},
            )).scalars().all()
        assert journalled == ["partial"]


@pytest.mark.asyncio
async def test_flush_failure_inside_savepoint_b_still_commits_the_vector_write(
    setup_database, monkeypatch
):
    """The other arming point: the flush between the denorm and supersession."""
    from sqlalchemy.ext.asyncio import AsyncSession

    real_flush = AsyncSession.flush

    async def _flush(self, objects=None):
        if objects is not None:
            raise RuntimeError("flush boom")
        return await real_flush(self, objects)

    async with savepoint_bed(["pgvector replaces faiss"], "savepoint-flush|4") as bed:
        monkeypatch.setattr(AsyncSession, "flush", _flush)

        results = await bed.pipe.process_batch(
            [bed.entry(content="pgvector replaces faiss")]
        )

        assert results[0]["vector"] == "ok"
        assert results[0]["graph"] == "error"
        assert await bed.embedding_rows() == 1
