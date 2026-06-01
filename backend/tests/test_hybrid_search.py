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
