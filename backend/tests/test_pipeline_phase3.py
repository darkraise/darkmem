"""Phase 3 of ``process_batch``: entity embedding through the two-level cache.

The phase exists to stop re-embedding entity names, so the properties under
test are the ones that make it worth having rather than merely correct:

1. **The hit rate is real and observable, split by level.** A cache stuck at a
   0% hit rate passes every correctness test while paying full embedding cost
   forever, so the counters are asserted against known-warm and known-cold
   states rather than merely asserted to exist.
2. **Cache writes are batched.** One statement for N newly embedded names. A
   per-entity write loop is equally correct and costs a round-trip per name.
3. **The key is ``(name_lower, fingerprint)``.** Entity names are lowercase on
   disk (``CLAUDE.md``), so a cache keyed on mixed case both misses constantly
   and fragments the partition.
4. **A rotation between Phase 1 and Phase 3 registers the new fingerprint and
   switches the cache key to it** — the register-before-insert half of
   invariant 2. The cross-fingerprint half lives in
   ``tests/test_embedder_rotation.py``.

Like the Phase 1 tests, these drive a real committing ``session_factory`` bound
to ``test_engine`` and tear their rows, child tables and registry cache entries
down by hand; only the embed and extraction calls are mocked.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import (
    assert_registered_before_every_partition_touch,
    cleanup,
    seed_memories,
    spy_partition_traffic,
)


class MarkedEmbedder:
    """Embedder stand-in whose vectors say who produced them.

    Component 0 carries a per-fingerprint marker and the rest is a one-hot slot
    per distinct text. Two consequences the tests depend on: a vector read back
    out of a partition can be attributed to the embedder that produced it, and
    two distinct names are near-orthogonal, so Phase 4's 0.85 dedup probe cannot
    quietly canonicalize one test entity onto another.

    ``fingerprints`` is consumed one entry per call (the last entry repeats),
    which is how a mid-batch rotation is reproduced without a live model.
    """

    def __init__(self, fingerprints: list[str], dims: int = 8):
        self._fingerprints = list(fingerprints)
        self.dims = dims
        self.calls = 0
        self.fail_calls: set[int] = set()
        self._slots: dict[str, int] = {}

    def marker(self, fingerprint: str) -> float:
        return 0.25 * (self._fingerprints.index(fingerprint) + 1)

    def vector(self, value: str, fingerprint: str) -> list[float]:
        slot = self._slots.setdefault(value, len(self._slots))
        vec = [0.0] * self.dims
        vec[0] = self.marker(fingerprint)
        vec[1 + slot % (self.dims - 1)] = 1.0
        return vec

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        call = self.calls
        self.calls += 1
        if call in self.fail_calls:
            raise RuntimeError("embedder unreachable")
        fingerprint = self._fingerprints[min(call, len(self._fingerprints) - 1)]
        return [self.vector(t, fingerprint) for t in texts], fingerprint


def make_pipeline(factory, embedder, extractions: list[dict], monkeypatch):
    """A pipeline whose extraction result can change between batches.

    ``extractions`` is consumed one entry per batch (the last entry repeats), so
    a warm-cache batch can extract the same names as the cold one that preceded
    it while still being a distinct memory.
    """
    pipe = ProcessingPipeline(embedder, factory)
    state = {"batch": 0}

    async def _extract(content, system_prompt=None, **kwargs):
        index = min(state["batch"], len(extractions) - 1)
        return dict(extractions[index])

    async def _resolve():
        return pipe.classification

    real_process_batch = pipe.process_batch

    async def _process_batch(entries):
        try:
            return await real_process_batch(entries)
        finally:
            state["batch"] += 1

    monkeypatch.setattr(pipe.extraction, "extract", _extract)
    monkeypatch.setattr(pipe, "_resolve_classifier", _resolve)
    monkeypatch.setattr(pipe, "process_batch", _process_batch)
    return pipe


def extraction_of(*names: str) -> dict:
    return {
        "entities": [{"name": name, "type": "tool"} for name in names],
        "relationships": [],
        "memory_type": "fact",
    }


async def cached_names(factory, fingerprint: str) -> list[str]:
    table = child_table("entity_embedding_cache", fingerprint)
    async with factory() as s:
        exists = (await s.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.{table}"},
        )).scalar_one_or_none()
        if exists is None:
            return []
        return list((await s.execute(
            text(f"SELECT name_lower FROM {table} ORDER BY name_lower")
        )).scalars().all())


async def entity_vectors(factory, fingerprint: str) -> dict[str, list[float]]:
    """Entity name → the vector stored in that fingerprint's own partition."""
    table = child_table("entity_embeddings", fingerprint)
    async with factory() as s:
        exists = (await s.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.{table}"},
        )).scalar_one_or_none()
        if exists is None:
            return {}
        rows = (await s.execute(
            text(f"SELECT e.name, ee.embedding::text FROM {table} ee "
                 f"JOIN entities e ON e.id = ee.entity_id")
        )).all()
    return {
        name: [float(x) for x in vec.strip("[]").split(",")]
        for name, vec in rows
    }


@pytest.mark.asyncio
async def test_warm_batch_reports_memory_hits_not_misses(setup_database, monkeypatch):
    """Done-when 1: the hit rate is a measurement, not a field that exists.

    The first batch is known-cold and must report every name as a miss; the
    second is known-warm on the same pipeline and must report every name as an
    in-memory hit and reach the embedder only for its content.
    """
    fingerprint = "phase3-warm|8"
    names = ["P3Alpha", "P3Beta"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["cold batch", "warm batch"])

    try:
        embedder = MarkedEmbedder([fingerprint])
        pipe = make_pipeline(factory, embedder, [extraction_of(*names)], monkeypatch)

        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "cold batch", "source": "api"}]
        )
        cold = pipe.last_entity_cache_stats
        assert (cold.memory_hits, cold.db_hits, cold.misses) == (0, 0, 2)
        assert cold.hit_rate == 0.0
        assert embedder.calls == 2

        await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "warm batch", "source": "api"}]
        )
        warm = pipe.last_entity_cache_stats
        assert (warm.memory_hits, warm.db_hits, warm.misses) == (2, 0, 0)
        assert warm.hit_rate == 1.0
        assert embedder.calls == 3, "a warm batch must not re-embed entity names"

        run = pipe.entity_cache_stats
        assert (run.memory_hits, run.db_hits, run.misses) == (2, 0, 2)
        assert run.lookups == 4
        assert run.hit_rate == 0.5
        assert run.as_dict()["hit_rate"] == 0.5
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


@pytest.mark.asyncio
async def test_db_cache_serves_a_pipeline_with_a_cold_memory_cache(
    setup_database, monkeypatch
):
    """Level two earns its keep: a fresh process re-uses persisted vectors."""
    fingerprint = "phase3-dbcache|8"
    names = ["P3Gamma", "P3Delta"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["first process", "second process"])

    try:
        first = make_pipeline(
            factory, MarkedEmbedder([fingerprint]), [extraction_of(*names)], monkeypatch
        )
        await first.process_batch(
            [{"memory_id": memory_ids[0], "content": "first process", "source": "api"}]
        )
        assert sorted(await cached_names(factory, fingerprint)) == [
            n.lower() for n in sorted(names)
        ]

        cold_embedder = MarkedEmbedder([fingerprint])
        second = make_pipeline(
            factory, cold_embedder, [extraction_of(*names)], monkeypatch
        )
        await second.process_batch(
            [{"memory_id": memory_ids[1], "content": "second process", "source": "api"}]
        )

        stats = second.last_entity_cache_stats
        assert (stats.memory_hits, stats.db_hits, stats.misses) == (0, 2, 0)
        assert cold_embedder.calls == 1, "the DB cache must absorb the entity embed"
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


@pytest.mark.asyncio
async def test_cache_writes_are_batched_not_per_entity(setup_database, monkeypatch):
    """Done-when 2: N new names cost one write, not N."""
    fingerprint = "phase3-batched|8"
    names = ["P3One", "P3Two", "P3Three", "P3Four", "P3Five"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["five fresh names"])

    writes: list[list[str]] = []
    real_write = PostgresGraphRepository.upsert_entity_embeddings_cache

    async def spy(self, name_to_embedding, fingerprint):
        writes.append(sorted(name_to_embedding))
        return await real_write(self, name_to_embedding, fingerprint)

    monkeypatch.setattr(
        PostgresGraphRepository, "upsert_entity_embeddings_cache", spy
    )

    try:
        pipe = make_pipeline(
            factory, MarkedEmbedder([fingerprint]), [extraction_of(*names)], monkeypatch
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "five fresh names", "source": "api"}]
        )

        assert len(writes) == 1, f"expected one batched cache write, got {writes}"
        assert writes[0] == sorted(n.lower() for n in names)
        assert sorted(await cached_names(factory, fingerprint)) == sorted(
            n.lower() for n in names
        )
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


@pytest.mark.asyncio
async def test_cache_key_is_lowercased_so_casing_variants_hit(
    setup_database, monkeypatch
):
    """Done-when 3 of the key contract: ``(name_lower, fingerprint)``.

    The same entity written ``PhaseThreeCasing`` once and ``PHASETHREECASING``
    the next batch is one cache entry, not two — otherwise every casing variant
    the model emits pays a fresh embedding and adds a row to the partition.
    """
    fingerprint = "phase3-casing|8"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["mixed case", "upper case"])

    try:
        embedder = MarkedEmbedder([fingerprint])
        pipe = make_pipeline(
            factory,
            embedder,
            [extraction_of("PhaseThreeCasing"), extraction_of("PHASETHREECASING")],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "mixed case", "source": "api"}]
        )
        assert pipe.last_entity_cache_stats.misses == 1

        await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "upper case", "source": "api"}]
        )
        stats = pipe.last_entity_cache_stats
        assert (stats.memory_hits, stats.misses) == (1, 0)
        assert embedder.calls == 3, "a casing variant must not re-embed"
        assert await cached_names(factory, fingerprint) == ["phasethreecasing"]
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["PhaseThreeCasing"])


@pytest.mark.asyncio
async def test_rotation_registers_and_switches_the_cache_key(
    setup_database, monkeypatch
):
    """Done-when 4: the rotated fingerprint owns the cache write, and is
    registered before that partition is touched."""
    first = "phase3-rota|8"
    second = "phase3-rotb|8"
    names = ["P3Rotated"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["the embedder rotated"])
    events = spy_partition_traffic(monkeypatch)

    try:
        pipe = make_pipeline(
            factory,
            MarkedEmbedder([first, second]),
            [extraction_of(*names)],
            monkeypatch,
        )
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "the embedder rotated",
              "source": "api"}]
        )

        assert results[0]["graph"] == "ok"
        assert_registered_before_every_partition_touch(events)
        assert f"register:{second}" in events

        async with factory() as s:
            registered = (await s.execute(
                text("SELECT count(*) FROM embedders WHERE fingerprint = :fp"),
                {"fp": second},
            )).scalar_one()
        assert registered == 1
        assert await cached_names(factory, second) == ["p3rotated"]
        assert await cached_names(factory, first) == []
    finally:
        await cleanup(factory, memory_ids, [first, second], names)
