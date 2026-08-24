"""``llm_usage`` is pruned by age, and the window is the operator's to set.

Unlike ``job_runs``, which is trimmed to a row ceiling because a quiet week and
a busy week produce wildly different volumes, this table is trimmed by age: its
whole purpose is answering "what did the last N days cost", and a row-count
ceiling would silently shorten that answer during exactly the busy period an
operator is investigating.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.llm_usage import LLMUsage
from app.services.job_registry import Job, JobRegistry
from app.services.job_runners import (
    LLM_USAGE_CLEANUP_JOB_KEY,
    LLM_USAGE_CONFIG_SCHEMA,
    make_llm_usage_cleanup_runner,
)
from tests.conftest import test_engine


def _row(days_ago: float, **kw) -> LLMUsage:
    base = dict(
        occurred_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        purpose="extraction", model="m", api_kind="openai",
        subject_type="memory", tokens_measured=False, duration_ms=1,
    )
    base.update(kw)
    return LLMUsage(**base)


@pytest_asyncio.fixture
async def run_usage_cleanup(clean_llm_usage):
    """Runs the real registered runner against a registry of its own.

    Reaching the runner through a JobRegistry rather than calling a bare
    function is the point: the retention window lives in the job's config row,
    so a runner that read it from anywhere else would pass a direct call and
    still ignore the operator in production.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    registry.register(Job(
        key=LLM_USAGE_CLEANUP_JOB_KEY,
        display_name="LLM Usage Retention",
        description="(test harness)",
        default_cron="0 4 * * *",
        min_interval_seconds=3600,
        runner=make_llm_usage_cleanup_runner(app, factory),
        config_schema=LLM_USAGE_CONFIG_SCHEMA,
    ))
    previous = getattr(app.state, "job_registry", None)
    app.state.job_registry = registry

    async def run(retention_days: int | None = None):
        if retention_days is not None:
            cfg = await registry.load_config(LLM_USAGE_CLEANUP_JOB_KEY)
            cfg.config["retention_days"] = retention_days
            await registry.save_config(LLM_USAGE_CLEANUP_JOB_KEY, cfg)
        return await registry.get(LLM_USAGE_CLEANUP_JOB_KEY).runner()

    yield run

    app.state.job_registry = previous
    async with factory() as s:
        from sqlalchemy import text as sa_text
        await s.execute(sa_text("DELETE FROM llm_usage"))
        await s.execute(sa_text(
            "DELETE FROM config WHERE key = :k"
        ), {"k": f"job:{LLM_USAGE_CLEANUP_JOB_KEY}"})
        await s.commit()


async def _seed(rows):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        s.add_all(rows)
        await s.commit()


async def _remaining() -> list[LLMUsage]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        return list((await s.execute(select(LLMUsage))).scalars().all())


@pytest.mark.asyncio
async def test_prunes_beyond_the_retention_window(run_usage_cleanup):
    await _seed([_row(400), _row(0)])
    await run_usage_cleanup(retention_days=90)
    left = await _remaining()
    assert len(left) == 1


@pytest.mark.asyncio
async def test_the_boundary_row_is_kept(run_usage_cleanup):
    """A row exactly at the edge is inside the window the operator asked for.
    Deleting it makes the reported window one day shorter than its label."""
    await _seed([_row(89.9), _row(90.1)])
    await run_usage_cleanup(retention_days=90)
    left = await _remaining()
    assert len(left) == 1


@pytest.mark.asyncio
async def test_a_sweep_with_nothing_to_do_reports_nothing(run_usage_cleanup):
    """0 is the no-op signal: a nightly sweep over a clean table must not write
    a job_runs row every night just to say it found nothing."""
    await _seed([_row(1)])
    assert await run_usage_cleanup(retention_days=90) == 0


@pytest.mark.asyncio
async def test_a_sweep_that_deleted_something_says_how_much(run_usage_cleanup):
    await _seed([_row(400), _row(401)])
    result = await run_usage_cleanup(retention_days=90)
    assert result["deleted"] == 2
    assert result["retention_days"] == 90


@pytest.mark.asyncio
async def test_the_operator_window_is_honoured_not_the_default(run_usage_cleanup):
    """The config row is the authority. A runner holding its own constant would
    pass every test that never changes the setting."""
    await _seed([_row(10), _row(2)])
    await run_usage_cleanup(retention_days=5)
    left = await _remaining()
    assert len(left) == 1
