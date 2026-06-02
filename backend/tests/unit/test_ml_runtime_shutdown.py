"""shutdown_all must cancel eviction watchdogs and clear loaded models.

This is the teardown the app lifespan invokes on shutdown; without it, loaded
torch models and their per-model eviction tasks leak across reload-heavy dev
loops and graceful restarts.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.ml_runtime import MLModelManager, _LoadedModel


@pytest.mark.asyncio
async def test_shutdown_all_cancels_tasks_and_clears_state():
    mgr = MLModelManager()

    async def _forever():
        await asyncio.Event().wait()

    task = asyncio.create_task(_forever())
    await asyncio.sleep(0)  # let the task start
    mgr._models["repo"] = _LoadedModel(
        tokenizer=None, model=None, id2label={}, last_used=0.0, eviction_task=task,
    )
    mgr._load_locks["repo"] = asyncio.Lock()

    await mgr.shutdown_all()

    assert task.cancelled()
    assert mgr._models == {}
    assert mgr._load_locks == {}
    assert mgr._stopped is True
