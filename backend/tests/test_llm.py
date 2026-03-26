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
    result = await llm.embed("hello world")
    assert result == [0.1, 0.2, 0.3]
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
    result = await llm.embed("test")
    assert result == [1.0, 2.0]
    await llm.close()
