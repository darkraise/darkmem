import pytest

from benchlib.caching_llm import CachingLLMOrchestrator

pytestmark = pytest.mark.usefixtures("_bench_db")


class _Recorder(CachingLLMOrchestrator):
    """Stub the parent LLM calls so the test needs no live model."""
    async def _live_embed(self, text):
        return ([0.1, 0.2, 0.3], "stub-fp")

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
