"""Unit tests for the cron parsing helpers on JobRegistry."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.job_registry import (
    Job,
    JobConfig,
    is_valid_cron,
    next_fire_delta_seconds,
)


def _schema_registry(key: str = "cfgjob"):
    from app.services.job_registry import Job, JobRegistry, FieldDescriptor
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _noop():
        return None

    reg.register(Job(
        key=key, display_name="Cfg", description="d",
        default_cron="*/5 * * * *", min_interval_seconds=1, runner=_noop,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    ))
    return reg, engine


@pytest.mark.asyncio
async def test_set_config_merges_and_validates():
    reg, engine = _schema_registry("cfg_set")
    try:
        cfg = await reg.set_config("cfg_set", {"batch_size": 20})
        assert cfg.config["batch_size"] == 20
        with pytest.raises(ValueError):
            await reg.set_config("cfg_set", {"nope": 1})
        with pytest.raises(ValueError):
            await reg.set_config("cfg_set", {"batch_size": 999})
    finally:
        await reg.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_config_survives_trigger_and_toggle():
    reg, engine = _schema_registry("cfg_survive")
    try:
        await reg.set_config("cfg_survive", {"batch_size": 33})
        await reg.trigger("cfg_survive")
        assert (await reg.load_config("cfg_survive")).config["batch_size"] == 33
        await reg.update_config("cfg_survive", enabled=False)
        assert (await reg.load_config("cfg_survive")).config["batch_size"] == 33
        await reg.update_config("cfg_survive", cron="*/2 * * * *")
        assert (await reg.load_config("cfg_survive")).config["batch_size"] == 33
    finally:
        await reg.stop_all()
        await engine.dispose()


def test_is_valid_cron_accepts_five_field():
    assert is_valid_cron("*/5 * * * *") is True
    assert is_valid_cron("0 0 * * *") is True
    assert is_valid_cron("0 9-17 * * 1-5") is True


def test_is_valid_cron_accepts_six_field_with_seconds():
    assert is_valid_cron("*/10 * * * * *") is True
    assert is_valid_cron("0 0 0 * * *") is True


def test_is_valid_cron_rejects_garbage():
    assert is_valid_cron("not a cron") is False
    assert is_valid_cron("") is False
    assert is_valid_cron("60 * * * *") is False  # minute > 59


def test_next_fire_delta_respects_floor():
    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("*/1 * * * * *", now, floor=10)
    assert delta >= 10


def test_next_fire_delta_minute_precision():
    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("*/5 * * * *", now, floor=1)
    assert 0 < delta <= 300


def test_next_fire_delta_hourly():
    now = datetime(2026, 5, 3, 12, 30, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("0 * * * *", now, floor=1)
    assert 1750 <= delta <= 1850


def test_job_config_round_trip():
    cfg = JobConfig(
        enabled=True,
        cron="*/5 * * * *",
        min_interval_seconds=30,
    )
    serialised = cfg.to_dict()
    restored = JobConfig.from_dict(serialised)
    assert restored.enabled is True
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 30


def test_job_config_from_dict_supplies_defaults():
    restored = JobConfig.from_dict({})
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 1


def test_job_config_round_trips_config_dict():
    from app.services.job_registry import JobConfig

    cfg = JobConfig(enabled=True, cron="*/5 * * * *", min_interval_seconds=1,
                    config={"batch_size": 17})
    assert cfg.to_dict()["config"] == {"batch_size": 17}
    assert JobConfig.from_dict(cfg.to_dict()).config == {"batch_size": 17}


def test_job_config_from_dict_defaults_config_to_empty():
    from app.services.job_registry import JobConfig

    cfg = JobConfig.from_dict({"enabled": True, "cron": "*/5 * * * *",
                               "min_interval_seconds": 1})
    assert cfg.config == {}


def test_job_default_config_from_schema():
    from app.services.job_registry import Job, FieldDescriptor

    async def _noop():
        return None

    job = Job(
        key="x", display_name="X", description="d",
        default_cron="*/5 * * * *", min_interval_seconds=1, runner=_noop,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    )
    assert job.default_config == {"batch_size": 5}
    assert job.config_schema[0].type == "int"


@pytest.mark.asyncio
async def test_list_with_config_emits_schema_and_merged_config():
    # Distinct key so a row committed by an earlier test cannot shadow the
    # "no saved row -> default applied" assertion below.
    reg, engine = _schema_registry("cfg_list")
    try:
        items = await reg.list_with_config()
        item = next(i for i in items if i["key"] == "cfg_list")
        assert item["config_schema"][0]["key"] == "batch_size"
        assert item["config"] == {"batch_size": 5}
        await reg.set_config("cfg_list", {"batch_size": 42})
        item = next(i for i in (await reg.list_with_config()) if i["key"] == "cfg_list")
        assert item["config"] == {"batch_size": 42}
    finally:
        await reg.stop_all()
        await engine.dispose()


def test_job_register_rejects_invalid_default_cron():
    from app.services.job_registry import JobRegistry

    async def _noop():
        return None

    registry = JobRegistry(session_factory=lambda: None)  # session unused for this path
    with pytest.raises(ValueError, match="not a valid"):
        registry.register(Job(
            key="bad",
            display_name="Bad",
            description="",
            default_cron="garbage",
            min_interval_seconds=1,
            runner=_noop,
        ))


# ── `running` means a run is in progress, not "the scheduler is alive" ──


@pytest.mark.asyncio
async def test_running_is_false_for_a_scheduled_but_idle_job():
    """`job.task` holds the *scheduling loop*, which is alive for the whole
    process once `start()` runs — so deriving `running` from it reported every
    registered job as running forever. The UI disables Trigger while a job
    runs, which made all twenty-one controls dead on a completely idle
    instance. The per-job lock is the authoritative signal, and is already
    what the trigger route's 409 branch consults.
    """
    import asyncio

    reg, engine = _schema_registry("idle_job")
    try:
        job = reg._jobs["idle_job"]
        # Stand in for the scheduling loop without starting the real one.
        job.task = asyncio.create_task(asyncio.sleep(30))
        try:
            items = await reg.list_with_config()
            item = next(i for i in items if i["key"] == "idle_job")
            assert item["running"] is False, (
                "a live scheduling loop is not a run in progress"
            )
        finally:
            job.task.cancel()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_running_is_true_while_the_job_lock_is_held():
    reg, engine = _schema_registry("busy_job")
    try:
        job = reg._jobs["busy_job"]
        async with job.lock:
            items = await reg.list_with_config()
            item = next(i for i in items if i["key"] == "busy_job")
            assert item["running"] is True
    finally:
        await engine.dispose()


# ── every run is journalled, not just the three that journal themselves ──


@pytest.mark.asyncio
async def test_every_run_journals_a_job_run_row(setup_database):
    """Only the three cleanup runners called `record_maintenance_run`, so the
    other eighteen jobs ran and finished leaving no trace a reader could find
    — the run history dialog was empty for them by construction, not because
    they had never run.
    """
    from sqlalchemy import text as sa_text

    reg, engine = _schema_registry("journalled_job")
    try:
        await reg._run_once("journalled_job")
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            rows = (await session.execute(sa_text(
                "SELECT payload FROM events WHERE event_type = 'job_run' "
                "AND payload->>'job' = 'journalled_job'"
            ))).all()
        assert len(rows) == 1, "a completed run must leave exactly one row"
        assert rows[0][0]["outcome"] == "ok"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_failing_run_journals_the_error_outcome(setup_database):
    from sqlalchemy import text as sa_text
    from app.services.job_registry import Job, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _boom():
        raise RuntimeError("runner exploded")

    reg.register(Job(key="failing_job", display_name="F", description="d",
                     default_cron="*/5 * * * *", min_interval_seconds=1,
                     runner=_boom))
    try:
        await reg._run_once("failing_job")
        async with factory() as session:
            rows = (await session.execute(sa_text(
                "SELECT payload FROM events WHERE event_type = 'job_run' "
                "AND payload->>'job' = 'failing_job'"
            ))).all()
        assert len(rows) == 1
        assert rows[0][0]["outcome"] == "error"
        # The reason has to survive: an outcome with no error is a run that
        # failed for no stated reason.
        assert "exploded" in rows[0][0]["detail"]["error"]
    finally:
        await engine.dispose()
