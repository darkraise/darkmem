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
    SHIPPED_DREAM_JOBS,
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


async def _drain_pending_tasks(before: set[asyncio.Task], *, timeout: float = 5.0) -> None:
    """Await whatever the wrapped call scheduled on this loop but did not
    itself await — e.g. a queue-on-busy regression's ``asyncio.create_task``
    — instead of guessing a fixed sleep window.

    A queued run only starts making progress once the caller's lock frees, and
    needs several loop turns of real DB I/O (lock acquire, config read, runner,
    config commit) to finish; checking state after a single ``sleep(0)`` yield
    always wins that race and observes the row before the queued write lands.
    Diffing ``asyncio.all_tasks()`` finds exactly what got scheduled and waits
    for exactly that, so detection does not depend on how long the write takes
    or on a guessed wall-clock margin. ``timeout`` is a safety net against a
    genuinely hung task, never the detection mechanism itself.
    """
    current = asyncio.current_task()
    spawned = [t for t in asyncio.all_tasks() if t not in before and t is not current]
    if spawned:
        await asyncio.wait(spawned, timeout=timeout)


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
async def test_each_job_has_its_own_cron_and_floor():
    # The config-row property (job:<key>, distinct per member) is proven by
    # persistence below (test_each_job_persists_config_under_its_own_row),
    # not by reaching into JobRegistry's private _config_key formatting here.
    registry, engine = _fresh_registry()
    try:
        seen_crons: dict[str, str] = {}
        seen_floors: dict[str, int] = {}
        for key in DREAM_JOB_KEYS:
            job = registry.get(key)
            assert job is not None, f"{key} did not register"
            assert job.key == key
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
        # contradiction_scan's schema is doc 08 §5.3's own two named fields,
        # not the generic batch_size the other five carry — a different
        # shape entirely, not just a different value.
        await registry.set_config(MEMORY_DREAM_JOB_KEY, {"batch_size": 3})
        await registry.set_config(
            CONTRADICTION_SCAN_JOB_KEY,
            {"contradiction_scan_batch": 4, "contradiction_candidate_top_k": 8},
        )
        assert (await registry.load_config(MEMORY_DREAM_JOB_KEY)).config["batch_size"] == 3
        cs_cfg = (await registry.load_config(CONTRADICTION_SCAN_JOB_KEY)).config
        assert cs_cfg["contradiction_scan_batch"] == 4
        assert cs_cfg["contradiction_candidate_top_k"] == 8
        assert "batch_size" not in cs_cfg
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
        before = set(asyncio.all_tasks())
        try:
            with pytest.raises(JobBusyError):
                await registry.trigger(CONTRADICTION_SCAN_JOB_KEY)
        finally:
            job.lock.release()
        # Busy means "refused", not "queued". A queue-on-busy regression
        # schedules its run via create_task before raising JobBusyError; that
        # task only starts making progress once the lock frees above, so
        # drain whatever trigger() left behind before reading state.
        await _drain_pending_tasks(before)
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
    """Proves the HTTP-level mapping and defense in depth: the route's own
    pre-check (``app/api/routes/jobs.py``'s ``if job.lock.locked(): raise
    HTTPException(409, ...)``) means a held lock never even reaches
    ``JobRegistry.trigger()`` on this path, so a request against a busy
    family job is refused before any run could be scheduled.

    The registry-internal busy path — the one a queue-on-busy regression in
    ``JobRegistry.trigger()`` itself would corrupt — is proven by
    ``test_trigger_while_locked_raises_busy_without_running`` above, which
    calls ``trigger()`` directly rather than through this route pre-check.
    """
    job = dream_family_client.get(MEMORY_DREAM_JOB_KEY)
    await job.lock.acquire()
    before = set(asyncio.all_tasks())
    try:
        response = await client.post(
            f"/api/v1/jobs/{MEMORY_DREAM_JOB_KEY}/trigger", headers=auth_headers,
        )
        assert response.status_code == 409
    finally:
        job.lock.release()
    await _drain_pending_tasks(before)
    cfg = await dream_family_client.load_config(MEMORY_DREAM_JOB_KEY)
    assert cfg.last_run_at is None
    assert cfg.last_status is None


# ── Done-when 3 + test-plan point 5: no Tier-A/B caller reaches a job ─────

# Whole files exempted from the scan entirely: the umbrella module itself,
# which necessarily names every key. Nothing else gets a blanket pass —
# app/main.py is scanned line-by-line like everything else (see
# _ALLOWED_DREAM_JOB_LINES below), so a hot-path call added anywhere else in
# main.py, outside its one legitimate registration call, still gets caught.
_ALLOWED_DREAM_JOB_FILES = {
    "app/services/dream_jobs.py",
}

# Exact stripped lines legitimate outside the umbrella module — today, only
# main.py's one import and one registration call in lifespan(). Keyed by
# file so a forbidden reference anywhere else in that same file still fails.
_ALLOWED_DREAM_JOB_LINES: dict[str, set[str]] = {
    "app/main.py": {
        "from app.services.dream_jobs import register_dream_jobs",
        "register_dream_jobs(job_registry)",
    },
}


# Modules that are legitimately imported by the umbrella but are shared
# infrastructure rather than a family job's body. Everything else the umbrella
# pulls out of `app.services` is a job implementation and inherits the scan.
_UMBRELLA_INFRASTRUCTURE = {"job_registry"}


def dream_job_implementation_modules() -> set[str]:
    """The modules holding a family job's real body, derived rather than listed.

    A shipped runner's work does not live in `dream_jobs.py` — the umbrella
    imports it — so scanning for `app.services.dream_jobs` alone stops catching
    a hot-path caller the moment the first member ships: importing the
    implementation module directly reaches the job just as effectively and
    names the umbrella nowhere. Reading the umbrella's own imports instead of
    keeping a hand-maintained list means the next member (T2.09, T2.11, T2.12,
    T2.53) is covered by the act of wiring it up, with nothing to remember.
    """
    umbrella = (BACKEND / "app" / "services" / "dream_jobs.py").read_text()
    modules: set[str] = set()
    for line in umbrella.splitlines():
        stripped = line.strip()
        prefix = "from app.services."
        if not stripped.startswith(prefix):
            continue
        module = stripped[len(prefix):].split()[0].split(".")[0]
        if module not in _UMBRELLA_INFRASTRUCTURE:
            modules.add(module)
    return modules


def _forbidden_dream_job_references(paths: list[Path], backend_root: Path) -> list[str]:
    """A forbidden reference is an import from `app.services.dream_jobs`, an
    import from any module holding a family job's real body, or a quoted literal
    naming one of the six family job keys — in any file outside the umbrella
    module, and on any line outside the one legitimate registration call site.

    Mirrors `tests/test_inert_objects.py`'s inert-purpose scan: a source
    scan that fails the build, not a convention a reviewer has to remember.
    """
    implementations = dream_job_implementation_modules()
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(backend_root))
        if rel in _ALLOWED_DREAM_JOB_FILES:
            continue
        allowed_lines = _ALLOWED_DREAM_JOB_LINES.get(rel, set())
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            forbidden = (
                "app.services.dream_jobs" in line
                or "from app.services import dream_jobs" in line
                or any(
                    f"app.services.{module}" in line
                    or f"from app.services import {module}" in line
                    for module in implementations
                )
                or any(f'"{key}"' in line or f"'{key}'" in line for key in DREAM_JOB_KEYS)
            )
            if forbidden and stripped not in allowed_lines:
                offenders.append(f"{rel}:{lineno}: {stripped}")
    return offenders


def _app_sources() -> list[Path]:
    return [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def test_no_app_code_reaches_a_family_job():
    paths = _app_sources()
    # A vacuous scan (e.g. BACKEND resolved to the wrong directory) would
    # pass by finding nothing to scan at all; this floor is well below the
    # real count (151 at the time of writing) but far above zero, so an
    # empty or near-empty scan fails loudly instead of silently passing.
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the source scan below "
        "would pass vacuously; check BACKEND / the glob path"
    )
    offenders = _forbidden_dream_job_references(paths, BACKEND)
    assert not offenders, (
        "a Tier-A/B (or any non-umbrella) module reached a dream-job family "
        "member:\n" + "\n".join(offenders)
        + "\nReconciliation must stay off the hot path (invariant 15) — trigger "
          "it through JobRegistry's cron/manual-trigger surface, never inline."
    )


def test_main_wires_the_family_at_boot():
    """Registrability is not the same as being wired at boot (I2): every
    registry-level test above builds its own `JobRegistry` via
    `register_dream_jobs`, so none of them would notice if `app/main.py`
    stopped calling it — the family would silently stop existing in the
    running app while the whole suite stayed green. This asserts the one
    legitimate call site the guard above allowlists actually exists."""
    main_src = (BACKEND / "app" / "main.py").read_text()
    stripped_lines = {line.strip() for line in main_src.splitlines()}
    for expected in _ALLOWED_DREAM_JOB_LINES["app/main.py"]:
        assert expected in stripped_lines, (
            f"app/main.py no longer wires the dream-job family at boot: "
            f"missing {expected!r}"
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


def test_the_scan_covers_a_shipped_jobs_implementation_module(tmp_path):
    """A shipped runner's body does not live in the umbrella, so reaching the
    job no longer requires naming `dream_jobs` at all — importing the
    implementation module directly is the same hot-path violation with none of
    the old scan's fingerprints. Negative control for that arm."""
    implementations = dream_job_implementation_modules()
    assert implementations, (
        "the umbrella imports no implementation module — either nothing has "
        "shipped, or the derivation below has stopped finding them and the "
        "scan would pass vacuously"
    )
    module = sorted(implementations)[0]

    offending = tmp_path / "fake_retrieval_service.py"
    offending.write_text(
        f"from app.services.{module} import run_lift\n"
        "\n"
        "async def search(session):\n"
        "    await run_lift(session)\n"
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, (
        f"the guard must flag a hot-path import of app.services.{module}, "
        "which is a family job's real body"
    )


def test_every_shipped_member_has_its_body_covered_by_the_scan():
    """The derivation is what makes the guard self-maintaining, so pin that it
    actually resolves the shipped members rather than returning something
    incidental."""
    implementations = dream_job_implementation_modules()
    assert "fact_lift" in implementations
    assert "job_registry" not in implementations, (
        "shared infrastructure must stay out, or every module in the tree "
        "that schedules anything would read as a violation"
    )


# ── Done-when / test-plan point 6: placeholders are identifiable ─────────


@pytest.mark.asyncio
async def test_unshipped_family_members_are_marked_placeholders():
    registry, engine = _fresh_registry()
    try:
        for key in DREAM_JOB_KEYS:
            if key in SHIPPED_DREAM_JOBS:
                continue
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


@pytest.mark.asyncio
async def test_shipped_family_members_no_longer_wear_the_placeholder_marker():
    """The inverse direction, and the one that catches a regression: a job
    whose owning task has landed must never be `isinstance`-true for the
    marker again. Without this, reverting a shipped runner to a placeholder
    would leave the whole suite green while the job silently stopped working."""
    assert SHIPPED_DREAM_JOBS, "at least one family member has shipped"
    assert SHIPPED_DREAM_JOBS <= set(DREAM_JOB_KEYS)
    registry, engine = _fresh_registry()
    try:
        for key in SHIPPED_DREAM_JOBS:
            job = registry.get(key)
            assert not isinstance(job.runner, PlaceholderJobRunner), (
                f"{key} is listed as shipped but still carries the "
                f"PlaceholderJobRunner marker"
            )
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
