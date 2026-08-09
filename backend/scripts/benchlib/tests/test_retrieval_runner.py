"""DB-backed tests for the real-retriever driver.

Opts into ``_bench_db`` (contrast test_retrieval_scorer.py, which is pure
and does not). This proves ``run_retrieval`` actually composes with the
real ``ProcessingPipeline`` end to end; the id-normalisation invariant
itself is a scorer concern and is tested there, not here.
"""
import pytest

from benchlib import bench_db, ingest, retrieval_runner
from benchlib.caching_llm import CachingLLMOrchestrator

pytestmark = pytest.mark.usefixtures("_bench_db")

_STUB_EXTRACTION = (
    '{"entities": [], "relationships": [], "memory_type": "fact", '
    '"importance": 0.5, "summary": "stub summary", "emotions": [], "flags": []}'
)


def _vec(text: str) -> list[float]:
    """A tiny deterministic embedding: one axis per keyword, so ANN search
    over these stub vectors actually discriminates the three memories
    instead of returning an arbitrary tie order."""
    lowered = text.lower()
    return [
        1.0 if "alpha" in lowered else 0.0,
        1.0 if "beta" in lowered else 0.0,
        1.0 if "gamma" in lowered else 0.0,
    ]


class _StubLLM(CachingLLMOrchestrator):
    async def _live_embed(self, text):
        return _vec(text), "stub-embed|3"

    async def _live_embed_batch(self, texts):
        return [_vec(t) for t in texts], "stub-embed|3"

    async def _live_chat(self, purpose, messages, **kwargs):
        return _STUB_EXTRACTION


_ENTRIES = [
    {"content": "The alpha service handles billing.", "memory_type": "fact"},
    {"content": "The beta pipeline handles ingestion.", "memory_type": "fact"},
    {"content": "The gamma worker handles cleanup.", "memory_type": "fact"},
]


async def _ingest_three(tmp_path) -> list[str]:
    await bench_db.reset_bench_db()
    llm = _StubLLM({}, cache_dir=str(tmp_path))
    result = await ingest.run_ingest(llm, _ENTRIES, ingest.GateConfig())
    return llm, [o["memory_id"] for o in result.outcomes]


@pytest.mark.asyncio
async def test_run_retrieval_actually_invokes_pipeline_semantic_search(monkeypatch, tmp_path):
    """A behavioural guard, not a source-text one. The previous version of
    this test asserted substrings of inspect.getsource(retrieval_runner) --
    a forked SQL reimplementation that merely kept ProcessingPipeline named
    in a docstring would still have passed it (found by adversarial review).
    This one fails unless ProcessingPipeline.semantic_search is the actual
    thing invoked, with the query and limit run_retrieval was given."""
    from app.services.pipeline import ProcessingPipeline

    llm, ids = await _ingest_three(tmp_path)
    calls: list[tuple[str, int, object]] = []
    original = ProcessingPipeline.semantic_search

    async def spy(self, query, limit=20, semantic_weight=0.7, filters=None):
        calls.append((query, limit, filters))
        return await original(
            self, query, limit=limit, semantic_weight=semantic_weight,
            filters=filters,
        )

    monkeypatch.setattr(ProcessingPipeline, "semantic_search", spy)

    gold_pairs = [
        {"id": "t-1", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
    ]

    ranked = await retrieval_runner.run_retrieval(
        llm, bench_db.session_factory, gold_pairs, limit=3,
    )

    # `filters=None` is the unscoped read every baseline row in the ledger was
    # measured under. Pinning it here is what stops a future caller from
    # quietly giving the default path a scope and invalidating those rows
    # (ruling 3); the arm-ablation path passes a scope explicitly instead.
    assert calls == [("alpha", 3, None)]
    assert ranked["t-1"]  # the spy delegated to the real method, which returned real hits


@pytest.mark.asyncio
async def test_run_retrieval_returns_one_ranked_list_per_live_pair(tmp_path):
    llm, ids = await _ingest_three(tmp_path)
    gold_pairs = [
        {"id": "t-1", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
        {"id": "t-2", "query": "beta", "relevant_memory_ids": [ids[1]], "slice_tags": ["exact"],
         "retired": True},
        {"id": "t-3", "query": "gamma", "relevant_memory_ids": [ids[2]], "slice_tags": ["exact"]},
    ]

    ranked = await retrieval_runner.run_retrieval(
        llm, bench_db.session_factory, gold_pairs, limit=2,
    )

    # The retired pair is skipped entirely -- never queried, never scored.
    assert set(ranked) == {"t-1", "t-3"}
    for hits in ranked.values():
        assert len(hits) <= 2
        assert all(str(h) in ids for h in hits)


@pytest.mark.asyncio
async def test_run_retrieval_ranks_the_lexically_matching_memory_first(tmp_path):
    llm, ids = await _ingest_three(tmp_path)
    gold_pairs = [
        {"id": "t-1", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
        {"id": "t-3", "query": "gamma", "relevant_memory_ids": [ids[2]], "slice_tags": ["exact"]},
    ]

    ranked = await retrieval_runner.run_retrieval(
        llm, bench_db.session_factory, gold_pairs, limit=3,
    )

    assert str(ranked["t-1"][0]) == ids[0]
    assert str(ranked["t-3"][0]) == ids[2]


@pytest.mark.asyncio
async def test_todays_default_gate_returns_string_ids(tmp_path):
    """Pins today's observable fact (hybrid_search_enabled defaults True,
    so ProcessingPipeline.semantic_search's hybrid path is what a bench run
    exercises unless a future GateConfig learns to flip it): ids come back
    as str, not UUID. The scorer must handle both regardless; this test
    only documents which one the real path emits by default today."""
    llm, ids = await _ingest_three(tmp_path)
    gold_pairs = [
        {"id": "t-1", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
    ]

    ranked = await retrieval_runner.run_retrieval(
        llm, bench_db.session_factory, gold_pairs, limit=1,
    )

    assert isinstance(ranked["t-1"][0], str)
