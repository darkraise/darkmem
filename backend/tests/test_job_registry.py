"""Unit tests for the cron parsing helpers on JobRegistry."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.services.job_registry import (
    FieldDescriptor,
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
    row = cfg.to_row()
    assert set(row) == {"enabled", "cron", "config"}
    restored = JobConfig.from_dict(row, min_interval_seconds=30)
    assert restored.enabled is True
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 30


def test_job_config_from_dict_supplies_defaults():
    restored = JobConfig.from_dict({}, min_interval_seconds=1)
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 1


def test_job_config_round_trips_config_dict():
    from app.services.job_registry import JobConfig

    cfg = JobConfig(enabled=True, cron="*/5 * * * *", min_interval_seconds=1,
                    config={"batch_size": 17})
    assert cfg.to_dict()["config"] == {"batch_size": 17}
    assert JobConfig.from_dict(cfg.to_row(), min_interval_seconds=1).config == {"batch_size": 17}


def test_job_config_from_dict_defaults_config_to_empty():
    from app.services.job_registry import JobConfig

    cfg = JobConfig.from_dict({"enabled": True, "cron": "*/5 * * * *"},
                              min_interval_seconds=1)
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
async def test_every_run_records_a_job_runs_row(setup_database):
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
                "SELECT outcome, detail FROM job_runs WHERE job_key = 'journalled_job'"
            ))).all()
        assert len(rows) == 1, "a completed run must leave exactly one row"
        assert rows[0][0] == "ok"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_failing_run_records_the_error_outcome(setup_database):
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
                "SELECT outcome, error FROM job_runs WHERE job_key = 'failing_job'"
            ))).all()
        assert len(rows) == 1
        assert rows[0][0] == "error"
        # The reason has to survive: an outcome with no error is a run that
        # failed for no stated reason.
        assert "exploded" in rows[0][1]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_runner_reporting_no_work_records_nothing(setup_database):
    """The no-op rule. `buffer_flush` polls an empty queue every five seconds
    and `code_enrichment` every ten; together they were 94% of the rows, all
    of them saying "ok, nothing to do" into a table nothing could prune."""
    from sqlalchemy import text as sa_text
    from app.services.job_registry import Job, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _idle():
        return 0

    reg.register(Job(key="idle_reporter", display_name="I", description="d",
                     default_cron="*/5 * * * * *", min_interval_seconds=1,
                     runner=_idle))
    try:
        await reg._run_once("idle_reporter")
        async with factory() as session:
            n = (await session.execute(sa_text(
                "SELECT count(*) FROM job_runs WHERE job_key = 'idle_reporter'"
            ))).scalar()
        assert n == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_runner_reporting_work_records_its_summary(setup_database):
    from sqlalchemy import text as sa_text
    from app.services.job_registry import Job, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _busy():
        return {"flushed": 7}

    reg.register(Job(key="busy_reporter", display_name="B", description="d",
                     default_cron="*/5 * * * * *", min_interval_seconds=1,
                     runner=_busy))
    try:
        await reg._run_once("busy_reporter")
        async with factory() as session:
            row = (await session.execute(sa_text(
                "SELECT detail FROM job_runs WHERE job_key = 'busy_reporter'"
            ))).first()
        assert row is not None and row[0] == {"flushed": 7}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_failing_no_op_is_still_recorded(setup_database):
    """A run that broke is the one row nobody can afford to have suppressed,
    whatever it claimed to have done."""
    from sqlalchemy import text as sa_text
    from app.services.job_registry import Job, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _broken():
        raise RuntimeError("nope")

    reg.register(Job(key="broken_reporter", display_name="B", description="d",
                     default_cron="*/5 * * * * *", min_interval_seconds=1,
                     runner=_broken))
    try:
        await reg._run_once("broken_reporter")
        async with factory() as session:
            n = (await session.execute(sa_text(
                "SELECT count(*) FROM job_runs WHERE job_key = 'broken_reporter'"
            ))).scalar()
        assert n == 1
    finally:
        await engine.dispose()


# ── the paginated history door ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_runs_endpoint_paginates_newest_first(client, auth_headers, session):
    """`total` is the unpaginated count, so a reader can tell "page 1 of many"
    from "that is everything" — which the previous client-side filter over a
    shared journal could not."""
    from datetime import timedelta
    from app.models.job_run import JobRun

    base = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    for i in range(5):
        session.add(JobRun(
            job_key="repo_sync", outcome="ok",
            started_at=base + timedelta(minutes=i),
            duration_seconds=0.1 * i, detail={"i": i},
        ))
    await session.commit()

    r = await client.get("/api/v1/jobs/repo_sync/runs?limit=2", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    # Newest first.
    assert body["items"][0]["detail"]["i"] == 4
    assert body["items"][1]["detail"]["i"] == 3

    page2 = (await client.get(
        "/api/v1/jobs/repo_sync/runs?limit=2&offset=2", headers=auth_headers
    )).json()
    assert page2["items"][0]["detail"]["i"] == 2
    assert page2["total"] == 5


@pytest.mark.asyncio
async def test_runs_endpoint_404s_an_unknown_job(client, auth_headers):
    r = await client.get("/api/v1/jobs/not_a_job/runs", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_a_repeating_failure_notifies_once_until_its_error_changes(
    setup_database, monkeypatch,
):
    """An outage fails the same job the same way on every tick. One message
    says so; a message per tick buries it, and a job on a five-second cron
    would send seventeen thousand a day."""
    import app.services.notifications as notif
    from app.services.job_registry import Job, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)
    sent: list[str | None] = []
    failure = ["embedder unreachable"]

    async def _spy(session_factory, *, job_key, error, duration_seconds):
        sent.append(error)

    async def _boom():
        raise RuntimeError(failure[0])

    monkeypatch.setattr(notif, "notify_job_failure", _spy)
    reg.register(Job(key="repeating_failure", display_name="R", description="d",
                     default_cron="*/5 * * * *", min_interval_seconds=1,
                     runner=_boom))
    try:
        await reg._run_once("repeating_failure")
        await reg._run_once("repeating_failure")
        assert sent == ["embedder unreachable"]

        failure[0] = "disk full"
        await reg._run_once("repeating_failure")
        assert sent == ["embedder unreachable", "disk full"]
    finally:
        await engine.dispose()


# ── run state, floors and run records ────────────────────────────────


def _committed_registry(*jobs):
    from app.services.job_registry import JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)
    for job in jobs:
        reg.register(job)
    return reg, factory, engine


def _job(key, runner=None, *, floor=1):
    async def _noop():
        return None

    return Job(key=key, display_name=key, description="d", default_cron="*/5 * * * *",
               min_interval_seconds=floor, runner=runner or _noop)


def _key(prefix):
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def _store_row(factory, key, value):
    from app.services.config import patch_config_row

    async with factory() as session:
        await patch_config_row(session, f"job:{key}", lambda _: value)


async def _row(factory, key):
    from sqlalchemy import text as sa_text

    async with factory() as session:
        return (await session.execute(
            sa_text("SELECT value FROM config WHERE key = :k"), {"k": f"job:{key}"},
        )).scalar_one_or_none()


@pytest.mark.asyncio
async def test_code_floor_applies_to_a_stored_row(setup_database):
    key = _key("floor")
    reg, factory, engine = _committed_registry(_job(key, floor=30))
    try:
        await _store_row(factory, key, {
            "enabled": True, "cron": "* * * * * *", "min_interval_seconds": 5,
        })
        cfg = await reg.load_config(key)
        assert cfg.min_interval_seconds == 30
        delta = next_fire_delta_seconds(
            cfg.cron, datetime.now(timezone.utc), floor=cfg.min_interval_seconds,
        )
        assert delta >= 30
        [item] = [i for i in await reg.list_with_config() if i["key"] == key]
        assert item["min_interval_seconds"] == 30
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_disable_answers_while_the_job_runs(client, auth_headers):
    import asyncio

    from app.main import app

    key = _key("busy")
    entered, release = asyncio.Event(), asyncio.Event()

    async def _held():
        entered.set()
        await release.wait()

    registry = app.state.job_registry
    job = _job(key, _held)
    job.config_schema = [FieldDescriptor(key="batch_size", label="B", default=5, min=1, max=100)]
    registry.register(job)
    try:
        run = asyncio.create_task(registry._run_once(key))
        await asyncio.wait_for(entered.wait(), 5)
        disabled = await asyncio.wait_for(client.put(
            f"/api/v1/jobs/{key}", json={"enabled": False}, headers=auth_headers,
        ), 1)
        assert disabled.status_code == 200, disabled.text
        configured = await asyncio.wait_for(client.put(
            f"/api/v1/jobs/{key}/config", json={"config": {"batch_size": 9}},
            headers=auth_headers,
        ), 1)
        assert configured.status_code == 200, configured.text
        busy = await client.post(f"/api/v1/jobs/{key}/trigger", headers=auth_headers)
        assert busy.status_code == 409
        release.set()
        await asyncio.wait_for(run, 5)
        stored = await _row(registry.session_factory, key)
        assert stored["enabled"] is False
        assert stored["config"] == {"batch_size": 9}
    finally:
        release.set()
        registry._jobs.pop(key, None)


@pytest.mark.asyncio
async def test_last_run_comes_from_job_runs(setup_database):
    from types import SimpleNamespace

    from sqlalchemy import text as sa_text

    from app.services.job_runners import make_job_run_cleanup_runner

    key, noise = _key("old_run"), _key("noise")
    reg, factory, engine = _committed_registry(_job(key))

    class _Cleanup:
        async def load_config(self, _key):
            return JobConfig(enabled=True, cron="0 * * * *", min_interval_seconds=1,
                             config={"max_rows": 1000})

    try:
        async with factory() as session:
            await session.execute(sa_text(
                "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds, "
                "error, detail) VALUES (:k, 'error', now() - interval '1 day', 1, "
                "'it broke', '{}')"
            ), {"k": key})
            await session.execute(sa_text(
                "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds, detail) "
                "SELECT :k, 'ok', now() - make_interval(secs => n), 0, '{}' "
                "FROM generate_series(1, 5000) AS n"
            ), {"k": noise})
            await session.commit()
        cleanup = make_job_run_cleanup_runner(
            SimpleNamespace(state=SimpleNamespace(job_registry=_Cleanup())), factory,
        )
        assert (await cleanup())["deleted"] > 0
        [item] = [i for i in await reg.list_with_config() if i["key"] == key]
        assert item["last_status"] == "error"
        assert item["last_error"] == "it broke"
        assert item["last_run_at"] is not None
    finally:
        async with factory() as session:
            await session.execute(
                sa_text("DELETE FROM job_runs WHERE job_key IN (:a, :b)"), {"a": key, "b": noise},
            )
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_tick_writes_no_config_row(setup_database):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    key = _key("tick")
    reg, factory, engine = _committed_registry(_job(key))
    written: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        head = statement.lstrip().upper()
        if head.startswith(("INSERT INTO CONFIG", "UPDATE CONFIG")):
            written.append(statement)

    event.listen(Engine, "before_cursor_execute", capture)
    try:
        for _ in range(3):
            await reg._run_once(key)
    finally:
        event.remove(Engine, "before_cursor_execute", capture)
        await engine.dispose()
    assert written == []


@pytest.mark.asyncio
async def test_stored_last_keys_are_ignored_and_dropped(setup_database):
    key = _key("legacy_row")
    reg, factory, engine = _committed_registry(_job(key))
    try:
        await _store_row(factory, key, {
            "enabled": True, "cron": "*/5 * * * *", "min_interval_seconds": 5,
            "last_run_at": "2020-01-01T00:00:00+00:00", "last_status": "error",
            "last_error": "from an older build", "config": {},
        })
        await reg._run_once(key)
        fresh, _, fresh_engine = _committed_registry(_job(key))
        try:
            cfg = await fresh.load_config(key)
            assert cfg.last_status == "ok"
            assert cfg.last_error is None
            assert cfg.last_run_at.year > 2020
            await fresh.update_config(key, cron="*/7 * * * *")
        finally:
            await fresh_engine.dispose()
        assert await _row(factory, key) == {
            "enabled": True, "cron": "*/7 * * * *", "config": {},
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failure_notification_dedupes_on_the_previous_run(setup_database, monkeypatch):
    import app.services.notifications as notif

    key = _key("dedupe")
    sent: list[str | None] = []
    failure = ["embedder unreachable"]

    async def _spy(session_factory, *, job_key, error, duration_seconds):
        sent.append(error)

    async def _boom():
        raise RuntimeError(failure[0])

    monkeypatch.setattr(notif, "notify_job_failure", _spy)
    first, _, first_engine = _committed_registry(_job(key, _boom))
    try:
        await first._run_once(key)
    finally:
        await first_engine.dispose()
    # A restarted process reads the previous run from `job_runs`.
    second, _, second_engine = _committed_registry(_job(key, _boom))
    try:
        await second._run_once(key)
        assert sent == ["embedder unreachable"]
        failure[0] = "disk full"
        await second._run_once(key)
        assert sent == ["embedder unreachable", "disk full"]
    finally:
        await second_engine.dispose()


@pytest.mark.asyncio
async def test_manual_trigger_is_recorded(setup_database):
    from sqlalchemy import text as sa_text

    key = _key("manual")
    reg, factory, engine = _committed_registry(_job(key))
    try:
        await reg.trigger(key)
        await reg._run_once(key)
        async with factory() as session:
            triggers = (await session.execute(sa_text(
                "SELECT trigger FROM job_runs WHERE job_key = :k ORDER BY started_at"
            ), {"k": key})).scalars().all()
        assert triggers == ["manual", "schedule"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_idle_cleanup_journals_nothing(setup_database):
    from sqlalchemy import text as sa_text

    from app.services import job_runners

    reg, factory, engine = _committed_registry()

    async def journalled(operation):
        async with factory() as session:
            return (await session.execute(sa_text(
                "SELECT payload FROM events WHERE event_type = 'maintenance_run' "
                "AND payload->>'operation' = :op ORDER BY created_at, id"
            ), {"op": operation})).scalars().all()

    makers = {
        "graph_orphan_cleanup": job_runners.make_graph_orphan_cleanup_runner,
        "tag_orphan_cleanup": job_runners.make_tag_orphan_cleanup_runner,
        "expired_memory_cleanup": job_runners.make_expired_memory_cleanup_runner,
    }
    try:
        for operation, make in makers.items():
            key = _key(operation)
            reg.register(_job(key, make(factory)))
            await reg._run_once(key)
            before = await journalled(operation)
            await reg._run_once(key)
            assert await journalled(operation) == before, operation
            async with factory() as session:
                detail = (await session.execute(sa_text(
                    "SELECT detail FROM job_runs WHERE job_key = :k "
                    "ORDER BY started_at DESC, id DESC LIMIT 1"
                ), {"k": key})).scalar_one()
            assert detail and not any(detail.values()), (operation, detail)

        async with factory() as session:
            await session.execute(
                sa_text("INSERT INTO tags (name) VALUES (:n)"), {"n": _key("orphan-tag")},
            )
            await session.commit()
        before = await journalled("tag_orphan_cleanup")
        await job_runners.make_tag_orphan_cleanup_runner(factory)()
        after = await journalled("tag_orphan_cleanup")
        assert len(after) == len(before) + 1
        assert after[-1]["detail"]["tags_removed"] >= 1
    finally:
        await engine.dispose()
