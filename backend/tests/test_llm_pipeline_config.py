"""Tests for the UI-facing LLM-pipeline config: LLM purpose settings for
extraction/classification, ml_* feature-flag toggles, and the system prompt
override surface.
"""
from __future__ import annotations

import pytest

from app.services import prompt as prompt_mod


# --- Prompt module cache --------------------------------------------------

def test_prompt_module_default_fallback():
    prompt_mod.set_overrides({})
    # Default prompt for extraction is the in-code one.
    assert prompt_mod.get("extraction") == prompt_mod.PROMPTS["extraction"]
    assert prompt_mod.get("__unknown__") == ""


def test_prompt_module_override_wins():
    prompt_mod.set_overrides({"extraction": "custom extraction prompt"})
    try:
        assert prompt_mod.get("extraction") == "custom extraction prompt"
        # Non-overridden purposes still fall back to the default.
        assert prompt_mod.get("chat") == prompt_mod.PROMPTS["chat"]
    finally:
        prompt_mod.set_overrides({})


def test_prompt_module_empty_string_override_is_dropped():
    prompt_mod.set_overrides({"extraction": ""})
    # An empty override should not shadow the default.
    assert prompt_mod.get("extraction") == prompt_mod.PROMPTS["extraction"]


def test_prompt_module_rejects_non_string_values():
    prompt_mod.set_overrides({"extraction": 123, "chat": None})  # type: ignore[dict-item]
    assert prompt_mod.get("extraction") == prompt_mod.PROMPTS["extraction"]
    assert prompt_mod.get("chat") == prompt_mod.PROMPTS["chat"]


# --- REST: GET /api/v1/config/llm includes classification ----------------

@pytest.mark.asyncio
async def test_llm_config_exposes_classification_purpose(client, auth_headers):
    resp = await client.get("/api/v1/config/llm", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "classification" in body, f"classification purpose missing: {list(body.keys())}"
    # Default comes from Settings.llm_classification (ollama/qwen2.5:3b).
    assert body["classification"]["provider"] == "ollama"
    assert body["classification"]["model"] == "qwen2.5:3b"


@pytest.mark.asyncio
async def test_llm_config_update_roundtrips_classification(client, auth_headers):
    payload = {
        "classification": {
            "provider": "ollama",
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:1.5b",
            "params": {"temperature": 0.1},
        }
    }
    resp = await client.post("/api/v1/config/llm", headers=auth_headers, json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["classification"]["model"] == "qwen2.5:1.5b"
    # Other purposes are preserved.
    assert "extraction" in body and "reasoning" in body


# --- REST: feature_flags ml_* toggles ------------------------------------

@pytest.mark.asyncio
async def test_feature_flags_expose_ml_path_toggles(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "ml_extraction",
        "ml_classification",
        "ml_retrieval",
        "ml_shadow_mode",
        "confidence_rank_gamma",
    ):
        assert key in body, f"feature_flags missing {key!r}: {body}"


@pytest.mark.asyncio
async def test_feature_flags_can_toggle_ml_extraction(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_extraction": True, "ml_classification": True, "ml_retrieval": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ml_extraction"] is True
    assert body["ml_classification"] is True
    assert body["ml_retrieval"] is False


@pytest.mark.asyncio
async def test_feature_flags_validates_confidence_rank_gamma(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"confidence_rank_gamma": -0.1},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"confidence_rank_gamma": 10.0},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"confidence_rank_gamma": 0.5},
    )
    assert resp.status_code == 200
    assert resp.json()["confidence_rank_gamma"] == 0.5


# --- REST: system prompts CRUD -------------------------------------------

@pytest.mark.asyncio
async def test_get_system_prompts_returns_defaults_and_no_overrides(client, auth_headers):
    # Reset any module-level state set by earlier tests in this file.
    prompt_mod.set_overrides({})
    resp = await client.get("/api/v1/config/system-prompts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "defaults" in body and "overrides" in body and "effective" in body
    assert "extraction" in body["defaults"]
    assert body["overrides"] == {}
    # Effective = defaults when no overrides are set.
    assert body["effective"]["extraction"] == body["defaults"]["extraction"]


@pytest.mark.asyncio
async def test_put_system_prompts_stores_override_and_refreshes_cache(client, auth_headers):
    prompt_mod.set_overrides({})
    custom = "Return JSON with entities only. No relationships."
    resp = await client.put(
        "/api/v1/config/system-prompts",
        headers=auth_headers,
        json={"overrides": {"extraction": custom}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["overrides"]["extraction"] == custom
    assert body["effective"]["extraction"] == custom

    # The process-level cache is refreshed; prompt.get() returns the override.
    assert prompt_mod.get("extraction") == custom

    # Empty-string override clears it.
    resp = await client.put(
        "/api/v1/config/system-prompts",
        headers=auth_headers,
        json={"overrides": {"extraction": ""}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "extraction" not in body["overrides"]
    assert prompt_mod.get("extraction") == prompt_mod.PROMPTS["extraction"]


@pytest.mark.asyncio
async def test_put_system_prompts_rejects_unknown_purpose(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/system-prompts",
        headers=auth_headers,
        json={"overrides": {"nonexistent_purpose": "hi"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_system_prompts_rejects_oversized_prompt(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/system-prompts",
        headers=auth_headers,
        json={"overrides": {"extraction": "x" * 25_000}},
    )
    assert resp.status_code == 422
