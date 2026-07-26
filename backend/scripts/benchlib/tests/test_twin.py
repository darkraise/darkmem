"""Tests for the latency and token-cost twin (T0.08).

Percentile math and token bookkeeping are pure and DB-free.
``instrument_retrieval`` is proven against the real, DB-backed retriever
the same way test_retrieval_runner.py proves ``run_retrieval`` reaches
``ProcessingPipeline.semantic_search`` -- a behavioural guard, not a
source-text one, so a forked reimplementation that merely kept the real
classes named somewhere would not pass it.
"""
import json

import pytest

from benchlib import bench_db, ingest, ledger, retrieval_runner, twin
from benchlib.caching_llm import CachingLLMOrchestrator
from benchlib.retrieval_scorer import PairScore, ScoreReport, SliceScore
from app.services.hybrid_search import HybridSearchService
from app.services.pipeline import ProcessingPipeline
from app.services.reranker import RerankerService

pytestmark = pytest.mark.usefixtures("_bench_db")


# ── percentiles ──────────────────────────────────────────────────────────


def test_nearest_rank_percentile_matches_hand_worked_example():
    samples = [float(i) for i in range(1, 21)]  # 1..20
    stats = twin._percentile_stats(samples, min_samples=20)
    assert stats.n == 20
    assert stats.powered is True
    # nearest-rank, p50: ceil(0.5*20)=10th smallest => 10.0
    assert stats.p50 == 10.0
    # p95: ceil(0.95*20)=19th smallest => 19.0
    assert stats.p95 == 19.0


def test_percentile_stats_below_min_samples_reports_no_number():
    stats = twin._percentile_stats([1.0, 2.0, 3.0], min_samples=20)
    assert stats.n == 3
    assert stats.powered is False
    assert stats.p50 is None
    assert stats.p95 is None


def test_latency_recorder_rejects_unknown_served_by():
    recorder = twin.LatencyRecorder()
    with pytest.raises(ValueError, match="served_by"):
        recorder.record("embed_query", 0.01, "warm")


def test_latency_recorder_separates_live_and_cache_populations():
    recorder = twin.LatencyRecorder()
    recorder.record("embed_query", 0.5, "live")
    recorder.record("embed_query", 0.001, "cache")
    stats = recorder.stats(min_samples=1)
    assert stats["embed_query"].live.n == 1
    assert stats["embed_query"].cache.n == 1
    assert stats["embed_query"].live.p50 == 0.5
    assert stats["embed_query"].cache.p50 == 0.001


def test_latency_recorder_reports_every_declared_channel_even_at_zero():
    recorder = twin.LatencyRecorder()
    stats = recorder.stats()
    assert set(twin.CHANNELS) <= set(stats)
    for channel in twin.CHANNELS:
        assert stats[channel].live.n == 0
        assert stats[channel].live.powered is False


def test_a_second_arm_declares_its_own_channels_instead_of_retrievals():
    """A non-retrieval arm (the full-context baseline) reuses this recorder
    but has no semantic_search to report; padding its twin with retrieval's
    five channels would describe channels the arm cannot have."""
    recorder = twin.LatencyRecorder()
    recorder.record("full_context_call", 1.2, "live")
    stats = recorder.stats(
        min_samples=1, declared_channels=("full_context_call", "end_to_end"),
    )

    assert set(stats) == {"full_context_call", "end_to_end"}
    assert stats["full_context_call"].live.n == 1
    assert stats["end_to_end"].live.n == 0

    captured = twin.Twin.capture(
        recorder, twin.TokenLedger(), min_samples=1,
        declared_channels=("full_context_call", "end_to_end"),
    )
    assert set(captured.channels) == {"full_context_call", "end_to_end"}


# ── instrument_retrieval: real DB-backed composition proof ─────────────

_STUB_EXTRACTION = (
    '{"entities": [], "relationships": [], "memory_type": "fact", '
    '"importance": 0.5, "summary": "s", "emotions": [], "flags": []}'
)


def _vec(text: str) -> list[float]:
    lowered = text.lower()
    return [1.0 if "alpha" in lowered else 0.0, 1.0 if "beta" in lowered else 0.0]


class _StubLLM(CachingLLMOrchestrator):
    async def _live_embed(self, text):
        return _vec(text), "stub-embed|2"

    async def _live_embed_batch(self, texts):
        return [_vec(t) for t in texts], "stub-embed|2"

    async def _live_chat(self, purpose, messages, **kwargs):
        return _STUB_EXTRACTION


async def _ingest_two(tmp_path):
    await bench_db.reset_bench_db()
    llm = _StubLLM({}, cache_dir=str(tmp_path))
    entries = [
        {"content": "The alpha service handles billing.", "memory_type": "fact"},
        {"content": "The beta pipeline handles ingestion.", "memory_type": "fact"},
    ]
    result = await ingest.run_ingest(llm, entries, ingest.GateConfig())
    return llm, [o["memory_id"] for o in result.outcomes]


@pytest.mark.asyncio
async def test_instrument_retrieval_times_the_real_channels(tmp_path):
    llm, ids = await _ingest_two(tmp_path)
    gold_pairs = [
        {"id": "t-1", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
        {"id": "t-2", "query": "alpha", "relevant_memory_ids": [ids[0]], "slice_tags": ["exact"]},
    ]

    with twin.instrument_retrieval(llm) as recorder:
        ranked = await retrieval_runner.run_retrieval(
            llm, bench_db.session_factory, gold_pairs, limit=2,
        )

    assert ranked["t-1"]
    stats = recorder.stats(min_samples=1)
    # Two retrieval calls -> two real DB round trips per DB channel, and
    # DB channels never have a cache-served population (the split applies
    # only to the model-backed channels and the composite).
    assert stats["semantic_search"].live.n == 2
    assert stats["keyword_search"].live.n == 2
    assert stats["semantic_search"].cache.n == 0
    assert stats["keyword_search"].cache.n == 0
    # Same query text twice: first embed is a live miss, second is a
    # disk-served cache hit -- exactly the population split ruling 2
    # requires.
    assert stats["embed_query"].live.n == 1
    assert stats["embed_query"].cache.n == 1
    # The composite inherits that split rather than calling both "live":
    # query 1's window paid for a live embed, query 2's paid for nothing.
    assert stats["end_to_end"].live.n == 1
    assert stats["end_to_end"].cache.n == 1
    # reranker_enabled is off by default (FEATURE_FLAGS_DEFAULTS) -- zero
    # samples is the honest state, not a defect (ruling 6).
    assert stats["reranker"].live.n == 0
    assert stats["reranker"].cache.n == 0


@pytest.mark.asyncio
async def test_instrument_retrieval_restores_the_shipping_classes_on_exit(tmp_path):
    llm, ids = await _ingest_two(tmp_path)
    before_semantic = HybridSearchService._semantic_search
    before_keyword = HybridSearchService._keyword_search
    before_rerank = RerankerService.rerank
    before_pipeline = ProcessingPipeline.semantic_search
    assert "embed" not in vars(llm)  # not an instance attribute yet

    with twin.instrument_retrieval(llm):
        assert HybridSearchService._semantic_search is not before_semantic
        assert "embed" in vars(llm)  # patched onto the instance

    assert HybridSearchService._semantic_search is before_semantic
    assert HybridSearchService._keyword_search is before_keyword
    assert RerankerService.rerank is before_rerank
    assert ProcessingPipeline.semantic_search is before_pipeline
    assert "embed" not in vars(llm)  # restored to the class-level method


@pytest.mark.asyncio
async def test_instrument_retrieval_restores_on_exception(tmp_path):
    llm, _ = await _ingest_two(tmp_path)
    before_semantic = HybridSearchService._semantic_search

    with pytest.raises(RuntimeError):
        with twin.instrument_retrieval(llm):
            raise RuntimeError("boom")

    assert HybridSearchService._semantic_search is before_semantic


# ── reranker channel: cache/live split, no DB needed ────────────────────


class _FakeRerankLLM:
    """Stands in for a CachingLLMOrchestrator on the reranker path: it
    carries the ``live_calls`` counter the spy reads and an ``embed``
    attribute for instrument_retrieval to patch, and bills a live call
    only when told to."""

    def __init__(self, bill_live: bool = False):
        self.live_calls = 0
        self._bill_live = bill_live

    async def embed(self, text):
        return [0.0], "fake-fp"

    async def chat_completion(self, purpose, messages, **kwargs):
        if self._bill_live:
            self.live_calls += 1
        return '{"score": 7}'


@pytest.mark.asyncio
@pytest.mark.parametrize("bill_live,expected", [(False, "cache"), (True, "live")])
async def test_the_shipped_reranker_spy_labels_by_live_call_delta(bill_live, expected):
    """Exercises twin.py's OWN spy_rerank through instrument_retrieval --
    not a copy of it hand-rolled in the test body. The DB-backed
    retrieval test runs with reranker_enabled=False, so without this the
    shipped reranker spy would never execute until a future
    reranker-enabled gate-evidence run."""
    fake_llm = _FakeRerankLLM(bill_live=bill_live)

    with twin.instrument_retrieval(fake_llm) as recorder:
        service = RerankerService(fake_llm)
        result = await service.rerank("q", [{"content": "doc"}])

    # The spy delegated: the real rerank ran and scored the document.
    assert result[0]["rerank_score"] == pytest.approx(1.0)

    stats = recorder.stats(min_samples=1)
    assert stats["reranker"].live.n == (1 if expected == "live" else 0)
    assert stats["reranker"].cache.n == (1 if expected == "cache" else 0)
    other = stats["reranker"].cache if expected == "live" else stats["reranker"].live
    assert other.n == 0


# ── TwinningOrchestrator: token capture + cache persistence ─────────────


class _UsageStubLLM(twin.TwinningOrchestrator):
    """Mimics what the real live-network path does: call ``self._log_usage``
    before returning content (llm.py:301/379), which is the capture point
    this class overrides."""

    def __init__(self, *a, usage=None, content='{"ok": true}', **kw):
        super().__init__(*a, **kw)
        self._stub_usage = usage
        self._stub_content = content

    async def _live_chat(self, purpose, messages, **kwargs):
        if self._stub_usage is not None:
            self._log_usage(purpose, "stub-model", self._stub_usage)
        return self._stub_content


@pytest.mark.asyncio
async def test_live_chat_call_accumulates_tokens_by_purpose(tmp_path):
    llm = _UsageStubLLM(
        {}, cache_dir=str(tmp_path),
        usage={"prompt_tokens": 100, "completion_tokens": 20,
               "prompt_tokens_details": {"cached_tokens": 30}},
    )
    await llm.chat_completion("extraction", [{"role": "user", "content": "x"}])

    usage = llm.tokens.as_dict()["extraction"]
    assert usage["live_calls"] == 1
    assert usage["live_prompt_tokens"] == 100
    assert usage["live_completion_tokens"] == 20
    assert usage["live_cached_prompt_tokens"] == 30
    assert usage["cache_known_calls"] == 0
    assert usage["cache_unknown_calls"] == 0


@pytest.mark.asyncio
async def test_replayed_call_reports_the_usage_it_was_paid_under(tmp_path):
    messages = [{"role": "user", "content": "x"}]
    writer = _UsageStubLLM(
        {}, cache_dir=str(tmp_path),
        usage={"prompt_tokens": 50, "completion_tokens": 10},
    )
    await writer.chat_completion("extraction", messages)

    reader = _UsageStubLLM({}, cache_dir=str(tmp_path))  # no usage stubbed
    reader._stub_content = "must not be used"  # would only fire on a miss

    async def _must_not_call(*a, **kw):
        raise AssertionError("must not hit the model on a cache hit")

    reader._live_chat = _must_not_call
    content = await reader.chat_completion("extraction", messages)

    assert json.loads(content) == {"ok": True}
    usage = reader.tokens.as_dict()["extraction"]
    assert usage["cache_known_calls"] == 1
    assert usage["cache_known_prompt_tokens"] == 50
    assert usage["cache_known_completion_tokens"] == 10
    assert usage["cache_unknown_calls"] == 0
    assert reader.live_calls == 0


@pytest.mark.asyncio
async def test_a_pre_t0_08_bare_string_cache_entry_still_reads_and_reports_unknown(tmp_path):
    """caching_llm.py's original format is a bare JSON string (the content
    itself, no usage). This must keep working -- ruling 3 forbids the new
    class from erroring on, or silently zero-costing, old cache entries."""
    messages = [{"role": "user", "content": "legacy"}]
    llm = twin.TwinningOrchestrator({}, cache_dir=str(tmp_path))
    key = llm._chat_key("extraction", messages, {})
    (tmp_path / f"{key}.json").write_text(json.dumps("legacy cached answer"))

    async def _must_not_call(*a, **kw):
        raise AssertionError("must not hit the model on a legacy cache hit")

    llm._live_chat = _must_not_call
    content = await llm.chat_completion("extraction", messages)

    assert content == "legacy cached answer"
    usage = llm.tokens.as_dict()["extraction"]
    assert usage["cache_unknown_calls"] == 1
    assert usage["cache_known_calls"] == 0
    assert llm.live_calls == 0


@pytest.mark.asyncio
async def test_a_live_call_with_no_vendor_usage_is_counted_unknown_not_zero(tmp_path):
    """The Ollama chat path only calls _log_usage when the response
    carries prompt_eval_count/eval_count, so a purpose pointed at Ollama
    produces live calls with no usage envelope at all. Those must be
    distinguishable from calls that genuinely cost zero tokens."""
    llm = _UsageStubLLM({}, cache_dir=str(tmp_path), usage=None)
    await llm.chat_completion("reranker", [{"role": "user", "content": "x"}])

    usage = llm.tokens.as_dict()["reranker"]
    assert usage["live_calls"] == 1
    assert usage["live_unknown_calls"] == 1
    assert usage["live_prompt_tokens"] == 0
    assert usage["live_completion_tokens"] == 0


@pytest.mark.asyncio
async def test_a_measured_live_call_is_not_marked_unknown(tmp_path):
    """Falsifiability for the test above: live_unknown_calls must track
    absent usage specifically, not just count every live call."""
    llm = _UsageStubLLM(
        {}, cache_dir=str(tmp_path),
        usage={"prompt_tokens": 7, "completion_tokens": 3},
    )
    await llm.chat_completion("reranker", [{"role": "user", "content": "x"}])

    usage = llm.tokens.as_dict()["reranker"]
    assert usage["live_calls"] == 1
    assert usage["live_unknown_calls"] == 0
    assert usage["live_prompt_tokens"] == 7


@pytest.mark.asyncio
async def test_the_base_orchestrator_reads_an_entry_the_twin_wrote(tmp_path):
    """Both classes share one cache directory, and the protocol docs still
    instruct composing with CachingLLMOrchestrator. A twin-written entry
    read back through the base class must yield the content string every
    caller expects, not the raw storage dict."""
    messages = [{"role": "user", "content": "x"}]
    writer = _UsageStubLLM(
        {}, cache_dir=str(tmp_path),
        usage={"prompt_tokens": 5, "completion_tokens": 1},
        content='{"entities": []}',
    )
    await writer.chat_completion("extraction", messages)

    class _NoLiveCalls(CachingLLMOrchestrator):
        async def _live_chat(self, purpose, messages, **kwargs):
            raise AssertionError("must not hit the model on a cache hit")

    reader = _NoLiveCalls({}, cache_dir=str(tmp_path))
    content = await reader.chat_completion("extraction", messages)

    assert content == '{"entities": []}'
    assert isinstance(content, str)
    assert reader.live_calls == 0


@pytest.mark.asyncio
async def test_both_classes_agree_on_the_chat_cache_key(tmp_path):
    """The two chat_completion implementations must resolve the same key
    for the same call, or a twin run would silently re-pay every call the
    base class had already cached (and vice versa)."""
    messages = [{"role": "user", "content": "x"}]
    base = CachingLLMOrchestrator({}, cache_dir=str(tmp_path))
    twinning = twin.TwinningOrchestrator({}, cache_dir=str(tmp_path))

    assert base._chat_key("extraction", messages, {"seed": 7}) == (
        twinning._chat_key("extraction", messages, {"seed": 7})
    )


@pytest.mark.asyncio
async def test_embed_and_embed_batch_are_unaffected_by_the_chat_override(tmp_path):
    """TwinningOrchestrator only overrides chat_completion/_log_usage;
    embed/embed_batch keep CachingLLMOrchestrator's exact behaviour."""
    class _Embeddable(twin.TwinningOrchestrator):
        async def _live_embed_batch(self, texts):
            return [[0.1, 0.2] for _ in texts], "stub-fp"

    llm = _Embeddable({}, cache_dir=str(tmp_path))
    v1 = await llm.embed_batch(["hello"])
    v2 = await llm.embed_batch(["hello"])
    assert v1 == v2
    assert llm.live_calls == 1


# ── EvalRun: the structural no-twin-no-accuracy guard (ruling 5) ───────


def _fake_score() -> ScoreReport:
    return ScoreReport(
        k=10, retrieval_limit=94, min_pairs=10, n_pairs=1,
        slices={"exact": SliceScore(
            slice_tag="exact", n_pairs=1, powered=False, mrr=None, hit_at_k=None,
        )},
        aggregate_powered=False, aggregate_mrr=None, aggregate_hit_at_k=None,
        pair_scores={"t-1": PairScore(
            pair_id="t-1", slice_tag="exact", reciprocal_rank=1.0,
            hit=True, n_relevant=1, n_found=1,
        )},
    )


def _fake_twin() -> twin.Twin:
    recorder = twin.LatencyRecorder()
    recorder.record("embed_query", 0.01, "cache")
    return twin.Twin.capture(recorder, twin.TokenLedger())


def test_a_twin_carrying_no_channels_cannot_be_constructed():
    """Presence of type is not presence of measurement: a channel-less
    Twin would satisfy EvalRun's isinstance guard while carrying nothing
    measured, which is the twin-less emission ruling 5 forbids wearing
    the right class."""
    with pytest.raises(ValueError, match="no channels"):
        twin.Twin(channels={}, tokens_by_purpose={})


def test_a_twin_whose_channels_all_have_zero_samples_is_still_valid():
    """Falsifiability: the guard refuses a Twin with NO channels, not one
    whose channels are legitimately empty (a disabled reranker, a run
    that never queried)."""
    empty = twin.Twin.capture(twin.LatencyRecorder(), twin.TokenLedger())
    assert set(twin.CHANNELS) <= set(empty.channels)
    assert all(c.live.n == 0 for c in empty.channels.values())


def test_eval_run_refuses_to_exist_with_twin_none():
    with pytest.raises(TypeError, match="twin"):
        twin.EvalRun(score=_fake_score(), twin=None)


def test_eval_run_refuses_a_lookalike_that_is_not_a_real_twin():
    with pytest.raises(TypeError, match="twin"):
        twin.EvalRun(score=_fake_score(), twin={"channels": {}, "tokens_by_purpose": {}})


def test_eval_run_accepts_a_real_twin_and_round_trips_through_the_ledger(tmp_path):
    run = twin.EvalRun(score=_fake_score(), twin=_fake_twin())
    path = tmp_path / "runs.jsonl"

    twin.record_eval_run(run, path=path)

    [recorded] = ledger.read_runs(path)
    assert recorded["score"]["n_pairs"] == 1
    assert recorded["twin"]["percentile_method"] == "nearest-rank"
    assert recorded["twin"]["channels"]["embed_query"]["cache"]["n"] == 1
