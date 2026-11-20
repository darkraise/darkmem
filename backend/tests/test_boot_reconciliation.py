"""Boot-time partition reconciliation is permanent and idempotent (T0.14).

Doc 19 §2 replaces the registry's old one-time creation sweep with a
reconciliation that runs at EVERY startup: it iterates the live ``embedders``
rows and runs each template's ``CREATE TABLE IF NOT EXISTS`` plus each aux
index's ``CREATE INDEX IF NOT EXISTS``. That is what dissolves the
sweep-versus-baseline coexistence problem — adding a partition family becomes a
template edit, and an existing deployment gains the new parent for its current
fingerprint at next boot with no re-register and no migration. It also
self-heals drift, and replays mechanically in the deferred .NET port because it
is a loop over rows running parameterised plain SQL.

G-A names idempotence explicitly, so it is asserted here rather than assumed.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.embedder_registry import (
    _TABLE_TEMPLATES,
    EmbedderInfo,
    EmbedderRegistry,
    child_table,
)

FP = "reconcile-probe|8"


async def _register(session, registry: EmbedderRegistry, fingerprint: str = FP, dims: int = 8):
    await registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id="reconcile-probe", dims=dims, source="llm"),
    )


async def _child_tables(session, fingerprint: str = FP) -> set[str]:
    names = [child_table(parent, fingerprint) for parent in _TABLE_TEMPLATES]
    rows = (await session.execute(
        text("SELECT tablename FROM pg_tables "
             "WHERE schemaname = 'public' AND tablename = ANY(:names)"),
        {"names": names},
    )).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_reconcile_creates_every_parent_for_a_live_fingerprint(session):
    registry = EmbedderRegistry()
    await _register(session, registry)

    present = await _child_tables(session)
    assert len(present) == len(_TABLE_TEMPLATES), (
        f"expected a child table per parent, got {sorted(present)}"
    )


@pytest.mark.asyncio
async def test_second_reconcile_is_a_no_op(session):
    """Booting twice against the same database changes nothing the second time."""
    registry = EmbedderRegistry()
    await _register(session, registry)

    before = await _child_tables(session)
    result = await registry.reconcile(session)
    after = await _child_tables(session)

    assert after == before
    assert result["fingerprints"] >= 1
    assert result["parents"] == len(_TABLE_TEMPLATES)


@pytest.mark.asyncio
async def test_reconcile_regrows_exactly_the_missing_child(session):
    """A restored dump missing one child table regrows that one, not the rest."""
    registry = EmbedderRegistry()
    await _register(session, registry)

    victim = child_table("entity_embeddings", FP)
    await session.execute(text(f"DROP TABLE {victim} CASCADE"))
    await session.commit()
    assert victim not in await _child_tables(session)

    survivors_before = await _child_tables(session)
    await registry.reconcile(session)
    after = await _child_tables(session)

    assert victim in after, "the missing child was not regrown"
    assert after == survivors_before | {victim}, "reconcile touched more than the gap"


@pytest.mark.asyncio
async def test_reconcile_skips_retired_fingerprints(session):
    """Only live rows reconcile — a retired embedder is not resurrected."""
    registry = EmbedderRegistry()
    await _register(session, registry)
    await session.execute(
        text("UPDATE embedders SET retired_at = now() WHERE fingerprint = :fp"), {"fp": FP}
    )
    await session.commit()

    victim = child_table("entity_embeddings", FP)
    await session.execute(text(f"DROP TABLE {victim} CASCADE"))
    await session.commit()

    await registry.reconcile(session)
    assert victim not in await _child_tables(session)


@pytest.mark.asyncio
async def test_malformed_fingerprint_is_rejected_at_registration_not_ddl_time(session):
    """A fingerprint folding to an empty slug fails loudly before any DDL runs.

    Its child tables would be named ``<parent>__`` — addressable by nothing —
    so the failure belongs at registration, where it is one clear error, not at
    DDL time where it would leave half a partition set behind.

    ``@@@`` is the shape that folds empty: every character is a separator, so
    the slug regex maps the lot to ``_`` and the strip leaves nothing. (A
    fingerprint that came through ``parse_fingerprint`` always carries at least
    one digit from ``|<dims>``, so this guard is defence in depth for callers
    that build an ``EmbedderInfo`` by hand.)
    """
    registry = EmbedderRegistry()
    with pytest.raises(RuntimeError, match="empty partition slug"):
        await _register(session, registry, fingerprint="@@@")
    await session.rollback()

    leaked = (await session.execute(
        text("SELECT count(*) FROM pg_tables "
             "WHERE schemaname = 'public' AND tablename LIKE '%\\_\\_'")
    )).scalar()
    assert leaked == 0, "a malformed fingerprint created child tables before failing"


def test_child_tables_are_only_ever_named_through_child_table():
    """Invariant 2: no literal slug interpolation anywhere in the registry.

    ``child_table`` is the sole namer. The one place ``<parent>__<slug>`` is
    assembled is inside that function; anything else building the name by hand
    would drift the moment the slug rule changes.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "app" / "services" / "embedder_registry.py"
    body = src.read_text()
    assert body.count('f"{parent}__') == 1, (
        "child-table names must be built only inside child_table()"
    )


# ── Boot recovery, pipeline state and partition maintenance ──────────────

import asyncio
import ast
import contextlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

FUTURE_MONTHS = text(
    "SELECT 'events_' || to_char(date_trunc('month', now() AT TIME ZONE 'UTC') "
    "+ make_interval(months => g), 'YYYYMM') FROM generate_series(0, 3) AS g"
)


def _committed_factory():
    from tests.conftest import test_engine

    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _event_children(factory) -> set[str]:
    async with factory() as s:
        return set((await s.execute(text(
            "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
            "WHERE i.inhparent = 'events'::regclass"
        ))).scalars().all())


async def _months_ahead(factory) -> list[str]:
    async with factory() as s:
        return list((await s.execute(FUTURE_MONTHS)).scalars().all())


async def _drop_far_partitions(factory) -> list[str]:
    """Drop the empty children two and three months ahead, so a reconcile that
    looks only one month ahead (or does not run) leaves them missing."""
    months = await _months_ahead(factory)
    async with factory() as s:
        for child in months[2:]:
            await s.execute(text(f'DROP TABLE IF EXISTS "{child}"'))
        await s.commit()
    return months


def _boot_llm_config():
    from app.config import LLMPurposeConfig
    from app.services.config import PURPOSES

    return {
        p: LLMPurposeConfig(base_url="http://127.0.0.1:9/v1", model="boot-probe", dimensions=None)
        for p in PURPOSES
    }


@contextlib.asynccontextmanager
async def booted(monkeypatch, *, llm_fails: bool):
    """Run the real lifespan against the test database with the scheduler and
    the MCP session manager stubbed, and restore app.state afterwards."""
    import app.database as database
    import app.main as main_module
    from app.api.mcp import server
    from app.main import app
    from app.services import config as config_service
    from app.services import pipeline_failures
    from app.services.job_registry import JobRegistry

    factory = _committed_factory()
    monkeypatch.setattr(database, "async_session_factory", factory)
    monkeypatch.setattr(JobRegistry, "start_all", AsyncMock())
    monkeypatch.setattr(
        main_module, "mcp_server",
        SimpleNamespace(session_manager=SimpleNamespace(run=contextlib.nullcontext)),
    )
    monkeypatch.setattr(server, "_pipeline", server._pipeline)
    if llm_fails:
        failing = AsyncMock(side_effect=RuntimeError("provider table unreadable"))
        monkeypatch.setattr(config_service, "get_llm_config", failing)
    else:
        monkeypatch.setattr(
            config_service, "get_llm_config", AsyncMock(return_value=_boot_llm_config()),
        )
    state_before = dict(app.state._state)
    handlers_before = dict(pipeline_failures.RETRY_HANDLERS)
    async with factory() as s:
        enrichment_row_existed = (await s.execute(
            select(Config.key).where(Config.key == "job:code_enrichment")
        )).scalar_one_or_none() is not None
        projects_before = set((await s.execute(text("SELECT name FROM projects"))).scalars())
    try:
        async with main_module.lifespan(app):
            yield factory
    finally:
        app.state._state.clear()
        app.state._state.update(state_before)
        pipeline_failures.RETRY_HANDLERS.clear()
        pipeline_failures.RETRY_HANDLERS.update(handlers_before)
        async with factory() as s:
            if not enrichment_row_existed:
                await s.execute(delete(Config).where(Config.key == "job:code_enrichment"))
            # The boot seeds the personal project and backfills the registry;
            # rows it committed would outlive this test.
            await s.execute(
                text("DELETE FROM projects WHERE NOT (name = ANY(CAST(:kept AS text[])))"),
                {"kept": sorted(projects_before)},
            )
            await s.commit()


from app.models.config import Config  # noqa: E402


@pytest.mark.asyncio
async def test_llm_setup_failure_still_reconciles_partitions(setup_database, monkeypatch):
    import app.main as main_module
    from app.main import app

    factory = _committed_factory()
    months = await _drop_far_partitions(factory)
    backfilled = []
    real_backfill = main_module.backfill_projects

    async def spy_backfill(session):
        backfilled.append(True)
        return await real_backfill(session)

    monkeypatch.setattr(main_module, "backfill_projects", spy_backfill)

    async with booted(monkeypatch, llm_fails=True):
        pipeline = app.state.pipeline
        boot_error = getattr(app.state, "pipeline_boot_error", None)

    assert set(months) - await _event_children(factory) == set()
    assert backfilled == [True]
    assert pipeline is None
    assert boot_error


@pytest.mark.asyncio
async def test_pipeline_is_built_once_an_orchestrator_is_installed(
    setup_database, client, monkeypatch,
):
    from app.api.auth import create_access_token
    from app.main import app
    from app.services import buffer_flush
    from app.services.job_registry import Job, JobRegistry
    from app.services.job_runners import make_buffer_flush_runner
    from app.services.llm import LLMOrchestrator
    from app.models.job_run import JobRun
    from tests.test_health import initialised

    monkeypatch.setattr(
        LLMOrchestrator, "embed", AsyncMock(side_effect=RuntimeError("embedder offline")),
    )
    stats = {"claimed": 1, "done": 1, "failed": 0, "rejected": 0, "reclaimed": 0, "swept": 0}
    flush = AsyncMock(return_value=stats)
    monkeypatch.setattr(buffer_flush, "flush_once", flush)

    async with initialised(), booted(monkeypatch, llm_fails=True) as factory:
        registry = JobRegistry(factory)
        key = f"buffer-flush-probe-{uuid.uuid4().hex[:8]}"
        registry.register(Job(
            key=key, display_name=key, description="", default_cron="*/5 * * * * *",
            min_interval_seconds=5, runner=make_buffer_flush_runner(app, factory),
        ))
        try:
            await registry._run_once(key)
            flush.assert_not_awaited()
            async with factory() as s:
                skipped = (await s.execute(
                    select(JobRun).where(JobRun.job_key == key)
                )).scalars().all()
            assert [r.detail.get("skipped_reason") for r in skipped] == [
                "no pipeline: LLM setup failed at boot"
            ]

            headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
            saved = await client.post("/api/v1/config/llm", headers=headers, json={})
            assert saved.status_code == 200, saved.text
            assert app.state.pipeline is not None
            health = (await client.get("/health")).json()
            assert health["pipeline_state"] == "ok"

            await registry._run_once(key)
            flush.assert_awaited_once()
            assert flush.await_args.args[1] is app.state.pipeline
        finally:
            async with factory() as s:
                await s.execute(delete(JobRun).where(JobRun.job_key == key))
                await s.commit()


@pytest.mark.asyncio
async def test_partitions_exist_three_months_ahead_with_the_cleanup_disabled(setup_database):
    from app.services.job_registry import Job, JobConfig, JobRegistry

    factory = _committed_factory()
    months = await _drop_far_partitions(factory)
    slept: list[float] = []
    parked = asyncio.Event()

    async def one_hour_passes(seconds):
        slept.append(seconds)
        if len(slept) > 1:
            await parked.wait()

    async def must_not_run():
        raise AssertionError("the disabled cleanup ran")

    registry = JobRegistry(factory, maintenance_sleep=one_hour_passes)
    registry.register(Job(
        key="pipeline_failure_cleanup", display_name="cleanup", description="",
        default_cron="0 * * * *", min_interval_seconds=60, runner=must_not_run,
    ))
    async with factory() as s:
        row_existed = (await s.execute(
            select(Config.key).where(Config.key == "job:pipeline_failure_cleanup")
        )).scalar_one_or_none() is not None
    await registry.save_config(
        "pipeline_failure_cleanup",
        JobConfig(enabled=False, cron="0 * * * *", min_interval_seconds=60, config={}),
    )
    try:
        await registry.start_all()
        for _ in range(100):
            if set(months) <= await _event_children(factory):
                break
            await asyncio.sleep(0.05)
        assert slept[:1] == [3600]
        assert set(months) <= await _event_children(factory)
    finally:
        await registry.stop_all()
        if not row_existed:
            async with factory() as s:
                await s.execute(delete(Config).where(Config.key == "job:pipeline_failure_cleanup"))
                await s.commit()


def test_job_count_is_still_twenty_seven():
    from pathlib import Path

    import app.main as main_module
    from app.services.dream_jobs import SHIPPED_DREAM_JOBS
    from tests.test_code_deriver import _binding_token, _direct_job_registrations, _job_kwarg

    direct = [
        _binding_token(_job_kwarg(call, "key"))
        for call in _direct_job_registrations(Path(main_module.__file__).read_text())
    ]
    assert len(direct) + len(SHIPPED_DREAM_JOBS) == 27
    assert not [key for key in direct if "partition" in key.lower()]
