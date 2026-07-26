import pytest

from benchlib import bench_db, ingest
from benchlib.caching_llm import CachingLLMOrchestrator

pytestmark = pytest.mark.usefixtures("_bench_db")

_STUB_EXTRACTION_NO_ENTITIES = (
    '{"entities": [], "relationships": [], "memory_type": "fact", '
    '"importance": 0.5, "summary": "stub summary", "emotions": [], "flags": []}'
)


class _StubLLM(CachingLLMOrchestrator):
    """Stub the parent LLM calls so the test needs no live model or network."""
    async def _live_embed_batch(self, texts):
        return ([[0.1, 0.2, 0.3] for _ in texts], "stub-embed|3")

    async def _live_chat(self, purpose, messages, **kwargs):
        return _STUB_EXTRACTION_NO_ENTITIES


def _corpus(n: int) -> list[dict]:
    # Deliberately free of any curated rescue-list token (extraction_clean's
    # _TYPE_OVERRIDES / _HARDWARE_TOKENS / _SHORT_TOOL_ALLOWLIST) so a stub
    # extraction of zero entities actually stays at zero entities -- the
    # rescue passes are real production code, not reimplemented here, and
    # would otherwise inject an entity these tests don't expect.
    return [{"content": f"The weather was mild on day {i} of the trip."} for i in range(n)]


@pytest.mark.asyncio
async def test_run_ingest_returns_per_memory_outcomes(tmp_path):
    llm = _StubLLM({}, cache_dir=str(tmp_path))
    entries = _corpus(3)
    gate = ingest.GateConfig(ml_profile_ref=None, classification_mode="simple", relation_rescue=True)

    result = await ingest.run_ingest(llm, entries, gate)

    assert len(result.outcomes) == 3
    for outcome in result.outcomes:
        assert outcome["embed"] == "ok"
        assert outcome["vector"] == "ok"
        assert outcome["extract"] in ("ok", "partial")
        assert outcome["memory_id"]

    assert result.fingerprint == "stub-embed|3"
    assert result.gate_config == {
        "ml_profile_ref": None,
        "classification_mode": "simple",
        "relation_rescue": True,
    }
    # 1 embed_batch call (3 contents fit in one default-sized chunk) + 3
    # per-entry extraction chat_completion calls (distinct content each).
    assert result.live_calls == 4


@pytest.mark.asyncio
async def test_run_ingest_uses_the_real_pipeline_class(tmp_path):
    """No forked phase logic: run_ingest must drive app.services.pipeline's
    real ProcessingPipeline, not a reimplementation of it."""
    import inspect

    assert inspect.iscoroutinefunction(ingest.run_ingest)
    source = inspect.getsource(ingest)
    from app.services.pipeline import ProcessingPipeline
    assert ProcessingPipeline.__name__ in source


@pytest.mark.asyncio
async def test_memory_id_is_assigned_when_entries_lack_one(tmp_path):
    llm = _StubLLM({}, cache_dir=str(tmp_path))
    entries = _corpus(2)
    assert "memory_id" not in entries[0]

    result = await ingest.run_ingest(llm, entries, ingest.GateConfig())

    ids = [o["memory_id"] for o in result.outcomes]
    assert len(set(ids)) == 2
    assert all(ids)


@pytest.mark.asyncio
async def test_second_run_with_a_fresh_cache_backed_orchestrator_makes_zero_live_calls(tmp_path):
    entries = _corpus(2)
    gate = ingest.GateConfig()

    warm = _StubLLM({}, cache_dir=str(tmp_path))
    first = await ingest.run_ingest(warm, entries, gate)
    assert first.live_calls > 0

    class _NoLiveCalls(CachingLLMOrchestrator):
        async def _live_embed_batch(self, texts):
            raise AssertionError("must not hit the model on a fully cached run")

        async def _live_chat(self, purpose, messages, **kwargs):
            raise AssertionError("must not hit the model on a fully cached run")

    cold = _NoLiveCalls({}, cache_dir=str(tmp_path))
    second = await ingest.run_ingest(cold, entries, gate)

    assert second.live_calls == 0
    assert len(second.outcomes) == 2
    assert second.fingerprint == first.fingerprint


@pytest.mark.asyncio
async def test_pin_gate_config_sets_explicit_values_not_ambient(tmp_path):
    from app.services.config import get_llm_config
    from app.services.feature_flags import get_feature_flags_dict

    gate = ingest.GateConfig(ml_profile_ref=None, classification_mode="expanded", relation_rescue=False)
    pinned = await ingest.pin_gate_config(bench_db.session_factory, gate)

    assert pinned == {
        "ml_profile_ref": None,
        "classification_mode": "expanded",
        "relation_rescue": False,
    }

    async with bench_db.session_factory() as session:
        flags = await get_feature_flags_dict(session)
        assert flags["classification_mode"] == "expanded"
        assert flags["relation_rescue"] is False

        cfg = await get_llm_config(session)
        assert cfg["classification"].ml_profile_ref is None

    # Re-pin back to the simple/rescue-on defaults so later tests in this
    # module (which share one session-scoped bench DB) see a known state.
    await ingest.pin_gate_config(
        bench_db.session_factory,
        ingest.GateConfig(ml_profile_ref=None, classification_mode="simple", relation_rescue=True),
    )


@pytest.mark.asyncio
async def test_pin_gate_config_rejects_unknown_ml_profile_ref(tmp_path):
    gate = ingest.GateConfig(ml_profile_ref="does-not-exist")
    with pytest.raises(ValueError, match="does-not-exist"):
        await ingest.pin_gate_config(bench_db.session_factory, gate)


@pytest.mark.asyncio
async def test_run_ingest_pins_gate_config_even_when_process_left_it_dirty(tmp_path):
    """A run must SET its gate values explicitly, not just read whatever an
    earlier run (or process) left in the DB."""
    await ingest.pin_gate_config(
        bench_db.session_factory,
        ingest.GateConfig(ml_profile_ref=None, classification_mode="expanded", relation_rescue=False),
    )

    llm = _StubLLM({}, cache_dir=str(tmp_path))
    result = await ingest.run_ingest(llm, _corpus(1), ingest.GateConfig(
        ml_profile_ref=None, classification_mode="simple", relation_rescue=True,
    ))

    assert result.gate_config == {
        "ml_profile_ref": None,
        "classification_mode": "simple",
        "relation_rescue": True,
    }


@pytest.mark.asyncio
async def test_run_never_mixes_fingerprints(tmp_path):
    """Phase 1 (content) and Phase 3 (entity) embeddings can legitimately
    land on different fingerprints if the embedder rotates mid-batch
    (CLAUDE.md's Pipeline-phases section) -- the production pipeline
    tolerates this, but a bench run must not: invariant 2 forbids a single
    run from mixing fingerprints, so run_ingest must hard-fail instead of
    silently recording whichever fingerprint it saw first."""
    class _RotatingLLM(CachingLLMOrchestrator):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._n = 0

        async def _live_embed_batch(self, texts):
            self._n += 1
            return ([[0.1, 0.2, 0.3] for _ in texts], f"stub-embed-{self._n}|3")

        async def _live_chat(self, purpose, messages, **kwargs):
            return (
                '{"entities": [{"name": "postgres", "type": "tool", "properties": {}}], '
                '"relationships": [], "memory_type": "fact", "importance": 0.5, '
                '"summary": "s", "emotions": [], "flags": []}'
            )

    llm = _RotatingLLM({}, cache_dir=str(tmp_path))
    entries = [{"content": "We use postgres for storage."}]

    with pytest.raises(RuntimeError, match="mixed"):
        await ingest.run_ingest(llm, entries, ingest.GateConfig())
