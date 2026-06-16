"""Tests for the UI-facing LLM-pipeline config: LLM purpose settings for
extraction/classification, feature-flag toggles, and the system prompt
override surface.
"""
from __future__ import annotations

import pytest

from app.services import prompt as prompt_mod


@pytest.fixture
async def seeded_llm(session):
    """Seed DEFAULT_PROVIDERS + DEFAULT_PROFILES into the test DB.

    Migration 0001 used to do this; that seed has moved into
    ``app.services.llm_seed`` and is now applied by the setup wizard's
    finalize handler. Tests that exercise the providers / profiles UI
    against an empty DB depend on this fixture to land an equivalent
    set of rows.
    """
    from app.services.llm_seed import DEFAULT_PROVIDERS, DEFAULT_PROFILES
    from app.models.llm_config import LLMProvider, LLMProfile

    name_to_id: dict[str, object] = {}
    for ps in DEFAULT_PROVIDERS:
        provider = LLMProvider(
            name=ps.name,
            provider=ps.provider,
            base_url=ps.base_url,
            api_kind=ps.api_kind,
            supports_embedding=ps.supports_embedding,
            api_key=None,
        )
        session.add(provider)
        await session.flush()
        name_to_id[ps.name] = provider.id

    for prof in DEFAULT_PROFILES:
        session.add(LLMProfile(
            name=prof.name,
            provider_id=name_to_id[prof.provider_name],
            model=prof.model,
            params=dict(prof.params),
            is_embedding=prof.is_embedding,
            reasoning=prof.reasoning,
        ))
    await session.flush()
    yield


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


# --- REST: feature_flags toggles -----------------------------------------

@pytest.mark.asyncio
async def test_feature_flags_expose_toggles(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "llm_enrichment_enabled",
        "hybrid_search_enabled",
        "relation_rescue",
        "confidence_rank_gamma",
    ):
        assert key in body, f"feature_flags missing {key!r}: {body}"


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


# --- LLM provider profiles ----------------------------------------------


@pytest.mark.asyncio
async def test_llm_providers_seed_includes_known_vendors(client, auth_headers, seeded_llm):
    """The migration seeds one profile per supported vendor with a null
    api_key so the user can configure them through the UI. Each cloud
    profile's api_kind names its vendor so a future native adapter lights
    up automatically."""
    resp = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    assert resp.status_code == 200
    profiles = resp.json()["profiles"]
    expected = {"ollama", "openai", "anthropic", "google", "deepseek", "zai"}
    assert expected.issubset(profiles.keys()), (
        f"missing seeded providers: {expected - profiles.keys()}"
    )
    # Each profile's api_kind matches its vendor name (ollama uses native).
    for name in expected:
        assert profiles[name]["api_kind"] == name, (
            f"{name} profile should default to api_kind={name!r}, "
            f"got {profiles[name]['api_kind']!r}"
        )
    # No api_key seeded — the user fills it in from the UI.
    assert profiles["openai"]["api_key"] is None
    # Anthropic and DeepSeek don't expose an OpenAI-compat embeddings
    # endpoint, so the seed marks them supports_embedding=false.
    assert profiles["anthropic"]["supports_embedding"] is False
    assert profiles["deepseek"]["supports_embedding"] is False
    assert profiles["openai"]["supports_embedding"] is True
    assert profiles["ollama"]["supports_embedding"] is True
    assert profiles["google"]["supports_embedding"] is True
    assert profiles["zai"]["supports_embedding"] is True


@pytest.mark.asyncio
async def test_llm_providers_rejects_unknown_api_kind(client, auth_headers):
    """``api_kind`` is a closed enum. ``vertex`` isn't (yet) one of the
    accepted vendor kinds, so the write must fail Pydantic validation."""
    resp = await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={
            "profiles": {
                "bogus": {
                    "provider": "x",
                    "base_url": "http://localhost",
                    "api_key": "k",
                    "api_kind": "vertex",
                }
            }
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_llm_profiles_seed_covers_all_purposes(client, auth_headers, seeded_llm):
    """The migration seeds one Profile per (provider, purpose) for the
    two main providers (Ollama, OpenAI) so a fresh install has working
    defaults for every pipeline stage."""
    resp = await client.get("/api/v1/config/llm-profiles", headers=auth_headers)
    assert resp.status_code == 200
    profiles = resp.json()["profiles"]

    expected = {
        f"{provider}-{purpose}"
        for provider in ("ollama", "openai")
        for purpose in (
            "embedding", "extraction", "classification",
            "reasoning", "summarization", "reranker",
        )
    }
    assert expected.issubset(profiles.keys()), (
        f"missing seeded LLM profiles: {expected - profiles.keys()}"
    )

    # Embedding profiles must have is_embedding=true; reasoning profiles
    # carry reasoning=true. Other purposes should NOT enable reasoning.
    for prov in ("ollama", "openai"):
        assert profiles[f"{prov}-embedding"]["is_embedding"] is True
        assert profiles[f"{prov}-reasoning"]["reasoning"] is True
        for other in ("extraction", "classification", "summarization", "reranker"):
            p = profiles[f"{prov}-{other}"]
            assert p["is_embedding"] is False
            assert p["reasoning"] is False

    # OpenAI reasoning profile is the gpt-5.4 flagship-reasoning tier.
    # gpt-5 family requires temperature=1 and supports reasoning_effort /
    # verbosity / max_completion_tokens.
    openai_reasoning = profiles["openai-reasoning"]
    assert openai_reasoning["model"] == "gpt-5.4"
    assert openai_reasoning["params"].get("temperature") == 1
    assert openai_reasoning["params"].get("reasoning_effort") == "high"
    assert openai_reasoning["params"].get("verbosity") == "medium"

    # Ollama extraction is deterministic.
    assert profiles["ollama-extraction"]["params"].get("temperature") == 0

    # OpenAI extraction / summarization run on gpt-5.4-mini; classification
    # and reranker use gpt-5.4-nano to keep per-call cost minimal on
    # short-output purposes. All four use reasoning_effort=none because
    # they emit structured output that doesn't need chain-of-thought.
    # ("minimal" was the prior value but OpenAI removed it from the
    # accepted set; the current valid range is none|low|medium|high|xhigh.)
    for purpose, expected_model in (
        ("extraction", "gpt-5.4-mini"),
        ("classification", "gpt-5.4-nano"),
        ("summarization", "gpt-5.4-mini"),
        ("reranker", "gpt-5.4-nano"),
    ):
        key = f"openai-{purpose}"
        p = profiles[key]
        assert p["model"] == expected_model, (
            f"{key} should use {expected_model}, got {p['model']!r}"
        )
        assert p["params"].get("temperature") == 1
        assert p["params"].get("reasoning_effort") == "none"
        assert "max_completion_tokens" in p["params"]

    # Embedding-large variant lets users opt into 3072-dim recall when the
    # default text-embedding-3-small isn't strong enough.
    assert profiles["openai-embedding-large"]["model"] == "text-embedding-3-large"
    assert profiles["openai-embedding-large"]["is_embedding"] is True

    # z.ai profiles: free flash tier + glm-5-turbo for higher quality.
    # Each purpose carries a distinct ``max_tokens`` so the dropdown
    # matcher can tell them apart when the user has selected one. The
    # extraction variant pins to glm-4.7-flash (rank 8 in the
    # 2026-05-01 cross-model evaluation; glm-4.5-flash ranked last and
    # was retired from extraction). All other purposes still use
    # glm-4.5-flash since the eval only reranked extraction.
    expected_max_tokens = {
        # Extraction emits the largest JSON (full entity/relationship graph);
        # 4096 keeps entity-dense memories from truncating mid-object.
        "extraction": 4096,
        "classification": 64,
        "summarization": 512,
        "reranker": 32,
    }
    expected_zai_flash_model = {
        "extraction": "glm-4.7-flash",
        "classification": "glm-4.5-flash",
        "summarization": "glm-4.5-flash",
        "reranker": "glm-4.5-flash",
    }
    for purpose in ("extraction", "classification", "summarization", "reranker"):
        flash = profiles[f"zai-flash-{purpose}"]
        assert flash["model"] == expected_zai_flash_model[purpose]
        assert flash["provider_ref"] == "zai"
        assert flash["params"].get("max_tokens") == expected_max_tokens[purpose]
        turbo = profiles[f"zai-turbo-{purpose}"]
        assert turbo["model"] == "glm-5-turbo"
        assert turbo["params"].get("max_tokens") == expected_max_tokens[purpose]
    assert profiles["zai-turbo-reasoning"]["reasoning"] is True
    assert profiles["zai-turbo-reasoning"]["model"] == "glm-5-turbo"

    # DeepSeek profiles: v4-flash pinned to the canonical model name on
    # extraction (the deepseek-chat alias is non-authoritative; vendor
    # may swap its target at any time). Other purposes still use
    # deepseek-chat for now. v4-pro extraction is also seeded as a
    # top-tier option.
    expected_deepseek_flash_model = {
        "extraction": "deepseek-v4-flash",
        "classification": "deepseek-chat",
        "summarization": "deepseek-chat",
        "reranker": "deepseek-chat",
    }
    for purpose in ("extraction", "classification", "summarization", "reranker"):
        ds = profiles[f"deepseek-flash-{purpose}"]
        assert ds["model"] == expected_deepseek_flash_model[purpose]
        assert ds["provider_ref"] == "deepseek"
        assert ds["params"].get("max_tokens") == expected_max_tokens[purpose]
    assert profiles["deepseek-flash-reasoning"]["model"] == "deepseek-reasoner"
    assert profiles["deepseek-flash-reasoning"]["reasoning"] is True
    assert profiles["deepseek-pro-reasoning"]["model"] == "deepseek-v4-pro"
    assert profiles["deepseek-pro-reasoning"]["reasoning"] is True
    assert profiles["deepseek-pro-extraction"]["model"] == "deepseek-v4-pro"
    assert profiles["deepseek-pro-extraction"]["reasoning"] is False

    # Anthropic profiles: haiku for chat purposes, sonnet for reasoning
    # and as a top-tier extraction option.
    for purpose in ("extraction", "classification", "summarization", "reranker"):
        a = profiles[f"anthropic-haiku-{purpose}"]
        assert a["model"] == "claude-haiku-4-5"
        assert a["provider_ref"] == "anthropic"
    assert profiles["anthropic-sonnet-reasoning"]["model"] == "claude-sonnet-4-6"
    assert profiles["anthropic-sonnet-reasoning"]["reasoning"] is True
    assert profiles["anthropic-sonnet-extraction"]["model"] == "claude-sonnet-4-6"
    assert profiles["anthropic-sonnet-extraction"]["reasoning"] is False

    # OpenAI: nano-extraction is the cheap-tier extraction option
    # (rank 4 in the 2026-05-01 eval); openai-extraction stays on
    # gpt-5.4-mini (rank 2).
    assert profiles["openai-nano-extraction"]["model"] == "gpt-5.4-nano"
    assert profiles["openai-nano-extraction"]["reasoning"] is False
    assert profiles["openai-nano-extraction"]["params"].get("max_completion_tokens") == 4096

    # Google profiles seeded 2026-05-02. Three tiers: lite (gemini-2.5-flash-lite),
    # flash (gemini-2.5-flash), pro (gemini-2.5-pro). All non-reasoning purposes
    # carry reasoning_effort=none because Gemini 2.5 is reasoning-by-default and
    # silently consumes max_tokens on hidden CoT otherwise.
    assert profiles["google-embedding"]["model"] == "gemini-embedding-001"
    assert profiles["google-embedding"]["is_embedding"] is True
    for purpose in ("classification", "summarization", "reranker"):
        p = profiles[f"google-flash-{purpose}"]
        assert p["model"] == "gemini-2.5-flash"
        assert p["params"].get("max_tokens") == expected_max_tokens[purpose]
        assert p["params"].get("reasoning_effort") == "none"
    assert profiles["google-lite-extraction"]["model"] == "gemini-2.5-flash-lite"
    assert profiles["google-lite-extraction"]["params"].get("reasoning_effort") == "none"
    assert profiles["google-flash-extraction"]["model"] == "gemini-2.5-flash"
    assert profiles["google-flash-extraction"]["params"].get("reasoning_effort") == "none"
    assert profiles["google-pro-extraction"]["model"] == "gemini-2.5-pro"
    assert profiles["google-pro-extraction"]["params"].get("reasoning_effort") == "none"
    assert profiles["google-pro-reasoning"]["model"] == "gemini-2.5-pro"
    assert profiles["google-pro-reasoning"]["reasoning"] is True
    assert profiles["google-pro-reasoning"]["params"].get("reasoning_effort") == "high"


@pytest.mark.asyncio
async def test_test_provider_returns_404_for_unknown_profile(client, auth_headers):
    resp = await client.post(
        "/api/v1/config/llm-providers/does-not-exist/test",
        headers=auth_headers,
        json={"mode": "chat"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_test_provider_rejects_embedding_when_unsupported(client, auth_headers, seeded_llm):
    """Anthropic profile is seeded supports_embedding=false; the test
    route must short-circuit instead of probing a known-404 endpoint."""
    resp = await client.post(
        "/api/v1/config/llm-providers/anthropic/test",
        headers=auth_headers,
        json={"mode": "embedding"},
    )
    assert resp.status_code == 409
    assert "supports_embedding" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_test_provider_happy_path_uses_correct_url(client, auth_headers, monkeypatch):
    """Probe the route end-to-end. We monkeypatch httpx.AsyncClient.post
    so the test doesn't depend on the network; the assertion verifies the
    route built the OpenAI-compat /chat/completions URL from the profile's
    base_url."""
    import httpx

    # Seed an api_key on the openai provider so the new cloud-key
    # short-circuit lets the request through to the probe path.
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={
            "profiles": {
                "openai": {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "api_kind": "openai",
                    "supports_embedding": True,
                },
            }
        },
    )

    captured: dict = {}

    class _Resp:
        status_code = 200
        is_success = True
        text = "ok"

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    resp = await client.post(
        "/api/v1/config/llm-providers/openai/test",
        headers=auth_headers,
        json={"mode": "chat", "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["status_code"] == 200
    assert body["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["json"]["model"] == "gpt-4o-mini"
    assert captured["json"]["max_tokens"] == 4


@pytest.mark.asyncio
async def test_test_provider_ollama_strips_v1_for_native_path(client, auth_headers, monkeypatch, seeded_llm):
    """ollama profile is api_kind=ollama with base_url ending in /v1 — the
    probe should strip /v1 and hit /api/chat."""
    import httpx

    captured: dict = {}

    class _Resp:
        status_code = 200
        is_success = True
        text = "ok"

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    resp = await client.post(
        "/api/v1/config/llm-providers/ollama/test",
        headers=auth_headers,
        json={"mode": "chat"},
    )
    assert resp.status_code == 200
    assert captured["url"] == "http://localhost:11434/api/chat"


@pytest.mark.asyncio
async def test_provider_models_short_circuits_when_cloud_key_missing(client, auth_headers, seeded_llm):
    """Seeded cloud Providers ship with api_key=null. The models route
    should return a structured error pointing the operator at Settings
    instead of passing through the vendor's 'Missing bearer auth' 401."""
    resp = await client.get("/api/v1/config/llm-providers/openai/models", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == []
    assert body["error"] is not None
    assert "API key not set" in body["error"]
    assert "Settings" in body["error"]


@pytest.mark.asyncio
async def test_test_provider_short_circuits_when_cloud_key_missing(client, auth_headers, seeded_llm):
    """Same short-circuit on the chat probe route — refuses with 409 when
    a cloud Provider has no API key configured."""
    resp = await client.post(
        "/api/v1/config/llm-providers/openai/test",
        headers=auth_headers,
        json={"mode": "chat"},
    )
    assert resp.status_code == 409
    assert "API key not set" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_llm_providers_accepts_vendor_specific_kinds(client, auth_headers):
    """All six vendor kinds are valid api_kind values."""
    payload_profiles = {
        f"profile-{kind}": {
            "provider": kind,
            "base_url": "http://example",
            "api_key": "k",
            "api_kind": kind,
        }
        for kind in ("openai", "ollama", "anthropic", "google", "deepseek", "zai")
    }
    resp = await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": payload_profiles},
    )
    assert resp.status_code == 200
    body_profiles = resp.json()["profiles"]
    for kind in ("openai", "ollama", "anthropic", "google", "deepseek", "zai"):
        assert body_profiles[f"profile-{kind}"]["api_kind"] == kind


@pytest.mark.asyncio
async def test_llm_providers_put_masks_api_key(client, auth_headers):
    payload = {
        "profiles": {
            "openai-prod": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-secret",
                "api_kind": "openai",
            }
        }
    }
    resp = await client.put("/api/v1/config/llm-providers", headers=auth_headers, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profiles"]["openai-prod"]["api_key"] == "***"
    assert body["profiles"]["openai-prod"]["base_url"] == "https://api.openai.com/v1"

    resp = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    assert resp.json()["profiles"]["openai-prod"]["api_key"] == "***"


@pytest.mark.asyncio
async def test_llm_providers_put_keeps_secret_on_sentinel(client, auth_headers, session):
    # Seed a real key first.
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"p1": {"base_url": "http://x", "api_key": "rotate-me"}}},
    )
    # Re-PUT with the *** sentinel — must keep "rotate-me" stored.
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"p1": {"base_url": "http://x", "api_key": "***"}}},
    )
    from app.services.config import get_llm_providers
    profiles = await get_llm_providers(session)
    assert profiles["p1"].api_key == "rotate-me"


@pytest.mark.asyncio
async def test_purpose_provider_ref_overlays_connection_fields(
    client, auth_headers, session,
):
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={
            "profiles": {
                "anthropic": {
                    "provider": "anthropic",
                    "base_url": "https://api.anthropic.com/v1",
                    "api_key": "sk-ant-xyz",
                    "api_kind": "openai",
                }
            }
        },
    )
    resp = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={
            "reasoning": {
                "model": "claude-sonnet-4-6",
                "provider_ref": "anthropic",
                # Stale duplicates that should be overridden by the profile:
                "base_url": "http://leftover",
                "api_key": "leftover",
            }
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reasoning"]["base_url"] == "https://api.anthropic.com/v1"
    assert body["reasoning"]["provider"] == "anthropic"
    assert body["reasoning"]["api_key"] == "***"
    assert body["reasoning"]["provider_ref"] == "anthropic"

    from app.services.config import get_llm_config
    cfg = await get_llm_config(session)
    assert cfg["reasoning"].api_key == "sk-ant-xyz"
    assert cfg["reasoning"].base_url == "https://api.anthropic.com/v1"


@pytest.mark.asyncio
async def test_delete_llm_provider_blocked_if_referenced(client, auth_headers):
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"p1": {"base_url": "http://x", "api_key": "k"}}},
    )
    await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"reasoning": {"model": "m", "provider_ref": "p1"}},
    )
    resp = await client.delete("/api/v1/config/llm-providers/p1", headers=auth_headers)
    assert resp.status_code == 409
    assert "reasoning" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_llm_provider_succeeds_when_unused(client, auth_headers):
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"orphan": {"base_url": "http://x", "api_key": "k"}}},
    )
    resp = await client.delete("/api/v1/config/llm-providers/orphan", headers=auth_headers)
    assert resp.status_code == 200
    assert "orphan" not in resp.json()["profiles"]


@pytest.mark.asyncio
async def test_provider_save_closes_previous_orchestrator(client, auth_headers, monkeypatch):
    """Each Save replaces ``app.state.llm`` with a freshly built
    orchestrator. Without the close, the previous instance's
    ``httpx.AsyncClient`` leaks its keep-alive connections, which (in
    dev) sporadically surfaces as a Bad Gateway on the next request and
    (in prod) builds up file descriptors over the process lifetime.
    """
    import asyncio
    from app.main import app

    closed: list[str] = []

    # Stub out close on the live orchestrator so we can observe whether
    # the replacement scheduled a teardown.
    original_llm = getattr(app.state, "llm", None)
    if original_llm is not None:
        async def fake_close():
            closed.append("ok")
        monkeypatch.setattr(original_llm, "close", fake_close)

    resp = await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={
            "profiles": {
                "openai": {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-rotation-test",
                    "api_kind": "openai",
                    "supports_embedding": True,
                },
            }
        },
    )
    assert resp.status_code == 200, resp.text

    # The teardown is scheduled as a background task — let the loop run
    # so the close coroutine actually fires before we inspect.
    for _ in range(5):
        await asyncio.sleep(0)

    if original_llm is not None:
        assert closed == ["ok"], "previous orchestrator's close() was not awaited"


@pytest.mark.asyncio
async def test_purpose_save_does_not_freeze_profile_into_row(
    client, auth_headers, session,
):
    """Saving a purpose with provider_ref must not bake the profile's
    connection fields into the per-purpose row, otherwise rotating the
    key on the profile would silently leave the purpose stuck on the old
    one."""
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"p1": {"base_url": "http://first", "api_key": "first"}}},
    )
    await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"reasoning": {"model": "m", "provider_ref": "p1"}},
    )
    # Rotate the profile's connection details.
    await client.put(
        "/api/v1/config/llm-providers",
        headers=auth_headers,
        json={"profiles": {"p1": {"base_url": "http://second", "api_key": "second"}}},
    )

    from app.services.config import get_llm_config
    cfg = await get_llm_config(session)
    assert cfg["reasoning"].base_url == "http://second"
    assert cfg["reasoning"].api_key == "second"
