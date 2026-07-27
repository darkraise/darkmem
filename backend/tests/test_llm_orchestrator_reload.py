"""T1.02 — one shared ``httpx.AsyncClient``, atomic live reload.

Doc 11 §3: ``LLMOrchestrator`` is constructed once (at boot, or on an admin
save) and every purpose dispatches through the *same* client for that
instance's whole lifetime. A reload never mutates a live instance in place —
it builds a full replacement and swaps the in-process reference, which is
what makes the swap atomic under the single-worker assumption (invariant 13):
a request either sees the whole old orchestrator or the whole new one, never
a hybrid of the two. Both failure modes this test suite guards against are
silent by nature (a leaked httpx client, a request served old-base-url +
new-api-key) so they are asserted here rather than left to inspection.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator


# --- One client instance for the process lifetime -------------------------

async def test_shared_client_constructed_once_and_reused(monkeypatch):
    """Building the orchestrator constructs exactly one ``httpx.AsyncClient``,
    and every subsequent call — embed or chat, any purpose — reuses it."""
    construct_count = 0
    real_async_client = httpx.AsyncClient

    def counting_async_client(*args, **kwargs):
        nonlocal construct_count
        construct_count += 1
        return real_async_client(*args, **kwargs)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}]}
        )

    monkeypatch.setattr(httpx, "AsyncClient", counting_async_client)
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", lambda **_: httpx.MockTransport(handler))

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed", dimensions=2),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test-reason"),
    }
    llm = LLMOrchestrator(config)
    assert construct_count == 1, "constructing one orchestrator must build exactly one client"

    client_identity = id(llm._client)

    await llm.embed("hello")
    await llm.embed("world")
    await llm.chat_completion("reasoning", messages=[{"role": "user", "content": "hi"}])

    assert construct_count == 1, (
        "embed/chat_completion must reuse the client built at construction, "
        "not build a new one per call"
    )
    assert id(llm._client) == client_identity

    await llm.close()


# --- Atomic swap: pipeline references move together, in one step ----------

async def test_pipeline_swap_is_atomic_under_concurrency():
    """``_swap_pipeline_llm`` updates every reference the pipeline holds in
    one synchronous pass. A reader task interleaved via ``asyncio.sleep(0)``
    must never observe a mixture — some references already the new
    orchestrator, others still the old one."""
    from app.api.routes.config import _swap_pipeline_llm

    old = SimpleNamespace(label="old")
    new = SimpleNamespace(label="new")
    pipeline = SimpleNamespace(
        llm=old,
        extraction=SimpleNamespace(llm=old),
        classification=SimpleNamespace(llm=old),
        _classifier_cache="stale",
    )

    mixed_observations: list[tuple] = []

    async def reader():
        for _ in range(200):
            snapshot = (pipeline.llm, pipeline.extraction.llm, pipeline.classification.llm)
            if len(set(id(x) for x in snapshot)) != 1:
                mixed_observations.append(snapshot)
            await asyncio.sleep(0)

    async def writer():
        await asyncio.sleep(0)
        _swap_pipeline_llm(pipeline, new)

    await asyncio.gather(reader(), writer())

    assert not mixed_observations, (
        f"reader observed a half-applied pipeline swap: {mixed_observations}"
    )
    assert pipeline.llm is new
    assert pipeline.extraction.llm is new
    assert pipeline.classification.llm is new
    assert pipeline._classifier_cache is None


@pytest.mark.asyncio
async def test_route_reload_swaps_state_and_pipeline_together(client, auth_headers, monkeypatch):
    """POST /api/v1/config/llm installs the new orchestrator on
    ``app.state.llm`` and on every pipeline reference in the same request —
    proving the HTTP-triggered reload path (not just the helper in
    isolation) is atomic."""
    from app.main import app

    class FakePipeline:
        def __init__(self, llm):
            self.llm = llm
            self.extraction = SimpleNamespace(llm=llm)
            self.classification = SimpleNamespace(llm=llm)
            self._classifier_cache = "stale"

    old_llm = getattr(app.state, "llm", None)
    fake_pipeline = FakePipeline(old_llm)
    monkeypatch.setattr(app.state, "pipeline", fake_pipeline, raising=False)

    resp = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={
            "reasoning": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "api_kind": "openai",
            }
        },
    )
    assert resp.status_code == 200, resp.text

    new_llm = app.state.llm
    assert new_llm is not old_llm, "save must install a new orchestrator instance"
    assert fake_pipeline.llm is new_llm
    assert fake_pipeline.extraction.llm is new_llm
    assert fake_pipeline.classification.llm is new_llm
    assert fake_pipeline._classifier_cache is None

    # Let the background close() of the superseded client run so it doesn't
    # leak across tests.
    for _ in range(5):
        await asyncio.sleep(0)


# --- Reload failure keeps the prior working config -------------------------

@pytest.mark.asyncio
async def test_reload_failure_keeps_prior_orchestrator(client, auth_headers, monkeypatch, session):
    """A construction failure mid-reload must surface (never be swallowed)
    and must never leave ``app.state.llm`` pointing at a broken or partial
    instance — the previous, working orchestrator stays live."""
    from app.main import app
    from app.services.config import get_llm_config as fetch_cfg

    initial_config = await fetch_cfg(session)
    good_llm = LLMOrchestrator(initial_config)
    monkeypatch.setattr(app.state, "llm", good_llm, raising=False)

    def boom(self, config):
        raise RuntimeError("simulated LLMOrchestrator construction failure")

    monkeypatch.setattr(LLMOrchestrator, "__init__", boom)

    with pytest.raises(RuntimeError, match="simulated LLMOrchestrator construction failure"):
        await client.post(
            "/api/v1/config/llm",
            headers=auth_headers,
            json={
                "reasoning": {
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o-mini",
                    "api_kind": "openai",
                }
            },
        )

    assert app.state.llm is good_llm, (
        "a reload that fails to construct its replacement must leave the "
        "prior working orchestrator live, not None or a half-built instance"
    )

    await good_llm.close()
