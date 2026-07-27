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


CANON_FP = "savepoint-canon|4"


async def _write_with_map(bed, extraction, canonical_map):
    return await bed.pipe._write_memory(
        bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
        extraction, None, {}, canonical_map,
    )


async def _entity_rows(bed) -> dict[tuple[str, str], dict]:
    async with bed.factory() as s:
        rows = (await s.execute(
            text("SELECT name, entity_type, properties FROM entities "
                 "WHERE CAST(:m AS uuid) = ANY(memory_ids)"),
            {"m": str(bed.memory_id)},
        )).mappings().all()
    return {(r["name"], r["entity_type"]): dict(r["properties"] or {}) for r in rows}


async def _relation_endpoints(bed) -> set[tuple[str, str, str]]:
    async with bed.factory() as s:
        rows = (await s.execute(
            text("SELECT s.name AS src, t.name AS tgt, r.rel_type "
                 "FROM entity_relations r "
                 "JOIN entities s ON s.id = r.source_entity_id "
                 "JOIN entities t ON t.id = r.target_entity_id "
                 "WHERE CAST(:m AS uuid) = ANY(r.memory_ids)"),
            {"m": str(bed.memory_id)},
        )).mappings().all()
    return {(r["src"], r["tgt"], r["rel_type"]) for r in rows}


@pytest.mark.asyncio
async def test_endpoint_types_are_recovered_before_names_are_rewritten(setup_database):
    """The ordering clause of the Phase-4 contract, made unbreakable.

    Endpoint types come from the extraction's PRE-canonicalisation names. Build
    that map after the rewrite loop and every endpoint whose entity was
    canonicalized stops resolving, because its type is then looked up under a
    name the map no longer carries.
    """
    async with savepoint_bed(
        ["postgresql runs on linux"], CANON_FP,
        ("postgresql", "postgres", "linux"),
    ) as bed:
        status = await _write_with_map(
            bed,
            {
                "entities": [
                    {"name": "PostgreSQL", "type": "tool"},
                    {"name": "linux", "type": "tool"},
                ],
                "relationships": [
                    {"source": "PostgreSQL", "target": "linux", "type": "DEPLOYED_ON"},
                ],
            },
            {("postgresql", "tool"): "postgres"},
        )

        assert status["graph"] == "ok"
        assert set(await _entity_rows(bed)) == {("postgres", "tool"), ("linux", "tool")}
        assert await _relation_endpoints(bed) == {("postgres", "linux", "DEPLOYED_ON")}


@pytest.mark.asyncio
async def test_a_name_absent_from_the_map_is_never_rewritten(setup_database):
    """``key in canonical_map`` is the rewrite test.

    The map carries only canonicalized names; a name that stayed distinct is
    absent rather than mapped to itself. An implementation that resolved by name
    alone would rewrite the ``concept`` here off the ``tool`` entry.
    """
    async with savepoint_bed(
        ["react the concept"], CANON_FP, ("react", "reactjs", "linux"),
    ) as bed:
        status = await _write_with_map(
            bed,
            {
                "entities": [{"name": "react", "type": "concept"}],
                "relationships": [],
            },
            {("react", "tool"): "reactjs"},
        )

        assert status["graph"] == "ok"
        assert set(await _entity_rows(bed)) == {("react", "concept")}


@pytest.mark.asyncio
async def test_an_ambiguous_name_leaves_its_endpoints_untouched(setup_database):
    """One name under two types in one extraction has no recoverable type.

    Keyed by name alone, the last entity wins and every endpoint named ``react``
    resolves under that arbitrary type — so an endpoint that was really the
    ``tool`` gets rewritten off the ``concept``'s map entry.
    """
    async with savepoint_bed(
        ["react and react"], CANON_FP, ("react", "reactjs", "webpack"),
    ) as bed:
        status = await _write_with_map(
            bed,
            {
                "entities": [
                    {"name": "react", "type": "tool"},
                    {"name": "React", "type": "concept"},
                    {"name": "webpack", "type": "tool"},
                ],
                "relationships": [
                    {"source": "react", "target": "webpack", "type": "USES"},
                ],
            },
            {("react", "concept"): "reactjs"},
        )

        assert status["graph"] == "ok"
        assert set(await _entity_rows(bed)) == {
            ("react", "tool"), ("reactjs", "concept"), ("webpack", "tool"),
        }
        assert await _relation_endpoints(bed) == {("react", "webpack", "USES")}


@pytest.mark.asyncio
async def test_canonicalization_never_collapses_across_types(setup_database):
    async with savepoint_bed(
        ["react tool stays"], CANON_FP, ("react", "reactjs"),
    ) as bed:
        await _write_with_map(
            bed,
            {"entities": [{"name": "react", "type": "tool"}], "relationships": []},
            {("react", "concept"): "reactjs"},
        )

        assert set(await _entity_rows(bed)) == {("react", "tool")}


@pytest.mark.asyncio
async def test_display_name_follows_the_surviving_entity_not_the_variant(
    setup_database,
):
    """Invariant 7, both halves.

    A canonicalized entity must not stamp the variant's casing onto the
    surviving entity's display_name; a distinct entity whose original casing
    differs must keep it.
    """
    async with savepoint_bed(
        ["casing"], CANON_FP, ("postgresql", "postgres", "darkmem"),
    ) as bed:
        await _write_with_map(
            bed,
            {
                "entities": [
                    {"name": "PostgreSQL", "type": "tool"},
                    {"name": "Darkmem", "type": "tool"},
                ],
                "relationships": [],
            },
            {("postgresql", "tool"): "postgres"},
        )

        rows = await _entity_rows(bed)
        assert set(rows) == {("postgres", "tool"), ("darkmem", "tool")}
        assert "display_name" not in rows[("postgres", "tool")]
        assert rows[("darkmem", "tool")]["display_name"] == "Darkmem"


@pytest.mark.asyncio
async def test_a_malformed_entity_dict_is_an_extraction_failure(setup_database):
    """Nothing was written, so nothing may be reported as a failed write."""
    async with savepoint_bed(["malformed"], CANON_FP, ()) as bed:
        status = await _write_with_map(
            bed,
            {"entities": [{"type": "tool"}], "relationships": []},
            {},
        )

        assert status["extract"] == "error"
        assert status["vector"] == "ok"
        assert status["graph"] == "skipped"
        assert status["entities_count"] == 0
        assert await bed.embedding_rows() == 1


@pytest.mark.asyncio
async def test_crossrefs_run_in_a_separate_session_after_the_main_commit(
    setup_database, monkeypatch
):
    """Invariant 11: the main transaction still holds locks on the rows the
    crossref probe reads, so its session may only open after that commit."""
    from sqlalchemy.ext.asyncio import AsyncSession

    async with savepoint_bed(["crossref ordering"], "savepoint-xreford|4") as bed:
        trace: list[str] = []
        tags: dict[int, int] = {}
        counter = {"n": 0}
        real_factory = bed.pipe.session_factory

        def recording_factory():
            counter["n"] += 1
            session = real_factory()
            tags[id(session)] = counter["n"]
            return session

        bed.pipe.session_factory = recording_factory

        real_commit = AsyncSession.commit
        real_upsert = PostgresVectorRepository.upsert
        real_find = PostgresVectorRepository.find_similar_memories

        async def commit(self):
            trace.append(f"commit:{tags.get(id(self))}")
            return await real_commit(self)

        async def upsert(self, *a, **k):
            trace.append(f"vector:{tags.get(id(self.session))}")
            return await real_upsert(self, *a, **k)

        async def find(self, *a, **k):
            trace.append(f"crossref:{tags.get(id(self.session))}")
            return await real_find(self, *a, **k)

        monkeypatch.setattr(AsyncSession, "commit", commit)
        monkeypatch.setattr(PostgresVectorRepository, "upsert", upsert)
        monkeypatch.setattr(PostgresVectorRepository, "find_similar_memories", find)

        await bed.pipe.process_batch([bed.entry()])

        write = next(e for e in trace if e.startswith("vector:")).split(":")[1]
        xref = next(e for e in trace if e.startswith("crossref:")).split(":")[1]
        assert write != xref
        assert trace.index(f"commit:{write}") < trace.index(f"crossref:{xref}")


@pytest.mark.asyncio
async def test_an_empty_similar_set_clears_the_previous_crossrefs(
    setup_database, monkeypatch
):
    """DELETE+INSERT, not INSERT-when-non-empty.

    The early return on an empty list sat above the DELETE, so a memory whose
    neighbours were since deleted — or which an embedder rotation moved into a
    sparse partition — kept crossref rows pointing at similarities that no
    longer hold, with nothing that ever clears them.
    """
    async with savepoint_bed(
        ["stale crossrefs", "the neighbour"], "savepoint-xrefstale|4",
    ) as bed:
        async with bed.factory() as s:
            await s.execute(
                text("INSERT INTO memory_crossrefs (memory_id, related_memory_id, score) "
                     "VALUES (CAST(:a AS uuid), CAST(:b AS uuid), 0.9)"),
                {"a": str(bed.memory_ids[0]), "b": str(bed.memory_ids[1])},
            )
            await s.commit()

        async def _none(self, *a, **k):
            return []

        monkeypatch.setattr(PostgresVectorRepository, "find_similar_memories", _none)

        status = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert status["vector"] == "ok"

        async with bed.factory() as s:
            remaining = (await s.execute(
                text("SELECT count(*) FROM memory_crossrefs "
                     "WHERE memory_id = CAST(:a AS uuid)"),
                {"a": str(bed.memory_ids[0])},
            )).scalar_one()
        assert remaining == 0


@pytest.mark.asyncio
async def test_a_crossref_failure_changes_no_step_status(setup_database, monkeypatch):
    """Crossrefs are enrichment after the commit, not a pipeline step; there is
    deliberately no ``crossref`` field in the status dict."""
    async with savepoint_bed(["crossref fails"], "savepoint-xreffail|4") as bed:
        async def _boom(self, *a, **k):
            raise RuntimeError("crossref boom")

        monkeypatch.setattr(PostgresVectorRepository, "find_similar_memories", _boom)

        status = (await bed.pipe.process_batch([bed.entry()]))[0]

        assert status["vector"] == "ok"
        assert status["graph"] == "ok"
        assert status["error"] is None
        assert [e for e, _ in bed.broadcasts] == ["pipeline.completed"]
