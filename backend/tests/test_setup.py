"""T1.56 — setup wizard finalize against the flattened config.

Focused on the property `test_setup_route.py` does not cover: T1.01 made
re-running the wizard the supported upgrade path for an existing install
(doc 20 §10 — no one-time config-transform migration was committed to), so
finalize must be safe to run more than once against surviving
`llm_purpose_configs` rows. Trust-on-first-use gating (doc 18) is otherwise
unchanged — the tests below re-open setup the only sanctioned way, by
clearing `admin_password_hash`, never via a reintroduced pre-setup secret.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.config import Config
from app.models.llm_config import LLMPurposeConfigRow
from app.services.llm_seed import DEFAULT_PURPOSE_CONFIGS

ADMIN_PASSWORD_KEY = "admin_password_hash"


async def _reopen_setup(session) -> None:
    """The only supported way to let `require_uninitialized` pass again:
    clear the admin password config row. Never a `SETUP_SECRET` (doc 18)."""
    row = (
        await session.execute(
            select(Config).where(Config.key == ADMIN_PASSWORD_KEY)
        )
    ).scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()


@pytest.mark.asyncio
async def test_setup_finalize_llm_reopen_is_idempotent(client, session):
    """finalize twice must overlay cleanly, never duplicate-key or partial."""
    first_payload = {
        "password": "test-pw-12345",
        "llm": {
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-first",
            "supports_embedding": True,
            "purposes": {
                "embedding": {"model": "text-embedding-3-small"},
                "extraction": {"model": "gpt-4o-mini"},
                "classification": {"model": "gpt-4o-mini"},
                "reasoning": {"model": "gpt-4o", "reasoning": True},
            },
        },
    }
    response = await client.post("/api/v1/setup", json=first_payload)
    assert response.status_code == 200, response.text
    assert response.json()["llm"]["ok"] is True

    rows_after_first = (
        await session.execute(select(LLMPurposeConfigRow))
    ).scalars().all()
    # Every DEFAULT_PURPOSE_CONFIGS purpose lands a row, including the two
    # Tier-C purposes seeded inert (T1.05) — one row each, never duplicated.
    assert len(rows_after_first) == len(DEFAULT_PURPOSE_CONFIGS)
    assert {r.purpose for r in rows_after_first} == {
        pc.purpose for pc in DEFAULT_PURPOSE_CONFIGS
    }

    await _reopen_setup(session)
    status = await client.get("/api/v1/setup/status")
    assert status.json() == {"initialized": False}

    second_payload = {
        "password": "test-pw-67890",
        "llm": {
            "api_kind": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk-second",
            "supports_embedding": False,
            "purposes": {
                "extraction": {"model": "deepseek-v4-flash"},
                "classification": {"model": "deepseek-chat"},
                "reasoning": {"model": "deepseek-reasoner", "reasoning": True},
            },
        },
    }
    response = await client.post("/api/v1/setup", json=second_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["llm"]["ok"] is True, body["llm"]

    rows_after_second = (
        await session.execute(select(LLMPurposeConfigRow))
    ).scalars().all()
    # Still exactly one row per purpose — an upsert, never a second insert.
    assert len(rows_after_second) == len(DEFAULT_PURPOSE_CONFIGS)
    by_purpose = {r.purpose: r for r in rows_after_second}

    # The second run's overlay landed cleanly, not merged with the first's.
    assert by_purpose["extraction"].model == "deepseek-v4-flash"
    assert by_purpose["extraction"].api_kind == "deepseek"
    assert by_purpose["extraction"].api_key == "sk-second"
    assert by_purpose["classification"].model == "deepseek-chat"
    assert by_purpose["reasoning"].model == "deepseek-reasoner"

    # embedding was not resupplied on the second run (deepseek has no
    # embeddings endpoint) — its row is reset to the DEFAULT_PURPOSE_CONFIGS
    # seed rather than left stale from the first run or duplicated.
    embedding_default = next(
        pc for pc in DEFAULT_PURPOSE_CONFIGS if pc.purpose == "embedding"
    )
    assert by_purpose["embedding"].model == embedding_default.model
    assert by_purpose["embedding"].api_kind == embedding_default.api_kind

    # The two Tier-C purposes stay inert defaults across both runs; no
    # consumer overlays them, and re-running never turns them into
    # duplicate rows either.
    assert by_purpose["synthesis"].model == "qwen2.5:3b"
    assert by_purpose["verification"].model == "qwen2.5:3b"


@pytest.mark.asyncio
async def test_setup_finalize_password_only_reopen_is_idempotent(client, session):
    """A password-only finalize, re-run after a re-open, must not error even
    though it writes no LLM block at all (llm=None on both calls)."""
    response = await client.post(
        "/api/v1/setup", json={"password": "test-pw-12345"}
    )
    assert response.status_code == 200
    assert response.json()["llm"]["ok"] is True

    await _reopen_setup(session)

    response = await client.post(
        "/api/v1/setup", json={"password": "test-pw-99999"}
    )
    assert response.status_code == 200
    assert response.json()["llm"]["ok"] is True

    config = (
        await session.execute(
            select(Config).where(Config.key == ADMIN_PASSWORD_KEY)
        )
    ).scalar_one_or_none()
    assert config is not None


class TestTheSeedsOllamaEndpointIsOverridable:
    """The seed pinned `localhost:11434` for every Ollama purpose, and the
    embedder on this network is not on localhost.

    That is what took the v0.5 release's API e2e step down to
    `ConnectError: All connection attempts failed` — the e2e boots a
    disposable stack, posts a password to `/api/v1/setup`, and the wizard
    seeds localhost. One test then *skipped* itself with "search cannot be
    proven without a reachable embedder", so the step reported green with its
    load-bearing assertion never run and the release shipped on it.

    Localhost stays the default, because a fresh install elsewhere has no LAN
    embedder to find. The override is what lets this machine's gate reach the
    one recorded in CLAUDE.md.
    """

    ENV = "DARKMEM_OLLAMA_BASE_URL"

    def test_default_is_localhost_when_unset(self, monkeypatch):
        monkeypatch.delenv(self.ENV, raising=False)
        import importlib
        from app.services import llm_seed
        importlib.reload(llm_seed)
        ollama = [c for c in llm_seed.DEFAULT_PURPOSE_CONFIGS if c.provider_name == "ollama"]
        assert ollama, "the seed must still pin the Ollama purposes"
        assert all(c.base_url == "http://localhost:11434/v1" for c in ollama)

    def test_the_override_reaches_every_ollama_purpose(self, monkeypatch):
        monkeypatch.setenv(self.ENV, "http://192.168.0.196:11434/v1")
        import importlib
        from app.services import llm_seed
        importlib.reload(llm_seed)
        ollama = [c for c in llm_seed.DEFAULT_PURPOSE_CONFIGS if c.provider_name == "ollama"]
        assert all(c.base_url == "http://192.168.0.196:11434/v1" for c in ollama), (
            "an override that reaches some purposes and not others splits the "
            "stack across two hosts, which is worse than not overriding at all"
        )
        # The embedding purpose is the one the e2e proves search with.
        embedding = next(c for c in ollama if c.purpose == "embedding")
        assert embedding.model == "qwen3-embedding:0.6b"
        assert embedding.dimensions == 1024
        importlib.reload(llm_seed)
