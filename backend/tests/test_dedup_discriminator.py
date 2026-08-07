"""Phase 4 of ``process_batch``: type-constrained ANN dedup and its lexical gate.

Phase 4 is the only place in the pipeline that can silently fuse two real
entities into one. Every property below therefore fails silently rather than
loudly, and a false merge is strictly worse than a missed one: once the graph
records the merged form, re-extraction cannot recover the two originals
(doc 06 §5, ``CLAUDE.md`` "Pipeline phases", invariants 2 and 4).

1. **The two calibration points are the specification, not illustration.**
   "february outage" vs "march outage" sit at ~0.885 cosine and must NOT merge;
   "postgres" vs "postgresql" sit at ~0.974 and MUST. Both are driven here at
   their real similarities, and each test asserts the ANN probe actually
   *returned* the neighbour at that score — otherwise a threshold drift would
   turn the negative case green for the wrong reason.
2. **The type constraint lives in the probe, not after it.** A post-filter over
   an unconstrained ``LIMIT 1`` passes the same-name tests while letting a
   nearer wrong-typed neighbour consume the limit and hide the right-typed one.
3. **``canonical_map`` is keyed ``(name_lower, entity_type)``** and Phase 5
   resolves entity names *and* relation endpoints by that same key. A key that
   drifts between the phases produces relations pointing at entities that do
   not exist — missing edges, never an error.
4. **The probe fan-out is bounded by ``pipeline_concurrency``.** An unbounded
   gather over every unique name passes correctness tests and falls over on a
   large batch.
5. **One dedup pass probes exactly one fingerprint's partition.** Phase 3's
   drop-and-re-resolve on embedder rotation exists so this holds; a probe pair
   spanning two partitions would compare cosines across embedding spaces.

Like the other ``process_batch`` tests these drive a real committing
``session_factory`` bound to ``test_engine`` and tear their rows, child tables
and registry cache entries down by hand.
"""
from __future__ import annotations

import asyncio
import math
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import cleanup, seed_memories
from tests.test_pipeline_phase3 import MarkedEmbedder, entity_vectors

DIMS = 8

# The two calibration points, at the cosine similarities doc 06 §5 measured.
FEBRUARY_MARCH_COSINE = 0.885
POSTGRES_POSTGRESQL_COSINE = 0.974


def _pair(slot: int, cosine: float) -> tuple[list[float], list[float]]:
    """Two unit vectors at exactly ``cosine``, orthogonal to every other pair.

    Each pair owns two dimensions, so vectors from different pairs have cosine
    0 and cannot interfere with one another's probes.
    """
    a = [0.0] * DIMS
    b = [0.0] * DIMS
    a[slot] = 1.0
    b[slot] = cosine
    b[slot + 1] = math.sqrt(1.0 - cosine * cosine)
    return a, b


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm


class CalibratedEmbedder:
    """Embedder stand-in whose vectors have chosen pairwise similarities.

    Anything not in ``vectors`` gets its own near-orthogonal one-hot slot, so
    memory contents and incidental entity names never land inside a calibrated
    pair's neighbourhood.
    """

    def __init__(self, fingerprint: str, vectors: dict[str, list[float]]):
        self.fingerprint = fingerprint
        self._vectors = {k.lower(): v for k, v in vectors.items()}
        self._slots: dict[str, int] = {}
        self.calls = 0

    def vector(self, value: str) -> list[float]:
        known = self._vectors.get(value.lower())
        if known is not None:
            return list(known)
        slot = self._slots.setdefault(value, len(self._slots))
        vec = [0.0] * DIMS
        # Fall back into the tail dimensions the calibrated pairs never use.
        vec[DIMS - 1 - (slot % 2)] = 1.0
        return vec

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.calls += 1
        return [self.vector(t) for t in texts], self.fingerprint


def make_pipeline(factory, embedder, extractions: list[dict], monkeypatch):
    """A pipeline whose extraction result changes from one batch to the next."""
    pipe = ProcessingPipeline(embedder, factory)
    state = {"batch": 0}

    async def _extract(content, system_prompt=None, **kwargs):
        index = min(state["batch"], len(extractions) - 1)
        return {
            "entities": [dict(e) for e in extractions[index]["entities"]],
            "relationships": [
                dict(r) for r in extractions[index].get("relationships", [])
            ],
            "memory_type": "fact",
        }

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


def entities_of(*pairs: tuple[str, str]) -> dict:
    return {"entities": [{"name": n, "type": t} for n, t in pairs], "relationships": []}


def spy_probe(monkeypatch) -> list[dict]:
    """Record every Phase-4 ANN probe: its type, fingerprint and result."""
    calls: list[dict] = []
    real = PostgresGraphRepository.find_similar_entity

    async def probe(self, embedding, fingerprint, threshold=0.85, entity_type=None,
                    exclude_entity_id=None):
        match = await real(
            self, embedding, fingerprint, threshold, entity_type, exclude_entity_id,
        )
        calls.append({
            "entity_type": entity_type,
            "fingerprint": fingerprint,
            "threshold": threshold,
            "match": match,
        })
        return match

    monkeypatch.setattr(PostgresGraphRepository, "find_similar_entity", probe)
    return calls


async def entity_rows(factory, names: list[str]) -> list[tuple[str, str, int]]:
    async with factory() as s:
        rows = (await s.execute(
            text("SELECT name, entity_type, cardinality(memory_ids) FROM entities "
                 "WHERE name = ANY(CAST(:names AS text[])) ORDER BY name, entity_type"),
            {"names": [n.lower() for n in names]},
        )).all()
    return [(r[0], r[1], r[2]) for r in rows]


async def set_pipeline_concurrency(factory, value: int) -> None:
    async with factory() as s:
        await s.execute(
            text("INSERT INTO config (key, value) "
                 "VALUES ('feature_flags', CAST(:v AS jsonb)) "
                 "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"),
            {"v": f'{{"pipeline_concurrency": {value}}}'},
        )
        await s.commit()
    _flag_cache_reset()


async def clear_feature_flags(factory) -> None:
    async with factory() as s:
        await s.execute(text("DELETE FROM config WHERE key = 'feature_flags'"))
        await s.commit()
    _flag_cache_reset()


# ── Calibration point 1: 0.885 must NOT merge ───────────────────────────────


@pytest.mark.asyncio
async def test_february_and_march_outage_stay_distinct_at_0_885(
    setup_database, monkeypatch
):
    """The ANN probe finds the neighbour; ``names_distinct`` refuses the merge.

    The score assertion is what makes this test mean something: without it a
    threshold that drifted above 0.885 would keep the two entities apart for
    the wrong reason and the discriminator could be deleted unnoticed.
    """
    fingerprint = "dedup-months|8"
    feb, mar = _pair(0, FEBRUARY_MARCH_COSINE)
    assert cosine(feb, mar) == pytest.approx(FEBRUARY_MARCH_COSINE)
    names = ["February Outage", "March Outage"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["the february one", "the march one"])

    try:
        embedder = CalibratedEmbedder(
            fingerprint, {"february outage": feb, "march outage": mar}
        )
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("February Outage", "event")),
                entities_of(("March Outage", "event")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "the february one", "source": "api"}]
        )

        probes = spy_probe(monkeypatch)
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "the march one", "source": "api"}]
        )
        assert results[0]["graph"] == "ok"

        assert len(probes) == 1
        match = probes[0]["match"]
        assert match is not None, (
            "the ANN probe found nothing, so this test proves nothing about the "
            "discriminator — the calibrated similarity is below the threshold"
        )
        assert match["name"] == "february outage"
        assert match["score"] == pytest.approx(FEBRUARY_MARCH_COSINE, abs=1e-6)
        assert match["score"] >= probes[0]["threshold"]

        assert await entity_rows(factory, names) == [
            ("february outage", "event", 1),
            ("march outage", "event", 1),
        ], "a discriminating month token must not be merged away"
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


# ── Calibration point 2: 0.974 MUST merge ───────────────────────────────────


@pytest.mark.asyncio
async def test_postgres_canonicalizes_onto_postgresql_at_0_974(
    setup_database, monkeypatch
):
    """The surface-variant half of the trade-off: recall must survive the gate."""
    fingerprint = "dedup-postgres|8"
    full, short = _pair(2, POSTGRES_POSTGRESQL_COSINE)
    assert cosine(full, short) == pytest.approx(POSTGRES_POSTGRESQL_COSINE)
    names = ["PostgreSQL", "Postgres"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we run postgresql", "we run postgres"])

    try:
        embedder = CalibratedEmbedder(
            fingerprint, {"postgresql": full, "postgres": short}
        )
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("PostgreSQL", "database")),
                entities_of(("Postgres", "database")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql", "source": "api"}]
        )

        probes = spy_probe(monkeypatch)
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "we run postgres", "source": "api"}]
        )
        assert results[0]["graph"] == "ok"

        assert probes[0]["match"]["score"] == pytest.approx(
            POSTGRES_POSTGRESQL_COSINE, abs=1e-6
        )
        assert await entity_rows(factory, names) == [
            ("postgresql", "database", 2)
        ], "a surface variant with no discriminating token must merge"
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


# ── The type constraint is in the query ─────────────────────────────────────


@pytest.mark.asyncio
async def test_a_nearer_wrong_typed_neighbour_does_not_crowd_out_the_right_one(
    session,
):
    """Ruling 2, stated as the case that separates the two implementations.

    The nearest neighbour overall is a ``tool``; the nearest *concept* is
    further away but still above threshold. Constraining inside the query
    returns the concept. Probing unconstrained and discarding wrong types
    afterwards returns the tool, drops it, and reports no match at all — the
    same tests pass, and a real merge is silently lost.
    """
    fingerprint = "dedup-crowding|8"
    repo = PostgresGraphRepository(session)
    await session.execute(
        text("INSERT INTO embedders (fingerprint, model_id, dims, source) "
             "VALUES (:fp, 'm', :d, 'llm') ON CONFLICT (fingerprint) DO NOTHING"),
        {"fp": fingerprint, "d": DIMS},
    )
    child = child_table("entity_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " PRIMARY KEY (entity_id, fingerprint))"
    ))

    probe_vec, near_tool = _pair(0, 0.99)
    _, far_concept = _pair(0, 0.90)
    mem = uuid.uuid4()
    seeded = {
        ("react router", "tool"): near_tool,
        ("reactjs", "concept"): far_concept,
    }
    for (name, etype), vec in seeded.items():
        row = await repo.create_entity(
            name=name, entity_type=etype, properties={}, memory_id=mem
        )
        await session.execute(
            text(f"INSERT INTO {child} (entity_id, fingerprint, embedding) "
                 "VALUES (CAST(:e AS uuid), :fp, CAST(:v AS vector))"),
            {"e": row["id"], "fp": fingerprint, "v": str(vec)},
        )

    match = await repo.find_similar_entity(
        probe_vec, fingerprint=fingerprint, threshold=0.85, entity_type="concept",
    )
    assert match is not None, (
        "the wrong-typed nearer neighbour consumed the LIMIT — the type "
        "constraint is being applied after the query instead of inside it"
    )
    assert (match["name"], match["entity_type"]) == ("reactjs", "concept")


@pytest.mark.asyncio
async def test_an_untyped_probe_is_rejected(session):
    """A probe with no type cannot be answered correctly, so it is not answered."""
    with pytest.raises(ValueError):
        await PostgresGraphRepository(session).find_similar_entity(
            [0.0] * DIMS, fingerprint="dedup-untyped|8", threshold=0.85,
        )


@pytest.mark.asyncio
async def test_same_name_across_types_dedups_separately(setup_database, monkeypatch):
    """Done-when 1, end to end: a 0.97 neighbour of another type never merges."""
    fingerprint = "dedup-types|8"
    lib, short = _pair(4, 0.97)
    names = ["PandasLib", "Pandas"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["the tool", "the concept"])

    try:
        embedder = CalibratedEmbedder(fingerprint, {"pandaslib": lib, "pandas": short})
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("PandasLib", "tool")),
                entities_of(("Pandas", "concept")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "the tool", "source": "api"}]
        )

        probes = spy_probe(monkeypatch)
        await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "the concept", "source": "api"}]
        )

        assert [p["entity_type"] for p in probes] == ["concept"]
        assert probes[0]["match"] is None
        assert await entity_rows(factory, names) == [
            ("pandas", "concept", 1),
            ("pandaslib", "tool", 1),
        ]
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


# ── The canonical_map key contract with Phase 5 ─────────────────────────────


@pytest.mark.asyncio
async def test_canonical_map_key_shape_and_endpoint_resolution(
    setup_database, monkeypatch
):
    """Done-when 3: the key Phase 4 writes is the key Phase 5 reads.

    Asserted on both sides — the literal map handed to Phase 5, and the edge
    Phase 5 actually wrote, which must land on the canonical entity rather than
    on a fresh row under the pre-merge name.
    """
    fingerprint = "dedup-map|8"
    full, short = _pair(0, POSTGRES_POSTGRESQL_COSINE)
    names = ["PostgreSQL", "Postgres", "Darkmem"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["postgresql exists", "darkmem uses it"])

    seen: list[dict] = []
    real_write = ProcessingPipeline._write_memory

    async def spy_write(self, *args, **kwargs):
        seen.append(args[7] if len(args) > 7 else kwargs["canonical_map"])
        return await real_write(self, *args, **kwargs)

    monkeypatch.setattr(ProcessingPipeline, "_write_memory", spy_write)

    try:
        embedder = CalibratedEmbedder(
            fingerprint, {"postgresql": full, "postgres": short}
        )
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("PostgreSQL", "database")),
                {
                    "entities": [
                        {"name": "Postgres", "type": "database"},
                        {"name": "Darkmem", "type": "tool"},
                    ],
                    "relationships": [
                        {"source": "Darkmem", "target": "Postgres", "type": "USES",
                         "weight": 0.9},
                    ],
                },
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "postgresql exists", "source": "api"}]
        )
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "darkmem uses it", "source": "api"}]
        )
        assert results[0]["graph"] == "ok"

        canonical_map = seen[-1]
        assert canonical_map == {("postgres", "database"): "postgresql"}
        (key,) = canonical_map
        name_lower, entity_type = key
        assert name_lower == name_lower.lower()
        assert entity_type == "database"
        assert canonical_map[key] == canonical_map[key].lower()

        async with factory() as s:
            edges = (await s.execute(
                text("SELECT s.name, s.entity_type, t.name, t.entity_type, r.rel_type "
                     "FROM entity_relations r "
                     "JOIN entities s ON s.id = r.source_entity_id "
                     "JOIN entities t ON t.id = r.target_entity_id "
                     "WHERE CAST(:mid AS uuid) = ANY(r.memory_ids)"),
                {"mid": str(memory_ids[1])},
            )).all()
        assert [tuple(e) for e in edges] == [
            ("darkmem", "tool", "postgresql", "database", "USES")
        ], "the endpoint was not resolved through the canonical_map key"
        assert await entity_rows(factory, ["Postgres"]) == []
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


# ── Bounded fan-out ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_fanout_is_bounded_by_pipeline_concurrency(
    setup_database, monkeypatch
):
    """Done-when 4: the bound is the configured one, and it actually bites.

    Twelve unique names against a limit of two. The peak in-flight count is the
    assertion; the probe count is asserted too, so a batch that quietly stopped
    probing could not pass by fanning out nothing.
    """
    fingerprint = "dedup-fanout|8"
    names = [f"FanoutName{i}" for i in range(12)]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    memory_ids = await seed_memories(factory, ["twelve names"])
    await set_pipeline_concurrency(factory, 2)

    inflight = {"now": 0, "peak": 0}
    real = PostgresGraphRepository.find_similar_entity

    async def probe(self, embedding, fingerprint, threshold=0.85, entity_type=None):
        inflight["now"] += 1
        inflight["peak"] = max(inflight["peak"], inflight["now"])
        try:
            # Yield so a second probe can overlap this one; without the bound
            # every probe would be in flight at this point.
            await asyncio.sleep(0.01)
            return await real(self, embedding, fingerprint, threshold, entity_type)
        finally:
            inflight["now"] -= 1

    monkeypatch.setattr(PostgresGraphRepository, "find_similar_entity", probe)

    try:
        pipe = make_pipeline(
            factory,
            CalibratedEmbedder(fingerprint, {}),
            [entities_of(*[(n, "tool") for n in names])],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "twelve names", "source": "api"}]
        )

        assert inflight["peak"] > 1, "the probes never overlapped; the bound is untested"
        assert inflight["peak"] <= 2, (
            f"{inflight['peak']} probes were in flight against a "
            f"pipeline_concurrency of 2"
        )
    finally:
        await clear_feature_flags(factory)
        await cleanup(factory, memory_ids, [fingerprint], names)


# ── One dedup pass, one fingerprint ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_one_dedup_pass_probes_exactly_one_fingerprint(
    setup_database, monkeypatch
):
    """Ruling 3 restated as an assertion on this phase.

    Phase 3 drops pre-rotation cache hits and re-resolves under the new
    fingerprint precisely so a dedup pass never has to reach into two
    partitions. Cosine between two embedding spaces is undefined, so a
    ``canonical_map`` built from a mixed pass would be numeric and meaningless.
    """
    first = "dedup-rot-a|8"
    second = "dedup-rot-b|8"
    names = ["DedupRotCached", "DedupRotFresh"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["warm", "rotate"])

    try:
        embedder = MarkedEmbedder([first, first, first, second])
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("DedupRotCached", "tool")),
                entities_of(("DedupRotCached", "tool"), ("DedupRotFresh", "tool")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "warm", "source": "api"}]
        )

        probes = spy_probe(monkeypatch)
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "rotate", "source": "api"}]
        )

        assert results[0]["graph"] == "ok"
        assert probes, "the rotated batch ran no dedup probes"
        assert {p["fingerprint"] for p in probes} == {second}
    finally:
        await cleanup(factory, memory_ids, [first, second], names)


# ── Canonicalization must never overwrite the survivor's embedding ──────────


@pytest.mark.asyncio
async def test_a_canonicalized_variants_embedding_does_not_overwrite_the_survivor(
    setup_database, monkeypatch
):
    """Done-when 1 and 2.

    ``postgresql`` is created first and is the ANN match target, so it is the
    survivor when ``postgres`` merges onto it a batch later. The survivor's
    stored vector must still be its own after the merge, never the
    last-written variant's — reverting Phase 5's lookup key back to the
    pre-canonicalization name makes this fail: it would read back
    ``variant_vec`` instead.
    """
    fingerprint = "dedup-embed-survivor|8"
    survivor_vec, variant_vec = _pair(0, POSTGRES_POSTGRESQL_COSINE)
    names = ["PostgreSQL", "Postgres"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we run postgresql", "we run postgres"])

    try:
        embedder = CalibratedEmbedder(
            fingerprint, {"postgresql": survivor_vec, "postgres": variant_vec}
        )
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("PostgreSQL", "database")),
                entities_of(("Postgres", "database")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql", "source": "api"}]
        )
        created = await entity_vectors(factory, fingerprint)
        assert created["postgresql"] == pytest.approx(survivor_vec)

        results = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "we run postgres", "source": "api"}]
        )
        assert results[0]["graph"] == "ok"
        assert await entity_rows(factory, names) == [("postgresql", "database", 2)]

        after_merge = await entity_vectors(factory, fingerprint)
        assert after_merge["postgresql"] == pytest.approx(survivor_vec), (
            "the survivor's stored vector must remain its own after a "
            "canonicalized variant merges onto it"
        )
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)


@pytest.mark.asyncio
async def test_two_merges_leave_the_survivors_embedding_unchanged(
    setup_database, monkeypatch
):
    """Done-when 3, the compounding half a single pass cannot see.

    ``postgres`` merges onto the already-created ``postgresql`` twice, in two
    separate batches. The first merge's entity embedding is a Phase 3 cache
    *miss*; the second reads the same name back out of the in-memory cache —
    a *hit*. Ruling 2 is that the survivor's vector must hold steady across
    both, so a fix that only keys the miss path correctly and falls back to
    the pre-canonicalization name on a cache hit would still fail this.
    """
    fingerprint = "dedup-embed-compound|8"
    survivor_vec, variant_vec = _pair(4, POSTGRES_POSTGRESQL_COSINE)
    names = ["PostgreSQL", "Postgres"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(
        factory,
        ["we run postgresql", "we run postgres first", "we run postgres again"],
    )

    try:
        embedder = CalibratedEmbedder(
            fingerprint, {"postgresql": survivor_vec, "postgres": variant_vec}
        )
        pipe = make_pipeline(
            factory,
            embedder,
            [
                entities_of(("PostgreSQL", "database")),
                entities_of(("Postgres", "database")),
                entities_of(("Postgres", "database")),
            ],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql", "source": "api"}]
        )

        first = await pipe.process_batch(
            [{"memory_id": memory_ids[1], "content": "we run postgres first", "source": "api"}]
        )
        assert first[0]["graph"] == "ok"
        assert pipe.last_entity_cache_stats.misses == 1, "the first merge must be a cache miss"
        after_first = await entity_vectors(factory, fingerprint)
        assert after_first["postgresql"] == pytest.approx(survivor_vec)

        second = await pipe.process_batch(
            [{"memory_id": memory_ids[2], "content": "we run postgres again", "source": "api"}]
        )
        assert second[0]["graph"] == "ok"
        assert pipe.last_entity_cache_stats.memory_hits == 1, (
            "the second merge must read postgres's embedding back out of the "
            "cache, not re-embed it, or this run never exercises Ruling 2"
        )
        after_second = await entity_vectors(factory, fingerprint)
        assert after_second["postgresql"] == pytest.approx(survivor_vec), (
            "two merges compounded and moved the survivor's vector away from "
            "its own"
        )

        assert await entity_rows(factory, names) == [("postgresql", "database", 3)]
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)
