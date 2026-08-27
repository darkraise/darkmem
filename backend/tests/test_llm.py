import json

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services import llm as llm_module
from app.services.llm import LLMOrchestrator, LLMTruncationError


def _make_orchestrator(handler):
    """Create orchestrator with a mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed", dimensions=3),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test-extract", params={"temperature": 0.2}),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test-reason"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test-sum"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=transport)
    return llm


async def test_embed():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "test-embed"
        assert body["input"] == "hello world"
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    llm = _make_orchestrator(handler)
    vector, fingerprint = await llm.embed("hello world")
    assert vector == [0.1, 0.2, 0.3]
    assert fingerprint == "test-embed|3"
    await llm.close()


async def test_chat_completion():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "test-extract"
        assert body["temperature"] == 0.2
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"entities": [], "relationships": []}'}}]
        })

    llm = _make_orchestrator(handler)
    result = await llm.chat_completion(
        "extraction",
        messages=[{"role": "user", "content": "test"}],
    )
    assert "entities" in result
    await llm.close()


async def test_chat_completion_raises_on_truncation_when_opted_in():
    def handler(request: httpx.Request):
        # finish_reason "length" with a half-written JSON body — the exact
        # shape that the extraction parser would otherwise mislabel as
        # "Invalid JSON".
        return httpx.Response(200, json={
            "choices": [
                {"message": {"content": '{"entities": [{"name": "a",'},
                 "finish_reason": "length"}
            ]
        })

    llm = _make_orchestrator(handler)
    with pytest.raises(LLMTruncationError) as ei:
        await llm.chat_completion(
            "extraction",
            messages=[{"role": "user", "content": "test"}],
            raise_on_truncation=True,
        )
    assert "truncated" in str(ei.value).lower()
    await llm.close()


async def test_chat_completion_ignores_truncation_by_default():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]
        })

    llm = _make_orchestrator(handler)
    # Without opting in, a length finish is returned verbatim — classification,
    # summarization, and reranker tolerate a clipped tail.
    result = await llm.chat_completion(
        "summarization", messages=[{"role": "user", "content": "x"}],
    )
    assert result == "partial"
    await llm.close()


async def test_chat_completion_ollama_raises_on_truncation():
    def handler(request: httpx.Request):
        # Ollama signals truncation via ``done_reason`` rather than the
        # OpenAI ``finish_reason``.
        return httpx.Response(200, json={
            "message": {"content": "partial"},
            "done_reason": "length",
            "eval_count": 10,
        })

    config = {
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="qwen2.5:3b",
            api_kind="ollama", params={"num_predict": 256},
        ),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(LLMTruncationError) as ei:
        await llm.chat_completion(
            "extraction",
            messages=[{"role": "user", "content": "x"}],
            raise_on_truncation=True,
        )
    assert "256" in str(ei.value)
    await llm.close()


async def test_chat_completion_with_extra_body():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body.get("thinking") is False
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "result"}}]
        })

    config = {
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="test",
            params={"temperature": 0.2, "extra_body": {"thinking": False}},
        ),
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    transport = httpx.MockTransport(handler)
    llm._client = httpx.AsyncClient(transport=transport)
    result = await llm.chat_completion("extraction", messages=[{"role": "user", "content": "test"}])
    assert result == "result"
    await llm.close()


async def test_chat_completion_forwards_seed():
    captured: dict = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    llm = _make_orchestrator(handler)
    await llm.chat_completion(
        "extraction",
        messages=[{"role": "user", "content": "test"}],
        seed=12345,
    )
    assert captured["body"]["seed"] == 12345
    await llm.close()


async def test_chat_completion_omits_seed_for_anthropic():
    captured: dict = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    config = {
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="claude", api_kind="anthropic",
        ),
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await llm.chat_completion(
        "extraction",
        messages=[{"role": "user", "content": "test"}],
        seed=12345,
    )
    assert "seed" not in captured["body"]
    await llm.close()


async def test_embed_with_api_key():
    def handler(request: httpx.Request):
        assert request.headers["Authorization"] == "Bearer sk-test123"
        return httpx.Response(200, json={"data": [{"embedding": [1.0, 2.0]}]})

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test", api_key="sk-test123", dimensions=2),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    vector, fingerprint = await llm.embed("test")
    assert vector == [1.0, 2.0]
    assert fingerprint == "test|2"
    await llm.close()


# --- prompt-cache telemetry --------------------------------------------------


def test_log_usage_handles_openai_cached_tokens(caplog):
    """OpenAI returns cached_tokens nested under prompt_tokens_details."""
    import logging
    caplog.set_level(logging.INFO, logger="app.services.llm")
    LLMOrchestrator._log_usage("extraction", "gpt-5-mini", {
        "prompt_tokens": 3623,
        "completion_tokens": 700,
        "prompt_tokens_details": {"cached_tokens": 3409},
    })
    assert any("cached=3409" in r.message and "94%" in r.message for r in caplog.records)


def test_log_usage_handles_deepseek_cache_hit_tokens(caplog):
    """DeepSeek surfaces the hit count at prompt_cache_hit_tokens."""
    import logging
    caplog.set_level(logging.INFO, logger="app.services.llm")
    LLMOrchestrator._log_usage("extraction", "deepseek-chat", {
        "prompt_tokens": 3623,
        "completion_tokens": 700,
        "prompt_cache_hit_tokens": 3409,
    })
    assert any("cached=3409" in r.message for r in caplog.records)


def test_log_usage_no_cache_field_logs_raw_counts(caplog):
    """Local Ollama / z.ai have no cache field — log token counts only."""
    import logging
    caplog.set_level(logging.INFO, logger="app.services.llm")
    LLMOrchestrator._log_usage("extraction", "qwen3.5:4b", {
        "prompt_tokens": 3623,
        "completion_tokens": 700,
    })
    rec = next((r for r in caplog.records if "qwen3.5:4b" in r.message), None)
    assert rec is not None
    assert "cached" not in rec.message


# --- z.ai thinking + timeout handling ---------------------------------------


async def test_zai_disables_thinking_for_non_reasoning_purposes():
    """GLM-4.5 / GLM-5 default to thinking mode which streams a long
    internal reasoning trace and reliably exceeds the httpx timeout on
    extraction prompts. Non-reasoning purposes must explicitly disable
    thinking; reasoning purposes must explicitly enable it."""
    captured: dict = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}],
        })

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="x"),
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="glm-4.5-flash",
            api_kind="zai", reasoning=False,
        ),
        "reasoning": LLMPurposeConfig(
            base_url="http://mock", model="glm-5-turbo",
            api_kind="zai", reasoning=True,
        ),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="x"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await llm.chat_completion("extraction", messages=[{"role": "user", "content": "hi"}])
    assert captured["body"].get("thinking") == {"type": "disabled"}

    await llm.chat_completion("reasoning", messages=[{"role": "user", "content": "hi"}])
    assert captured["body"].get("thinking") == {"type": "enabled"}

    await llm.close()


async def test_zai_timeout_surfaces_actionable_error():
    """A ReadTimeout on a z.ai call should report model + api_kind + a
    pointer to the thinking flag so operators can self-diagnose."""
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("timed out", request=request)

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="x"),
        "extraction": LLMPurposeConfig(
            base_url="https://api.z.ai/api/paas/v4",
            model="glm-4.5-flash", api_kind="zai", reasoning=False,
        ),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="x"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="x"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match=r"timed out against .*z\.ai.*glm-4\.5-flash.*zai"):
        await llm.chat_completion("extraction", messages=[{"role": "user", "content": "hi"}])

    await llm.close()


# ── retry on retriable vendor failures ────────────────────────────────────
# Three attempts per request. The transport-level `retries=` setting handles
# connection flakiness only, so these cover what it cannot see: response
# status, and the exceptions httpx raises after a connection is established.


@pytest.fixture
def no_sleep(monkeypatch):
    """Record backoff delays instead of serving them."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("app.services.llm._sleep", fake_sleep)
    return slept


async def test_chat_completion_retries_then_succeeds(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"entities": []}'}}]
        })

    llm = _make_orchestrator(handler)
    result = await llm.chat_completion(
        "extraction", messages=[{"role": "user", "content": "test"}],
    )
    assert "entities" in result
    assert len(calls) == 3
    assert len(no_sleep) == 2
    await llm.close()


async def test_chat_completion_gives_up_after_three_attempts(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(503, text="upstream unavailable")

    llm = _make_orchestrator(handler)
    with pytest.raises(RuntimeError, match="503"):
        await llm.chat_completion(
            "extraction", messages=[{"role": "user", "content": "test"}],
        )
    assert len(calls) == 3
    await llm.close()


async def test_chat_completion_does_not_retry_client_error(no_sleep):
    """A 400 is the same on every attempt; retrying only triples the latency."""
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(400, text="bad request")

    llm = _make_orchestrator(handler)
    with pytest.raises(RuntimeError, match="400"):
        await llm.chat_completion(
            "extraction", messages=[{"role": "user", "content": "test"}],
        )
    assert len(calls) == 1
    assert no_sleep == []
    await llm.close()


async def test_chat_completion_retries_transient_transport_error(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("connection reset", request=request)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}]
        })

    llm = _make_orchestrator(handler)
    assert await llm.chat_completion(
        "extraction", messages=[{"role": "user", "content": "test"}],
    ) == "ok"
    assert len(calls) == 2
    await llm.close()


async def test_read_timeout_is_not_retried(no_sleep):
    """The read budget is 300s and the flush ceiling is 300s: three attempts
    would outlive the run that owns the row. Kept single-shot deliberately."""
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    llm = _make_orchestrator(handler)
    with pytest.raises(RuntimeError, match="timed out against"):
        await llm.chat_completion(
            "extraction", messages=[{"role": "user", "content": "test"}],
        )
    assert len(calls) == 1
    assert no_sleep == []
    await llm.close()


async def test_retry_after_header_is_honoured(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"}, text="slow down")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}]
        })

    llm = _make_orchestrator(handler)
    await llm.chat_completion("extraction", messages=[{"role": "user", "content": "t"}])
    assert no_sleep == [7.0]
    await llm.close()


async def test_retry_after_is_capped(no_sleep):
    """A vendor must not be able to park a flush worker indefinitely."""
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "9000"}, text="slow down")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    llm = _make_orchestrator(handler)
    await llm.chat_completion("extraction", messages=[{"role": "user", "content": "t"}])
    assert no_sleep == [llm_module._RETRY_MAX_DELAY_SECONDS]
    await llm.close()


async def test_embed_retries_on_retriable_status(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    llm = _make_orchestrator(handler)
    vector, _ = await llm.embed("hello world")
    assert vector == [0.1, 0.2, 0.3]
    assert len(calls) == 2
    await llm.close()


async def test_embed_batch_retries_on_retriable_status(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"data": [
            {"embedding": [0.1, 0.2, 0.3], "index": 0},
        ]})

    llm = _make_orchestrator(handler)
    vectors, _ = await llm.embed_batch(["hello"])
    assert vectors == [[0.1, 0.2, 0.3]]
    assert len(calls) == 2
    await llm.close()


async def test_ollama_native_chat_retries(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, text="model loading")
        return httpx.Response(200, json={"message": {"content": "ok"}})

    config = {
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="test-extract", api_kind="ollama",
        ),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert await llm.chat_completion(
        "extraction", messages=[{"role": "user", "content": "t"}],
    ) == "ok"
    assert len(calls) == 2
    await llm.close()


async def test_backoff_grows_and_stays_within_bounds(no_sleep):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(503, text="down")

    llm = _make_orchestrator(handler)
    with pytest.raises(RuntimeError):
        await llm.chat_completion("extraction", messages=[{"role": "user", "content": "t"}])
    assert len(no_sleep) == 2
    base = llm_module._RETRY_BASE_DELAY_SECONDS
    # Equal jitter: attempt N waits between half and all of base * 2**(N-1).
    assert base / 2 <= no_sleep[0] <= base
    assert base <= no_sleep[1] <= base * 2
    assert no_sleep[1] > no_sleep[0]
