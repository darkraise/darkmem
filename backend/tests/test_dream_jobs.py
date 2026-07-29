"""The Tier-C consolidation ("dreaming") job family umbrella (T2.08, doc 08 §5).

T2.08 lands the umbrella only — the registration shape, the per-job
configuration surface, and the guard that keeps every member off the hot
path (invariant 15). No family member's real work is implemented here; each
job is a `PlaceholderJobRunner` whose owning task (T2.09-T2.14, T2.53)
replaces it.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.services.dream_jobs import (
    ARTICLE_SYNTHESIS_JOB_KEY,
    CONTRADICTION_SCAN_JOB_KEY,
    DREAM_JOB_KEYS,
    DREAM_JOB_OWNERS,
    FACT_LIFT_JOB_KEY,
    MEMORY_DREAM_JOB_KEY,
    PlaceholderJobRunner,
    TOPIC_DETECTION_JOB_KEY,
    VERIFICATION_RECOMPUTE_JOB_KEY,
    register_dream_jobs,
)
from app.services.job_registry import JobBusyError, JobRegistry

BACKEND = Path(__file__).resolve().parent.parent


def _fresh_registry():
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    register_dream_jobs(registry)
    return registry, engine


# ── Done-when 1: each job independently scheduled, locked, configurable ──


def test_all_six_family_members_are_registered():
    assert set(DREAM_JOB_KEYS) == {
        VERIFICATION_RECOMPUTE_JOB_KEY,
        FACT_LIFT_JOB_KEY,
        CONTRADICTION_SCAN_JOB_KEY,
        MEMORY_DREAM_JOB_KEY,
        ARTICLE_SYNTHESIS_JOB_KEY,
        TOPIC_DETECTION_JOB_KEY,
    }
    assert len(DREAM_JOB_KEYS) == 6


@pytest.mark.asyncio
async def test_each_job_has_its_own_cron_floor_and_config_row():
    registry, engine = _fresh_registry()
    try:
        seen_crons: dict[str, str] = {}
        seen_floors: dict[str, int] = {}
        for key in DREAM_JOB_KEYS:
            job = registry.get(key)
            assert job is not None, f"{key} did not register"
            assert job.key == key
            # Own config row key: job:<key>, distinct per member.
            assert registry._config_key(key) == f"job:{key}"
            seen_crons[key] = job.default_cron
            seen_floors[key] = job.min_interval_seconds
        # Each member's cron and floor are independent values, not one
        # shared setting copy-pasted across the family.
        assert len(set(seen_crons.values())) > 1
        assert len(set(seen_floors.values())) > 1
        # Doc 08 §5's cadence table, spot-checked on the two non-LLM,
        # frequent members.
        assert registry.get(VERIFICATION_RECOMPUTE_JOB_KEY).min_interval_seconds == 30
        assert registry.get(FACT_LIFT_JOB_KEY).default_cron == "*/15 * * * *"
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_each_job_persists_config_under_its_own_row():
    registry, engine = _fresh_registry()
    try:
        for key in DREAM_JOB_KEYS:
            cfg = await registry.load_config(key)
            assert cfg.cron == registry.get(key).default_cron
    finally:
        await registry.stop_all()
        await engine.dispose()


# ── Done-when 1 (configurable) + test-plan point 2 ────────────────────────


@pytest.mark.asyncio
async def test_set_config_validates_against_its_own_schema_only():
    registry, engine = _fresh_registry()
    try:
        cfg = await registry.set_config(FACT_LIFT_JOB_KEY, {"batch_size": 7})
        assert cfg.config["batch_size"] == 7

        # A sibling's config is untouched by the write above.
        sibling = await registry.load_config(VERIFICATION_RECOMPUTE_JOB_KEY)
        assert sibling.config.get("batch_size", 100) == 100

        # Each job's schema is its own: an out-of-range value valid for one
        # job's schema is still validated against that same job's own bounds.
        with pytest.raises(ValueError):
            await registry.set_config(FACT_LIFT_JOB_KEY, {"batch_size": 999999})
        with pytest.raises(ValueError):
            await registry.set_config(FACT_LIFT_JOB_KEY, {"unknown_key": 1})
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_sibling_config_survives_a_neighbours_update():
    registry, engine = _fresh_registry()
    try:
        await registry.set_config(MEMORY_DREAM_JOB_KEY, {"batch_size": 3})
        await registry.set_config(CONTRADICTION_SCAN_JOB_KEY, {"batch_size": 4})
        assert (await registry.load_config(MEMORY_DREAM_JOB_KEY)).config["batch_size"] == 3
        assert (await registry.load_config(CONTRADICTION_SCAN_JOB_KEY)).config["batch_size"] == 4
    finally:
        await registry.stop_all()
        await engine.dispose()


# ── Done-when 1 (locked) + test-plan point 3 ──────────────────────────────


@pytest.mark.asyncio
async def test_each_job_has_its_own_lock_instance():
    registry, engine = _fresh_registry()
    try:
        locks = {registry.get(key).lock for key in DREAM_JOB_KEYS}
        assert len(locks) == 6, "every family member must hold a distinct asyncio.Lock"
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_holding_one_members_lock_does_not_block_a_siblings_trigger():
    registry, engine = _fresh_registry()
    try:
        held = registry.get(FACT_LIFT_JOB_KEY)
        await held.lock.acquire()
        try:
            # A sibling with an independent lock must trigger cleanly.
            cfg = await registry.trigger(VERIFICATION_RECOMPUTE_JOB_KEY)
            assert cfg.last_status == "ok"
        finally:
            held.lock.release()
    finally:
        await registry.stop_all()
        await engine.dispose()


# ── Done-when 2: trigger-while-locked returns 409, never queues ──────────


@pytest.mark.asyncio
async def test_trigger_while_locked_raises_busy_without_running():
    registry, engine = _fresh_registry()
    try:
        job = registry.get(CONTRADICTION_SCAN_JOB_KEY)
        await job.lock.acquire()
        try:
            with pytest.raises(JobBusyError):
                await registry.trigger(CONTRADICTION_SCAN_JOB_KEY)
        finally:
            job.lock.release()
        # Busy means "refused", not "queued" — nothing ran while the lock
        # was held, so last_run_at must still be unset after the refusal.
        cfg = await registry.load_config(CONTRADICTION_SCAN_JOB_KEY)
        assert cfg.last_run_at is None
        assert cfg.last_status is None
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.fixture
async def dream_family_client(client):
    """The real family registered on the live app, replacing the minimal
    repo_sync-only stub `client` installs, so the 409 assertion below exercises
    the actual route, not a hand-rolled registry."""
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    register_dream_jobs(registry)
    prev = app.state.job_registry
    app.state.job_registry = registry
    try:
        yield registry
    finally:
        await registry.stop_all()
        app.state.job_registry = prev
        await engine.dispose()


@pytest.mark.asyncio
async def test_trigger_route_returns_409_and_does_not_queue_a_run(
    dream_family_client, client, auth_headers,
):
    job = dream_family_client.get(MEMORY_DREAM_JOB_KEY)
    await job.lock.acquire()
    try:
        response = await client.post(
            f"/api/v1/jobs/{MEMORY_DREAM_JOB_KEY}/trigger", headers=auth_headers,
        )
        assert response.status_code == 409
    finally:
        job.lock.release()
    # No queued run fires once the lock frees — a queued implementation
    # would show a completed run here; a refusing one leaves the row untouched.
    await asyncio.sleep(0)
    cfg = await dream_family_client.load_config(MEMORY_DREAM_JOB_KEY)
    assert cfg.last_run_at is None
    assert cfg.last_status is None


# ── Done-when 3 + test-plan point 5: no Tier-A/B caller reaches a job ─────

_ALLOWED_DREAM_JOB_REFERRERS = {
    "app/services/dream_jobs.py",
    "app/main.py",
}


def _forbidden_dream_job_references(paths: list[Path], backend_root: Path) -> list[str]:
    """A forbidden reference is either an import from `app.services.dream_jobs`
    or a quoted literal naming one of the six family job keys, in any file
    outside the umbrella module and its one legitimate registration call site.

    Mirrors `tests/test_inert_objects.py`'s inert-purpose scan: a source
    scan that fails the build, not a convention a reviewer has to remember.
    """
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(backend_root))
        if rel in _ALLOWED_DREAM_JOB_REFERRERS:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "app.services.dream_jobs" in line or "from app.services import dream_jobs" in line:
                offenders.append(f"{rel}:{lineno}: {stripped}")
                continue
            for key in DREAM_JOB_KEYS:
                if f'"{key}"' in line or f"'{key}'" in line:
                    offenders.append(f"{rel}:{lineno}: {stripped}")
                    break
    return offenders


def _app_sources() -> list[Path]:
    return [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def test_no_app_code_reaches_a_family_job():
    offenders = _forbidden_dream_job_references(_app_sources(), BACKEND)
    assert not offenders, (
        "a Tier-A/B (or any non-umbrella) module reached a dream-job family "
        "member:\n" + "\n".join(offenders)
        + "\nReconciliation must stay off the hot path (invariant 15) — trigger "
          "it through JobRegistry's cron/manual-trigger surface, never inline."
    )


def test_guard_fails_when_a_forbidden_call_is_introduced(tmp_path):
    """Negative control: prove the scan actually catches a violation rather
    than vacuously passing. A capture-path-shaped file that imports the
    umbrella and calls one member inline must be flagged."""
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(
        "from app.services.dream_jobs import register_dream_jobs\n"
        "\n"
        "async def handle_capture(job_registry):\n"
        '    await job_registry.trigger("fact_lift")\n'
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "the guard must flag an inline call to a family job"
    assert any("fact_lift" in o for o in offenders)


# ── Done-when / test-plan point 6: placeholders are identifiable ─────────


@pytest.mark.asyncio
async def test_every_family_member_is_a_marked_placeholder():
    registry, engine = _fresh_registry()
    try:
        for key in DREAM_JOB_KEYS:
            job = registry.get(key)
            assert isinstance(job.runner, PlaceholderJobRunner), (
                f"{key}'s runner must stay a PlaceholderJobRunner until "
                f"{DREAM_JOB_OWNERS[key]} lands its real work"
            )
            assert job.runner.job_key == key
            assert job.runner.owner_task == DREAM_JOB_OWNERS[key]
            # A placeholder run is genuinely inert.
            await job.runner()
    finally:
        await registry.stop_all()
        await engine.dispose()


def test_placeholder_marker_is_not_a_shipped_runner_type():
    """A shipped runner is a plain coroutine function; a placeholder is the
    distinct `PlaceholderJobRunner` type. This is what a future task's real
    runner will stop being `isinstance`-true for — proving the marker is
    structural rather than a name a reviewer has to remember to check."""
    async def real_runner() -> None:
        return None

    assert not isinstance(real_runner, PlaceholderJobRunner)
    assert isinstance(PlaceholderJobRunner("x", "T9.99"), PlaceholderJobRunner)
