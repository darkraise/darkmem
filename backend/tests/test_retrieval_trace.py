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
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset

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


@pytest.mark.parametrize("door", ["list", "paginated", "traced"])
async def test_semantic_doors_require_every_requested_tag(session, session_factory, door, monkeypatch):
    from app.repositories.relational import PostgresMemoryRepository

    monkeypatch.setattr(HybridSearchService, "_record_access", lambda *args: None)
    await _seed_partition(session)
    rejected = await _seed_memory(session, content="tag intersection incomplete")
    first = await _seed_memory(session, content="tag intersection complete first")
    second = await _seed_memory(session, content="tag intersection complete second")
    tag_repo = PostgresMemoryRepository(session)
    for memory, names in ((rejected, ["one"]), (first, ["one", "two"]), (second, ["one", "two"])):
        await tag_repo.set_tags(memory.id, names)
        await _seed_embedding(session, memory.id, [1.0, 0.0, 0.0, 0.0])
    _flag_cache_reset()
    service = MemoryService(session, ProcessingPipeline(_StubLLM([1.0, 0.0, 0.0, 0.0]), session_factory))
    request = MemorySearchRequest(query="tag intersection", tags_all=["one", "two"], limit=10, with_trace=door == "traced")
    if door == "list":
        rows = await service.search_memories(request)
    else:
        result = await service.search_memories_paginated(request)
        assert result["total"] == 2
        rows = [row.memory for row in result["items"]] if door == "traced" else result["items"]
        if door == "traced":
            assert result["envelope"].excluded == {"tags": 1}
    assert {row.id for row in rows} == {first.id, second.id}
    request = request.model_copy(update={"limit": 1, "offset": 1})
    if door == "list":
        page = await service.search_memories(request)
    else:
        result = await service.search_memories_paginated(request)
        page = [row.memory for row in result["items"]] if door == "traced" else result["items"]
    assert [row.id for row in page] == [rows[1].id]


@pytest.mark.parametrize("flag", ["confidence_rank_gamma", "w_importance", "w_heat", "w_recency", "w_context_boost", "hybrid_search_enabled"])
async def test_trace_preserves_real_pipeline_membership_and_ranking(session, session_factory, flag, monkeypatch):
    from datetime import datetime, timedelta, timezone

    await _seed_partition(session)
    first = await _seed_memory(session, content="unrelated closest vector", confidence=0.1)
    second = await _seed_memory(session, content="parity keyword winner", confidence=0.99)
    if flag == "hybrid_search_enabled":
        await _seed_memory(session, content="parity keyword only without embedding")
    first.importance, second.importance = 0.0, 1.0
    await session.flush()
    await _seed_embedding(session, first.id, [1.0, 0.0, 0.0, 0.0])
    await _seed_embedding(session, second.id, [0.9, 0.1, 0.0, 0.0])
    for memory_id, count, accessed in (
        (first.id, 1, datetime.now(timezone.utc) - timedelta(days=365)),
        (second.id, 100000, datetime.now(timezone.utc)),
    ):
        await session.execute(text(
            "INSERT INTO memory_access_stats (memory_id, access_count, last_accessed) VALUES (:id, :count, :accessed)"
        ), {"id": memory_id, "count": count, "accessed": accessed})
    session.add(Config(key="feature_flags", value={flag: False if flag == "hybrid_search_enabled" else 1.0}))
    await session.flush()
    monkeypatch.setattr(HybridSearchService, "_record_access", lambda *args: None)
    _flag_cache_reset()
    service = MemoryService(session, ProcessingPipeline(_StubLLM([1.0, 0.0, 0.0, 0.0]), session_factory))
    request = MemorySearchRequest(query="parity keyword", limit=10, semantic_weight=1.0)
    ordinary = await service.search_memories_paginated(request)
    traced = await service.search_memories_paginated(request.model_copy(update={"with_trace": True}))
    expected = [first.id, second.id] if flag in {"hybrid_search_enabled", "w_context_boost"} else [second.id, first.id]
    assert [row.id for row in ordinary["items"]] == expected
    assert [row.memory.id for row in traced["items"]] == expected
    assert traced["total"] == ordinary["total"]
    if flag == "hybrid_search_enabled":
        assert traced["envelope"].channels["keyword"].ran is False


@pytest.mark.parametrize("hybrid_enabled", [False])
async def test_trace_preserves_sql_fallback_membership(session, session_factory, hybrid_enabled, monkeypatch):
    monkeypatch.setattr(HybridSearchService, "_record_access", lambda *args: None)
    await _seed_partition(session)
    memory = await _seed_memory(session, content="astrology reference")
    session.add(Config(key="feature_flags", value={"hybrid_search_enabled": hybrid_enabled}))
    await session.flush()
    _flag_cache_reset()
    service = MemoryService(session, ProcessingPipeline(_StubLLM([1.0, 0.0, 0.0, 0.0]), session_factory))
    ordinary = await service.search_memories_paginated(MemorySearchRequest(query="astrology"))
    traced = await service.search_memories_paginated(MemorySearchRequest(query="astrology", with_trace=True))
    assert [row.id for row in ordinary["items"]] == [memory.id]
    assert [row.memory.id for row in traced["items"]] == [memory.id]


@pytest.mark.parametrize("arm", ["ppr", "dual_level"])
@pytest.mark.parametrize("enabled", [False, True])
async def test_trace_preserves_graph_only_candidates_without_enabling_dormant_arms(session, session_factory, monkeypatch, arm, enabled):
    from app.services import ppr_snapshot, relation_embeddings
    from app.services.embedder_registry import embedder_registry
    from tests.test_ppr_snapshot import seed_entity, seed_relation

    monkeypatch.setattr(HybridSearchService, "_record_access", lambda *args: None)
    await _seed_partition(session)
    anchor = await _seed_memory(session, content="embedded anchor")
    graph_only = await _seed_memory(session, content="graph witness")
    await _seed_embedding(session, anchor.id, [1.0, 0.0, 0.0, 0.0])
    source = await seed_entity(session, "trace-source", [anchor.id])
    target = await seed_entity(session, "trace-target", [graph_only.id])
    relation = await seed_relation(session, source, target, [graph_only.id])
    if arm == "ppr":
        built = await ppr_snapshot.build_snapshot(session, "trace-test")
        ppr_snapshot.snapshot_cache().put(built.snapshot)
    else:
        class RelationEmbedder:
            async def embed_batch_chunked(self, texts, chunk_size, concurrency):
                return [[1.0, 0.0, 0.0, 0.0] for value in texts], FINGERPRINT

        embedder_registry.forget(FINGERPRINT)
        await relation_embeddings.embed_relations(session, RelationEmbedder(), relation_ids=[str(relation)])
    weight_key = "w_ppr" if arm == "ppr" else "w_dual"
    session.add(Config(key="feature_flags", value={f"{arm}_enabled": enabled, weight_key: 0.5}))
    await session.flush()
    _flag_cache_reset()
    try:
        service = MemoryService(session, ProcessingPipeline(_StubLLM([1.0, 0.0, 0.0, 0.0]), session_factory))
        request = MemorySearchRequest(query="no lexical match", project="trace-test", limit=10)
        ordinary = await service.search_memories_paginated(request)
        traced = await service.search_memories_paginated(request.model_copy(update={"with_trace": True}))
        expected = {anchor.id, graph_only.id} if enabled else {anchor.id}
        assert {row.id for row in ordinary["items"]} == expected
        assert [row.memory.id for row in traced["items"]] == [row.id for row in ordinary["items"]]
    finally:
        ppr_snapshot.snapshot_cache().drop("trace-test")
        embedder_registry.forget(FINGERPRINT)


async def test_trace_and_ordinary_reranking_remain_authoritative_over_rank_arms(session, session_factory, monkeypatch):
    monkeypatch.setattr(HybridSearchService, "_record_access", lambda *args: None)
    await _seed_partition(session)
    preferred = await _seed_memory(session, content="reranker prefers this")
    boosted = await _seed_memory(session, content="importance prefers this")
    preferred.importance, boosted.importance = 0.0, 1.0
    for memory in (preferred, boosted):
        await _seed_embedding(session, memory.id, [1.0, 0.0, 0.0, 0.0])
    await session.execute(text(
        f"UPDATE {child_table('memory_embeddings', FINGERPRINT)} AS embedding "
        "SET payload = jsonb_build_object('content', memory.content) FROM memories AS memory "
        "WHERE memory.id = embedding.memory_id"
    ))
    session.add(Config(key="feature_flags", value={"reranker_enabled": True, "w_importance": 1.0}))
    await session.flush()

    class RerankLLM(_StubLLM):
        async def chat_completion(self, purpose, messages, **kwargs):
            assert purpose == "reranker"
            return '{"score": 10}' if "reranker prefers this" in messages[-1]["content"] else '{"score": 1}'

    _flag_cache_reset()
    service = MemoryService(session, ProcessingPipeline(RerankLLM([1.0, 0.0, 0.0, 0.0]), session_factory))
    request = MemorySearchRequest(query="prefers", limit=10)
    ordinary = await service.search_memories_paginated(request)
    traced = await service.search_memories_paginated(request.model_copy(update={"with_trace": True}))
    assert [row.id for row in ordinary["items"]] == [preferred.id, boosted.id]
    assert [row.memory.id for row in traced["items"]] == [preferred.id, boosted.id]
    assert traced["envelope"].reranked
    assert traced["items"][0].rank_fusion_breakdown["importance"] == pytest.approx(0.5)


@pytest.mark.parametrize(("door", "with_trace"), [
    ("service_list", False), ("service_paginated", False), ("service_paginated", True),
    ("api_list", False), ("api_paginated", False), ("api_paginated", True),
])
async def test_read_only_vector_mode_uses_filtered_local_search_without_provider_dispatch(
    session, session_factory, client, auth_headers, monkeypatch, door, with_trace,
):
    from app.config import settings
    from app.main import app
    from app.repositories.relational import PostgresMemoryRepository

    attempted_dispatches = []

    class NoProviderAccess:
        def __getattr__(self, name):
            attempted_dispatches.append(name)
            raise AssertionError(f"read-only search touched provider dispatch: {name}")

    def no_fingerprint_dispatch(*args, **kwargs):
        attempted_dispatches.append("fingerprint")
        raise AssertionError("read-only keyword fallback dispatched a fingerprint")

    async def no_graph_arm(*args, **kwargs):
        attempted_dispatches.append("graph")
        raise AssertionError("vector-only fallback enabled a graph arm")

    primary = await _seed_memory(session, content="worker offline retrieval")
    secondary = await _seed_memory(session, content="worker offline retrieval")
    incomplete = await _seed_memory(session, content="worker offline retrieval")
    foreign = await _seed_memory(session, content="worker offline retrieval", project="foreign")
    deprecated = await _seed_memory(session, content="worker offline retrieval")
    archived = await _seed_memory(session, content="worker offline retrieval")
    unrelated = await _seed_memory(session, content="unrelated content")
    primary.importance, secondary.importance = 1.0, 0.0
    deprecated.status = "deprecated"
    archived.is_archived = True
    repository = PostgresMemoryRepository(session)
    for memory in (primary, secondary, incomplete, foreign, deprecated, archived, unrelated):
        await repository.set_tags(memory.id, ["required"] if memory is incomplete else ["required", "complete"])
    session.add(Config(key="feature_flags", value={
        "hybrid_search_enabled": False, "reranker_enabled": True, "w_importance": 1.0,
        "ppr_enabled": True, "w_ppr": 1.0, "dual_level_enabled": True, "w_dual": 1.0,
    }))
    await session.flush()
    monkeypatch.setattr(settings, "read_only", True)
    monkeypatch.setattr("app.services.hybrid_search.child_table", no_fingerprint_dispatch)
    monkeypatch.setattr(HybridSearchService, "_ppr_search", no_graph_arm)
    monkeypatch.setattr(HybridSearchService, "_dual_level_search", no_graph_arm)
    pipeline = ProcessingPipeline(NoProviderAccess(), session_factory)
    monkeypatch.setattr(app.state, "pipeline", pipeline, raising=False)
    service = MemoryService(session, pipeline)
    base = MemorySearchRequest(
        query="worker offline", project="trace-test", status=["active"],
        tags_all=["required", "complete"], limit=10, with_trace=with_trace,
    )
    for request in (base, base.model_copy(update={"limit": 1, "offset": 1})):
        envelope = None
        if door == "service_list":
            rows = await service.search_memories(request)
            ids = [str(row.id) for row in rows]
        elif door == "service_paginated":
            result = await service.search_memories_paginated(request)
            assert result["total"] == 2
            ids = [str(row.memory.id if with_trace else row.id) for row in result["items"]]
            if with_trace:
                envelope = result["envelope"].model_dump()
                assert all(row.scores["semantic"] is None for row in result["items"])
                assert all(row.scores["keyword"] > 0 for row in result["items"])
        else:
            path = "/api/v1/memories/search" if door == "api_list" else "/api/v1/memories/search/paginated"
            response = await client.post(path, json=request.model_dump(mode="json"), headers=auth_headers)
            assert response.status_code == 200
            result = response.json()
            if door == "api_list":
                ids = [row["id"] for row in result]
            else:
                assert result["total"] == 2
                ids = [row["id"] for row in result["items"]]
                if with_trace:
                    envelope = result["envelope"]
                    assert all(row["trace"]["scores"]["semantic"] is None for row in result["items"])
                    assert all(row["trace"]["scores"]["keyword"] > 0 for row in result["items"])
        expected = [str(secondary.id)] if request.offset else [str(primary.id), str(secondary.id)]
        assert ids == expected
        if envelope is not None:
            assert envelope["channels"]["semantic"] == {"ran": False, "failed": False}
            assert envelope["channels"]["keyword"] == {"ran": True, "failed": False}
            assert envelope["reranked"] is False
            assert envelope["excluded"] == {"tags": 1}
    assert attempted_dispatches == []
