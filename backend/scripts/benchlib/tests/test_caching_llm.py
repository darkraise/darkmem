import pytest

from app.config import LLMPurposeConfig
from benchlib.caching_llm import CachingLLMOrchestrator

pytestmark = pytest.mark.usefixtures("_bench_db")


class _Recorder(CachingLLMOrchestrator):
    """Stub the parent LLM calls so the test needs no live model."""
    async def _live_embed(self, text):
        return ([0.1, 0.2, 0.3], "stub-fp")

    async def _live_embed_batch(self, texts):
        return ([[0.1, 0.2, 0.3] for _ in texts], "stub-fp")

    async def _live_chat(self, purpose, messages, **kwargs):
        return '{"ok": true}'


@pytest.mark.asyncio
async def test_embed_is_cached_after_first_call(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    v1 = await llm.embed("hello")
    v2 = await llm.embed("hello")
    assert v1 == v2 == ([0.1, 0.2, 0.3], "stub-fp")
    assert llm.live_calls == 1  # second call served from disk


@pytest.mark.asyncio
async def test_chat_completion_is_cached(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    m = [{"role": "user", "content": "hi"}]
    r1 = await llm.chat_completion("extraction", m, seed=7)
    r2 = await llm.chat_completion("extraction", m, seed=7)
    assert r1 == r2 == '{"ok": true}'
    assert llm.live_calls == 1


@pytest.mark.asyncio
async def test_embed_batch_is_cached_after_first_call(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    v1 = await llm.embed_batch(["a", "b"])
    v2 = await llm.embed_batch(["a", "b"])
    assert v1 == v2 == ([[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]], "stub-fp")
    assert llm.live_calls == 1  # second call fully served from disk


@pytest.mark.asyncio
async def test_embed_batch_only_refetches_misses(tmp_path):
    class _Tracking(_Recorder):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.batch_calls: list[list[str]] = []

        async def _live_embed_batch(self, texts):
            self.batch_calls.append(list(texts))
            return await super()._live_embed_batch(texts)

    llm = _Tracking({}, cache_dir=str(tmp_path))
    await llm.embed_batch(["a", "b"])
    vecs, fp = await llm.embed_batch(["a", "b", "c"])

    assert llm.live_calls == 2
    assert llm.batch_calls == [["a", "b"], ["c"]]
    assert vecs == [[0.1, 0.2, 0.3]] * 3
    assert fp == "stub-fp"


@pytest.mark.asyncio
async def test_embed_batch_fully_cached_run_makes_zero_live_calls(tmp_path):
    warm = _Recorder({}, cache_dir=str(tmp_path))
    await warm.embed_batch(["x", "y"])

    class _NoLiveCalls(CachingLLMOrchestrator):
        async def _live_embed_batch(self, texts):
            raise AssertionError("must not hit the model on a fully cached run")

        async def _live_chat(self, purpose, messages, **kwargs):
            raise AssertionError("must not hit the model on a fully cached run")

    cold = _NoLiveCalls({}, cache_dir=str(tmp_path))
    vecs, fp = await cold.embed_batch(["x", "y"])
    assert cold.live_calls == 0
    assert fp == "stub-fp"
    assert vecs == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


@pytest.mark.asyncio
async def test_embed_batch_empty_list_returns_empty_without_live_call(tmp_path):
    config = {"embedding": LLMPurposeConfig(model="stub-model", dimensions=3)}
    llm = _Recorder(config, cache_dir=str(tmp_path))
    vecs, fp = await llm.embed_batch([])
    assert vecs == []
    assert fp == "stub-model|3"
    assert llm.live_calls == 0


@pytest.mark.asyncio
async def test_embed_batch_shares_cache_with_embed(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    await llm.embed("shared")
    vecs, fp = await llm.embed_batch(["shared"])
    assert llm.live_calls == 1  # the embed_batch call was a full cache hit
    assert vecs == [[0.1, 0.2, 0.3]]


@pytest.mark.asyncio
async def test_embed_batch_raises_on_mixed_fingerprints(tmp_path):
    class _Rotating(CachingLLMOrchestrator):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._n = 0

        async def _live_embed_batch(self, texts):
            self._n += 1
            return ([[0.1, 0.2, 0.3] for _ in texts], f"stub-fp-{self._n}")

        async def _live_chat(self, purpose, messages, **kwargs):
            return '{"ok": true}'

    llm = _Rotating({}, cache_dir=str(tmp_path))
    await llm.embed_batch(["a"])  # caches "a" under stub-fp-1
    with pytest.raises(RuntimeError, match="mixed fingerprints"):
        await llm.embed_batch(["a", "b"])  # "a" hits fp-1, "b" misses to fp-2


@pytest.mark.asyncio
async def test_embed_batch_tracks_fingerprints_seen(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    assert llm.fingerprints_seen == set()
    await llm.embed_batch(["a"])
    assert llm.fingerprints_seen == {"stub-fp"}
