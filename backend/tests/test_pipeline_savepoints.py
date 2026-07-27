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
from app.repositories.vector import PostgresVectorRepository
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
    extraction: dict = field(default_factory=lambda: dict(EXTRACTION))
    extraction_error: Exception | None = None

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

    if extraction is not None:
        bed.extraction = dict(extraction)

    async def _extract(content, system_prompt=None, **kwargs):
        if bed.extraction_error is not None:
            raise bed.extraction_error
        return dict(bed.extraction)

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


@pytest.mark.asyncio
async def test_vector_failure_skips_the_graph_entirely(setup_database, monkeypatch):
    """Savepoint A is the gate on savepoint B: no vector, no graph attempt."""
    async with savepoint_bed(["vector write fails"], "savepoint-vecfail|4") as bed:
        async def _boom(self, *a, **k):
            raise RuntimeError("vector boom")

        monkeypatch.setattr(PostgresVectorRepository, "upsert", _boom)

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["vector"] == "error"
        assert status["graph"] == "skipped"
        assert await bed.embedding_rows() == 0
        assert await bed.entity_names() == set()


@pytest.mark.asyncio
async def test_entity_write_failure_keeps_the_embedding(setup_database, monkeypatch):
    async with savepoint_bed(["entity write fails"], "savepoint-entfail|4") as bed:
        async def _boom(self, *a, **k):
            raise RuntimeError("entity boom")

        monkeypatch.setattr(PostgresGraphRepository, "create_entity", _boom)

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["vector"] == "ok"
        assert status["graph"] == "error"
        assert await bed.embedding_rows() == 1
        assert await bed.entity_names() == set()


@pytest.mark.asyncio
async def test_entity_embedding_failure_rolls_back_only_the_graph(
    setup_database, monkeypatch
):
    """The entity row is written before its embedding, so a failure on the
    embedding must take the entity with it and leave the content vector."""
    async with savepoint_bed(["entity embedding fails"], "savepoint-embfail|4") as bed:
        async def _boom(self, *a, **k):
            raise RuntimeError("entity embedding boom")

        monkeypatch.setattr(PostgresGraphRepository, "upsert_entity_embedding", _boom)

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["vector"] == "ok"
        assert status["graph"] == "error"
        assert await bed.embedding_rows() == 1
        assert await bed.entity_names() == set()


@pytest.mark.asyncio
async def test_strip_failure_fails_the_graph_step(setup_database, monkeypatch):
    """A failed strip must fail savepoint B, not warn and write on top.

    The strip is what makes re-extraction idempotent. Swallowing its failure and
    proceeding writes the new graph over the un-stripped old one, which is
    exactly the duplicate-by-type accumulation the strip exists to prevent — with
    a log line as the only symptom and ``graph=ok`` on the wire.
    """
    async with savepoint_bed(
        ["strip fails"], "savepoint-stripfail|4", ("pgvector", "faiss", "chroma"),
    ) as bed:
        first = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert first["graph"] == "ok"
        assert await bed.entity_names() == {"pgvector", "faiss"}

        async def _boom(self, *a, **k):
            raise RuntimeError("strip boom")

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", _boom)
        bed.extraction = {
            "entities": [{"name": "chroma", "type": "tool"}],
            "relationships": [],
            "memory_type": "fact",
        }

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["vector"] == "ok"
        assert status["graph"] == "error"
        assert await bed.entity_names() == {"pgvector", "faiss"}


@pytest.mark.asyncio
async def test_savepoint_b_failure_leaves_the_prior_graph_standing(
    setup_database, monkeypatch
):
    """D1, in executable form: the strip lives INSIDE savepoint B.

    With the strip outside the savepoints its deletion is made durable by the
    outer commit, so a savepoint-B failure leaves the memory with no graph at all
    and a `technologies` denorm that no longer matches anything on disk. Inside
    B, strip-and-write is one atomic replace: the graph for a memory is always
    exactly one extraction's output.
    """
    async with savepoint_bed(
        ["prior graph survives"], "savepoint-prior|4", ("pgvector", "faiss", "chroma"),
    ) as bed:
        first = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert first["graph"] == "ok"
        assert await bed.entity_names() == {"pgvector", "faiss"}
        assert await bed.technologies() == ["faiss", "pgvector"]

        async def _boom(self, *a, **k):
            raise RuntimeError("entity boom")

        monkeypatch.setattr(PostgresGraphRepository, "create_entity", _boom)
        bed.extraction = {
            "entities": [{"name": "chroma", "type": "tool"}],
            "relationships": [],
            "memory_type": "fact",
        }

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["graph"] == "error"
        assert await bed.entity_names() == {"pgvector", "faiss"}
        assert await bed.technologies() == ["faiss", "pgvector"]


@pytest.mark.asyncio
async def test_extraction_failure_never_strips_the_prior_graph(setup_database):
    """The routine path: savepoint B is never entered, so nothing is stripped.

    An extraction failure is an ordinary outcome, not a decision to empty the
    memory's graph. With the strip outside the savepoints it ran and committed
    on this path, silently discarding a good graph whenever the extractor had a
    bad day.
    """
    async with savepoint_bed(
        ["extraction fails on the second pass"], "savepoint-extfail|4",
    ) as bed:
        first = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert first["graph"] == "ok"
        assert await bed.entity_names() == {"pgvector", "faiss"}

        bed.extraction_error = RuntimeError("extractor unreachable")
        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["extract"] == "error"
        assert status["graph"] == "skipped"
        assert await bed.entity_names() == {"pgvector", "faiss"}
        assert await bed.technologies() == ["faiss", "pgvector"]
