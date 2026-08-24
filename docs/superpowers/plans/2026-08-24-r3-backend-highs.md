# R3 — Backend Correctness Singletons

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The article-synthesis rotation cursor wraps instead of pinning past the last project, a `code_reconcile` tick takes the indexing claim it needs instead of running on top of another indexer, and MCP `code_symbol` stops raising `MissingGreenlet` on every symbol that exists.

**Architecture:** Three independent backend fixes with no shared files. Each is small, each is behind R2 for a stated reason, and each closes a path that is broken today for every caller that reaches it.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0 async, asyncpg, FastMCP, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-review-remediation.md`

## Why these three, and why here

All three are reachable-path defects that produce no error anyone sees:

- **The article rotation** persists the same cursor it was handed when the sweep comes back empty, so after one pass the job synthesises nothing forever while `JobRegistry._run_once` records `last_status="ok"`. Its sibling `_make_topic_runner` computes the wrap and its comment names this exact failure — *"The rotation has to wrap, or the job goes inert after one pass."*
- **`code_reconcile`** is a fourth caller of `CodePipeline.run` that takes no indexing claim. `claim_for_indexing`'s docstring names three callers; this one was added later. The per-job `asyncio.Lock` serialises reconcile against itself, not against the webhook, the reindex route or `repo_sync`.
- **MCP `code_symbol`** dereferences `CodeSymbol.file` — the one relationship in the ORM declared with default `lazy="select"` — from outside greenlet context. The tool works only on its failure path: a symbol that does not exist returns "Symbol not found", a symbol that exists raises.

They sit behind R2 because `code_reconcile`'s repair cannot be verified in an image
that cannot clone, and because `repo_manager.py` must not be rebasing while R2 edits it.

## Global Constraints

- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q <path>`. Needs the dev Postgres on `127.0.0.1:5433` and database `darkmem_test`. Baseline on master today is **6179 passed, 22 skipped** — a change in that count is a signal, not noise.
- **Parallel lanes need their own database.** `darkmem_test_2` … `darkmem_test_5` exist for this. Keep `darkmem_test` for whoever runs the controller gate. conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` and then runs `DROP SCHEMA public CASCADE` — never point a lane at a real database.
- **Frontend tests:** from `frontend/`, `npx vitest run <path>`. Typecheck is `npx tsc -b` (plain `tsc` misses the project refs). Baseline is **1233 passing**.
- **Merge gate:** `./scripts/gate.sh` from the repo root. `--full` adds the retrieval eval, the API e2e suite, Playwright and a port-hygiene diff. Each task below says which it needs and why.
- **Commits:** `<type>(<scope>): <subject>`, type one of `feat|fix|docs|style|refactor|test|chore|perf`, subject imperative, ≤ 50 characters, no trailing period. Atomic — never combine two concerns.
- **Comments:** default to none. Add one only where the WHY is non-obvious — a hidden constraint, a subtle invariant, a workaround for a specific bug. Never explain WHAT the code does; never reference this plan, this task, or a ticket.
- **Never** hardcode a value or special-case an input to make a test pass, and never use `--no-verify`. If a fix turns out to be infeasible or a finding turns out to be wrong, say so and stop — do not work around it.
- **This changes the running artifact, so it is redeployed after the gate.** `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → wait for `healthy` → **then confirm the change is in the running image, not only in the tree**. compose reuses an image whose tag did not move, so a skipped or failed build redeploys the old bits and still reports `Started`. `DARKMEM_PUSH=0` is not optional: the script's default is to push, and image push is CI-only.
- **These three share no files and can be developed as three parallel branches**, merged in any order — give each lane its own test database (`darkmem_test_2` … `darkmem_test_5`).
- **`backend/api/mcp/server.py` has a later claimant.** Task 3 is the first writer; the door-parity package in a later stage is the second.
- **`backend/app/services/job_runners.py` has a later claimant.** Task 2 is the first writer; the memory-delete-demotion package is the second.

---

### Task 1: Wrap the article-synthesis rotation cursor

**Effort:** ~25 minutes.

**Files:**
- Modify: `backend/app/services/dream_jobs.py:561-585`
- Test: `backend/tests/test_dream_jobs.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

- [ ] **Step 1: Write the failing test**

Append both tests to the END of backend/tests/test_dream_jobs.py (the file currently ends at line 1097 with `test_the_family_holds_no_placeholders_left`). The first test is the one that fails today; the second is the guard that stops "always reset" from counting as a fix, and passes both before and after.

```python


# ─────────────────── T3.02 — article_synthesis, the rotation ──────────────────


@pytest.mark.asyncio
async def test_the_article_rotation_wraps_when_the_sweep_comes_back_short():
    """The Critical `_make_topic_runner`'s own comment names, at the sibling
    that never got it.

    `_NEXT_PROJECTS_SQL` selects strictly `project > :after_project`, so once
    the cursor reaches the lexicographically last project every later tick
    claims nothing — and `run_article_synthesis` seeds `last_project` with the
    cursor it was handed, so an empty sweep returns that same value and the
    runner writes it straight back. The rotation pins there forever: nothing is
    synthesised, the re-synthesis pass runs over an empty batch, and the tick
    still records `last_status="ok"`. A project created later that sorts before
    the cursor is never visited at all.

    The cursor is set to the table's own maximum project so the sweep is empty
    whatever else the suite has committed, in whatever collation the database
    compares under. No orchestrator is needed: with zero projects claimed there
    is no subject to draft.
    """
    from sqlalchemy import text as _text

    from app.services import dream_jobs

    registry, engine = _fresh_registry()
    try:
        async with registry.session_factory() as session:
            highest = (await session.execute(
                _text("SELECT max(project) FROM knowledge_triples")
            )).scalar()
            await dream_jobs._save_article_cursor(
                session, highest or "zzzz-no-projects"
            )
            await session.commit()

        await registry.get(ARTICLE_SYNTHESIS_JOB_KEY).runner()

        async with registry.session_factory() as session:
            cursor = await dream_jobs._load_article_cursor(session)
        assert cursor is None, (
            f"the rotation never wrapped; the cursor is still {cursor!r}. A "
            f"cursor that only advances pins past the last project and every "
            f"later tick synthesises nothing, forever."
        )
    finally:
        async with registry.session_factory() as session:
            await session.execute(
                _text("DELETE FROM config WHERE key = CAST(:k AS text)"),
                {"k": dream_jobs._ARTICLE_STATE_CONFIG_KEY},
            )
            await session.commit()
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_full_article_batch_advances_the_cursor(monkeypatch):
    """The other half of the wrap, so a reset that always fires is not a fix.

    A full batch means projects may remain past it, so the cursor advances and
    the next tick resumes there rather than restarting the rotation.
    """
    from sqlalchemy import text as _text

    from app.services import dream_jobs
    from app.services.article_synthesis import SynthesisOutcome

    registry, engine = _fresh_registry()

    async def fake_run(
        session_factory, llm_provider=None, *, batch_size, after_project, **knobs
    ):
        visited = [f"project-{n}" for n in range(batch_size)]
        return SynthesisOutcome(last_project=visited[-1], visited=visited)

    async def fake_resynthesis(session_factory, llm_provider=None, **knobs):
        return None

    try:
        monkeypatch.setattr(dream_jobs, "run_article_synthesis", fake_run)
        monkeypatch.setattr(dream_jobs, "run_article_resynthesis", fake_resynthesis)

        await registry.get(ARTICLE_SYNTHESIS_JOB_KEY).runner()

        async with registry.session_factory() as session:
            cursor = await dream_jobs._load_article_cursor(session)
        assert cursor == "project-9", cursor
    finally:
        async with registry.session_factory() as session:
            await session.execute(
                _text("DELETE FROM config WHERE key = CAST(:k AS text)"),
                {"k": dream_jobs._ARTICLE_STATE_CONFIG_KEY},
            )
            await session.commit()
        await registry.stop_all()
        await engine.dispose()
```

Notes for whoever applies this:
- `_fresh_registry`, `ARTICLE_SYNTHESIS_JOB_KEY` and `pytest` are already imported at the top of this file; no header change is needed. `SynthesisOutcome` and `sqlalchemy.text` are imported inside the test bodies, which is the shape the neighbouring `test_the_rotation_wraps_and_the_real_composition_succeeds` uses.
- `_fresh_registry()` builds its own engine, so these tests write on a real committed connection (conftest's rollback fixture does not cover it). That is why each test deletes the `article_synthesis_state` config row in its `finally`.
- `register_dream_jobs(registry)` inside `_fresh_registry` passes no `llm_provider`, so the first test drives the REAL `run_article_synthesis` and `run_article_resynthesis` with `llm=None`. With zero projects claimed neither reaches a model call, so the test needs no stub LLM and no network.
- `"project-9"` in the second test is `batch_size - 1` at the schema default of 10 (`ARTICLE_SYNTHESIS_CONFIG_SCHEMA`'s `batch_size` FieldDescriptor). The fake builds exactly `batch_size` visited projects, i.e. a full batch, which must NOT wrap.

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_dream_jobs.py -k "article_rotation or full_article_batch"

(Requires the dev Postgres on 127.0.0.1:5433 with database darkmem_test, per the repo's backend test setup.)
```

Expected — this is what the run actually printed on master:

Actually observed on master today (2026-08-24):

```
>           assert cursor is None, (
                f"the rotation never wrapped; the cursor is still {cursor!r}. A "
                f"cursor that only advances pins past the last project and every "
                f"later tick synthesises nothing, forever."
            )
E           AssertionError: the rotation never wrapped; the cursor is still 'zzzz-no-projects'. A cursor that only advances pins past the last project and every later tick synthesises nothing, forever.
E           assert 'zzzz-no-projects' is None

tests/test_dream_jobs.py:1141: AssertionError
=========================== short test summary info ============================
FAILED tests/test_dream_jobs.py::test_the_article_rotation_wraps_when_the_sweep_comes_back_short
1 failed, 1 passed, 37 deselected, 1 warning in 0.98s
```

The literal in the message is whatever `max(project)` is in `knowledge_triples` at the time — `'zzzz-no-projects'` when that table is empty (which it is on a fresh test-database run), or the highest committed project name otherwise. Either way the assertion is `<the cursor it was given> is None`, i.e. the runner echoed the cursor back instead of resetting it.

`test_a_full_article_batch_advances_the_cursor` is the "1 passed" above: it passes before and after the fix, and exists so that a fix which always resets the cursor is caught.

- [ ] **Step 3: Apply the fix**

One defect, one fix site. F01 (`dream_jobs.py:583`, the persist) and F02 (`article_synthesis.py:932`, the seed) are two slices of the same bug: the article-synthesis rotation cursor never wraps, so once it reaches the lexicographically last project the job is inert forever while still reporting `last_status="ok"`.

The fix belongs entirely in `backend/app/services/dream_jobs.py`, in `_make_article_runner`. **`backend/app/services/article_synthesis.py` must NOT be changed** — see "Why article_synthesis.py is left alone" at the bottom; changing it there breaks an existing passing test and is the wrong layer.

CURRENT CODE — `backend/app/services/dream_jobs.py`, inside `_make_article_runner`'s `async def run()`, lines 561-585:

```python
        outcome = await run_article_synthesis(
            registry.session_factory,
            llm_provider,
            batch_size=int(settings_.get("batch_size", 10)),
            after_project=after_project,
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        # T3.05's second pass, over the batch the first pass rotated onto — new
        # articles first, then the standing ones whose knowledge moved. The
        # order matters only in that a subject cannot be in both: the selector
        # excludes subjects holding a live article, and this pass reads only
        # subjects that hold one.
        await run_article_resynthesis(
            registry.session_factory,
            llm_provider,
            projects=outcome.visited,
            debounce_hours=float(settings_.get("debounce_hours", DEFAULT_DEBOUNCE_HOURS)),
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        async with registry.session_factory() as session:
            await _save_article_cursor(session, outcome.last_project)
            await session.commit()
```

REPLACEMENT (same block, in full):

```python
        batch_size = int(settings_.get("batch_size", 10))
        outcome = await run_article_synthesis(
            registry.session_factory,
            llm_provider,
            batch_size=batch_size,
            after_project=after_project,
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        # T3.05's second pass, over the batch the first pass rotated onto — new
        # articles first, then the standing ones whose knowledge moved. The
        # order matters only in that a subject cannot be in both: the selector
        # excludes subjects holding a live article, and this pass reads only
        # subjects that hold one.
        await run_article_resynthesis(
            registry.session_factory,
            llm_provider,
            projects=outcome.visited,
            debounce_hours=float(settings_.get("debounce_hours", DEFAULT_DEBOUNCE_HOURS)),
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        # **The rotation has to wrap, or the job goes inert after one pass**,
        # the failure `_make_topic_runner` states in full: `next_projects`
        # selects strictly `project > :after_project`, and `run_article_synthesis`
        # seeds `last_project` with the cursor it was handed, so an empty sweep
        # returns that same value. Persisting it pins the rotation past the last
        # project forever, while every tick still records `last_status="ok"`.
        wrapped = len(outcome.visited) < batch_size
        async with registry.session_factory() as session:
            await _save_article_cursor(
                session, None if wrapped else outcome.last_project
            )
            await session.commit()
```

That is the whole change: three edits in one function — hoist `batch_size` into a local (it was inlined at the one call site and is now needed twice), compute `wrapped`, and pass `None` instead of the echoed cursor when the batch came back short. `_save_article_cursor` already handles `None` and its docstring already describes exactly this reset; today that branch is unreachable, and after this change it is reached.

This mirrors `_make_topic_runner` (same file, ~line 377) verbatim in intent: `wrapped = outcome.visited < batch_size; cursor = None if wrapped else outcome.last_project`. The only difference is `len(...)`: `DetectionOutcome.visited` is an `int`, while `SynthesisOutcome.visited` is a `list[str]` (it carries the project names so `run_article_resynthesis` runs over the same batch).

Why `< batch_size` and not `== 0`: a short batch — including the zero case — is the end of the rotation, because `_NEXT_PROJECTS_SQL` is `ORDER BY project LIMIT :batch_size` over everything past the cursor. Fewer rows than the limit means there was nothing more to claim. This is the same predicate the topic runner and `make_ppr_snapshot_runner` use, and the same one `verification_recompute`'s slow arm uses.

Why article_synthesis.py is left alone:
- `run_article_synthesis` seeding `outcome = SynthesisOutcome(last_project=after_project)` is correct at its own layer: it reports the last project *visited*, and when it visited none, the last one visited is still the one the caller's cursor named. `SynthesisOutcome.visited` exists precisely so the caller can tell a short batch from a full one — F02's own text says so.
- Making it return `last_project=None` on a short batch instead would break the existing passing test `backend/tests/test_article_synthesis.py::TestTheRun::test_the_cursor_names_the_last_project_visited`, which runs with `batch_size=200` over 2 projects (a short batch by definition) and asserts `outcome.last_project is not None`. That test is right; the wrap is a rotation-policy decision that belongs to the thing that owns the persisted cursor.

House-rule note: this changes `backend/`, so it alters the running artifact and this host must be redeployed after it lands (gate → `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → confirm the change is in the running image). It touches no migration and no schema.

- [ ] **Step 4: Run the same command and confirm it passes**

```
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_dream_jobs.py -k "article_rotation or full_article_batch"
..                                                                       [100%]
2 passed, 37 deselected, 1 warning in 0.81s
```

(The one warning is the pre-existing `pynvml` FutureWarning from `app/services/system_metrics.py`, unrelated.)

Wider run, also actually executed with the fix applied:

```
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_dream_jobs.py tests/test_article_synthesis.py tests/test_article_staleness.py tests/test_inert_objects.py tests/test_job_registry.py
167 passed, 5 skipped, 7 warnings in 4.04s
```

- [ ] **Step 5: Run the surrounding suite for regressions**

The behaviour change is real, not cosmetic: after this lands, a tick whose sweep returns fewer than `batch_size` projects resets the persisted cursor to NULL instead of leaving it at the last project. On the next tick the rotation restarts from the beginning of the project list. That is the intended fix, and it is the same policy `topic_detection` and `ppr_snapshot` already run under, but two consequences are worth stating:

1. **Re-visiting costs model calls, not just rows.** On an install with fewer projects than `batch_size` (the default single-project install: 1 project, batch_size 10), *every* tick now wraps, so every tick re-rotates onto every project. That is what the job is supposed to do — it was doing nothing at all before — but it means the daily `0 5 * * *` tick starts spending again. The per-project subject budget still bounds it: `select_for_synthesis` applies `synthesis_budget` from the `article_selection` config row and already excludes subjects that hold a live article, and T3.05's re-synthesis pass is separately damped by `debounce_hours`. So the steady state is "nothing new to synthesise" queries, not a nightly re-draft of everything.

2. **First tick after deploy on this host.** Production has been armed since 2026-08-17 and its `article_synthesis_state` row may already be pinned past the last project. The first tick after the redeploy will wrap and then actually synthesise the backlog it has been silently skipping. Expect a longer-than-usual run and real LLM spend on that first night, and expect articles to appear for projects created after the cursor pinned. There is no manual step: the wrap is what un-pins it.

Edge case deliberately not handled, matching the sibling: if an operator writes `batch_size <= 0` directly into the `config` row (bypassing `set_config`'s schema validation, which enforces min 1 / max 200), `run_article_synthesis` clamps the SQL `LIMIT` with `max(1, batch_size)` while the runner compares against the raw value, so `wrapped` would read False and the cursor would advance. `_make_topic_runner` has the identical asymmetry. Not worth a divergence from the sibling; a value that cannot be written through the only surface that writes it.

Existing tests covering the surrounding behaviour (all run, all green with the fix applied):
- `backend/tests/test_dream_jobs.py` — the whole rotation/registration/lock family, including `test_topic_detection_persists_its_rotation_cursor`, `test_the_cursor_advances_even_when_the_batch_partly_failed` and `test_the_rotation_wraps_and_the_real_composition_succeeds` (the sibling this fix mirrors), plus `test_the_family_holds_no_placeholders_left`.
- `backend/tests/test_article_synthesis.py` — `TestTheRun`, including `test_the_cursor_names_the_last_project_visited`, which is the test that pins `run_article_synthesis`'s own cursor semantics and is the reason the fix must not move into that module.
- `backend/tests/test_article_staleness.py` — `TestTheConfigRow::test_the_runner_forwards_it_from_that_row` parses `_make_article_runner`'s source with `ast` and asserts `debounce_hours` is still forwarded to `run_article_resynthesis` by keyword. The replacement leaves that call untouched, and the test passes.
- `backend/tests/test_inert_objects.py` and `backend/tests/test_job_registry.py` — registration and job-run bookkeeping around the same runner.

No migration, no schema file, no frontend, no API surface, no config-schema change. `backend/migrations/versions/0001_baseline.py` is not touched.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/dream_jobs.py backend/tests/test_dream_jobs.py
git commit -m "fix(dream-jobs): wrap the article rotation cursor"
```

### Task 2: Take the indexing claim in the code_reconcile job runner

**Effort:** ~40 minutes.

**Files:**
- Modify: `backend/app/services/job_runners.py:119-152`
- Modify: `backend/app/services/repo_manager.py:240-241`
- Test: `backend/tests/test_code_reconcile.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

One product-visible choice the repo owner may want to overrule: a reconcile run that dies before `CodePipeline.run` writes its own status now leaves the repository at `status='stale'` with the exception string in `status_message`. `stale` mirrors what the pipeline's own failure handler writes for a repo that still has a graph to serve, and it keeps the repo claimable by the next tick — but it is a user-visible badge in the repositories view for a failure that produced no partial index. The alternatives are `error` (louder, but the pipeline reserves that for a repo with nothing to keep) or restoring `ready` (silent, and hides a repo whose drift nothing can reconcile). Nothing else in the task is open.

- [ ] **Step 1: Write the failing test**

Append both tests verbatim to the END of backend/tests/test_code_reconcile.py.
They reuse the module's existing helper `_git_init_repo` and the existing
module-level imports (`uuid`, `Path`, `pytest`, `Repository`, `CodePipeline`,
`make_code_reconcile_runner`, `RepoManager`); everything else is imported
locally, which is this file's established style.

# ── The indexing claim (T4.16) ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_skips_a_repo_whose_indexing_claim_is_held(
    setup_database, monkeypatch,
):
    """`code_reconcile` is a fourth entry point into `CodePipeline.run`, and
    `JobRegistry`'s per-job lock only serialises it against itself. A tick
    landing inside a `repo_sync` / webhook / reindex run has to lose the claim
    and skip the repo, exactly as `repo_sync` does — otherwise two pipelines
    interleave delete/insert on the same `(repo_id, file_path)`, and whichever
    finishes second flips the status to `ready`, releasing a claim it never
    took.

    `test_runner_reconciles_drifted_repo_and_skips_clean_one` above is the
    counterpart: without it this would pass against a runner that stopped
    reconciling anything at all.
    """
    import tempfile

    from sqlalchemy import delete, select, update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    with tempfile.TemporaryDirectory() as dirty_dir:
        _git_init_repo(
            Path(dirty_dir),
            {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        )

        async with factory() as session:
            repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=dirty_dir)
            session.add(repo)
            await session.flush()
            repo_id = repo.id
            pipe = CodePipeline(
                session=session, llm=None, vector_repo=None,
                repo_manager=RepoManager(session),
            )
            assert (await pipe.run(repo.id, full=True))["status"] == "indexed"
            await session.commit()

        try:
            (Path(dirty_dir) / "svc.py").write_text(
                "class Svc:\n    def start(self):\n        return 1\n"
                "    def stop(self):\n        return 0\n",
                encoding="utf-8",
            )

            async with factory() as session:
                await session.execute(
                    update(Repository)
                    .where(Repository.id == repo_id)
                    .values(status="indexing", status_message="Periodic sync...")
                )
                await session.commit()

            dispatched: list = []

            async def _tracking_run(self, *args, **kwargs):
                dispatched.append((args, kwargs))
                return {"status": "indexed"}

            monkeypatch.setattr(CodePipeline, "run", _tracking_run)

            class _FakeApp:
                class state:
                    llm = None

            await make_code_reconcile_runner(_FakeApp, factory)()

            assert dispatched == [], (
                "code_reconcile ran CodePipeline against a repository whose "
                "indexing claim another run already holds — the concurrent "
                "double-index"
            )

            async with factory() as session:
                held = (await session.execute(
                    select(Repository.status).where(Repository.id == repo_id)
                )).scalar_one()
            assert held == "indexing", "code_reconcile released a claim it never took"
        finally:
            async with factory() as session:
                await session.execute(delete(Repository).where(Repository.id == repo_id))
                await session.commit()


@pytest.mark.asyncio
async def test_reconcile_hands_its_claim_back_when_the_run_dies(
    setup_database, monkeypatch,
):
    """Taking the claim obliges handing it back. `CodePipeline.run` writes its
    own terminal status only once it is past `pull_repo` and the HEAD read, so
    anything raising before that (a `local_path` repo whose `.git` was removed
    since the last index) would pin the repo at `indexing` forever, blocking
    every other entry point with it.
    """
    import tempfile

    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    with tempfile.TemporaryDirectory() as dirty_dir:
        _git_init_repo(
            Path(dirty_dir),
            {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        )

        async with factory() as session:
            repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=dirty_dir)
            session.add(repo)
            await session.flush()
            repo_id = repo.id
            pipe = CodePipeline(
                session=session, llm=None, vector_repo=None,
                repo_manager=RepoManager(session),
            )
            assert (await pipe.run(repo.id, full=True))["status"] == "indexed"
            await session.commit()

        try:
            (Path(dirty_dir) / "svc.py").write_text(
                "class Svc:\n    def start(self):\n        return 1\n"
                "    def stop(self):\n        return 0\n",
                encoding="utf-8",
            )

            async def _dies_before_writing_status(self, *args, **kwargs):
                raise RuntimeError("git rev-parse HEAD failed")

            monkeypatch.setattr(CodePipeline, "run", _dies_before_writing_status)

            class _FakeApp:
                class state:
                    llm = None

            await make_code_reconcile_runner(_FakeApp, factory)()

            async with factory() as session:
                status = (await session.execute(
                    select(Repository.status).where(Repository.id == repo_id)
                )).scalar_one()
            assert status == "stale", (
                f"a failed reconcile left the repo at {status!r}; the claim it "
                "took is never handed back"
            )

            async with factory() as session:
                assert await RepoManager(session).claim_for_indexing(
                    repo_id, message="next run"
                ) is True
        finally:
            async with factory() as session:
                await session.execute(delete(Repository).where(Repository.id == repo_id))
                await session.commit()


- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_code_reconcile.py

Needs the dev Postgres on 127.0.0.1:5433 with database darkmem_test. If another
agent lane is using darkmem_test concurrently, its session-scoped schema reset
will blow this run up with `relation "repositories" does not exist`; in that
case create a private lane database and prefix the command with
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/<lane_db>
(that is how the run below was verified).
```

Expected — this is what the run actually printed on master:

Measured against the unmodified tree (12 collected, 2 fail):

FAILED tests/test_code_reconcile.py::test_reconcile_skips_a_repo_whose_indexing_claim_is_held
E   AssertionError: code_reconcile ran CodePipeline against a repository whose indexing claim another run already holds — the concurrent double-index
E   assert [((UUID('b8584208-...'),), {'forced_files': (['svc.py'], [])})] == []
E     Left contains one more item: ((UUID('b8584208-...'),), {'forced_files': (['svc.py'], [])})

FAILED tests/test_code_reconcile.py::test_reconcile_hands_its_claim_back_when_the_run_dies
E   AssertionError: a failed reconcile left the repo at 'ready'; the claim it took is never handed back
E   assert 'ready' == 'stale'

2 failed, 10 passed, 1 warning in 2.74s

- [ ] **Step 3: Apply the fix**

Two edits. No schema change, no migration, no touch of
backend/migrations/versions/0001_baseline.py. `repositories.status` is a plain
VARCHAR(20) with no CHECK constraint (baseline line 851), so the new `stale`
write needs nothing from the database.

────────────────────────────────────────────────────────────────────────────
EDIT 1 of 2 — backend/app/services/repo_manager.py

Add a release method directly after `claim_for_indexing`. `update` is already
imported at the top of this module (line 10), so no import change is needed.

CURRENT CODE (lines 239-242, the tail of `claim_for_indexing` and the start of
the next method):

        await self.session.commit()
        return claimed is not None

    async def list_all(self) -> list[dict]:

REPLACEMENT:

        await self.session.commit()
        return claimed is not None

    async def release_indexing_claim(self, repo_id: UUID, *, message: str) -> bool:
        """Hand the claim back when the run holding it died before reaching
        `CodePipeline.run`'s own terminal status write.

        Predicated on ``status='indexing'`` for the mirror of the reason the
        claim is predicated on its absence: a run that did reach the pipeline's
        failure handler has already committed ``stale``/``error`` with a
        specific cause there, and this generic one must not overwrite it.
        ``stale`` rather than ``error`` because only a repo that already has a
        graph to keep serving can reach here.
        """
        released = (await self.session.execute(
            update(Repository)
            .where(Repository.id == repo_id, Repository.status == "indexing")
            .values(status="stale", status_message=message)
            .returning(Repository.id)
        )).scalar_one_or_none()
        await self.session.commit()
        return released is not None

    async def list_all(self) -> list[dict]:

────────────────────────────────────────────────────────────────────────────
EDIT 2 of 2 — backend/app/services/job_runners.py

Replace the whole per-repo loop inside `make_code_reconcile_runner`.

CURRENT CODE (lines 119-152, ending at the `return run` on line 153 which is
NOT part of the replacement — keep it as-is):

        for repo in repos_to_check:
            async with session_factory() as repo_session:
                try:
                    manager = RepoManager(repo_session)
                    repo_row = await manager.get(repo.id)
                    if repo_row is None:
                        continue
                    work_dir = manager.repo_working_dir(repo_row)
                    if not work_dir.exists():
                        continue

                    changed, deleted = await compute_working_tree_drift(
                        repo_session, repo_row, work_dir,
                    )
                    if not changed and not deleted:
                        continue

                    pipeline = CodePipeline(
                        session=repo_session, llm=None, vector_repo=None,
                        repo_manager=manager,
                    )
                    await pipeline.run(repo_row.id, forced_files=(changed, deleted))
                    await repo_session.commit()
                    logger.info(
                        "Code reconcile: repo=%s changed=%d deleted=%d",
                        repo_row.name, len(changed), len(deleted),
                    )
                except ValueError as e:
                    # repo_working_dir's local_path revalidation rejects a row
                    # whose path moved into a blocked tree since it was created.
                    logger.warning("Code reconcile skipped repo %s: %s", repo.name, e)
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Code reconcile failed for %s: %s", repo.name, e)

REPLACEMENT:

        for repo in repos_to_check:
            claimed = False
            handed_back = False
            cause = "Reconcile aborted"
            async with session_factory() as repo_session:
                try:
                    manager = RepoManager(repo_session)
                    repo_row = await manager.get(repo.id)
                    if repo_row is None:
                        continue
                    work_dir = manager.repo_working_dir(repo_row)
                    if not work_dir.exists():
                        continue

                    changed, deleted = await compute_working_tree_drift(
                        repo_session, repo_row, work_dir,
                    )
                    if not changed and not deleted:
                        continue

                    # This is the fourth entry point into CodePipeline.run, and
                    # the JobRegistry lock above only serialises it against
                    # itself. Claimed after the drift scan, never before: a
                    # clean tree takes the `continue` above, and a claim taken
                    # on that path is one no branch here ever hands back.
                    if not await manager.claim_for_indexing(
                        repo_row.id, message="Reconciling working tree...",
                    ):
                        logger.info(
                            "Code reconcile skipped for %s: already indexing",
                            repo_row.name,
                        )
                        continue
                    claimed = True

                    pipeline = CodePipeline(
                        session=repo_session, llm=None, vector_repo=None,
                        repo_manager=manager,
                    )
                    await pipeline.run(repo_row.id, forced_files=(changed, deleted))
                    await repo_session.commit()
                    handed_back = True
                    logger.info(
                        "Code reconcile: repo=%s changed=%d deleted=%d",
                        repo_row.name, len(changed), len(deleted),
                    )
                except ValueError as e:
                    # repo_working_dir's local_path revalidation rejects a row
                    # whose path moved into a blocked tree since it was created.
                    cause = f"{type(e).__name__}: {e}"[:500]
                    logger.warning("Code reconcile skipped repo %s: %s", repo.name, e)
                except Exception as e:
                    await repo_session.rollback()
                    cause = f"{type(e).__name__}: {e}"[:500]
                    logger.error("Code reconcile failed for %s: %s", repo.name, e)
                finally:
                    if claimed and not handed_back:
                        try:
                            async with session_factory() as release_session:
                                await RepoManager(release_session).release_indexing_claim(
                                    repo.id, message=cause,
                                )
                        except Exception as release_e:
                            logger.error(
                                "Failed to release reconcile claim for %s: %s",
                                repo.id, release_e,
                            )

────────────────────────────────────────────────────────────────────────────
WHY THE PIECES ARE WHERE THEY ARE (do not reorder them)

* The claim is taken AFTER `compute_working_tree_drift`, not before. The clean
  tree case takes an unconditional `continue`; a claim taken before the drift
  scan would be left held on every healthy repo, wedging it at `indexing`
  forever. Hashing a tree that another run is indexing is wasted work at worst.

* `handed_back` is set only after `repo_session.commit()`. On the success path
  `CodePipeline.run` itself writes `status='ready'` and commits, which IS the
  release — the `finally` must not fire there.

* The `finally` also runs on every `continue` above, where `claimed` is still
  False, so those paths are a no-op.

* The release uses a SECOND session (`release_session`) because `repo_session`
  may be in a needs-rollback state after a database-level failure — the same
  reason `make_repo_sync_runner` opens its own `fail_session` for
  `mark_periodic_sync_failure`.

* The release cannot steal someone else's claim: while we hold `indexing`, the
  compare-and-set in `claim_for_indexing` refuses every other caller, so the
  only writer of that row's status during our hold is our own pipeline. Its
  `stale`/`error` write makes the `WHERE status = 'indexing'` predicate match
  nothing, which is exactly the "don't overwrite the specific verdict" case.

* Reconcile deliberately does NOT reuse `mark_periodic_sync_failure` (which
  repo_sync uses to release): that also sets `auto_sync = False`, which is
  repo_sync's own knob and nothing to do with reconcile.


- [ ] **Step 4: Run the same command and confirm it passes**

cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_code_reconcile.py

............                                                             [100%]
12 passed, 1 warning in 2.47s

(The one warning is the pre-existing pynvml FutureWarning from
app/services/system_metrics.py, present on every run of this suite.)

- [ ] **Step 5: Run the surrounding suite for regressions**

MEASURED. Ran the fix plus both new tests against a private lane database:
tests/test_code_reconcile.py tests/test_push_webhook.py tests/test_repos.py
tests/test_code_fail_stale.py tests/test_index_debt.py tests/test_code_deriver.py
tests/test_code_pipeline_integration.py tests/test_repo_hint_ssrf.py
→ 224 passed, 1 failed. The single failure is
tests/test_repos.py::test_pull_repo_never_rewinds_a_local_checkout, which is
another agent lane's already-red test for finding F03 (`git reset --hard` on a
local_path repo). It fails identically without this change and touches nothing
here.

Real behaviour changes an engineer should expect:

1. A repo whose reconcile raises before `CodePipeline.run` writes its own
   status now ends at `status='stale'` instead of staying `ready`. That value
   is served on `RepoResponse.status` (`GET /api/v1/repos`) and rendered by the
   repositories view. `stale` is not a new vocabulary item — `CodePipeline.run`
   already writes it for a mid-run failure on a repo with a prior graph, and
   tests/test_code_fail_stale.py covers that surface. `stale` is not in
   `RepoManager.BUSY_STATUSES`, so the next tick can claim it normally.

2. Drift found while another run holds the claim is now deferred to the next
   15-minute tick instead of being indexed immediately. That is the point of
   the fix, but it does mean a working-tree edit made during a long index waits
   one extra cycle.

3. `claim_for_indexing` commits. The reconcile runner's session therefore
   commits mid-iteration now, where it previously only committed after the
   pipeline. Nothing is written before that point — `manager.get` and
   `compute_working_tree_drift` are reads — so the commit lands an empty
   transaction. Confirmed harmless: `expire_on_commit=False` on
   `app.database.async_session_factory` (the factory `app/main.py` passes to
   this runner), so `repo_row` is not expired by the commit and the subsequent
   `repo_row.id` / `repo_row.name` reads cannot trigger a MissingGreenlet lazy
   load.

Existing tests that cover the surrounding behaviour:
* tests/test_code_reconcile.py::test_runner_reconciles_drifted_repo_and_skips_clean_one
  — the counterpart proving the runner still reconciles a repo nobody holds.
* tests/test_code_reconcile.py::test_unchanged_tree_short_circuits_with_no_work
  — proves a clean tree still never reaches `CodePipeline.run` (i.e. the claim
  was not hoisted above the drift scan).
* tests/test_push_webhook.py::TestTheIndexClaimIsAtomic — the claim's own
  semantics (two simultaneous claims, polling skipping a held repo, a free repo
  still being claimable).
* tests/test_code_fail_stale.py — the `stale` status and the "keep serving the
  prior graph" contract.
* tests/test_index_debt.py, tests/test_code_pipeline_integration.py — the
  incremental path `forced_files` feeds.

FILE COLLISION WARNING for the orchestrator: finding F03 also edits
backend/app/services/repo_manager.py, in `pull_repo` (~line 394). This task's
edit is an insertion at line 240-241, a different region — the two merge
cleanly but must not be applied by two concurrent worktrees writing the whole
file. F04 edits backend/app/services/code_pipeline.py, which this task does not
touch.

DEPLOY: this alters backend/, so per CLAUDE.md the host needs the full
`./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh` →
`docker compose up -d` → confirm-the-change-is-in-the-image sequence after it
lands.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/job_runners.py backend/app/services/repo_manager.py backend/tests/test_code_reconcile.py
git commit -m "fix(jobs): take the indexing claim in code_reconcile"
```

### Task 3: Fix MCP code_symbol raising MissingGreenlet on every hit

**Effort:** ~20 minutes.

**Files:**
- Modify: `backend/app/api/mcp/server.py:852-876`
- Test: `backend/tests/test_mcp_surface_parity.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

- [ ] **Step 1: Write the failing test**

Insert the function below into the existing file backend/tests/test_mcp_surface_parity.py,
in the "The code family" section, immediately AFTER the existing
`test_code_blast_radius_still_raises_on_an_unknown_symbol` (which currently ends at line
239) and BEFORE the `# Identity` divider comment. Separate it from its neighbours with the
usual two blank lines.

No new imports are needed: the file already imports `json`, `uuid`, `pytest`,
`app.api.mcp.server as mcp_server` and `CodeFile, CodeSymbol, Repository` from
`app.models.code`, and it already defines the `mcp_session` fixture this test uses.

async def test_code_symbol_serves_the_file_path_of_a_symbol_that_exists(mcp_session):
    """The tool must publish the path of the row it selected.

    It read ``CodeSymbol.file`` instead -- the one relationship in the code
    models left at SQLAlchemy's default ``lazy="select"`` -- and the tool's own
    ``select(CodeSymbol).join(CodeFile)`` puts no ``CodeFile`` in the identity
    map, so the dereference emitted a SELECT from outside greenlet context and
    every symbol that exists answered ``MissingGreenlet``. Only the not-found
    path worked, which is why the parity roster could register the tool and
    stay green.

    ``expunge_all`` is load-bearing: a many-to-one lazy load answered from the
    identity map emits no IO, so a session still holding the seeded
    ``CodeFile`` passes here while production fails.
    """
    repo = Repository(name="symbol-repo")
    mcp_session.add(repo)
    await mcp_session.flush()
    code_file = CodeFile(
        id=uuid.uuid4(), repo_id=repo.id, file_path="pkg/pipeline.py",
        language="python", content_hash="h",
    )
    mcp_session.add(code_file)
    await mcp_session.flush()
    mcp_session.add(CodeSymbol(
        id=uuid.uuid4(), file_id=code_file.id, name="ProcessingPipeline",
        kind="class", line_start=10, line_end=42,
        source_code="class ProcessingPipeline: ...",
        signature="class ProcessingPipeline", visibility="public",
    ))
    await mcp_session.flush()
    mcp_session.expunge_all()

    rows = json.loads(await mcp_server.code_symbol(
        name="ProcessingPipeline", repo_name="symbol-repo",
    ))

    assert [r["file_path"] for r in rows] == ["pkg/pipeline.py"]
    assert rows[0]["name"] == "ProcessingPipeline"
    assert rows[0]["kind"] == "class"
    assert rows[0]["line_start"] == 10

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_mcp_surface_parity.py::test_code_symbol_serves_the_file_path_of_a_symbol_that_exists

(Needs the dev Postgres on 127.0.0.1:5433 and the darkmem_test database. To run on a
private lane database instead, prefix with
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/<your_db>.)
```

Expected — this is what the run actually printed on master:

The test errors out of the tool call, not out of an assertion. Verified today against the
unmodified tree:

    app/api/mcp/server.py:866: in code_symbol
        "file_path": s.file.file_path if s.file else "",
    ...
    E   sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call
        await_only() here. Was IO attempted in an unexpected place?
        (Background on this error at: https://sqlalche.me/e/20/xd2s)

    .venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py:123: MissingGreenlet
    =========================== short test summary info ============================
    FAILED tests/test_mcp_surface_parity.py::test_code_symbol_serves_the_file_path_of_a_symbol_that_exists
    1 failed, 2 warnings in 2.77s

Running the whole file on the unmodified tree gives "1 failed, 8 passed".

- [ ] **Step 3: Apply the fix**

One file, one function: `code_symbol` in backend/app/api/mcp/server.py.

The tool selects only `CodeSymbol` columns and then walks the `CodeSymbol.file`
relationship. That relationship is declared at backend/app/models/code.py:68 with no
`lazy=` argument, so it is SQLAlchemy's default `lazy="select"`. The `JOIN code_files` in
the query does not put any `CodeFile` into the session's identity map, so the many-to-one
`use_get` shortcut misses and SQLAlchemy emits a real SELECT — from a plain coroutine, not
from inside `greenlet_spawn`, which `AsyncSession` answers with `MissingGreenlet`.

The fix is the shape `code_context` (server.py:1011) and `code_rename` (server.py:1295)
already use: select the path as a second column and read it off the row.

CURRENT CODE — backend/app/api/mcp/server.py, lines 852-876 (inside
`async with _code_service_context() as session:`):

        query = select(CodeSymbol).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == name)
        rows = (await session.execute(query)).scalars().all()

        if not rows:
            raise ValueError(f"Symbol not found: {name}")

        return json.dumps([
            {
                "id": str(s.id),
                "name": s.name,
                "kind": s.kind,
                "file_path": s.file.file_path if s.file else "",
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "docstring": s.docstring,
                "source_code": s.source_code,
                "summary": s.summary,
                "visibility": s.visibility,
            }
            for s in rows
        ])

REPLACEMENT — same 25 lines, same indentation:

        query = select(CodeSymbol, CodeFile.file_path).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == name)
        rows = (await session.execute(query)).all()

        if not rows:
            raise ValueError(f"Symbol not found: {name}")

        return json.dumps([
            {
                "id": str(s.id),
                "name": s.name,
                "kind": s.kind,
                "file_path": file_path,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "docstring": s.docstring,
                "source_code": s.source_code,
                "summary": s.summary,
                "visibility": s.visibility,
            }
            for s, file_path in rows
        ])

Exactly three edits: add `, CodeFile.file_path` to the `select(...)`; drop `.scalars()` so
`.all()` yields `(CodeSymbol, str)` rows; and unpack `for s, file_path in rows`, with
`"file_path": file_path` replacing the relationship walk. No new imports (`CodeFile` is
already imported at line 849). No comment is warranted — the two sibling tools in this same
module already carry this shape uncommented.

Two things NOT to change, both checked:
* `code_file_symbols` (server.py:893-912) and `code_blast_radius` (server.py:935+) sit
  beside this and are already safe — neither dereferences `.file`.
* `CodeFile.repository` (models/code.py:44) is also at the default `lazy="select"`, so the
  finding's "the only relationship not selectin" is slightly off. It is dereferenced
  nowhere in `backend/app`, so it needs no change. `rg -n "\.file\.file_path"
  backend/app` returns exactly one hit, the line being fixed.

No schema change; backend/migrations/versions/0001_baseline.py is untouched.

This edits backend/, so the host needs the standard redeploy after it lands:
./scripts/gate.sh -> DARKMEM_PUSH=0 ./scripts/build-push.sh -> docker compose up -d ->
wait for healthy -> confirm the new code is in the running image.

- [ ] **Step 4: Run the same command and confirm it passes**

    1 passed, 2 warnings in 0.9s

and the whole file:

    cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_mcp_surface_parity.py
    9 passed, 2 warnings in 0.87s

Both verified today by applying the replacement, running, and then reverting the tree.

- [ ] **Step 5: Run the surrounding suite for regressions**

Low and contained. `code_symbol` is the only caller of this query and nothing else in the
tree reads `CodeSymbol.file`, so the blast radius is one tool's JSON body.

The one real behaviour change beyond "it stops raising": `.scalars().all()` becomes
`.all()`, so `rows` is a list of `Row` tuples rather than ORM objects. Anything added later
that iterates `rows` expecting a bare `CodeSymbol` would break; the same statement now
covers both the emptiness check (`if not rows`) and the projection, and both are inside
this function.

Second, subtler point: the JOIN was already there, so a symbol whose `file_id` dangles was
filtered out before and still is — the `if s.file else ""` fallback was dead code, not a
guarded case, and dropping it changes nothing. A symbol name appearing in several files
still returns one row per file, now each with its own correct path.

Third: with `repo_name` supplied, `CodeFile` is joined once and `Repository` is joined onto
it. Selecting `CodeFile.file_path` adds no second FROM entry, so the row count and the
generated plan are unchanged. Verified by the passing suite rather than by inspection.

Existing tests covering the surrounding behaviour, all run together with the fix applied
(58 passed):
  backend/tests/test_mcp_surface_parity.py   - the MCP code family (code_search,
                                               code_blast_radius) and the mcp_session fixture
  backend/tests/test_door_parity.py          - the code.symbols two-door roster entry that
                                               registers this tool (line ~408)
  backend/tests/test_mcp.py                  - the MCP door's memory + code_search tests
  backend/tests/test_code_search_order.py    - CodeQueryService's own symbol queries
  backend/tests/test_wiki_symbol_query.py    - CodeSymbol/CodeFile ORM seeding and N+1 guard
  backend/tests/test_repositories.py         - repo/file/symbol counts
  backend/tests/test_mcp_vault_tools.py      - the other MCP tool family on the same session
                                               plumbing

Note the door-parity note for `code.symbols` says the two implementations are "not yet
observably divergent". That is currently false — the MCP door raises where REST answers —
and the fix is what makes the note true again, so it needs no edit.

Test-side risk worth flagging to whoever applies this: the `mcp_session.expunge_all()` in
the new test is not decoration. Without it the seeded `CodeFile` sits in the identity map,
the many-to-one lazy load is served from there with no IO, and the test passes against the
broken code. I confirmed that directly: the same test minus `expunge_all` passes on the
unmodified tree. Do not "tidy" that line away.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp_surface_parity.py
git commit -m "fix(mcp): serve code_symbol file path from its query"
```

---

## Finishing this plan

- [ ] `./scripts/gate.sh` from the repo root — the floor is enough here; nothing in this plan touches compose, the browser, or the ranking path.
- [ ] Redeploy: all three are `backend/app`. Confirm in the image, e.g. `docker exec darkmem-prod-darkmem-1 grep -n 'claim_for_indexing' app/services/job_runners.py`.
- [ ] Answer Task 2's owner decision (what status a reconcile run that dies mid-flight should leave behind) before starting, not during.
