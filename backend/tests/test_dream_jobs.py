"""The Tier-C consolidation ("dreaming") job family umbrella (T2.08, doc 08 §5).

T2.08 lands the umbrella only — the registration shape, the per-job
configuration surface, and the guard that keeps every member off the hot
path (invariant 15). No family member's real work is implemented here; each
job is a `PlaceholderJobRunner` whose owning task (T2.09-T2.14, T2.53)
replaces it.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.services.memory_community_detection import (
    DetectionOutcome,
    TOPIC_DETECTION_CONFIG_SCHEMA,
)
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

from tests._reachability_scan import (
    ReachabilityRules,
    app_sources,
    find_forbidden_reach,
    service_modules_imported_by,
)

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
# app/main.py is scanned like everything else, exempted only at the two
# specific nodes _main_py_exempt_node_ids resolves below, so a hot-path call
# added anywhere else in main.py, outside its one legitimate registration
# site, still gets caught.
_ALLOWED_DREAM_JOB_FILES = {
    "app/services/dream_jobs.py",
}


def _main_py_exempt_node_ids(rel: str, tree: ast.Module) -> set[int]:
    """main.py's one legitimate wiring, found by structural role rather than
    by text — the umbrella import and its single registration call, both
    direct statements of `lifespan`.

    T2.67 replaces the pre-existing exact-stripped-line-text allowlist with
    this. Text matching has a real defect a formatter can trigger by
    accident: two occurrences of the identical line — the real one inside
    `lifespan`, and a second, illegitimate copy pasted in somewhere else in
    the same file — render as the same string and would both have been
    silently exempted. Matched by structural role instead — an ImportFrom
    or Call node of a specific shape, found only inside the `lifespan`
    function — a textually-identical duplicate outside that scope is not
    swept in alongside the real node
    (`test_a_duplicate_registration_outside_lifespan_is_still_flagged`
    proves it).

    **The `Call` arm exempts nothing for *this* call, even though `ast.Call`
    nodes became flaggable in general once the loader-call route landed
    (`_reachability_scan._resolve_relative_loader_call`).** That route only
    fires for a `Call` to `import_module`/`__import__` shaped with a
    relative literal name and a literal `package=`; `register_dream_jobs(
    job_registry, lambda: getattr(app.state, "llm", None))` matches neither
    the function name nor the argument shape, so it was never reachable by
    any route before the loader-call route existed and still is not after.
    Collecting its id here is therefore still a no-op for suppression on
    this specific node, not because no route can ever flag a `Call` (that
    claim is no longer true in general) but because this particular call
    doesn't have the shape any route checks for. It is collected because
    `test_main_wires_the_family_at_boot` reuses this exact same structural
    walk as its "is the family actually wired at boot" presence witness,
    and duplicating the walk in a second function would risk the two
    drifting out of sync with each other over time.
    """
    if rel != "app/main.py":
        return set()
    exempt: set[int] = set()
    lifespan = next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan"
        ),
        None,
    )
    if lifespan is None:
        return exempt
    for node in ast.walk(lifespan):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module == "app.services.dream_jobs"
            and {alias.name for alias in node.names} == {"register_dream_jobs"}
        ):
            exempt.add(id(node))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "register_dream_jobs"
        ):
            exempt.add(id(node))
    return exempt


# Modules that are legitimately imported by the umbrella but are shared
# infrastructure rather than a family job's body. Everything else the umbrella
# pulls out of `app.services` is a job implementation and inherits the scan.
# This is the escape valve for the one-hop derivation below: a future shared
# module a job body needs to expose to outside callers (T2.13's
# `dream_journal.py`, shared between `memory_dream` and its undo service) is
# added here, not solved by making the derivation transitive.
_UMBRELLA_INFRASTRUCTURE = {"job_registry"}


def dream_job_implementation_modules() -> set[str]:
    """The modules holding a family job's real body, derived rather than listed.

    A shipped runner's work does not live in `dream_jobs.py` — the umbrella
    imports it — so scanning for `app.services.dream_jobs` alone stops catching
    a hot-path caller the moment the first member ships: importing the
    implementation module directly reaches the job just as effectively and
    names the umbrella nowhere. Reading the umbrella's own imports instead of
    keeping a hand-maintained list means the next member (T2.09, T2.11, T2.12,
    T2.53) is covered by the act of wiring it up, with nothing to remember —
    a job that is not reachable from the umbrella is not wired at all.

    **This derivation is deliberately ONE HOP — `dream_jobs.py`'s own direct
    imports, minus `_UMBRELLA_INFRASTRUCTURE`, never a transitive closure —
    and that is a contract other tasks depend on, not an implementation
    detail free to "improve" into a full import-graph walk.** A transitive
    version would forbid every module a job body imports too: T2.12 built
    `app/repositories/memory_relations.py` for T2.16/T2.17 to import
    specifically because repositories sit outside `app.services.*` and
    `service_modules_imported_by` cannot see them — a second shield, but one
    that only works because the derivation is shallow. T2.13's undo service
    needs to share a constant with `memory_dream` through a neutral
    `app/services/dream_journal.py` that *both* import; a transitive walk
    would fold `dream_journal` into the forbidden set the moment
    `memory_dream` imports it, and `dream_undo` importing the same module
    would fail the build, taking that layout down with it. If a future job
    body needs to import a genuinely shared module that must stay reachable
    from outside the family, the fix is to add it to
    `_UMBRELLA_INFRASTRUCTURE` (exactly the category that constant exists
    for), never to widen this function into a transitive walk.
    """
    umbrella = (BACKEND / "app" / "services" / "dream_jobs.py").read_text()
    return service_modules_imported_by(umbrella) - _UMBRELLA_INFRASTRUCTURE


def _dream_job_rules() -> ReachabilityRules:
    """The family scan's vocabulary, all on the shared AST walk.

    Module route: `app.services.dream_jobs` (the umbrella) and every module
    `dream_job_implementation_modules()` derives (a shipped member's real
    body) — matched against parsed import statements, and, since T2.67's
    Critical fix, against any `str`/`bytes` constant containing one of
    these dotted paths at an identifier boundary (`exec("import
    app.services.fact_lift")`, a `bytes` literal decoded before use, a
    loader-spec string). Attribute route: the same modules' bare basenames,
    closing T2.18's residual for this scan too — `from app import
    services; services.fact_lift.run_lift(...)` names no forbidden module
    in any import statement. Literal route (exact-match half): the six job
    keys (the registry-trigger vocabulary, `job_registry.trigger("fact_
    lift")`) plus the same bare basenames the attribute route uses, so
    `getattr(services, "fact_lift")` is caught by the same literal it would
    have to spell out. The bare names stay exact-match only — see
    `_reachability_scan.ReachabilityRules`'s docstring for why a substring
    check over bare names would flag ordinary prose instead of a real
    reach.
    """
    implementations = dream_job_implementation_modules()
    modules = {"app.services.dream_jobs"} | {
        f"app.services.{module}" for module in implementations
    }
    attrs = {"dream_jobs"} | implementations
    literals = set(DREAM_JOB_KEYS) | attrs
    return ReachabilityRules(
        forbidden_modules=frozenset(modules),
        forbidden_attrs=frozenset(attrs),
        forbidden_literals=frozenset(literals),
    )


def _forbidden_dream_job_references(paths: list[Path], backend_root: Path) -> list[str]:
    """A forbidden reference is an import from `app.services.dream_jobs`, an
    import from (or attribute reach into) any module holding a family job's
    real body, or a literal naming one of the six family job keys — in any
    file outside the umbrella module, and at any node outside the one
    legitimate registration site `_main_py_exempt_node_ids` resolves.

    Mirrors `tests/test_inert_objects.py`'s inert-purpose scan: a source
    scan that fails the build, not a convention a reviewer has to remember.
    """
    return find_forbidden_reach(
        paths,
        backend_root,
        _dream_job_rules(),
        skip_files=frozenset(_ALLOWED_DREAM_JOB_FILES),
        exempt_node_ids=_main_py_exempt_node_ids,
    )


def test_no_app_code_reaches_a_family_job():
    paths = app_sources(BACKEND)
    # This floor is well below the real count (151 at the time of writing)
    # but far above zero, so an empty or near-empty scan fails loudly
    # instead of silently passing (app_sources already asserts len > 100;
    # this is the family scan's own belt-and-suspenders on top of it).
    assert len(paths) > 100
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
    legitimate call site the guard above exempts actually exists, by the
    same structural predicate the guard itself uses rather than a text
    comparison.

    **Residual, pre-existing and not narrowed by this fix**: this pins a
    function literally *named* `lifespan`, not the callable FastAPI is
    actually constructed with (`FastAPI(lifespan=...)`). A class-body
    `async def lifespan` carrying the same import and call, never passed to
    `FastAPI`, would satisfy this test while the app boots unwired. The
    pre-T2.67 text-based version had the identical gap — it checked for the
    two exact lines anywhere in the file, with no scope check at all — so
    this is strictly no weaker than before, just not a full fix."""
    main_src = (BACKEND / "app" / "main.py").read_text()
    tree = ast.parse(main_src, filename="app/main.py")
    exempt = _main_py_exempt_node_ids("app/main.py", tree)
    kinds = {type(node).__name__ for node in ast.walk(tree) if id(node) in exempt}
    assert kinds == {"ImportFrom", "Call"}, (
        "app/main.py no longer wires the dream-job family at boot: expected "
        "both the umbrella import and the register_dream_jobs() call inside "
        f"lifespan(), found {kinds!r}"
    )


def test_a_duplicate_registration_outside_lifespan_is_still_flagged(tmp_path):
    """The node-addressable allowlist's own negative control. A second,
    textually-identical copy of main.py's one legitimate umbrella import,
    added outside `lifespan`, is a neighbour with the same *text* as the
    exempted import but not the same *structural role*. A text-based
    allowlist (the pre-T2.67 shape, which matched on exact stripped line
    text) would have silently exempted this duplicate too, since its
    stripped line is identical to the real one; the node-addressable
    version must still fail the build on it."""
    offending = tmp_path / "app" / "main.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "async def lifespan(app):\n"
        "    from app.services.dream_jobs import register_dream_jobs\n"
        '    register_dream_jobs(job_registry, lambda: getattr(app.state, "llm", None))\n'
        "    yield\n"
        "\n"
        "def _rogue_second_wireup(job_registry):\n"
        "    from app.services.dream_jobs import register_dream_jobs\n"
        "    register_dream_jobs(job_registry)\n"
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders == [
        "app/main.py:7: import route: app.services.dream_jobs.register_dream_jobs"
    ], offenders


def test_the_family_scan_catches_a_wrapped_import(tmp_path):
    """The form an import formatter produces, and the exact shape that
    defeated the pre-T2.67 line-based scan: the import spans three lines and
    no single line names both the package and the module."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(
        f"from app.services import (\n    {module},\n)\n"
        "\n"
        f"async def handle_capture():\n"
        f"    return {module}\n"
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a parenthesised multi-line import must still be caught"


def test_the_family_scan_catches_a_split_dotted_path(tmp_path):
    """Adjacent string literals concatenate at parse time, so a dynamic reach
    spelled across two fragments is one constant by the time the scan sees
    it — a substring match over raw source text would never find this."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_retrieval_service.py"
    offending.write_text(
        "from importlib import import_module\n"
        f'import_module("app.services." "{module}")\n'
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a split-string dynamic import must still be caught"


def test_the_family_scan_catches_a_relative_symbol_import(tmp_path):
    """A relative import of a symbol *inside* an implementation module, not
    the module itself, is a shape a naive combined `base.alias` string
    misses: `base` alone carries the real module path, and appending the
    imported symbol name pushes a trailing-segment comparison one slot out
    of alignment. Found by inventing an evasion the existing battery did not
    cover, per the mutation-discipline note in T2.67's brief — this closed a
    real gap discovered while verifying this task, not a hypothetical one."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(f"from .{module} import run_lift\n")
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a relative import of a symbol inside a job body must still be caught"


def test_the_family_scan_catches_an_attribute_reach(tmp_path):
    """T2.18's own residual, closed here for the family scan as well:
    importing the parent package and reaching a job's body through attribute
    access names no forbidden module in any import statement — inert today
    only because nothing imports `app.services` as a bare handle, and live
    the moment something does (doc 08 §5's own note on T2.53's umbrella)."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_retrieval_service.py"
    offending.write_text(
        "from app import services\n"
        "\n"
        "async def search():\n"
        f"    return services.{module}.run_lift\n"
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "reach through a parent-package import must still be caught"


def test_the_family_scan_catches_an_exec_import(tmp_path):
    """A named-Critical fix, per re-review: the literal route used to match
    a `str`/`bytes` constant only by exact equality, so a dotted path
    spelled inside an `exec`/`eval` body — which is one whole-line string,
    never equal to the bare path alone — passed clean. Reproduced against
    the real `app/services/pipeline.py` during verification; this is the
    permanent tmp_path regression guard for the same shape."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(f'exec("import app.services.{module}")\n')
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "an exec()-wrapped import must still be caught"


def test_the_family_scan_catches_an_eval_dynamic_import(tmp_path):
    # This `eval(...)` text is never executed — it is written to a tmp_path
    # fixture file that `_forbidden_dream_job_references` only `ast.parse`s,
    # exercising the evasion shape the scanner must catch, not running it.
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(f'_dyn = eval(\'__import__("app.services.{module}")\')\n')
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "an eval()-wrapped dynamic import must still be caught"


def test_the_family_scan_catches_a_bytes_decoded_dynamic_import(tmp_path):
    """`bytes` constants were not examined at all before this fix — a
    `b"..."` literal fed through `.decode()` before reaching
    `import_module` reached the exact same module with none of the `str`
    literal route's fingerprints."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(
        "from importlib import import_module\n"
        f'import_module(b"app.services.{module}".decode())\n'
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a bytes-literal dynamic import must still be caught"
    assert any("bytes" in o for o in offenders), offenders


def test_the_family_scan_catches_a_loader_spec_literal(tmp_path):
    """The `module:attr` spelling a plugin loader or entry-point resolver
    takes as configuration — the dotted path is present but followed by a
    colon, not a dot or end-of-string, so it must still hit the boundary
    check rather than only an exact-equality one."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(f'_SPEC = "app.services.{module}:run_lift"\n')
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a loader-spec literal naming the module must still be caught"


def test_the_family_scan_catches_a_relative_loader_call_with_package(tmp_path):
    """The one Important finding a re-review raised after the Critical fix:
    `import_module`/`__import__` called with a relative literal name and a
    literal `package=` is a fully static, literal-spelled executable reach
    — neither argument is computed — that no prior version of this scan
    (or T2.18's original AST rebuild) ever recognised. Restored, in the
    shared walker, so all three scans (family, detector, reports) gain it
    together."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_retrieval_service.py"
    offending.write_text(
        "from importlib import import_module\n"
        f'import_module(".{module}", package="app.services")\n'
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a relative import_module()+package= reach must be caught"
    assert any("loader-call" in o for o in offenders), offenders


def test_the_family_scan_catches_a_non_docstring_prose_constant(tmp_path):
    """A constant that is not a docstring (not the first statement of a
    module/class/function body) gets no exemption at all — only an actual
    docstring does, and only by structural role, never by matching text."""
    module = sorted(dream_job_implementation_modules())[0]
    offending = tmp_path / "fake_capture_route.py"
    offending.write_text(
        "def f():\n"
        "    pass\n"
        f'_NOTE = "See app.services.{module} for the implementation"\n'
    )
    offenders = _forbidden_dream_job_references([offending], tmp_path)
    assert offenders, "a non-docstring constant naming the module must still be caught"


def test_the_family_scan_does_not_flag_a_bare_name_inside_ordinary_prose(tmp_path):
    """The design choice that keeps `forbidden_literals` (bare job keys and
    module basenames) exact-match-only rather than boundary-substring, like
    the dotted-path route: real, currently-shipping log and help text in
    this repository contains a bare job key as a natural substring
    (`verification_recompute.py` logs a "verification_recompute:" prefix,
    `memory_community_detection.py`'s help text says "topic_detection run").
    A boundary-substring check over bare names would flag that text; this
    pins that it does not."""
    offending = tmp_path / "fake_help_text.py"
    offending.write_text(
        'HELP = "Projects visited per topic_detection run, in rotating order."\n'
        'LOG_PREFIX = "verification_recompute: fast-arm recompute failed"\n'
    )
    assert _forbidden_dream_job_references([offending], tmp_path) == []


def test_the_family_scan_does_not_fail_on_prose(tmp_path):
    """The umbrella module's own docstring names every job key and every
    implementation module to explain the guard it belongs to; a scan that
    flagged its own prose would be loosened away the first time it fired."""
    innocent = tmp_path / "app" / "services" / "some_other_module.py"
    innocent.parent.mkdir(parents=True)
    innocent.write_text(
        '"""No file under `app/` may import fact_lift or trigger '
        '"fact_lift" directly."""\n'
    )
    assert _forbidden_dream_job_references([innocent], tmp_path) == []


def test_the_family_scan_does_not_fail_on_a_docstring_that_is_the_bare_key(tmp_path):
    """The literal route matches a string constant by exact equality, not by
    substring — deliberately, so `_STATE_CONFIG_KEY = "memory_dream_state"`
    in the real `memory_dream.py` is never a false positive (see the module
    docstring's note on `_reachability_scan`'s literal route). That choice
    makes the *sentence*-shaped prose test above pass for a reason that has
    nothing to do with docstring exemption: no English sentence equals a bare
    job key. This is the case where the exemption is actually load-bearing —
    a docstring whose entire text *is* exactly the forbidden literal, the
    shape a "see also" or bare reference comment would take."""
    innocent = tmp_path / "app" / "services" / "some_other_module.py"
    innocent.parent.mkdir(parents=True)
    innocent.write_text('"""fact_lift"""\n')
    assert _forbidden_dream_job_references([innocent], tmp_path) == []


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
    # Total, not name-pinned: every shipped member declares the module holding
    # its body, and every one of those must be a module the derivation found.
    # A member wired without an umbrella import fails here rather than silently
    # losing its guard.
    missing = set(SHIPPED_DREAM_JOBS.values()) - implementations
    assert not missing, (
        f"shipped member bodies {sorted(missing)} are not reachable from the "
        "umbrella's imports, so the invariant-15 source scan does not cover them"
    )


def test_the_import_parser_covers_every_import_style():
    """The derivation's own negative control. Parsing only the dotted style
    would drop a future member wired either of the other two ways, and the
    guard would lose coverage with nothing failing."""
    parsed = service_modules_imported_by(
        "from app.services.alpha import run\n"
        "from app.services import beta, gamma as g\n"
        "import app.services.delta\n"
        "from app.services.epsilon.nested import thing\n"
        "# from app.services.commented import ignored\n"
        "from app.repositories.zeta import other\n"
    )
    assert parsed == {"alpha", "beta", "gamma", "delta", "epsilon"}


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
    assert set(SHIPPED_DREAM_JOBS) <= set(DREAM_JOB_KEYS)
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


# ─────────────────── T2.53 — topic_detection, productively ───────────────────


@pytest.mark.asyncio
async def test_topic_detection_registers_with_its_real_schema_and_bounds():
    """Doc 08 §5's row for this job: its own cron, floor and ceiling, and the
    detector's real knobs rather than the placeholder's generic `batch_size`.

    The schema swap is the half that could regress silently. An operator
    editing `hub_cap` through `PUT /jobs/{key}/config` was rejected as an
    unknown key while the placeholder schema stood, so a job that looked
    configurable was not.
    """
    registry, engine = _fresh_registry()
    try:
        job = registry.get(TOPIC_DETECTION_JOB_KEY)
        assert job.default_cron == "0 4 * * *"
        assert job.min_interval_seconds == 300
        assert job.max_run_seconds == 900
        # Named explicitly, not compared to the schema object the job
        # registers — that comparison holds for any schema content and asserts
        # nothing. These are T2.18's five knobs plus T2.93's two; a lost one is
        # a knob the operator's `PUT /jobs/{key}/config` starts rejecting as
        # unknown.
        keys = {field.key for field in job.config_schema}
        assert keys == {
            "batch_size", "hub_cap", "min_community_size",
            "leiden_timeout_seconds", "max_projection_edges",
            # T2.93: the report pass this job now runs is bounded by config,
            # not by a module constant the operator cannot see.
            "report_batch", "min_report_size",
        }
        # The placeholder's key, default and ceiling survive the swap, so no
        # value already persisted under the generic schema is orphaned.
        batch = next(f for f in job.config_schema if f.key == "batch_size")
        assert (batch.default, batch.max) == (5, 100)
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_topic_detection_persists_its_rotation_cursor(monkeypatch):
    """The cursor lives in its own `config` row, not in the job's `config`
    dict: `set_config` validates that dict against the schema and is the
    operator-facing surface, so a cursor there would be either rejected or
    editable. This drives two ticks and asserts the second resumes where the
    first stopped."""
    from app.services import dream_jobs

    registry, engine = _fresh_registry()
    seen: list[str | None] = []

    async def fake_run(
        session_factory, llm_provider=None, *, batch_size, after_project, **knobs
    ):
        seen.append(after_project)
        # A full batch: more projects may remain, so the cursor advances.
        return DetectionOutcome(
            last_project=f"project-{len(seen)}", visited=batch_size
        )

    try:
        monkeypatch.setattr(dream_jobs, "run_topic_detection", fake_run)
        job = registry.get(TOPIC_DETECTION_JOB_KEY)
        await job.runner()
        await job.runner()
        assert seen == [None, "project-1"], seen

        async with registry.session_factory() as session:
            cursor = await dream_jobs._load_topic_cursor(session)
        assert cursor == "project-2"
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_cursor_advances_even_when_the_batch_partly_failed(monkeypatch):
    """`run_topic_detection` advances `last_project` *before* attempting each
    project and swallows a per-project failure into `skipped`, so the cursor
    names the last project visited rather than the last that succeeded.
    Persisting it regardless is what keeps the rotation moving: a
    deterministically failing project would otherwise pin the cursor and
    starve every project behind it."""
    from app.services import dream_jobs

    registry, engine = _fresh_registry()

    async def fake_run(
        session_factory, llm_provider=None, *, batch_size, after_project, **knobs
    ):
        return DetectionOutcome(
            last_project="wedged", skipped=1, visited=batch_size
        )

    try:
        monkeypatch.setattr(dream_jobs, "run_topic_detection", fake_run)
        await registry.get(TOPIC_DETECTION_JOB_KEY).runner()
        async with registry.session_factory() as session:
            assert await dream_jobs._load_topic_cursor(session) == "wedged"
    finally:
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_rotation_wraps_and_the_real_composition_succeeds():
    """The Critical the monkeypatched cursor tests structurally could not see,
    and the composition assertion the first fix omitted.

    `next_projects` selects strictly `project > :after_project`, so once the
    cursor reaches the lexicographically last project every later tick claims
    nothing — forever, while still recording `last_status="ok"`. The fake in
    the tests above always returns a fresh project name, so the empty-batch
    echo, the one case that matters at the end of a rotation, was
    unrepresentable in it.

    **Asserting the journal row is what makes this a composition test.** The
    runner forwards four schema knobs to `detect_for_project` by name; a
    renamed parameter or a renamed field raises `TypeError` inside
    `run_topic_detection`'s blanket `except Exception`, which turns *every*
    project into a skip, advances the cursor past all of them, and finishes
    the tick with `last_status="ok"` and no error. Only the per-project journal
    row tells the difference, so the cursor alone cannot pin it.

    The project name sorts first so a batch of one always claims it, whatever
    other projects earlier tests left behind, and the cursor is cleared up
    front for the same reason.
    """
    from sqlalchemy import text as _text

    from app.services import dream_jobs

    registry, engine = _fresh_registry()
    project = "0000-t253-wrap"
    try:
        async with registry.session_factory() as session:
            await session.execute(
                _text(
                    "INSERT INTO memories (id, content, source, project, status) "
                    "VALUES (gen_random_uuid(), 'wrap probe', 'api', "
                    "CAST(:project AS text), CAST('active' AS memory_status))"
                ),
                {"project": project},
            )
            from app.services.dream_jobs import _save_topic_cursor
            await _save_topic_cursor(session, None)
            await session.commit()
        await registry.set_config(TOPIC_DETECTION_JOB_KEY, {"batch_size": 1})

        job = registry.get(TOPIC_DETECTION_JOB_KEY)

        # Tick 1 claims exactly our project. A *full* batch means more may
        # remain, so the cursor advances rather than wrapping — which is also
        # what pins the detector's `visited` against under-reporting: a low
        # count here would wrap every tick and starve everything past the
        # first batch, the mirror of the defect this test exists for.
        await job.runner()
        async with registry.session_factory() as session:
            assert await dream_jobs._load_topic_cursor(session) == project

            reasons = (await session.execute(
                _text(
                    "SELECT payload->>'skipped_reason' FROM events "
                    "WHERE project = CAST(:p AS text) AND object_type = 'topic' "
                    "ORDER BY created_at, id"
                ),
                {"p": project},
            )).scalars().all()
        assert reasons, "the tick journalled nothing for the seeded project"
        assert reasons[-1] is None, (
            f"the project was skipped ({reasons[-1]!r}) rather than detected. "
            f"A renamed knob or parameter raises TypeError inside "
            f"run_topic_detection's blanket except, which skips every project "
            f"and still reports last_status='ok' — the cursor cannot see it."
        )

        # Then tick until the rotation wraps. The bound is what makes this a
        # real assertion: before the fix the cursor pinned and this loop would
        # exhaust without ever seeing None.
        cursors = []
        for _ in range(12):
            await job.runner()
            async with registry.session_factory() as session:
                cursors.append(await dream_jobs._load_topic_cursor(session))
            if cursors[-1] is None:
                break

        assert None in cursors, (
            f"the rotation never wrapped in 12 ticks; cursors were {cursors}. "
            f"A cursor that only ever advances pins at the last project and "
            f"every later tick claims nothing, forever."
        )
    finally:
        async with registry.session_factory() as session:
            await session.execute(
                _text("DELETE FROM memories WHERE project = CAST(:p AS text)"),
                {"p": project},
            )
            await session.commit()
        await registry.stop_all()
        await engine.dispose()
