"""Phase 1 of ``process_batch``: the content embed and fingerprint discipline.

Three properties are load-bearing here and every one of them fails silently
rather than loudly, so each gets a test that breaks if the guard is removed
(doc 05 §5, invariant 2):

1. **Register before insert.** Every touch of a ``__<slug>`` partition — the
   Phase-5 content vector, the Phase-3 entity cache read and write, the Phase-4
   probe — must be preceded by a ``register`` of that exact fingerprint. An
   insert against an unregistered fingerprint is the violation invariant 2
   forbids; the tables simply do not exist yet.
2. **Registered exactly once.** ``_register_fingerprint`` short-circuits on the
   process-global registry cache, so a second batch under the same fingerprint
   must not re-run the DDL.
3. **Phase-1 failure has a defined downstream state.** Whether the embedder
   raises, returns a vector count that does not match the batch, or the
   registration itself fails, every memory in the batch reports ``embed=error``
   and no partition or graph row is written — and each memory still gets a real
   per-memory status rather than an exception escaping the batch.

``process_batch`` builds and commits its own sessions from ``session_factory``,
so these tests run against a real committing factory bound to ``test_engine``
(the conftest ``session`` fixture's rollback cannot reach those commits) and
tear their rows, child tables and ``embedder_registry`` cache entries down by
hand. Rows in ``events`` are deliberately left behind: that table is
append-only by trigger, so the session-end schema reset is its only cleanup.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.embedder_registry import (
    _TABLE_TEMPLATES,
    EmbedderRegistry,
    child_table,
    embedder_registry,
)
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine


class FakeEmbedder:
    """Stands in for the ``LLMOrchestrator`` embed surface.

    ``fingerprints`` is consumed one entry per call (the last entry repeats),
    which is how the mid-batch embedder rotation between Phase 1 and Phase 3 is
    reproduced without a live model.
    """

    def __init__(self, fingerprints: list[str], dims: int = 4):
        self._fingerprints = list(fingerprints)
        self.dims = dims
        self.calls = 0
        self.fail_calls: set[int] = set()
        self.drop_last = 0

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        call = self.calls
        self.calls += 1
        if call in self.fail_calls:
            raise RuntimeError("embedder unreachable")
        fingerprint = self._fingerprints[min(call, len(self._fingerprints) - 1)]
        produced = max(len(texts) - self.drop_last, 0)
        vectors = [[0.1 * (i + 1)] * self.dims for i in range(produced)]
        return vectors, fingerprint


def make_pipeline(factory, embedder, extraction: dict, monkeypatch):
    """A pipeline whose only live dependencies are the DB and ``embedder``."""
    pipe = ProcessingPipeline(embedder, factory)

    async def _extract(content, system_prompt=None, **kwargs):
        return dict(extraction)

    monkeypatch.setattr(pipe.extraction, "extract", _extract)
    return pipe


async def seed_memories(factory, contents: list[str]) -> list[uuid.UUID]:
    ids = [uuid.uuid4() for _ in contents]
    async with factory() as s:
        for mem_id, content in zip(ids, contents):
            s.add(Memory(id=mem_id, content=content, source="api",
                         importance=0.5, metadata_={}))
        await s.commit()
    return ids


async def cleanup(factory, memory_ids, fingerprints, entity_names=()):
    async with factory() as s:
        if memory_ids:
            ids = [str(m) for m in memory_ids]
            await s.execute(
                text("DELETE FROM pipeline_failures "
                     "WHERE entity_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": ids},
            )
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": ids},
            )
        if entity_names:
            await s.execute(
                text("DELETE FROM entities WHERE name = ANY(CAST(:names AS text[]))"),
                {"names": [n.lower() for n in entity_names]},
            )
        for fingerprint in fingerprints:
            for parent in _TABLE_TEMPLATES:
                await s.execute(
                    text(f"DROP TABLE IF EXISTS {child_table(parent, fingerprint)}")
                )
            await s.execute(
                text("DELETE FROM embedders WHERE fingerprint = :fp"),
                {"fp": fingerprint},
            )
        await s.commit()
    for fingerprint in fingerprints:
        embedder_registry.forget(fingerprint)


def spy_partition_traffic(monkeypatch) -> list[str]:
    """Record registrations and partition touches in call order.

    Every recorded partition entry carries the fingerprint it addresses, so the
    ordering assertion can be stated as the invariant itself: no partition is
    touched before its own fingerprint was registered.
    """
    events: list[str] = []

    real_register = EmbedderRegistry.register
    real_upsert = PostgresVectorRepository.upsert
    real_entity_upsert = PostgresGraphRepository.upsert_entity_embedding
    real_cache_read = PostgresGraphRepository.get_cached_entity_embeddings
    real_cache_write = PostgresGraphRepository.upsert_entity_embeddings_cache
    real_probe = PostgresGraphRepository.find_similar_entity

    async def register(self, session, info):
        events.append(f"register:{info.fingerprint}")
        return await real_register(self, session, info)

    async def upsert(self, *args, **kwargs):
        events.append(f"partition:{kwargs['fingerprint']}")
        return await real_upsert(self, *args, **kwargs)

    async def entity_upsert(self, entity_id, embedding, fingerprint):
        events.append(f"partition:{fingerprint}")
        return await real_entity_upsert(self, entity_id, embedding, fingerprint)

    async def cache_read(self, name_lowers, fingerprint):
        events.append(f"partition:{fingerprint}")
        return await real_cache_read(self, name_lowers, fingerprint)

    async def cache_write(self, name_to_embedding, fingerprint):
        events.append(f"partition:{fingerprint}")
        return await real_cache_write(self, name_to_embedding, fingerprint)

    async def probe(self, embedding, fingerprint, threshold=0.85, entity_type=None):
        events.append(f"partition:{fingerprint}")
        return await real_probe(self, embedding, fingerprint, threshold, entity_type)

    monkeypatch.setattr(EmbedderRegistry, "register", register)
    monkeypatch.setattr(PostgresVectorRepository, "upsert", upsert)
    monkeypatch.setattr(PostgresGraphRepository, "upsert_entity_embedding", entity_upsert)
    monkeypatch.setattr(PostgresGraphRepository, "get_cached_entity_embeddings", cache_read)
    monkeypatch.setattr(
        PostgresGraphRepository, "upsert_entity_embeddings_cache", cache_write
    )
    monkeypatch.setattr(PostgresGraphRepository, "find_similar_entity", probe)
    return events


def assert_registered_before_every_partition_touch(events: list[str]) -> None:
    registered: set[str] = set()
    for event in events:
        kind, fingerprint = event.split(":", 1)
        if kind == "register":
            registered.add(fingerprint)
        else:
            assert fingerprint in registered, (
                f"partition write under unregistered fingerprint {fingerprint!r}; "
                f"order was {events}"
            )


EXTRACTION = {
    "entities": [{"name": "PhaseOneTool", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
}


@pytest.mark.asyncio
async def test_fingerprint_registered_before_any_partition_write(
    setup_database, monkeypatch
):
    fingerprint = "phase1-order|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["phase one orders its writes"])
    events = spy_partition_traffic(monkeypatch)

    try:
        pipe = make_pipeline(
            factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch
        )
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "phase one orders its writes",
              "source": "api"}]
        )

        assert results[0]["embed"] == "ok"
        assert results[0]["vector"] == "ok"
        assert results[0]["graph"] == "ok"

        assert events, "no partition traffic was recorded"
        assert events[0] == f"register:{fingerprint}"
        assert_registered_before_every_partition_touch(events)

        child = child_table("memory_embeddings", fingerprint)
        async with factory() as s:
            row = (await s.execute(
                text(f"SELECT 1 FROM {child} WHERE memory_id = CAST(:m AS uuid)"),
                {"m": str(memory_ids[0])},
            )).first()
        assert row is not None
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["PhaseOneTool"])


@pytest.mark.asyncio
async def test_fingerprint_registered_exactly_once_across_batches(
    setup_database, monkeypatch
):
    fingerprint = "phase1-once|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["first batch", "second batch"])
    events = spy_partition_traffic(monkeypatch)

    try:
        pipe = make_pipeline(
            factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch
        )
        for mem_id, content in zip(memory_ids, ["first batch", "second batch"]):
            await pipe.process_batch(
                [{"memory_id": mem_id, "content": content, "source": "api"}]
            )

        assert events.count(f"register:{fingerprint}") == 1
        assert_registered_before_every_partition_touch(events)
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["PhaseOneTool"])


@pytest.mark.asyncio
async def test_vector_count_mismatch_is_a_phase_one_failure(setup_database, monkeypatch):
    """A short embed return must fail the batch, not silently drop its tail.

    ``zip(entries, vectors, ...)`` in Phase 5 truncates to the shortest input,
    so a vendor that returns one vector less than we sent would drop the last
    memory with no status, no ``pipeline_failures`` row and no broadcast — and
    hand the caller fewer results than entries.
    """
    fingerprint = "phase1-short|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    contents = ["short one", "short two", "short three"]
    memory_ids = await seed_memories(factory, contents)

    try:
        embedder = FakeEmbedder([fingerprint])
        embedder.drop_last = 1
        pipe = make_pipeline(factory, embedder, EXTRACTION, monkeypatch)
        results = await pipe.process_batch([
            {"memory_id": mem_id, "content": content, "source": "api"}
            for mem_id, content in zip(memory_ids, contents)
        ])

        assert len(results) == len(memory_ids)
        for status in results:
            assert status["embed"] == "error"
            assert status["vector"] == "skipped"
            assert status["graph"] == "skipped"
            # The reason has to reach the failure row: without it every
            # embedding outage is recorded as "Unknown error".
            assert "returned 2 vectors for 3 contents" in status["error"]

        async with factory() as s:
            registered = (await s.execute(
                text("SELECT 1 FROM embedders WHERE fingerprint = :fp"),
                {"fp": fingerprint},
            )).first()
            entities = (await s.execute(
                text("SELECT count(*) FROM entities WHERE name = 'phaseonetool'")
            )).scalar_one()
        assert registered is None
        assert entities == 0
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["PhaseOneTool"])


@pytest.mark.asyncio
async def test_registration_failure_degrades_to_phase_one_failure(
    setup_database, monkeypatch
):
    """A registry failure must not escape the batch as an exception.

    Every memory needs a real per-memory outcome; and with no partition to write
    into, the whole batch has to take the Phase-1-failure path.
    """
    fingerprint = "phase1-regfail|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    contents = ["registration fails one", "registration fails two"]
    memory_ids = await seed_memories(factory, contents)

    try:
        pipe = make_pipeline(
            factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch
        )

        async def _boom(fingerprint):
            raise RuntimeError("registry unavailable")

        monkeypatch.setattr(pipe, "_register_fingerprint", _boom)

        results = await pipe.process_batch([
            {"memory_id": mem_id, "content": content, "source": "api"}
            for mem_id, content in zip(memory_ids, contents)
        ])

        assert len(results) == len(memory_ids)
        for status in results:
            assert isinstance(status, dict)
            assert status["embed"] == "error"
            assert status["vector"] == "skipped"
            assert status["graph"] == "skipped"

        async with factory() as s:
            exists = (await s.execute(
                text("SELECT to_regclass(:t)"),
                {"t": child_table("memory_embeddings", fingerprint)},
            )).scalar_one()
            entities = (await s.execute(
                text("SELECT count(*) FROM entities WHERE name = 'phaseonetool'")
            )).scalar_one()
        assert exists is None
        assert entities == 0
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["PhaseOneTool"])


@pytest.mark.asyncio
async def test_rotation_keeps_content_and_entity_vectors_in_own_partitions(
    setup_database, monkeypatch
):
    """A mid-batch embedder rotation must not mix the two fingerprints.

    Phase 1's content vector belongs to the fingerprint that produced it; Phase
    3's entity vectors belong to the rotated one. Writing either into the
    other's partition puts two embedders' vectors in one ``vector(N)`` column,
    where cosine distance is undefined (invariant 2).
    """
    first = "phase1-rota|4"
    second = "phase1-rotb|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["the embedder rotated mid batch"])
    events = spy_partition_traffic(monkeypatch)

    try:
        pipe = make_pipeline(
            factory, FakeEmbedder([first, second]), EXTRACTION, monkeypatch
        )
        results = await pipe.process_batch([{
            "memory_id": memory_ids[0],
            "content": "the embedder rotated mid batch",
            "source": "api",
        }])

        assert results[0]["vector"] == "ok"
        assert results[0]["graph"] == "ok"
        assert_registered_before_every_partition_touch(events)

        async with factory() as s:
            counts = {}
            for fingerprint in (first, second):
                counts[("memory", fingerprint)] = (await s.execute(
                    text(f"SELECT count(*) FROM "
                         f"{child_table('memory_embeddings', fingerprint)}")
                )).scalar_one()
                counts[("entity", fingerprint)] = (await s.execute(
                    text(f"SELECT count(*) FROM "
                         f"{child_table('entity_embeddings', fingerprint)}")
                )).scalar_one()

        assert counts[("memory", first)] == 1
        assert counts[("memory", second)] == 0
        assert counts[("entity", second)] == 1
        assert counts[("entity", first)] == 0
    finally:
        await cleanup(factory, memory_ids, [first, second], ["PhaseOneTool"])


@pytest.mark.asyncio
async def test_empty_batch_never_reaches_the_embedder(setup_database, monkeypatch):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    embedder = FakeEmbedder(["phase1-empty|4"])
    pipe = make_pipeline(factory, embedder, EXTRACTION, monkeypatch)

    assert await pipe.process_batch([]) == []
    assert embedder.calls == 0
