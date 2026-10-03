import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import job_runners
from app.services.llm import LLMOrchestrator


@pytest.mark.parametrize("runner_name", [
    "make_repo_sync_runner", "make_code_enrichment_runner", "make_ppr_snapshot_runner",
    "make_relation_embedding_runner", "make_repo_entity_anchoring_runner",
    "make_repo_entity_merge_runner", "make_block_embedding_runner",
])
async def test_job_capture_holds_llm_through_predispatch_await_and_cancellation(runner_name):
    llm = LLMOrchestrator({})
    waiting = asyncio.Event()
    release = asyncio.Event()

    async def load_config(_key):
        if runner_name != "make_ppr_snapshot_runner":
            waiting.set()
            await release.wait()
        return SimpleNamespace(config={})

    @asynccontextmanager
    async def factory():
        waiting.set()
        await release.wait()
        yield SimpleNamespace()

    app = SimpleNamespace(state=SimpleNamespace(
        llm=llm, job_registry=SimpleNamespace(load_config=load_config),
    ))
    running = asyncio.create_task(getattr(job_runners, runner_name)(app, factory)())
    retiring = None
    try:
        await asyncio.wait_for(waiting.wait(), 2)
        app.state.llm = None
        retiring = asyncio.create_task(llm.close())
        await asyncio.sleep(0)
        assert not retiring.done()
        assert not llm._client.is_closed
    finally:
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        if retiring is not None:
            await asyncio.wait_for(retiring, 2)
        else:
            await llm.close()
    assert llm._client.is_closed


@pytest.mark.parametrize("failure", [False, True])
async def test_enrichment_job_lease_survives_swap_until_completion(monkeypatch, failure):
    llm = LLMOrchestrator({})
    entered = asyncio.Event()
    resume = asyncio.Event()

    async def process_batch(_worker, **_kwargs):
        entered.set()
        await resume.wait()
        assert not llm._client.is_closed
        if failure:
            raise RuntimeError("controlled failure")
        return 1

    monkeypatch.setattr("app.services.enrichment_worker.EnrichmentWorker.process_batch", process_batch)
    app = SimpleNamespace(state=SimpleNamespace(llm=llm, job_registry=SimpleNamespace(
        load_config=AsyncMock(return_value=SimpleNamespace(config={})),
    )))
    running = asyncio.create_task(job_runners.make_code_enrichment_runner(app, None)())
    await asyncio.wait_for(entered.wait(), 2)
    app.state.llm = None
    retiring = asyncio.create_task(llm.close())
    try:
        await asyncio.sleep(0)
        assert not retiring.done()
    finally:
        resume.set()
        if failure:
            with pytest.raises(RuntimeError, match="controlled failure"):
                await running
        else:
            assert await running == {"enriched": 1}
        await asyncio.wait_for(retiring, 2)
    assert llm._client.is_closed
