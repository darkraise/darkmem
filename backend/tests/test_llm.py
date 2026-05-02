import json

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator


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
