"""The recorder is reached from every path that spends tokens.

Six paths bypass the old ``_log_usage`` line: embeddings never touched it,
both streams break before it, and every error path raises ahead of it. These
tests pin that each one now reports.
"""
import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator


class SpyRecorder:
    def __init__(self):
        self.calls = []

    async def record(self, **kw):
        self.calls.append(kw)


def _orch(body: dict, status: int = 200):
    """Mock transport, matching how tests/test_api_kind_dispatch.py stubs the
    wire. No pytest-httpx in this project."""
    cfg = LLMPurposeConfig(base_url="http://mock/v1", model="m", dimensions=3)
    spy = SpyRecorder()
    o = LLMOrchestrator({"extraction": cfg, "embedding": cfg}, recorder=spy)
    o._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json=body)
        )
    )
    return o, spy


@pytest.mark.asyncio
async def test_embed_reports():
    o, spy = _orch({"data": [{"embedding": [0.1, 0.2, 0.3]}],
                    "usage": {"prompt_tokens": 11}})
    await o.embed("hello")
    assert [c["purpose"] for c in spy.calls] == ["embedding"]
    assert spy.calls[0]["payload"]["usage"]["prompt_tokens"] == 11
    await o.close()


@pytest.mark.asyncio
async def test_embed_batch_reports_its_batch_size():
    """So the per-memory view can say 'batched' instead of dividing one cost
    N ways and presenting the arithmetic as an observation."""
    o, spy = _orch({
        "data": [{"embedding": [0.1, 0.2, 0.3], "index": 0},
                 {"embedding": [0.4, 0.5, 0.6], "index": 1}],
        "usage": {"prompt_tokens": 20}})
    await o.embed_batch(["a", "b"])
    assert spy.calls[0]["extra_raw"] == {"batch_size": 2}
    await o.close()


@pytest.mark.asyncio
async def test_a_failed_call_reports_before_it_raises():
    """The waste this feature exists to find. Every error path raises before
    the old logging line, so a recorder placed there saw only successes."""
    o, spy = _orch({"error": "boom"}, status=500)
    with pytest.raises(RuntimeError):
        await o.embed("hello")
    assert len(spy.calls) == 1
    assert spy.calls[0]["ok"] is False
    assert spy.calls[0]["payload"] is None
    await o.close()


@pytest.mark.asyncio
async def test_chat_reports_and_keeps_its_return_shape():
    o, spy = _orch({
        "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        "model": "m"})
    got = await o.chat_completion("extraction", [{"role": "user", "content": "q"}])
    assert got == "hi"                       # str callers are unaffected
    assert spy.calls[0]["purpose"] == "extraction"
    assert spy.calls[0]["payload"]["usage"]["completion_tokens"] == 2
    await o.close()


@pytest.mark.asyncio
async def test_an_explicit_subject_reaches_the_recorder():
    o, spy = _orch({
        "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    await o.chat_completion("extraction", [{"role": "user", "content": "q"}],
                            usage_subject=("memory", "m1", "default"))
    assert spy.calls[0]["subject"] == ("memory", "m1", "default")
    await o.close()
