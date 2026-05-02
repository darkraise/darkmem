"""Tests for the /health endpoint.

The endpoint differentiates hard vs soft dependencies:
- pgvector is hard — its failure returns 503.
- The LLM probe is soft — its failure stays at 200 with status="degraded"
  so a flaky vendor cannot trip orchestrator health alarms.

Regression coverage for two bugs in the previous implementation:
1. ``base_url.rstrip("/v1")`` stripped the character set ``{/, v, 1}``,
   not the suffix — surprising on URLs like ``/api/v1``.
2. Hard-coded ``/api/tags`` worked only for Ollama; OpenAI / Anthropic /
   DeepSeek configurations made the probe permanently fail and the
   route returned 503 even when the LLM was perfectly reachable.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health_degraded_returns_200_when_llm_unreachable(client):
    """LLM down must NOT return 503 — orchestrators would page on it."""
    fake_cfg = SimpleNamespace(
        base_url="https://api.openai.com/v1",
        api_kind="openai",
        api_key="sk-test",
    )
    fake_llm = SimpleNamespace(config={"embedding": fake_cfg})
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = fake_llm
    try:
        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.get = AsyncMock(side_effect=Exception("connection refused"))
            response = await client.get("/health")
    finally:
        app.state.llm = original_llm

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["pgvector"] is True
    assert body["services"]["llm"] is False


@pytest.mark.asyncio
async def test_health_returns_200_when_llm_unconfigured(client):
    """A fresh install has no LLM orchestrator yet; health must still be 200."""
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = None
    try:
        response = await client.get("/health")
    finally:
        app.state.llm = original_llm

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["llm"] is False


@pytest.mark.asyncio
async def test_health_uses_models_endpoint_for_openai_compat(client):
    """Regression: probe must hit ``{base_url}/models`` for non-Ollama kinds."""
    fake_cfg = SimpleNamespace(
        base_url="https://api.openai.test/v1",
        api_kind="openai",
        api_key="sk-test",
    )
    fake_llm = SimpleNamespace(config={"embedding": fake_cfg})
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = fake_llm

    mock_response = AsyncMock()
    mock_response.is_success = True

    try:
        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_response)
            response = await client.get("/health")
    finally:
        app.state.llm = original_llm

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["llm"] is True
    call = instance.get.await_args
    assert call.args[0] == "https://api.openai.test/v1/models"
    assert call.kwargs["headers"]["Authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
async def test_health_uses_anthropic_headers(client):
    fake_cfg = SimpleNamespace(
        base_url="https://api.anthropic.test/v1",
        api_kind="anthropic",
        api_key="sk-ant",
    )
    fake_llm = SimpleNamespace(config={"embedding": fake_cfg})
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = fake_llm

    mock_response = AsyncMock()
    mock_response.is_success = True

    try:
        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_response)
            response = await client.get("/health")
    finally:
        app.state.llm = original_llm

    assert response.status_code == 200
    headers = instance.get.await_args.kwargs["headers"]
    assert headers["x-api-key"] == "sk-ant"
    assert headers["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_health_uses_native_tags_for_ollama_with_v1_suffix(client):
    """Regression for the rstrip('/v1') bug: must strip the suffix, not a char set."""
    fake_cfg = SimpleNamespace(
        base_url="http://ollama.test:11434/v1",
        api_kind="ollama",
        api_key=None,
    )
    fake_llm = SimpleNamespace(config={"embedding": fake_cfg})
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = fake_llm

    mock_response = AsyncMock()
    mock_response.is_success = True

    try:
        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_response)
            response = await client.get("/health")
    finally:
        app.state.llm = original_llm

    assert response.status_code == 200
    call = instance.get.await_args
    assert call.args[0] == "http://ollama.test:11434/api/tags"
