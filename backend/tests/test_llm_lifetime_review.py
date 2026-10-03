import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import LLMPurposeConfig, settings
from app.services.llm import LLMOrchestrator, lease_llm


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_parent", [False, True])
async def test_chunk_failure_drains_siblings_before_retirement(monkeypatch, cancel_parent):
    from app.api.routes import config

    sibling_started = asyncio.Event()
    failure_ready = asyncio.Event()
    cancellation_started = asyncio.Event()
    finish_cleanup = asyncio.Event()
    child_tasks = set()
    retirement_tasks = []
    original_error = RuntimeError("first chunk failed")
    cleanup_observations = []

    async def handler(request):
        child_tasks.add(asyncio.current_task())
        chunk = json.loads(request.content)["input"][0]
        if chunk == "failure":
            await failure_ready.wait()
            raise original_error
        sibling_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancellation_started.set()
            await finish_cleanup.wait()
            cleanup_observations.append(old._client.is_closed)

    old = LLMOrchestrator({"embedding": LLMPurposeConfig(base_url="http://mock", model="test", dimensions=3)})
    await old._client.aclose()
    old._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def consumer():
        with lease_llm(old):
            return await old.embed_batch_chunked(["failure", "sibling", "queued"], 1, 2)

    def spawn(coroutine, **kwargs):
        task = asyncio.create_task(coroutine)
        retirement_tasks.append(task)
        return task

    monkeypatch.setattr(config, "spawn", spawn)
    operation = asyncio.create_task(consumer())
    try:
        await asyncio.wait_for(sibling_started.wait(), 1)
        config._replace_orchestrator(SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(llm=old))), SimpleNamespace())
        if cancel_parent:
            operation.cancel()
        else:
            failure_ready.set()
        await asyncio.wait_for(cancellation_started.wait(), 1)
        assert not operation.done()
        assert not old._client.is_closed
        finish_cleanup.set()
        with pytest.raises(asyncio.CancelledError if cancel_parent else RuntimeError) as caught:
            await operation
        if not cancel_parent:
            assert caught.value is original_error
        assert cleanup_observations and not any(cleanup_observations)
        assert all(task.done() for task in child_tasks)
        await asyncio.wait_for(asyncio.gather(*retirement_tasks), 1)
        assert old._client.is_closed
    finally:
        finish_cleanup.set()
        failure_ready.set()
        operation.cancel()
        for task in child_tasks:
            task.cancel()
        await asyncio.gather(operation, *child_tasks, return_exceptions=True)
        await asyncio.gather(*retirement_tasks, return_exceptions=True)
        await old.close()


@pytest.mark.asyncio
async def test_read_only_empty_llm_update_never_probes(client, auth_headers, monkeypatch):
    from fastapi import HTTPException
    from app.api.routes import config
    from app.main import app

    resolved = {purpose: LLMPurposeConfig(base_url="http://mock", model="test", dimensions=None) for purpose in config.PURPOSES}
    monkeypatch.setattr(config, "fetch_llm_config", AsyncMock(return_value=resolved))
    monkeypatch.setattr(config, "_replace_orchestrator", lambda *args: None)
    monkeypatch.setattr(app.state, "pipeline", None, raising=False)
    outbound = AsyncMock(return_value=([0.0, 0.0, 0.0], "test|3"))
    monkeypatch.setattr(LLMOrchestrator, "embed", outbound)
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.post("/api/v1/config/llm", headers=auth_headers, json={})
    outbound.assert_not_awaited()
    assert response.status_code == 403
    with pytest.raises(HTTPException) as refusal:
        await config.apply_llm_config_change(SimpleNamespace(app=app), None)
    assert refusal.value.status_code == 403
    config.fetch_llm_config.assert_not_awaited()
    outbound.assert_not_awaited()
