"""Mid-batch embedder rotation: one batch must never mix two embedding spaces.

Phase 1 embeds contents under whatever embedder is active; Phase 3 embeds
entity names some moments later. If the active embedder rotates in between,
Phase 3 registers the new fingerprint and switches to it — but every vector it
already holds was read out of the *pre-rotation* partition, and carrying those
across writes one embedder's vectors into another's ``vector(N)`` column. That
is invariant 2's cross-fingerprint prohibition, and it is silent exactly when
it matters: two embedders with different dimension counts make the insert fail
loudly, while two that share a dimension count (1536 and 768 are common across
vendors) make it succeed and leave every later cosine comparison against those
rows meaningless but numeric.

Every test here therefore rotates between two fingerprints of the **same**
width unless it is specifically exercising the differing-width case, and
attributes each stored vector to the embedder that produced it through the
marker component ``MarkedEmbedder`` writes.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.embedder_registry import child_table
from app.services.pipeline import _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import (
    assert_registered_before_every_partition_touch,
    cleanup,
    seed_memories,
    spy_partition_traffic,
)
from tests.test_pipeline_phase3 import (
    MarkedEmbedder,
    cached_names,
    entity_vectors,
    extraction_of,
    make_pipeline,
)


async def cached_vectors(factory, fingerprint: str) -> dict[str, list[float]]:
    table = child_table("entity_embedding_cache", fingerprint)
    async with factory() as s:
        exists = (await s.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.{table}"},
        )).scalar_one_or_none()
        if exists is None:
            return {}
        rows = (await s.execute(
            text(f"SELECT name_lower, embedding::text FROM {table}")
        )).all()
    return {
        name: [float(x) for x in vec.strip("[]").split(",")]
        for name, vec in rows
    }


def assert_all_produced_by(
    vectors: dict[str, list[float]], embedder: MarkedEmbedder, fingerprint: str, where: str
) -> None:
    expected = embedder.marker(fingerprint)
    for name, vector in vectors.items():
        assert vector[0] == pytest.approx(expected), (
            f"{where} holds a vector for {name!r} produced by a different "
            f"embedder (marker {vector[0]}, expected {expected}) — a "
            f"cross-fingerprint write"
        )


@pytest.mark.asyncio
async def test_pre_rotation_cache_hits_never_reach_the_new_partition(
    setup_database, monkeypatch
):
    """The defect this task exists for, at the width where it is silent.

    Batch one warms the cache under the first fingerprint. Batch two extracts
    that same name plus a fresh one, so Phase 3 has both a cache hit (old
    space) and a miss — and the miss-embed is what rotates the embedder. The
    cached vector must not be carried across into the rotated partition.
    """
    first = "rotation-hit-a|8"
    second = "rotation-hit-b|8"
    names = ["RotCached", "RotFresh"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["warm the cache", "rotate", "settle"])

    try:
        # Calls: 0 batch-1 content, 1 batch-1 entities, 2 batch-2 content,
        # 3 batch-2 entity misses — the rotation.
        embedder = MarkedEmbedder([first, first, first, second])
        pipe = make_pipeline(
            factory,
            embedder,
            [extraction_of("RotCached"), extraction_of(*names)],
            monkeypatch,
        )

        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "warm the cache", "source": "api"}]
        )
        assert pipe.last_entity_cache_stats.misses == 1
        assert await cached_names(factory, first) == ["rotcached"]

        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "rotate", "source": "api"}]
        )
        assert results[0]["graph"] == "ok"

        rotated = await entity_vectors(factory, second)
        assert sorted(rotated) == ["rotcached", "rotfresh"]
        assert_all_produced_by(
            rotated, embedder, second, f"entity_embeddings for {second}"
        )
        assert_all_produced_by(
            await cached_vectors(factory, second), embedder, second,
            f"entity_embedding_cache for {second}",
        )
        assert_all_produced_by(
            await entity_vectors(factory, first), embedder, first,
            f"entity_embeddings for {first}",
        )

        # The rotated fingerprint's cache is coherent afterwards: a following
        # batch under it re-uses both names instead of re-embedding either.
        calls_before = embedder.calls
        await pipe.process_batch(
            [{"memory_id": memory_ids[2], "content": "settle", "source": "api"}]
        )
        stats = pipe.last_entity_cache_stats
        assert (stats.memory_hits, stats.misses) == (2, 0)
        assert embedder.calls == calls_before + 1
    finally:
        await cleanup(factory, memory_ids, [first, second], names)


@pytest.mark.asyncio
async def test_rotation_registers_the_new_fingerprint_before_writing_it(
    setup_database, monkeypatch
):
    """The fix must not reach a partition ahead of its registration."""
    first = "rotation-reg-a|8"
    second = "rotation-reg-b|8"
    names = ["RotRegCached", "RotRegFresh"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["warm", "rotate"])
    events = spy_partition_traffic(monkeypatch)

    try:
        embedder = MarkedEmbedder([first, first, first, second])
        pipe = make_pipeline(
            factory,
            embedder,
            [extraction_of("RotRegCached"), extraction_of(*names)],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "warm", "source": "api"}]
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "rotate", "source": "api"}]
        )

        assert f"register:{second}" in events
        assert_registered_before_every_partition_touch(events)
    finally:
        await cleanup(factory, memory_ids, [first, second], names)


@pytest.mark.asyncio
async def test_rotation_across_a_width_change_keeps_each_space_whole(
    setup_database, monkeypatch
):
    """The loud variant: the two embedders disagree about the vector width.

    Carrying an 8-wide cache hit into a 16-wide partition would abort the write
    rather than corrupt it, so this case proves the cached name is genuinely
    re-embedded under the new fingerprint instead of merely dropped.
    """
    first = "rotation-width-a|8"
    second = "rotation-width-b|16"
    names = ["RotWideCached", "RotWideFresh"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["warm wide", "rotate wide"])

    try:
        embedder = MarkedEmbedder([first, first, first, second])
        pipe = make_pipeline(
            factory,
            embedder,
            [extraction_of("RotWideCached"), extraction_of(*names)],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "warm wide", "source": "api"}]
        )
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "rotate wide", "source": "api"}]
        )

        assert results[0]["graph"] == "ok"
        rotated = await entity_vectors(factory, second)
        assert sorted(rotated) == ["rotwidecached", "rotwidefresh"]
        for name, vector in rotated.items():
            assert len(vector) == 16, f"{name} kept the pre-rotation width"
        assert_all_produced_by(
            rotated, embedder, second, f"entity_embeddings for {second}"
        )
        assert sorted(await cached_names(factory, second)) == [
            "rotwidecached", "rotwidefresh"
        ]
    finally:
        await cleanup(factory, memory_ids, [first, second], names)


@pytest.mark.asyncio
async def test_an_embedder_rotating_every_call_degrades_instead_of_looping(
    setup_database, monkeypatch
):
    """Re-resolving after a rotation must be bounded.

    An embedder that hands back a new fingerprint on every call would otherwise
    keep the retry going forever. The batch gives up on entity vectors — Phase 4
    dedup and the entity partitions simply get nothing — rather than spinning or
    writing a mixed partition.
    """
    fingerprints = [
        "rotation-storm-a|8", "rotation-storm-b|8",
        "rotation-storm-c|8", "rotation-storm-d|8", "rotation-storm-e|8",
    ]
    names = ["RotStorm"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["every call rotates"])

    try:
        embedder = MarkedEmbedder(fingerprints)
        pipe = make_pipeline(
            factory, embedder, [extraction_of(*names)], monkeypatch
        )
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "every call rotates",
              "source": "api"}]
        )

        assert results[0]["vector"] == "ok"
        assert results[0]["graph"] == "ok"
        assert embedder.calls <= len(fingerprints)
        for fingerprint in fingerprints:
            assert await entity_vectors(factory, fingerprint) == {}
    finally:
        await cleanup(factory, memory_ids, fingerprints, names)
