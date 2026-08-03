"""Tests for HybridSearchService — RRF fusion + the str/UUID id boundary.

Two layers:

* ``_rrf_fuse`` is unit-tested directly (fusion ordering, weighting, the
  cross-source id-merge that combines a memory appearing on both the semantic
  and keyword sides into one fused row).
* ``HybridSearchService.search`` is exercised against the live test database:
  a real memory row plus a real per-fingerprint embedding partition are
  seeded, the embedder is faked so no network call happens, and the test
  asserts the returned ``memory_id`` is a *string* that round-trips to the
  seeded UUID. This is the str/UUID boundary the codebase relies on — hybrid
  search emits string ids and every consumer must normalize to ``UUID``.
* The honest-partial-results contract (doc 07 §2, invariant 14) is pinned
  against *database-level* failures, which is the only kind that can poison
  the sibling channel: both channels run on one shared session, so an aborted
  transaction is what a per-channel savepoint exists to contain.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.services.embedder_registry import child_table
from app.services.hybrid_search import RRF_K, HybridSearchService


# ── _rrf_fuse unit tests ──────────────────────────────────────────────


def test_rrf_fuse_orders_by_fused_score():
    semantic = [{"memory_id": "a", "score": 0.9}, {"memory_id": "b", "score": 0.8}]
    keyword = [{"memory_id": "b", "score": 5.0}, {"memory_id": "c", "score": 4.0}]
    fused = HybridSearchService._rrf_fuse(semantic, keyword, semantic_weight=0.7, limit=10)

    # b appears in both lists, so its rrf_score accumulates from both sides and
    # it must rank first.
    assert fused[0]["memory_id"] == "b"
    ids = [r["memory_id"] for r in fused]
    assert set(ids) == {"a", "b", "c"}
    # Every fused row carries rrf_score and drops the per-side ``source`` tag.
    assert all("rrf_score" in r for r in fused)
    assert all("source" not in r for r in fused)


def test_rrf_fuse_accumulates_cross_source_score():
    semantic = [{"memory_id": "x", "score": 0.9}]
    keyword = [{"memory_id": "x", "score": 0.5}]
    fused = HybridSearchService._rrf_fuse(semantic, keyword, semantic_weight=0.7, limit=10)
    assert len(fused) == 1
    expected = 0.7 / (RRF_K + 1) + 0.3 / (RRF_K + 1)
    assert fused[0]["rrf_score"] == pytest.approx(expected)


def test_rrf_fuse_respects_limit():
    semantic = [{"memory_id": str(i), "score": 1.0 / (i + 1)} for i in range(10)]
    fused = HybridSearchService._rrf_fuse(semantic, [], semantic_weight=0.7, limit=3)
    assert len(fused) == 3


def test_rrf_fuse_weight_split_favours_semantic_at_default():
    # Same rank on both sides; the 0.7 semantic weight must dominate.
    semantic = [{"memory_id": "s", "score": 0.1}]
    keyword = [{"memory_id": "k", "score": 0.1}]
    fused = HybridSearchService._rrf_fuse(semantic, keyword, semantic_weight=0.7, limit=10)
    assert fused[0]["memory_id"] == "s"


# ── integration: search() and the str/UUID boundary ──────────────────


class _FakeLLM:
    """Minimal stand-in for LLMOrchestrator: only ``embed`` is exercised by
    ``HybridSearchService.search``. Returns a fixed vector + fingerprint so no
    network call happens."""

    def __init__(self, vector: list[float], fingerprint: str):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


async def _seed_embedding_partition(session, fingerprint: str, dims: int) -> None:
    """Create the embedders row + the memory_embeddings child table for a
    fingerprint, mirroring EmbedderRegistry.register but inside the test's
    rolled-back transaction so nothing leaks."""
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint, "mid": "fake-embedder", "dims": dims},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


@pytest.mark.asyncio
async def test_search_returns_string_id_that_normalizes_to_uuid(session):
    """search() emits a string memory_id; UUID(str_id) must round-trip back to
    the seeded memory's UUID primary key (the str/UUID boundary contract)."""
    fingerprint = "fake-embedder|4"
    dims = 4
    vector = [1.0, 0.0, 0.0, 0.0]

    mem_id = uuid.uuid4()
    mem = Memory(
        id=mem_id,
        content="postgres connection pooling with pgbouncer",
        source="test",
        project="hybrid-search-test",
    )
    session.add(mem)
    await session.flush()

    await _seed_embedding_partition(session, fingerprint, dims)
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": mem_id, "fp": fingerprint, "vec": str(vector)},
    )
    await session.flush()

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    results = await svc.search("pgbouncer pooling", limit=10)

    assert results, "expected at least one fused result"
    returned_id = results[0]["memory_id"]
    # Boundary contract: the id is a *string*, not a UUID object.
    assert isinstance(returned_id, str)
    # ...and it normalizes back to the exact UUID we seeded.
    assert uuid.UUID(returned_id) == mem_id
    assert "rrf_score" in results[0]


@pytest.mark.asyncio
async def test_search_keyword_side_matches_via_fts(session):
    """The keyword side queries memories.search_vector (populated by the FTS
    trigger). A memory whose embedding does not match still surfaces via the
    keyword path, and its id is the same seeded UUID as a string."""
    fingerprint = "fake-embedder|4"
    dims = 4
    # A query vector orthogonal to the seeded embedding so the semantic side
    # ranks it last/poorly; the keyword side carries the match.
    query_vector = [0.0, 0.0, 0.0, 1.0]
    stored_vector = [1.0, 0.0, 0.0, 0.0]

    mem_id = uuid.uuid4()
    mem = Memory(
        id=mem_id,
        content="kubernetes ingress controller tuning notes",
        source="test",
        project="hybrid-search-test",
    )
    session.add(mem)
    await session.flush()

    await _seed_embedding_partition(session, fingerprint, dims)
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": mem_id, "fp": fingerprint, "vec": str(stored_vector)},
    )
    await session.flush()

    svc = HybridSearchService(_FakeLLM(query_vector, fingerprint), session)
    results = await svc.search("kubernetes ingress", limit=10)

    ids = {r["memory_id"] for r in results}
    assert str(mem_id) in ids
    assert all(isinstance(r["memory_id"], str) for r in results)


# ── the honest-partial-results contract, broken in the database (T2.66) ──
#
# A channel broken in Python — a patched query builder, an exception raised
# before ``execute`` — leaves the transaction usable, so it cannot observe
# what the per-channel savepoints exist for: a database error aborts the
# whole transaction, and without a savepoint the *other* channel's own valid
# SQL then fails on the aborted one. A one-sided outage is then reported as a
# both-sided one, naming a channel that never independently failed. Nothing
# below patches the service; each side is broken in the database.

# The semantic side reads ``memory_embeddings__<slug>``, and no such child
# table exists for a fingerprint nobody registered — the shape a rotated
# embedder produces when its partition write never happened.
_UNREGISTERED_FINGERPRINT = "never-registered-embedder|4"

# Only the keyword side spells the query into SQL, and no text search
# configuration drops these, so the tsquery the database is asked to build
# overflows. The semantic side never sees the string: it searches by vector.
_KEYWORD_SIDE_POISON = "alpha beta gamma " * 20_000


async def _seed_memory(session, content: str) -> uuid.UUID:
    mem = Memory(
        id=uuid.uuid4(), content=content, source="test", project="hybrid-search-test",
    )
    session.add(mem)
    await session.flush()
    return mem.id


async def _assert_the_session_survived(session) -> None:
    assert (await session.execute(text("SELECT 1"))).scalar() == 1


@pytest.mark.asyncio
async def test_a_database_level_semantic_failure_degrades_to_the_keyword_side(session):
    mem_id = await _seed_memory(session, "kubernetes ingress controller tuning notes")

    svc = HybridSearchService(_FakeLLM([1.0, 0.0, 0.0, 0.0], _UNREGISTERED_FINGERPRINT), session)
    trace = await svc.search_with_trace("kubernetes ingress", limit=10)

    assert trace.semantic_failed is True
    assert trace.keyword_failed is False
    assert str(mem_id) in {row["memory_id"] for row in trace.results}
    await _assert_the_session_survived(session)


@pytest.mark.asyncio
async def test_a_database_level_keyword_failure_leaves_the_session_usable(session):
    """The side that fails last poisons nothing the search itself needs.

    It runs second, so no sibling channel can observe its failure — only the
    caller can, and the caller is holding the request transaction.
    """
    fingerprint = "fake-embedder|4"
    vector = [1.0, 0.0, 0.0, 0.0]
    mem_id = await _seed_memory(session, "postgres connection pooling with pgbouncer")
    await _seed_embedding_partition(session, fingerprint, 4)
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": mem_id, "fp": fingerprint, "vec": str(vector)},
    )
    await session.flush()

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    trace = await svc.search_with_trace(_KEYWORD_SIDE_POISON, limit=10)

    assert trace.keyword_failed is True
    assert trace.semantic_failed is False
    assert str(mem_id) in {row["memory_id"] for row in trace.results}
    await _assert_the_session_survived(session)


@pytest.mark.asyncio
async def test_a_both_sided_database_failure_raises_rather_than_returning_empty(session):
    """Invariant 14 does not soften because the failure was a real one."""
    await _seed_memory(session, "postgres connection pooling with pgbouncer")

    svc = HybridSearchService(_FakeLLM([1.0, 0.0, 0.0, 0.0], _UNREGISTERED_FINGERPRINT), session)
    with pytest.raises(RuntimeError, match="both semantic and keyword"):
        await svc.search(_KEYWORD_SIDE_POISON, limit=10)

    await _assert_the_session_survived(session)
