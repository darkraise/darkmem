"""The retrieval trace envelope + per-row explanation (doc 07 §8, T1.33).

Three things this file proves:

* the trace-assembly path is structurally zero-cost when not requested — a
  spy proves it is never *entered*, not merely that its output is discarded
  (Ruling 2);
* every row a filter drops is counted under a named reason, and the count
  renders even when zero rows survive — the mirror of a silent include, the
  seven leaks this session closed elsewhere (Ruling 1);
* ``rrf_score`` is the only signal the trace's ordering follows; the
  per-modality ``scores.semantic`` / ``scores.keyword`` never drive it. This
  reuses the disagreeing-lists fixture T1.30 pinned the same trap with in
  ``test_rrf_fusion.py`` (Ruling 3).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.config import Config
from app.models.memory import Memory
from app.schemas.memory import MemorySearchRequest
from app.services.confidence import CONFIDENCE_DEFAULT
from app.services.embedder_registry import child_table
from app.services.hybrid_search import ChannelTrace, HybridSearchService
from app.services.memory import MemoryService, MemoryTraceRow
from app.services.rank_fusion import rank_fusion_factor

pytestmark = pytest.mark.asyncio

FINGERPRINT = "retrieval-trace-test|4"
DIMS = 4


class _StubLLM:
    def __init__(self, vector: list[float]):
        self._vector = vector

    async def embed(self, query: str):
        return self._vector, FINGERPRINT


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "fake-embedder", "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _seed_embedding(session, memory_id: uuid.UUID, vector: list[float]) -> None:
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": memory_id, "fp": FINGERPRINT, "vec": str(vector)},
    )
    await session.flush()


async def _seed_memory(
    session, *, content: str, memory_type: str = "fact",
    confidence: float = CONFIDENCE_DEFAULT, project: str = "trace-test",
) -> Memory:
    mem = Memory(
        id=uuid.uuid4(), content=content, source="test", project=project,
        memory_type=memory_type, confidence=confidence,
    )
    session.add(mem)
    await session.flush()
    return mem


class _RealPipelineStub:
    """Just enough of ``ProcessingPipeline`` for the traced path: ``.llm``.

    The traced path never calls ``pipeline.semantic_search`` — if it did,
    this stub has no such method and the test would fail with an
    ``AttributeError`` rather than silently passing through the untraced
    logic.
    """

    def __init__(self, vector: list[float]):
        self.llm = _StubLLM(vector)


# ── Ruling 2: zero cost, structurally, when not requested ────────────


async def test_untraced_search_never_enters_trace_assembly(session, monkeypatch):
    calls = {"n": 0}

    async def spy(self, params):
        calls["n"] += 1
        raise AssertionError("trace assembly must not run when with_trace=False")

    monkeypatch.setattr(MemoryService, "_search_memories_paginated_traced", spy, raising=True)

    svc = MemoryService(session, pipeline=None)
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query=None, limit=5, with_trace=False),
    )
    assert calls["n"] == 0
    assert "envelope" not in result


async def test_untraced_search_never_calls_search_with_trace(session, monkeypatch):
    calls = {"n": 0}

    async def spy(self, *a, **kw):
        calls["n"] += 1
        raise AssertionError("search_with_trace must not run when with_trace=False")

    monkeypatch.setattr(HybridSearchService, "search_with_trace", spy, raising=True)

    mem = await _seed_memory(session, content="hello world")

    class _Pipeline:
        def __init__(self):
            self.llm = _StubLLM([1.0, 0.0, 0.0, 0.0])

        async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
            return [{"memory_id": str(mem.id), "score": 1.0}]

    svc = MemoryService(session, pipeline=_Pipeline())
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="hello", limit=5, with_trace=False),
    )
    assert calls["n"] == 0
    assert result["items"][0].id == mem.id


async def test_traced_search_does_call_search_with_trace(session, monkeypatch):
    """The mirror check: the spy above proves silence when unrequested; this
    proves the branch is real and actually reachable when requested."""
    calls = {"n": 0}
    real = HybridSearchService.search_with_trace

    async def spy(self, *a, **kw):
        calls["n"] += 1
        return await real(self, *a, **kw)

    monkeypatch.setattr(HybridSearchService, "search_with_trace", spy, raising=True)
    await _seed_partition(session)
    mem = await _seed_memory(session, content="paginated trace wiring check")
    await _seed_embedding(session, mem.id, [1.0, 0.0, 0.0, 0.0])

    svc = MemoryService(session, pipeline=_RealPipelineStub([1.0, 0.0, 0.0, 0.0]))
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="paginated trace wiring check", limit=5, with_trace=True),
    )
    assert calls["n"] == 1
    assert "envelope" in result


# ── Ruling 1: no row disappears uncounted ─────────────────────────────


async def test_excluded_rows_are_counted_by_reason_not_silently_dropped(session):
    await _seed_partition(session)
    kept = await _seed_memory(session, content="artifact retention policy", memory_type="fact")
    dropped = await _seed_memory(session, content="artifact retention notes", memory_type="note")
    await _seed_embedding(session, kept.id, [1.0, 0.0, 0.0, 0.0])
    await _seed_embedding(session, dropped.id, [1.0, 0.0, 0.0, 0.0])

    svc = MemoryService(session, pipeline=_RealPipelineStub([1.0, 0.0, 0.0, 0.0]))
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="artifact retention", limit=10, memory_type="fact", with_trace=True),
    )

    assert result["total"] == 1
    assert [row.memory.id for row in result["items"]] == [kept.id]
    assert result["envelope"].excluded == {"memory_type": 1}


async def test_exclusion_count_renders_even_when_zero_rows_survive(session):
    """The case Ruling 1 names explicitly: a caller must be able to tell
    "nothing matched" apart from "everything was filtered out". If the
    excluded count were only reported alongside surviving rows, this exact
    scenario — every match filtered away — would render as an empty result
    with no explanation, indistinguishable from a true no-match.
    """
    await _seed_partition(session)
    a = await _seed_memory(session, content="quarterly budget review", memory_type="note")
    b = await _seed_memory(session, content="quarterly budget notes", memory_type="note")
    await _seed_embedding(session, a.id, [1.0, 0.0, 0.0, 0.0])
    await _seed_embedding(session, b.id, [1.0, 0.0, 0.0, 0.0])

    svc = MemoryService(session, pipeline=_RealPipelineStub([1.0, 0.0, 0.0, 0.0]))
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="quarterly budget", limit=10, memory_type="fact", with_trace=True),
    )

    assert result["items"] == []
    assert result["total"] == 0
    # The honesty half: zero survivors is not zero information.
    assert result["envelope"].excluded.get("memory_type") == 2


# ── Ruling 3: rrf_score is the only ordering signal ───────────────────


async def test_traced_order_follows_rrf_score_not_the_per_modality_score(session):
    """Reuses T1.30's disagreeing-lists shape at the full traced path: one
    row wins on raw semantic score but is found by only one channel; the
    other scores worse on semantics but is found by both channels and wins
    on fused rank mass. A consumer reading `scores.semantic` as "the score"
    would return the wrong row first and look plausible doing it.
    """
    await _seed_partition(session)
    nearest = await _seed_memory(session, content="alpha beta gamma delta epsilon")
    both = await _seed_memory(session, content="kubernetes ingress controller tuning")
    await _seed_embedding(session, nearest.id, [1.0, 0.0, 0.0, 0.0])
    await _seed_embedding(session, both.id, [0.0, 1.0, 0.0, 0.0])

    # The stub embed() ignores the query text and always returns `nearest`'s
    # own vector — a deliberately fake embedding so the semantic side ranks
    # `nearest` first while the keyword side (real FTS over the query text)
    # ranks `both` first, exactly the disagreement this test needs.
    svc = MemoryService(session, pipeline=_RealPipelineStub([1.0, 0.0, 0.0, 0.0]))
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="kubernetes ingress", limit=10, with_trace=True),
    )

    ids = [row.memory.id for row in result["items"]]
    assert ids == [both.id, nearest.id]

    by_semantic_score = [
        row.memory.id
        for row in sorted(result["items"], key=lambda r: -(r.scores.get("semantic") or 0))
    ]
    assert by_semantic_score != ids, "fixture must disagree, or it proves nothing"

    for row in result["items"]:
        assert set(row.scores) == {"semantic", "keyword", "rrf_score", "rerank_score"}
        assert "score" not in row.scores, "the ambiguous first-seen key must never leak into the trace"


# ── rank_fusion_factor breakdown reaches the row trace ────────────────


async def test_row_trace_carries_the_rank_fusion_breakdown(session):
    await _seed_partition(session)
    session.add(Config(key="feature_flags", value={"confidence_rank_gamma": 1.0}))
    await session.flush()

    mem = await _seed_memory(session, content="confidence weighted row", confidence=0.9)
    await _seed_embedding(session, mem.id, [1.0, 0.0, 0.0, 0.0])

    svc = MemoryService(session, pipeline=_RealPipelineStub([1.0, 0.0, 0.0, 0.0]))
    result = await svc.search_memories_paginated(
        MemorySearchRequest(query="confidence weighted row", limit=10, with_trace=True),
    )

    row = result["items"][0]
    assert row.rank_fusion_breakdown["confidence"] == pytest.approx(1.15)
    assert row.rank_fusion_factor == pytest.approx(
        rank_fusion_factor({"confidence": 0.9}, {"confidence_rank_gamma": 1.0}),
    )


# ── HybridSearchService.search_with_trace: the channel-level unit ────


async def test_search_with_trace_reports_per_channel_scores_and_channel_status(session):
    await _seed_partition(session)
    mem_id = uuid.uuid4()
    mem = Memory(id=mem_id, content="kubernetes ingress controller tuning", source="test")
    session.add(mem)
    await session.flush()
    await _seed_embedding(session, mem_id, [1.0, 0.0, 0.0, 0.0])

    svc = HybridSearchService(_StubLLM([1.0, 0.0, 0.0, 0.0]), session)
    trace = await svc.search_with_trace("kubernetes ingress", limit=10)

    assert isinstance(trace, ChannelTrace)
    assert trace.semantic_failed is False
    assert trace.keyword_failed is False
    channel = trace.channel_scores[str(mem_id)]
    assert "semantic" in channel
    assert "keyword" in channel
    assert all("rrf_score" in row for row in trace.results)
