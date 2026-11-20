"""update_config must take the per-job config lock for its read-modify-write.

set_config and update_config both read, patch and write the `job:<key>` row;
unlocked, two concurrent saves would each overwrite the other's change.
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.job_registry import FieldDescriptor, Job, JobRegistry


def _registry(key: str):
    engine = create_async_engine(settings.test_database_url)
    reg = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))

    async def _noop():
        return None

    reg.register(Job(
        key=key, display_name="Cfg", description="d",
        default_cron="*/5 * * * *", min_interval_seconds=1, runner=_noop,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch", default=5, min=1, max=100)],
    ))
    return reg, engine


@pytest.mark.asyncio
async def test_update_config_acquires_the_config_lock():
    reg, engine = _registry("cfg_lock")
    try:
        # Warm the connection pool so the timing below isolates the lock, not a
        # slow first connection.
        baseline = (await reg.load_config("cfg_lock")).cron
        assert baseline != "*/2 * * * *"

        job = reg._jobs["cfg_lock"]
        async with job.config_lock:
            task = asyncio.create_task(reg.update_config("cfg_lock", cron="*/2 * * * *"))
            await asyncio.sleep(0.3)  # ample time for an UNLOCKED save to land
            # If update_config respects the lock it is still blocked here, so the
            # cron change has not been persisted yet.
            during = (await reg.load_config("cfg_lock")).cron
            assert during == baseline, "update_config wrote while the config lock was held"

        await task
        assert (await reg.load_config("cfg_lock")).cron == "*/2 * * * *"
    finally:
        await reg.stop_all()
        await engine.dispose()
