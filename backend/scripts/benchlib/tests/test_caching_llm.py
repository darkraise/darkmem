import json

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


# ── the key must carry the resolved purpose config ────────────────────


class _Labelled(CachingLLMOrchestrator):
    """Answers with the model name it was configured with, so a replayed
    answer from another configuration is visible in the value itself."""
    async def _live_embed(self, text):
        return ([len(self.config["embedding"].model)], "stub-fp")

    async def _live_embed_batch(self, texts):
        return ([[len(self.config["embedding"].model)] for _ in texts], "stub-fp")

    async def _live_chat(self, purpose, messages, **kwargs):
        return json.dumps({"answered_by": self.config[purpose].model})


def _chat_config(model: str, **overrides):
    return {"extraction": LLMPurposeConfig(model=model, **overrides)}


@pytest.mark.asyncio
async def test_a_model_swap_misses_the_cache_instead_of_replaying(tmp_path):
    """The reviewed defect: warm the cache under one extraction model, swap
    the seeded model to evaluate a new extractor, and the rerun replayed the
    old model's outputs at live_calls == 0 -- a green, zero-cost run whose
    ledger record implies metrics for a model that never ran."""
    messages = [{"role": "user", "content": "extract this"}]

    old = _Labelled(_chat_config("deepseek-v4-flash"), cache_dir=str(tmp_path))
    assert json.loads(await old.chat_completion("extraction", messages))["answered_by"] == (
        "deepseek-v4-flash"
    )

    new = _Labelled(_chat_config("deepseek-v5-thinking"), cache_dir=str(tmp_path))
    answer = json.loads(await new.chat_completion("extraction", messages))

    assert answer["answered_by"] == "deepseek-v5-thinking"
    assert new.live_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("base_url", "https://api.example.com/v1"),
    ("api_kind", "ollama"),
    ("reasoning", True),
    ("params", {"temperature": 0.9}),
])
async def test_every_output_shaping_purpose_field_invalidates_the_chat_cache(
    tmp_path, field, value,
):
    messages = [{"role": "user", "content": "extract this"}]
    base = _chat_config("deepseek-v4-flash")

    first = _Labelled(base, cache_dir=str(tmp_path))
    await first.chat_completion("extraction", messages)

    second = _Labelled(
        _chat_config("deepseek-v4-flash", **{field: value}), cache_dir=str(tmp_path),
    )
    await second.chat_completion("extraction", messages)

    assert second.live_calls == 1


@pytest.mark.asyncio
async def test_rotating_the_api_key_alone_still_hits_the_cache(tmp_path):
    """A credential does not change an answer, so it must not invalidate --
    and it must never be part of what the key is derived from."""
    messages = [{"role": "user", "content": "extract this"}]

    first = _Labelled(_chat_config("deepseek-v4-flash", api_key="sk-old"), cache_dir=str(tmp_path))
    await first.chat_completion("extraction", messages)

    second = _Labelled(_chat_config("deepseek-v4-flash", api_key="sk-new"), cache_dir=str(tmp_path))
    await second.chat_completion("extraction", messages)

    assert second.live_calls == 0


@pytest.mark.asyncio
async def test_an_embedding_model_swap_misses_the_cache(tmp_path):
    old_config = {"embedding": LLMPurposeConfig(model="qwen3-embedding:0.6b", dimensions=1)}
    new_config = {"embedding": LLMPurposeConfig(model="nomic-embed-text", dimensions=1)}

    old = _Labelled(old_config, cache_dir=str(tmp_path))
    old_vecs, _ = await old.embed_batch(["some text"])

    new = _Labelled(new_config, cache_dir=str(tmp_path))
    new_vecs, _ = await new.embed_batch(["some text"])

    assert new.live_calls == 1
    assert new_vecs != old_vecs


@pytest.mark.asyncio
async def test_changing_the_embedding_dimensions_misses_the_cache(tmp_path):
    """dimensions names the partition a cached vector belongs to
    (llm_fingerprint() is model|dimensions), so a change must not replay
    vectors labelled for the old partition."""
    first = _Labelled(
        {"embedding": LLMPurposeConfig(model="qwen3-embedding:0.6b", dimensions=1024)},
        cache_dir=str(tmp_path),
    )
    await first.embed_batch(["some text"])

    second = _Labelled(
        {"embedding": LLMPurposeConfig(model="qwen3-embedding:0.6b", dimensions=768)},
        cache_dir=str(tmp_path),
    )
    await second.embed_batch(["some text"])

    assert second.live_calls == 1


@pytest.mark.asyncio
async def test_an_unchanged_config_still_replays_from_disk(tmp_path):
    """Falsifiability: the misses above must come from the config change,
    not from a key that never hits."""
    messages = [{"role": "user", "content": "extract this"}]
    config = {
        **_chat_config("deepseek-v4-flash"),
        "embedding": LLMPurposeConfig(model="qwen3-embedding:0.6b", dimensions=1),
    }

    warm = _Labelled(config, cache_dir=str(tmp_path))
    await warm.chat_completion("extraction", messages)
    await warm.embed_batch(["some text"])

    class _NoLiveCalls(_Labelled):
        async def _live_chat(self, purpose, messages, **kwargs):
            raise AssertionError("must not hit the model on an unchanged config")

        async def _live_embed_batch(self, texts):
            raise AssertionError("must not hit the model on an unchanged config")

    cold = _NoLiveCalls(config, cache_dir=str(tmp_path))
    await cold.chat_completion("extraction", messages)
    await cold.embed_batch(["some text"])
    assert cold.live_calls == 0
