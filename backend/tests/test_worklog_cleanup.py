"""worklog_cleanup: closed workstreams past the window go, journalled; open and retained ones stay.

The runner is reached through a JobRegistry rather than called bare: the
window lives in the job's config row, so a runner that read it from anywhere
else would pass a direct call and still ignore the operator in production.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.services import worklog
from app.services.job_registry import Job, JobRegistry
from app.services.worklog_cleanup import (
    RETENTION_DAYS_DEFAULT,
    WORKLOG_CLEANUP_CONFIG_SCHEMA,
    WORKLOG_CLEANUP_CRON,
    WORKLOG_CLEANUP_JOB_KEY,
    make_worklog_cleanup_runner,
)
from tests.conftest import test_engine

PROJECT = "worklog-cleanup"


async def _clear(made):
    async with made() as cleanup:
        await cleanup.execute(text("DELETE FROM workstreams WHERE project = :p"), {"p": PROJECT})
        await cleanup.execute(text("DELETE FROM projects WHERE name = :p"), {"p": PROJECT})
        await cleanup.execute(
            text("DELETE FROM config WHERE key = :k"), {"k": f"job:{WORKLOG_CLEANUP_JOB_KEY}"}
        )
        await cleanup.commit()


@pytest_asyncio.fixture
async def factory(setup_database):
    made = async_sessionmaker(test_engine, expire_on_commit=False)
    # conftest resets the schema per session; this guards a row left by a
    # teardown that failed earlier in the same session.
    await _clear(made)
    async with made() as s:
        stray = (await s.execute(
            text(
                "SELECT count(*) FROM workstreams WHERE state = 'closed' AND NOT retain "
                "AND closed_at < now() - interval '1 day' AND project <> :p"
            ),
            {"p": PROJECT},
        )).scalar_one()
    assert stray == 0, "another suite left an eligible workstream committed; the sweep would erase it"
    yield made
    await _clear(made)


@pytest_asyncio.fixture
async def run_cleanup(factory):
    registry = JobRegistry(factory)
    registry.register(Job(
        key=WORKLOG_CLEANUP_JOB_KEY,
        display_name="Work Log Retention",
        description="(test harness)",
        default_cron=WORKLOG_CLEANUP_CRON,
        min_interval_seconds=3600,
        runner=make_worklog_cleanup_runner(app, factory),
        config_schema=WORKLOG_CLEANUP_CONFIG_SCHEMA,
    ))
    previous = getattr(app.state, "job_registry", None)
    app.state.job_registry = registry

    async def run(retention_days: int | None = None):
        if retention_days is not None:
            cfg = await registry.load_config(WORKLOG_CLEANUP_JOB_KEY)
            cfg.config["retention_days"] = retention_days
            await registry.save_config(WORKLOG_CLEANUP_JOB_KEY, cfg)
        return await registry.get(WORKLOG_CLEANUP_JOB_KEY).runner()

    yield run

    app.state.job_registry = previous


async def _workstream(factory, key, *, closed_days_ago=None, retain=False, entries=1):
    """A committed workstream; closed that many days ago when closed_days_ago is given."""
    async with factory() as s:
        result = await worklog.append(
            s, project=PROJECT, key=key, run_key="r",
            entries=[{"kind": "note", "body": f"{key} {i}"} for i in range(entries)],
        )
        ws_id = result.workstream.id
        if closed_days_ago is not None:
            await worklog.update_workstream(s, ws_id, state="closed", retain=retain)
            await s.execute(
                text(
                    "UPDATE workstreams SET closed_at = now() - make_interval(days => CAST(:d AS integer)) "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"d": closed_days_ago, "id": str(ws_id)},
            )
        await s.commit()
        return ws_id


async def _keys(factory) -> list[str]:
    async with factory() as s:
        rows = await s.execute(
            text("SELECT key FROM workstreams WHERE project = :p ORDER BY key"), {"p": PROJECT}
        )
        return list(rows.scalars().all())


def test_the_schema_is_one_retention_window_defaulting_to_ninety_days():
    assert WORKLOG_CLEANUP_JOB_KEY == "worklog_cleanup"
    assert RETENTION_DAYS_DEFAULT == 90
    [field] = WORKLOG_CLEANUP_CONFIG_SCHEMA
    assert (field.key, field.default, field.min, field.max) == ("retention_days", 90, 1, 3650)


async def test_the_default_window_is_ninety_days(factory, run_cleanup):
    await _workstream(factory, "expired", closed_days_ago=91, entries=2)
    await _workstream(factory, "inside", closed_days_ago=89)
    assert await run_cleanup() == {"workstreams": 1, "entries": 2, "retention_days": 90}
    assert await _keys(factory) == ["inside"]


async def test_the_operator_window_is_honoured_not_the_default(factory, run_cleanup):
    await _workstream(factory, "three-days", closed_days_ago=3)
    await _workstream(factory, "one-day", closed_days_ago=1)
    result = await run_cleanup(retention_days=2)
    assert result["workstreams"] == 1
    assert result["retention_days"] == 2
    assert await _keys(factory) == ["one-day"]


async def test_one_sweep_takes_every_expired_workstream(factory, run_cleanup):
    for key in ("a", "b", "c"):
        await _workstream(factory, key, closed_days_ago=10)
    result = await run_cleanup(retention_days=1)
    assert (result["workstreams"], result["entries"]) == (3, 3)
    assert await _keys(factory) == []


async def test_open_and_retained_workstreams_are_never_swept(factory, run_cleanup):
    await _workstream(factory, "open")
    await _workstream(factory, "retained", closed_days_ago=400, retain=True)
    assert await run_cleanup(retention_days=1) == 0
    assert await _keys(factory) == ["open", "retained"]


async def test_the_sweep_passes_a_locked_workstream_and_erases_the_next(factory, run_cleanup):
    held_id = await _workstream(factory, "held", closed_days_ago=100)
    await _workstream(factory, "free", closed_days_ago=91)
    async with factory() as holder:
        await holder.execute(
            text("SELECT id FROM workstreams WHERE id = CAST(:id AS uuid) FOR UPDATE"),
            {"id": str(held_id)},
        )
        result = await asyncio.wait_for(run_cleanup(), timeout=10)
        await holder.rollback()
    assert result == {"workstreams": 1, "entries": 1, "retention_days": 90}
    assert await _keys(factory) == ["held"]


async def test_each_erase_is_journalled_by_the_job(factory, run_cleanup):
    ws_id = await _workstream(factory, "journalled", closed_days_ago=91)
    await run_cleanup()
    async with factory() as s:
        row = (await s.execute(
            text(
                "SELECT actor, payload FROM events WHERE event_type = 'workstream_purged' "
                "AND object_type = 'workstream' AND object_id = CAST(:w AS uuid)"
            ),
            {"w": str(ws_id)},
        )).one()
    assert row.actor == WORKLOG_CLEANUP_JOB_KEY
    assert row.payload == {"key": "journalled", "entries": 1, "retention_days": 90}


async def test_a_journal_failure_stops_the_sweep_and_keeps_the_workstream(factory, run_cleanup, monkeypatch):
    await _workstream(factory, "kept", closed_days_ago=91)

    async def writes_nothing(*args, **kwargs):
        return False

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await run_cleanup()
    assert await _keys(factory) == ["kept"]


async def test_a_journal_failure_mid_sweep_keeps_every_earlier_erase(factory, run_cleanup, monkeypatch):
    await _workstream(factory, "first", closed_days_ago=100)
    await _workstream(factory, "second", closed_days_ago=95)
    real = worklog.record_event
    calls = 0

    async def fails_on_the_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        return False if calls == 2 else await real(*args, **kwargs)

    monkeypatch.setattr(worklog, "record_event", fails_on_the_second)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await run_cleanup()
    assert await _keys(factory) == ["second"]


def test_the_job_is_registered_with_its_runner_and_schema():
    import ast
    from pathlib import Path

    tree = ast.parse((Path(__file__).resolve().parent.parent / "app" / "main.py").read_text())
    keywords = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Job":
            kw = {k.arg: k.value for k in node.keywords}
            key = kw.get("key")
            if isinstance(key, ast.Name) and key.id == "WORKLOG_CLEANUP_JOB_KEY":
                keywords = kw
                break

    assert keywords is not None, "worklog_cleanup is not wired at boot"
    assert isinstance(keywords["config_schema"], ast.Name)
    assert keywords["config_schema"].id == "WORKLOG_CLEANUP_CONFIG_SCHEMA"
    assert isinstance(keywords["default_cron"], ast.Name)
    assert keywords["default_cron"].id == "WORKLOG_CLEANUP_CRON"
    runner = keywords["runner"]
    assert isinstance(runner, ast.Call) and isinstance(runner.func, ast.Name)
    assert runner.func.id == "make_worklog_cleanup_runner"
    assert isinstance(keywords["min_interval_seconds"], ast.Constant)
    assert keywords["min_interval_seconds"].value == 3600
