# R1 — Stop the Two Unrecoverable Data Losses

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** darkmem can no longer destroy an operator's own git checkout, a restore can no longer gut a live database it then fails to repopulate, a failed backup can no longer masquerade as a good one, and no eval script can purge whatever `DATABASE_URL` happens to point at.

**Architecture:** Four independent changes, no shared code between the first three. Each one replaces a destructive operation with a refusing one: `reset --hard` becomes `merge --ff-only` on a checkout darkmem does not own; the restore recreates the database instead of dropping objects inside a live one; the dump lands under a temporary name and is renamed only on success; the eval scripts call the target guard that already exists.

**Tech Stack:** Python 3.13, SQLAlchemy async, asyncpg, pytest, bash, PostgreSQL 16, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-24-review-remediation.md`

## Why this plan runs first

These are the only findings in the review whose failure mode has no undo. Everything
else in the programme is wrong behaviour that can be corrected once it is noticed.
These four destroy something first and are noticed afterwards, or not at all:

| Finding | What is gone |
|---|---|
| F03 `repo_manager.py:394` | The operator's uncommitted edits and unpushed commits, recoverable only from the reflog |
| F07 `restore.sh:20` | Every foreign key and every trigger on a live database, including the append-only guards on the audit journal |
| F08 `backup.sh:18` | A real backup, deleted by the retention prune to keep an empty one |
| `purge_eval.py:27` | Every supersession lineage in the corpus, in whatever database `DATABASE_URL` resolved to |

F03 is the sharpest of the four because the job that fires it is `code_reconcile`,
whose entire purpose is to notice that the operator edited that working tree.

## Global Constraints

- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q <path>`. Needs the dev Postgres on `127.0.0.1:5433` and database `darkmem_test`. Baseline on master today is **6179 passed, 22 skipped** — a change in that count is a signal, not noise.
- **Parallel lanes need their own database.** `darkmem_test_2` … `darkmem_test_5` exist for this. Keep `darkmem_test` for whoever runs the controller gate. conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` and then runs `DROP SCHEMA public CASCADE` — never point a lane at a real database.
- **Frontend tests:** from `frontend/`, `npx vitest run <path>`. Typecheck is `npx tsc -b` (plain `tsc` misses the project refs). Baseline is **1233 passing**.
- **Merge gate:** `./scripts/gate.sh` from the repo root. `--full` adds the retrieval eval, the API e2e suite, Playwright and a port-hygiene diff. Each task below says which it needs and why.
- **Commits:** `<type>(<scope>): <subject>`, type one of `feat|fix|docs|style|refactor|test|chore|perf`, subject imperative, ≤ 50 characters, no trailing period. Atomic — never combine two concerns.
- **Comments:** default to none. Add one only where the WHY is non-obvious — a hidden constraint, a subtle invariant, a workaround for a specific bug. Never explain WHAT the code does; never reference this plan, this task, or a ticket.
- **Never** hardcode a value or special-case an input to make a test pass, and never use `--no-verify`. If a fix turns out to be infeasible or a finding turns out to be wrong, say so and stop — do not work around it.
- **Order inside this plan is fixed:** Task 1 (F03) → Task 2 (F07) → Task 3 (F08) → Task 4 (the harness guard). Task 2 before Task 3 because F07's open question — whether `backup.sh` should stop emitting `--clean --if-exists` at all — only makes sense once `restore.sh` recreates the database, and Task 3 is the change that will be sitting in that file.
- **Three tasks append to `backend/tests/test_deployment_artifact.py`,** which is also claimed by R2. F07 lands here first; R2's additions go on top. Two lanes appending to the same 194-line file at the same offset conflict mechanically for no semantic reason.
- **Only Task 1 needs a redeploy.** `scripts/backup.sh`, `scripts/restore.sh` and `backend/scripts/` are not copied into the image, so Tasks 2–4 change operator procedure and nothing the container runs. Confirm Task 1 in the running image with `docker exec darkmem-prod-darkmem-1 grep -n 'ff-only' app/services/repo_manager.py`.
- **Prerequisite:** the working tree must be committed first (see the spec's Stage 0). `backend/app/services/code_pipeline.py` currently carries an uncommitted fix that is not this plan's.

---

### Task 1: Stop pull_repo hard-resetting the operator's own checkout

**Effort:** ~35 minutes.

**Files:**
- Modify: `backend/app/services/repo_manager.py:370-397`
- Test: `backend/tests/test_repos.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Should a `local_path` repository update its working tree at all? This plan keeps
the pull and makes it non-destructive (`merge --ff-only`), because the setup
wizard's own code comment tells the operator they are enabling auto-*pull*. The
stricter alternative -- `if is_local: return None` before the fetch, so darkmem
never runs a mutating git command in a tree it does not own -- is two lines
instead of eight and has no failure modes or log noise at all, but it silently
turns auto-sync into a no-op for every wizard-registered folder and would make
`test_pull_repo_fast_forwards_a_clean_local_checkout` fail. Either way the
critical bug is closed; only the owner can say which of "my folder tracks its
remote" and "darkmem never writes to my checkout" is the product promise.

- [ ] **Step 1: Write the failing test**

Append the following to the END of backend/tests/test_repos.py (the file has no
module-level imports by convention -- every test imports inside its own body --
so the three helpers below import `subprocess` locally, matching
`tests/test_code_reconcile.py::_git_init_repo`).

```python


def _git(cwd, *args) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=test@test.local", "-c", "user.name=Test", *args],
        cwd=str(cwd), check=True, capture_output=True,
    )


def _head(cwd) -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(cwd), capture_output=True, text=True,
    ).stdout.strip()


def _upstream_and_checkout(tmp_path):
    """An upstream repo one commit ahead of the operator's own clone of it.

    This is the shape the setup wizard's folder picker registers: a
    ``local_path`` repo whose ``origin`` remote resolves and fetches. The
    remote-less checkouts in ``test_code_reconcile.py`` never reach the
    fetch-succeeded branch of ``pull_repo`` at all.
    """
    import subprocess

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-q", "-m", "one")

    checkout = tmp_path / "checkout"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(checkout)],
        check=True, capture_output=True,
    )

    (upstream / "shipped.py").write_text("SHIPPED = True\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-q", "-m", "two")
    return upstream, checkout


async def test_pull_repo_never_rewinds_a_local_checkout(session, tmp_path):
    """`pull_repo` must not discard work in a tree the app does not own.

    `local_path` points at the operator's own checkout and `git reset --hard`
    moves the branch ref as well as the working tree, so a repo registered
    with a live `origin` lost both the uncommitted edit and the unpushed
    commit on the next `repo_sync` or `code_reconcile` tick -- the second of
    those being the job whose whole purpose is to notice that edit.
    """
    from app.models.code import Repository
    from app.services.repo_manager import RepoManager

    _, checkout = _upstream_and_checkout(tmp_path)

    (checkout / "wip.py").write_text("WIP = True\n", encoding="utf-8")
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "-q", "-m", "operator work, not pushed")
    operator_head = _head(checkout)
    edit = "VERSION = 1  # operator edit\n"
    (checkout / "app.py").write_text(edit, encoding="utf-8")

    repo = Repository(
        name="operator-checkout", local_path=str(checkout), default_branch="main",
    )
    session.add(repo)
    await session.flush()

    await RepoManager(session).pull_repo(repo)

    assert (checkout / "app.py").read_text(encoding="utf-8") == edit
    assert (checkout / "wip.py").exists()
    assert _head(checkout) == operator_head


async def test_pull_repo_fast_forwards_a_clean_local_checkout(session, tmp_path):
    """The other half of the same branch: a checkout holding nothing of its
    own still tracks its remote, so refusing to rewind must not turn a
    registered folder's auto-sync into a permanent no-op."""
    from app.models.code import Repository
    from app.services.repo_manager import RepoManager

    upstream, checkout = _upstream_and_checkout(tmp_path)

    repo = Repository(
        name="clean-checkout", local_path=str(checkout), default_branch="main",
    )
    session.add(repo)
    await session.flush()

    sha = await RepoManager(session).pull_repo(repo)

    assert sha == _head(upstream)
    assert (checkout / "shipped.py").exists()
```

Notes for whoever applies this:

- `test_pull_repo_never_rewinds_a_local_checkout` is the failing test. It fails
  today on all three of its assertions, the first being the one pytest reports.
- `test_pull_repo_fast_forwards_a_clean_local_checkout` PASSES both before and
  after the fix on purpose. It is the guard rail against over-correcting the
  fix into "never touch a local checkout at all", which would silently make
  auto-sync a no-op for every wizard-registered folder. Keep it.
- The tests use the `session` fixture (DB-backed, rolled back per test) purely
  so the `Repository` row is realistic; `pull_repo` itself resolves everything
  off the ORM object and only touches the DB when `auth_token_ref` is set.
- `git init -b main` needs git >= 2.28 (the host has 2.47.3).

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_repos.py -k pull_repo

(Needs the dev Postgres on 127.0.0.1:5433 with database darkmem_test. If another
lane is using darkmem_test concurrently, prefix the command with
TEST_DATABASE_URL='postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2'
or another free lane database -- I verified this task against a throwaway
darkmem_test_f03 which I created and dropped again.)
```

Expected — this is what the run actually printed on master:

```
>       assert (checkout / "app.py").read_text(encoding="utf-8") == edit
E       AssertionError: assert 'VERSION = 1\n' == 'VERSION = 1 ...erator edit\n'
E
E         - VERSION = 1  # operator edit
E         + VERSION = 1

tests/test_repos.py:345: AssertionError
=========================== short test summary info ============================
FAILED tests/test_repos.py::test_pull_repo_never_rewinds_a_local_checkout - A...
1 failed, 1 passed, 14 deselected, 1 warning in 2.48s
```

The uncommitted edit is gone because `git reset --hard FETCH_HEAD` restored
`app.py` to the upstream content. Had the run got past that line, the other two
assertions would have failed too: `wip.py` no longer exists and HEAD has been
moved off the operator's unpushed commit onto origin/main. I confirmed all three
with a standalone reproduction before writing the test -- the operator's local
commit is only recoverable from the reflog after one tick of this job.

- [ ] **Step 3: Apply the fix**

Two edits, both inside `pull_repo` in `backend/app/services/repo_manager.py`.

EDIT 1 -- amend the `is_local` comment (currently lines 372-373) so the rule it
states covers the new branch as well.

Current code:

```python
        # local_path repos point at the operator's OWN checkout; that working
        # tree must never be rmtree'd or re-cloned (the reclone fallback below).
        is_local = bool(repo.local_path)
```

Replacement:

```python
        # local_path repos point at the operator's OWN checkout; that working
        # tree must never be rmtree'd, re-cloned (the reclone fallback below)
        # or rewound (the fast-forward branch below).
        is_local = bool(repo.local_path)
```

EDIT 2 -- split the update step (currently lines 393-394).

Current code:

```python
                await self._run_git(cwd, ["git", "fetch", fetch_target, repo.default_branch], env=env)
                await self._run_git(cwd, ["git", "reset", "--hard", "FETCH_HEAD"], env=env)
```

Replacement:

```python
                await self._run_git(cwd, ["git", "fetch", fetch_target, repo.default_branch], env=env)
                if is_local:
                    # `reset --hard` moves the branch ref as well as the tree, so
                    # on the operator's own checkout it discards uncommitted edits
                    # and any commit they have not pushed. `--ff-only` advances or
                    # refuses; a refusal lands in the RuntimeError branch below,
                    # which leaves the tree alone and lets the caller read HEAD.
                    await self._run_git(cwd, ["git", "merge", "--ff-only", "FETCH_HEAD"], env=env)
                else:
                    await self._run_git(cwd, ["git", "reset", "--hard", "FETCH_HEAD"], env=env)
```

Nothing else changes. In particular:

- The `except RuntimeError` block immediately below already does the right thing
  with a refused fast-forward: for `is_local` it logs
  "Pull failed for local repo ... (working tree left intact)" and returns `None`,
  and `CodePipeline.run` then reads HEAD off disk itself
  (`code_pipeline.py:166-171`). So a diverged or dirty checkout indexes the bytes
  that are actually on disk -- exactly what `code_reconcile` wants.
- The re-clone fallback further down is already gated on `not is_local`, so it
  is untouched.
- Leave the existing "reset to FETCH_HEAD since the remote-tracking ref isn't
  updated when fetching from a bare URL" comment where it is; it explains why
  `FETCH_HEAD` rather than `origin/<branch>` is the target, which is still true
  of both branches.

Why `merge --ff-only` and not simply skipping the update for local repos: git
itself refuses every destructive case, so this keeps the auto-pull the setup
wizard advertises ("once they're sure each one should be auto-pulled",
`backend/app/api/routes/setup.py:556-560`) without any path that can lose work.
The four refusal cases are (1) local commits ahead -> not a fast-forward,
(2) local branch diverged -> not a fast-forward, (3) a tracked file with
uncommitted changes that the incoming commits touch -> "local changes would be
overwritten", (4) an untracked file the incoming commits would add -> "untracked
working tree files would be overwritten". All four raise `RuntimeError` out of
`_run_git` and land in the existing local branch. The only case that proceeds is
a clean fast-forward, which is what `git pull --ff-only` does and is the
behaviour an operator who ticked auto-sync asked for.

A local checkout with NO fetchable `origin` (the shape
`tests/test_code_reconcile.py::_git_init_repo` builds, and the case
`code_reconcile`'s module docstring describes) is unaffected: its `git fetch`
already fails before either branch is reached.

- [ ] **Step 4: Run the same command and confirm it passes**

```
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_repos.py -k pull_repo
..                                                                       [100%]
2 passed, 14 deselected, 1 warning in 1.55s
```

I also ran the surrounding suites with the fix applied:

```
.venv/bin/python -m pytest -q tests/test_repos.py tests/test_repositories.py \
  tests/test_code_reconcile.py tests/test_index_debt.py tests/test_code_fail_stale.py \
  tests/test_push_webhook.py tests/test_code_pipeline_integration.py \
  tests/test_summary_carryover.py tests/test_code_deriver.py
176 passed, 39 warnings in 11.61s
```

- [ ] **Step 5: Run the surrounding suite for regressions**

Low, and bounded to `local_path` repositories -- clone-directory repos (anything
with a `url` and no `local_path`) take the untouched `else` branch and behave
byte-for-byte as before.

What genuinely changes for a `local_path` repo whose `origin` fetches:

1. It is no longer force-synced to origin. If the operator's checkout has local
   commits, is on a different branch, or has uncommitted changes to files the
   incoming commits touch, the fast-forward is refused and darkmem indexes what
   is on disk instead of what is on origin. That is the point of the fix, but it
   is a behaviour change an operator could notice as "my repo stopped updating".
   It surfaces as the existing warning line
   "Pull failed for local repo <name> (working tree left intact)".
2. Log noise: `RepoManager._run_git` logs at ERROR on any non-zero git exit, so a
   permanently-diverged local checkout with auto_sync on now logs one ERROR per
   `repo_sync` tick (every 5 minutes). This is not new in kind -- a `local_path`
   repo with no `origin` at all already logs an ERROR on its failing `git fetch`
   every tick today, and `code_reconcile`'s module docstring documents that path
   as the normal case -- but it is new for this class of repo. If it proves
   annoying the follow-up is to demote the expected refusals in `_run_git`, not
   to reinstate the reset.

Existing tests that cover the surrounding behaviour, all passing with the fix:

- `backend/tests/test_code_reconcile.py::test_runner_reconciles_drifted_repo_and_skips_clean_one`
  -- real remote-less git checkouts through the real `pull_repo`; the closest
  thing to end-to-end coverage this function has.
- `backend/tests/test_code_reconcile.py` (12 tests) -- the drift job as a whole.
- `backend/tests/test_code_fail_stale.py` -- the `stale`/`error` terminal-status
  paths that a `pull_repo` returning `None` feeds into.
- `backend/tests/test_index_debt.py`, `backend/tests/test_summary_carryover.py`,
  `backend/tests/test_push_webhook.py`,
  `backend/tests/test_code_pipeline_integration.py` -- all stub `pull_repo`, so
  they pin `CodePipeline.run`'s side of the contract rather than this function.
- `backend/tests/test_repos.py` -- the repo routes plus the existing `RepoManager`
  unit tests.

CONCURRENCY WARNING for whoever schedules this: while I was verifying, another
agent in this session was editing `backend/app/services/repo_manager.py` in the
same working tree (adding a `release_indexing_claim` method and an `OSError`
handler in `_run_git`, then reverting them again). This file is contended --
serialise this task against any other task that touches it, and re-read
`pull_repo` before applying the two edits above rather than trusting the line
numbers.

This changes `backend/`, so it alters the running artifact: after it lands the
host needs `./scripts/gate.sh` -> `DARKMEM_PUSH=0 ./scripts/build-push.sh` ->
`docker compose up -d`, then a check that the new `merge --ff-only` line is in
the built image. It does not touch `backend/migrations/versions/0001_baseline.py`
and needs no schema change.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/repo_manager.py backend/tests/test_repos.py
git commit -m "fix(repos): never rewind a local_path working tree"
```

### Task 2: Restore into a recreated database, not over a live one

**Effort:** ~45 minutes.

**Files:**
- Modify: `scripts/restore.sh:1-23 (whole file replaced)`
- Modify: `backend/tests/test_deployment_artifact.py:29-30 (add the RESTORE path constant) and :194-end (append the new section)`
- Modify: `docs/wiki/deployment-guide.md:85-86`
- Test: `backend/tests/test_deployment_artifact.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Should `backup.sh` also stop passing `--clean --if-exists`? Once restore.sh
recreates the database, those DROP statements are dead weight in every future
dump, and while they exist the landmine stays armed for anyone who replays a
dump by hand (`gunzip -c d.sql.gz | psql -d darkmem`) rather than through
restore.sh. Two reasons it is left out of this task and needs the owner's call:
finding F08 is already editing `backup.sh` and the two changes would collide,
and dropping the flag would mean dumps taken before and after the change behave
differently under a hand-rolled replay. The restore path itself is fully
repaired either way, for both old and new dumps.

- [ ] **Step 1: Write the failing test**

## Which kind of test this is

`scripts/restore.sh` is a shell script that drives `docker compose exec`, so
per the house rule the test is a real assertion in
`backend/tests/test_deployment_artifact.py` (that file exists for exactly this
and its own module docstring explains the trade-off: it reads the shipped
artefact as text). The behavioural proof — an actual dump replayed into an
actual database, both before and after the fix — is the runnable reproduction
command recorded under `expected_failure` / `expected_pass`; it needs a running
compose Postgres and a `pg_dump` binary, neither of which the pytest suite may
assume, so it stays a command rather than a test.

## Step 1 — add the path constant beside the other artefact paths

In the block at the top of the file that already reads:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"
DEV_SERVER = REPO_ROOT / "scripts" / "start_dev_server.sh"
PROD_COMPOSE = REPO_ROOT / "docker-compose.yml"
DEV_COMPOSE = REPO_ROOT / "docker-compose.dev.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
```

add one line after `DOCKERFILE`:

```python
RESTORE = REPO_ROOT / "scripts" / "restore.sh"
```

## Step 2 — append this section at the end of the file

(The block below repeats the `RESTORE = ...` line so it is self-contained and
runs if pasted alone; delete that repeat once step 1 is applied — module-level
assignment order does not matter here, the constant is only read at call time.)

```python


# ── The restore path replays into an empty database, never over a live one ──

RESTORE = REPO_ROOT / "scripts" / "restore.sh"


def _restore_lines() -> list[str]:
    """Comment-free, so a comment naming a statement cannot be read as one."""
    return [
        ln for ln in _unwrapped(RESTORE).splitlines()
        if not ln.lstrip().startswith("#")
    ]


def _one(lines: list[str], predicate) -> int:
    hits = [i for i, ln in enumerate(lines) if predicate(ln)]
    assert len(hits) == 1, hits
    return hits[0]


def test_restore_recreates_the_database_before_replaying_the_dump():
    """`events` is declaratively RANGE-partitioned, so backup.sh's
    ``--clean --if-exists`` dump carries ``ALTER TABLE IF EXISTS ONLY
    public.events_YYYYMM DROP CONSTRAINT IF EXISTS events_YYYYMM_pkey`` for
    every monthly child, and PostgreSQL refuses to drop an inherited
    constraint. Replayed over a database that still holds the schema, that
    error aborts psql under ON_ERROR_STOP partway through the DROP phase --
    after every trigger and every foreign key above it has already been
    dropped and before the first CREATE runs. The operator sees a non-zero
    exit and a database that still has all its rows, none of its foreign
    keys, and neither the events append-only guards nor the search_vector
    trigger. Recreating the database first leaves those statements nothing
    to match, which is the only shape that cannot reach the error."""
    lines = _restore_lines()
    recreate = _one(lines, lambda ln: "CREATE DATABASE" in ln)
    replay = _one(lines, lambda ln: "gunzip -c" in ln and "psql" in ln)
    assert recreate < replay, "the dump is replayed before the database is recreated"

    statement = lines[recreate]
    assert "-d postgres" in statement, statement
    assert "DROP DATABASE" in statement, statement
    assert "$DB" in statement, statement


def test_restore_proves_the_dump_is_complete_before_dropping_the_database():
    """Recreating means the dump is the only surviving copy from that point
    on, so an unreadable one must be refused while the database still
    exists. gzip of an empty stream is valid gzip, so integrity alone proves
    nothing -- pg_dump's completion marker, the same evidence backup.sh
    checks before it publishes a dump, is what proves there is something to
    restore."""
    lines = _restore_lines()
    marker = _one(lines, lambda ln: "PostgreSQL database dump complete" in ln)
    drop = _one(lines, lambda ln: "DROP DATABASE" in ln)
    assert marker < drop, "the dump is validated only after the database is gone"


def test_restore_still_stops_on_the_first_error_it_meets():
    lines = _restore_lines()
    replay = lines[_one(lines, lambda ln: "gunzip -c" in ln and "psql" in ln)]
    assert "-v ON_ERROR_STOP=1" in replay, replay
```

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_deployment_artifact.py
```

Expected — this is what the run actually printed on master:

A. The pytest test, run against today's `scripts/restore.sh` (verified — this
is the real captured output):

    FAILED tests/test_deployment_artifact.py::test_restore_recreates_the_database_before_replaying_the_dump
    FAILED tests/test_deployment_artifact.py::test_restore_proves_the_dump_is_complete_before_dropping_the_database
    2 failed, 24 passed, 1 warning in 0.73s

with the first failure reading:

    lines = _restore_lines()
    >   recreate = _one(lines, lambda ln: "CREATE DATABASE" in ln)
    E   AssertionError: []
    E   assert 0 == 1

i.e. restore.sh contains no `CREATE DATABASE` at all — it pipes the dump
straight into the live database.

B. The behavioural reproduction (verified against the dev Postgres,
`darkmem-postgres-1` on 127.0.0.1:5433, and against the real production dump
/root/darkmem-backups/darkmem-20260824-033009.sql.gz). Run from any directory:

    # two databases, both migrated to the baseline
    docker exec -i darkmem-postgres-1 psql -U darkmem -d darkmem -c 'CREATE DATABASE f07_a;'
    docker exec -i darkmem-postgres-1 psql -U darkmem -d darkmem -c 'CREATE DATABASE f07_b;'
    cd /root/repositories/darkmem/backend
    for d in f07_a f07_b; do
      DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/$d" \
        .venv/bin/python -m alembic upgrade head
    done

    # what backup.sh produces
    docker exec -i darkmem-postgres-1 pg_dump -U darkmem -d f07_a --clean --if-exists > /tmp/f07_a.sql

    # what restore.sh does today: replay it over a database that has the schema
    docker exec -i darkmem-postgres-1 psql -U darkmem -d f07_b -At \
      -c "select (select count(*) from pg_trigger where not tgisinternal),
                 (select count(*) from pg_constraint where contype='f')"
    cat /tmp/f07_a.sql | docker exec -i darkmem-postgres-1 psql -U darkmem -d f07_b -v ON_ERROR_STOP=1
    echo "rc=$?"
    docker exec -i darkmem-postgres-1 psql -U darkmem -d f07_b -At \
      -c "select (select count(*) from pg_trigger where not tgisinternal),
                 (select count(*) from pg_constraint where contype='f')"

Observed output today:

    11|27                                                    <- before: 11 triggers, 27 FKs
    ERROR:  cannot drop inherited constraint "events_202609_pkey" of relation "events_202609"
    rc=3
    0|0                                                      <- after: every trigger and every FK gone

The dump line that causes it is present in the output of every backup.sh run:

    ALTER TABLE IF EXISTS ONLY public.events_202609 DROP CONSTRAINT IF EXISTS events_202609_pkey;
    ALTER TABLE IF EXISTS ONLY public.events_202608 DROP CONSTRAINT IF EXISTS events_202608_pkey;

The abort lands after the dump's DROP TRIGGER / FK DROP CONSTRAINT block and
before its first CREATE, which is why the rows survive and the structure does
not. Gone with it: `events_forbid_row`, `events_forbid_truncate` and the
per-child truncate guards (the append-only enforcement), `memories_fts_update`
(so `search_vector` stops updating and hybrid search's keyword arm silently
stops seeing new memories), all four `touch_updated_at` triggers, and every
foreign key including `fk_memories_superseded_by`.

- [ ] **Step 3: Apply the fix**

## The change: replace `scripts/restore.sh` in full

Two things change. The script recreates the target database before replaying
(the fix), and it proves the dump is complete before it does so (required,
because recreating makes the dump the only surviving copy — without this, a
bad dump would turn a failed restore into total data loss).

`backup.sh` is deliberately NOT touched: the 14 dumps already on disk were
made with `--clean --if-exists` and must stay restorable, and finding F08 is
already editing that file.

### CURRENT code — the whole of `scripts/restore.sh` (23 lines)

```bash
#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by backup.sh.
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
# WARNING: this overwrites the current database. Stop the API first.
set -euo pipefail

BACKUP_FILE="${1:?usage: restore.sh BACKUP_FILE.sql.gz}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

echo "This will OVERWRITE database '$DB'. Stop the darkmem service first."
read -r -p "Restore from $BACKUP_FILE? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }

echo "Restoring..."
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Restore complete. Restart the API:  $COMPOSE up -d darkmem"
```

### REPLACEMENT — write this over the file, keep it executable (`chmod +x`) and LF-only

```bash
#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by backup.sh.
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
# WARNING: this drops and recreates the database. Stop the API first.
set -euo pipefail

BACKUP_FILE="${1:?usage: restore.sh BACKUP_FILE.sql.gz}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

# From the recreate below onwards this file is the only surviving copy, so it is
# proved good while the database still exists. gzip of an empty stream is itself
# valid gzip, so integrity alone proves nothing — pg_dump writes the completion
# marker last and only on success, the same evidence backup.sh checks before it
# publishes a dump.
if ! gunzip -c "$BACKUP_FILE" 2>/dev/null | tail -c 512 \
     | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Not a complete pg_dump dump: $BACKUP_FILE" >&2
    echo "Nothing was changed." >&2
    exit 1
fi

echo "This will DROP AND RECREATE database '$DB'. Stop the darkmem service first."
read -r -p "Restore from $BACKUP_FILE? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }

# Never replay a --clean dump over a live schema. `events` is declaratively
# RANGE-partitioned, so the dump's DROP phase carries one `ALTER TABLE ONLY
# events_YYYYMM DROP CONSTRAINT events_YYYYMM_pkey` per monthly child, and
# PostgreSQL refuses to drop an inherited constraint. ON_ERROR_STOP aborts
# there — after every trigger and foreign key above it is already gone and
# before the first CREATE — leaving a database with all its rows and none of
# its structure. An empty target leaves those statements nothing to match.
echo "Recreating database '$DB'..."
$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE);" \
  -c "CREATE DATABASE \"$DB\" OWNER \"$USER\";"

echo "Restoring..."
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Restore complete. Restart the API:  $COMPOSE up -d darkmem"
```

Notes on the details, so nobody "simplifies" them back:

- `tail -c 512` reads the stream to its end, so it never closes the pipe early;
  a `head -c` here would raise SIGPIPE in `gunzip` and, under `set -o pipefail`,
  fail the check on every good dump. This mirrors the marker check backup.sh
  already runs before it publishes a dump.
- The two `-c` flags must stay two separate flags. `DROP DATABASE` cannot run
  inside a transaction block, and two statements inside ONE `-c` string get an
  implicit one — verified: `psql -c "DROP DATABASE a; DROP DATABASE b;"` fails
  with `ERROR: DROP DATABASE cannot run inside a transaction block`.
- `-d postgres` is required: you cannot drop the database you are connected to.
- `WITH (FORCE)` (PostgreSQL 13+; both compose files run pgvector pg17)
  terminates leftover connections instead of failing when the operator forgot
  to stop the API. It is reached only after an explicit y/N confirmation to
  overwrite the database, so it is strictly less destructive than what follows.
- This is the same drop/recreate `docs/runbook-deployment.md` (the schema-repair
  procedure, around line 220) already performs by hand.

## Docs

`docs/wiki/deployment-guide.md` line 85-86 currently reads:

```markdown
`restore.sh` **overwrites** the live database and prompts before doing it. Stop
the app first.
```

Replace with:

```markdown
`restore.sh` **drops and recreates** the database and prompts before doing it.
Stop the app first. It replays into an empty database on purpose: a
`--clean` dump cannot be replayed over a live schema, because PostgreSQL
refuses to drop the `events` partitions' inherited primary keys and psql
aborts partway through the dump's DROP phase.
```

`README.md` line 131 is only the invocation example and needs no change.

- [ ] **Step 4: Run the same command and confirm it passes**

A. The pytest test, after the fix (verified — real captured output):

    26 passed, 1 warning in 0.72s

(23 tests today, 24 once finding F16's CORS test lands, plus the 3 added here.)

B. The behavioural reproduction, after the fix. Rebuild `f07_a` / `f07_b` as
above, then run the fixed script end to end against the dev compose stack:

    cd /tmp && gzip -c /tmp/f07_a.sql > /tmp/f07_a.sql.gz
    echo y | env \
      COMPOSE_CMD="docker compose -f /root/repositories/darkmem/docker-compose.dev.yml" \
      POSTGRES_SERVICE=postgres POSTGRES_DB=f07_b POSTGRES_USER=darkmem \
      bash /root/repositories/darkmem/scripts/restore.sh /tmp/f07_a.sql.gz
    echo "rc=$?"
    docker exec -i darkmem-postgres-1 psql -U darkmem -d f07_b -At \
      -c "select (select count(*) from pg_trigger where not tgisinternal),
                 (select count(*) from pg_constraint where contype='f'),
                 (select version_num from alembic_version)"

Observed (verified, starting from an f07_b that already held a full live
schema — the exact scenario that destroys it today):

    This will DROP AND RECREATE database 'f07_b'. Stop the darkmem service first.
    Recreating database 'f07_b'...
    DROP DATABASE
    CREATE DATABASE
    Restoring...
    ... (SET / CREATE TABLE / COPY / CREATE INDEX / CREATE TRIGGER / ALTER TABLE)
    Restore complete. Restart the API:  docker compose ... up -d darkmem
    rc=0
    11|27|0001

11 triggers, 27 foreign keys, alembic stamped at the baseline — identical to a
freshly migrated database, where today the same input leaves 0 and 0.

C. The pre-flight refuses without touching anything (verified):

    : | gzip -c > /tmp/empty.sql.gz          # 20 bytes, valid gzip
    echo y | env COMPOSE_CMD=... POSTGRES_DB=f07_b ... bash scripts/restore.sh /tmp/empty.sql.gz
    -> Not a complete pg_dump dump: /tmp/empty.sql.gz
       Nothing was changed.
       rc=1
    and f07_b still reports 11|27.

    head -c 20000 /tmp/f07_a.sql | gzip -c > /tmp/trunc.sql.gz   # truncated mid-dump
    -> same refusal, rc=1, database untouched.

D. Existing dumps stay restorable (verified): all 14 files in
/root/darkmem-backups carry the completion marker, and the newest
(darkmem-20260824-033009.sql.gz) replays into a freshly created database with
rc=0, 11 triggers, 42 foreign keys and 50 memories.

Cleanup after reproducing:

    docker exec -i darkmem-postgres-1 psql -U darkmem -d darkmem \
      -c 'DROP DATABASE IF EXISTS f07_a WITH (FORCE);' \
      -c 'DROP DATABASE IF EXISTS f07_b WITH (FORCE);'

- [ ] **Step 5: Run the surrounding suite for regressions**

**No redeploy needed.** `Dockerfile` copies only `frontend/`, `backend/app/`,
`backend/migrations/`, `backend/alembic.ini` and `entrypoint.sh` — `scripts/`
is never copied into the image. This change does not alter the running
artifact, so the standard "redeploy after every change that lands" rule does
not apply here. The schema baseline is not touched either.

Honest risks, in order:

1. **The window between "y" and a finished replay is now fatal.** Today a
   failed restore leaves the rows (with the structure destroyed); after the
   fix the database is dropped first, so a replay that dies halfway leaves an
   empty database. This is why the completion-marker pre-flight is part of the
   change and runs *before* the prompt: an incomplete or empty dump is refused
   while the database still exists (verified, including the 20-byte empty gzip
   that finding F08 describes and a mid-stream truncation). A complete dump
   replays cleanly — verified end to end and on the real production dump.

2. **`WITH (FORCE)` kills live connections instead of failing.** Without it the
   drop would error out with "database is being accessed by other users" and
   nothing would be lost. It is reached only after an explicit y/N confirmation
   to overwrite the database, and the script still tells the operator to stop
   the API first. If the reviewer prefers the fail-safe posture, drop
   `WITH (FORCE)`; the test does not assert it.

3. **PostgreSQL 13+ required** for `WITH (FORCE)`. Both compose files pin
   pgvector pg17 images, so this holds for every supported stack.

4. **Per-database settings are not preserved.** The recreate is
   `CREATE DATABASE "$DB" OWNER "$USER"` from template1 — the same statement
   `docs/runbook-deployment.md` already runs by hand. A dump made without
   `--create` never carried `ALTER DATABASE ... SET` either, so nothing is lost
   that a restore preserves today.

5. **Verbose psql output.** Unchanged; the restore already echoed every
   statement.

Existing tests covering the surrounding behaviour:

- `backend/tests/test_deployment_artifact.py` (23 tests today) is the only
  automated coverage of the deployment artefacts; nothing anywhere in the
  6179-test suite reads `scripts/restore.sh` or `scripts/backup.sh` today, so
  this task adds the first coverage of either.
- `backend/tests/test_events_append_only.py` and
  `backend/tests/test_partition_templates.py` cover the `events` triggers and
  the per-child partition guards that the abort was silently deleting. They run
  against a migrated database and never see the restore path, so they were
  green throughout — which is exactly why this went unnoticed.
- `backend/tests/test_deployment_artifact.py` is also being edited by finding
  F16 (the CORS test). Both changes are additive and land in different parts of
  the file, but they will conflict textually if applied to the same worktree
  without a rebase.

Run the whole file, not just `-k restore`, when applying:
`cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_deployment_artifact.py`

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_deployment_artifact.py docs/wiki/deployment-guide.md scripts/restore.sh
git commit -m "fix(ops): restore into a recreated database"
```

### Task 3: Never leave a failed backup dump under the keep name

**Effort:** ~25 minutes.

**Files:**
- Modify: `scripts/backup.sh:17-21`
- Create: `backend/tests/test_backup_script.py`
- Test: `backend/tests/test_backup_script.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Only one, and it is scope rather than a blocker: after this fix a failed backup is loud but still only in the systemd journal — `darkmem-backup.service` has no `OnFailure=` unit and nothing notifies the operator. Fourteen silent failed nights now leave the operator with 14 genuine but increasingly stale dumps instead of 14 empty ones, which is strictly better but still not a signal. Whether to add an `OnFailure=` notification unit (or a healthcheck-style touchfile) is the repo owner's call and is deliberately not part of this task.

- [ ] **Step 1: Write the failing test**

"""scripts/backup.sh, executed for real against a stub compose command.

Every assertion here is behavioural: the script runs, and the test looks at
what is left in the destination directory. That is the only way to catch this
class of bug, because the failure artefact is a *well-formed* gzip file with
the canonical name -- a text check on the script would have to restate the
fix to notice it was gone.

The stubs stand in for ``docker compose``. backup.sh reads COMPOSE_CMD, so no
container, daemon or database is involved.
"""
from __future__ import annotations

import gzip
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP = REPO_ROOT / "scripts" / "backup.sh"

RETENTION_GLOB = "darkmem-*.sql.gz"

# What pg_dump writes last, and only once the dump has fully succeeded. Every
# dump in /root/darkmem-backups carries it inside the last 512 bytes (pg 17
# appends a \unrestrict line after it).
DUMP_TAIL = (
    "--\n"
    "-- PostgreSQL database dump complete\n"
    "--\n\n"
    "\\unrestrict 8kvVxEh2RfunUmIMTeMD2xzvdmSViN3iUM5sEn1PcqEZ2dw76TtkvKS087t25gb\n\n"
)
DUMP_BODY = "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.memories (id uuid);\n\n"


def _stub(tmp_path: Path, name: str, body: str) -> Path:
    stub = tmp_path / name
    stub.write_text("#!/usr/bin/env bash\n" + body)
    stub.chmod(0o755)
    return stub


def _good_compose(tmp_path: Path) -> Path:
    return _stub(tmp_path, "compose-ok.sh", f"cat <<'SQL'\n{DUMP_BODY}{DUMP_TAIL}SQL\n")


def _failing_compose(tmp_path: Path) -> Path:
    return _stub(
        tmp_path,
        "compose-fail.sh",
        'echo "Error response from daemon: container is not running" >&2\nexit 1\n',
    )


def _truncated_compose(tmp_path: Path) -> Path:
    """Exits 0, having written a dump that stops mid-stream."""
    return _stub(tmp_path, "compose-truncated.sh", f"cat <<'SQL'\n{DUMP_BODY}SQL\n")


def _run_backup(dest: Path, compose: Path, keep: str | None = None):
    env = {**os.environ, "COMPOSE_CMD": str(compose)}
    if keep is not None:
        env["BACKUP_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _dumps(dest: Path) -> list[Path]:
    return sorted(dest.glob(RETENTION_GLOB))


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    out = tmp_path / "backups"
    out.mkdir()
    return out


def test_a_successful_dump_lands_under_the_retention_name(dest, tmp_path):
    """Without this the failure tests below could pass on a script that
    produces nothing at all."""
    result = _run_backup(dest, _good_compose(tmp_path))
    assert result.returncode == 0, result.stderr
    (dump,) = _dumps(dest)
    assert gzip.decompress(dump.read_bytes()).decode().endswith(DUMP_TAIL)
    assert list(dest.iterdir()) == [dump]


def test_a_failed_dump_leaves_no_file_behind(dest, tmp_path):
    """The redirection creates $OUT before pg_dump writes a byte and gzip -c
    exits 0 on empty input, so the aborted run leaves a well-formed 20-byte
    .sql.gz under the canonical name. Retention is name-and-mtime only, so
    that artefact is the newest file on disk and survives every later prune
    while real dumps age past KEEP."""
    result = _run_backup(dest, _failing_compose(tmp_path))
    assert result.returncode != 0, "a failed dump must still fail the run"
    assert list(dest.iterdir()) == [], "failed run left a file in the backup directory"


def test_a_truncated_dump_leaves_no_file_behind(dest, tmp_path):
    """The variant pipefail cannot see: the dump command exits 0 having
    written a stream that stops before pg_dump's completion marker."""
    result = _run_backup(dest, _truncated_compose(tmp_path))
    assert result.returncode != 0, "an incomplete dump must fail the run"
    assert list(dest.iterdir()) == []


def test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact(dest, tmp_path):
    """The consequence, end to end. With one real dump already on disk and
    room for two, a failed night followed by a good one must leave both real
    dumps -- not the newest artefact plus the newest dump."""
    old = dest / "darkmem-20200101-000000.sql.gz"
    old.write_bytes(gzip.compress((DUMP_BODY + DUMP_TAIL).encode()))
    os.utime(old, (0, 0))

    failed = _run_backup(dest, _failing_compose(tmp_path), keep="2")
    assert failed.returncode != 0
    # The dump filename is stamped to the second, so without this the good run
    # would overwrite the artefact instead of joining it on disk, and the test
    # would pass today for the wrong reason.
    time.sleep(1.1)

    result = _run_backup(dest, _good_compose(tmp_path), keep="2")
    assert result.returncode == 0, result.stderr

    survivors = _dumps(dest)
    assert old in survivors, "retention pruned a real dump"
    for dump in survivors:
        assert gzip.decompress(dump.read_bytes()), f"{dump.name} is an empty dump"


- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_backup_script.py

(The suite's session-scoped autouse fixture still resets darkmem_test, so the dev Postgres on 127.0.0.1:5433 must be up even though these four tests never touch it.)
```

Expected — this is what the run actually printed on master:

Three of the four fail today (measured, not predicted):

    FAILED tests/test_backup_script.py::test_a_failed_dump_leaves_no_file_behind
    FAILED tests/test_backup_script.py::test_a_truncated_dump_leaves_no_file_behind
    FAILED tests/test_backup_script.py::test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact
    3 failed, 1 passed, 1 warning in 2.26s

with these messages:

  test_a_failed_dump_leaves_no_file_behind
    AssertionError: failed run left a file in the backup directory
    assert [PosixPath('.../backups/darkmem-20260824-212408.sql.gz')] == []

  test_a_truncated_dump_leaves_no_file_behind
    AssertionError: an incomplete dump must fail the run
    assert 0 != 0

  test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact
    AssertionError: retention pruned a real dump
    assert PosixPath('.../darkmem-20200101-000000.sql.gz') in
      [PosixPath('.../darkmem-20260824-212434.sql.gz'),
       PosixPath('.../darkmem-20260824-212435.sql.gz')]

test_a_successful_dump_lands_under_the_retention_name passes today and after
the fix; it is there so the other three cannot pass on a script that produces
nothing at all.

The same failure outside pytest, against the real script:

    $ mkdir -p /tmp/f08/dest
    $ printf '#!/usr/bin/env bash\nexit 1\n' > /tmp/f08/fail.sh && chmod +x /tmp/f08/fail.sh
    $ COMPOSE_CMD=/tmp/f08/fail.sh bash scripts/backup.sh /tmp/f08/dest ; echo "exit=$?"
    exit=1
    $ ls -l /tmp/f08/dest
    -rw-r--r-- 1 root root 20 ... darkmem-20260824-212228.sql.gz     # 20-byte artefact
    $ gzip -t /tmp/f08/dest/*.sql.gz ; echo "gzip -t exit=$?"        # gzip -t exit=0


- [ ] **Step 3: Apply the fix**

One edit, scripts/backup.sh. Replace lines 17-21 exactly.

CURRENT CODE (lines 17-21, immediately after `OUT="$DEST_DIR/darkmem-$STAMP.sql.gz"` and immediately before the `# Retention.` comment block):

    echo "Dumping database '$DB' from compose service '$SERVICE' -> $OUT"
    $COMPOSE exec -T "$SERVICE" pg_dump -U "$USER" -d "$DB" --clean --if-exists \
      | gzip -c > "$OUT"

    echo "Backup complete: $OUT ($(du -h "$OUT" | cut -f1))"

REPLACEMENT:

    # Dump to a name the retention glob cannot match, and rename only once the
    # dump is known good. The redirection below creates its target before pg_dump
    # writes a byte and gzip -c exits 0 on empty input, so writing straight to
    # $OUT leaves a well-formed empty .sql.gz behind on every failure — and
    # retention sorts by mtime alone, so those artefacts are always the newest
    # files on disk and survive every prune while real dumps age past KEEP.
    PART="$OUT.part"
    trap 'rm -f -- "$PART"' EXIT

    echo "Dumping database '$DB' from compose service '$SERVICE' -> $OUT"
    $COMPOSE exec -T "$SERVICE" pg_dump -U "$USER" -d "$DB" --clean --if-exists \
      | gzip -c > "$PART"

    # pg_dump writes this marker last and only on success, so it also catches the
    # truncated stream that still exits 0, which pipefail cannot see. A size floor
    # would not: this database's nightly dumps have ranged from 14 KB to 2.4 MB.
    if ! gunzip -c "$PART" | tail -c 512 | grep -F 'PostgreSQL database dump complete' >/dev/null; then
        echo "Incomplete dump: no pg_dump completion marker. Nothing written to $OUT." >&2
        exit 1
    fi

    mv -- "$PART" "$OUT"

    echo "Backup complete: $OUT ($(du -h "$OUT" | cut -f1))"

Nothing else in the file changes. The retention block below it is left exactly as
it is, and no other file is touched.

Why this shape, for a reader with no context:

1. `PART="$OUT.part"` is per-run unique (the stamp is in it), so two concurrent
   runs cannot fight over one temp file. `find -maxdepth 1 -name 'darkmem-*.sql.gz'`
   matches the whole basename, so `darkmem-<stamp>.sql.gz.part` does not match the
   retention glob — verified directly:
       $ touch darkmem-1.sql.gz darkmem-2.sql.gz.part
       $ find . -maxdepth 1 -name 'darkmem-*.sql.gz' -type f -printf '%p\n'
       ./darkmem-1.sql.gz
   so the retention scan needs no change.
2. The EXIT trap removes the temp file on every exit path. Without it a failed
   night would leave a `.part` that no prune can ever reach, which is the same
   disk-fill hazard the retention block exists to prevent. After a successful
   `mv` the file is gone and the trap's `rm -f` is a no-op. It is the only trap
   in the script.
3. The completion-marker check is a real integrity test, not a threshold. It
   catches the case `pipefail` cannot see: the dump command exits 0 having
   written a stream that stops early. `gzip -t` cannot catch it (an empty input
   compresses to a valid 20-byte gzip file — measured), and a percentage-of-
   previous-dump floor would have produced false failures on this very host:
   /root/darkmem-backups shows 48960 -> 14061 bytes on 2026-08-18 and
   74668 -> 21973 on 2026-08-21, both ~29% of the night before.
4. `grep -F ... >/dev/null` rather than `grep -qF`: `-q` exits on first match and
   could SIGPIPE `tail`, which under `set -o pipefail` would read as a failed
   check. Without `-q` grep drains its input, so it cannot.
5. `set -e` is suspended inside an `if` condition, so a failed check reaches the
   explicit error message and `exit 1` rather than aborting silently.
6. Verified against real pg_dump output, not only stubs: with COMPOSE_CMD
   pointing at `docker exec -i darkmem-postgres-1`, the fixed script produced a
   558-byte dump of darkmem_test (exit 0); against darkmem-prod-postgres-1 it
   produced the real 2.5 MB production dump (exit 0). Both of the newest files in
   /root/darkmem-backups also carry the marker inside their last 512 bytes.
7. `bash -n scripts/backup.sh` is clean.

The live host needs no cleanup after this lands: /root/darkmem-backups currently
holds 14 real dumps (14 KB to 2.4 MB) and no failure artefact.

NOT a redeploy. The Dockerfile copies only backend/app, backend/migrations,
alembic.ini, entrypoint.sh and the built SPA — `scripts/` is not in the image.
The nightly systemd unit runs
/root/repositories/darkmem/scripts/backup.sh from the working tree, so the change
is live at the next 03:30 run with no rebuild. Do not run build-push for it.

- [ ] **Step 4: Run the same command and confirm it passes**

    4 passed, 1 warning in 1.77s

(measured with the fix applied; the run takes ~2s, of which 1.1s is the
deliberate sleep in the retention test.)

And the shell reproduction inverts:

    $ COMPOSE_CMD=/tmp/f08/fail.sh bash scripts/backup.sh /tmp/f08/dest ; echo "exit=$?"
    exit=1
    $ ls -A /tmp/f08/dest        # empty — no .sql.gz and no .part

- [ ] **Step 5: Run the surrounding suite for regressions**

1. The completion marker is pg_dump's, not ours. If PostgreSQL ever changes or
   drops the line "PostgreSQL database dump complete" from plain-text output,
   every nightly backup starts failing with exit 1 instead of silently writing
   junk. That is the right direction (a backup should fail closed), but it fails
   into the systemd journal, which is exactly where the finding says nobody
   looks. Verified present on pg 17.6 (pgvector/pgvector:0.8.2-pg17, both the dev
   and prod containers) and in all the dumps currently in /root/darkmem-backups.
   Note pg 17 appends a `\unrestrict <token>` line AFTER the marker, which is why
   the check reads the last 512 bytes rather than the final line; the marker sits
   115 bytes from EOF in a real dump.

2. Cost: the check decompresses the whole dump once per run. Measured on the real
   2.5 MB production dump the total script runtime stayed around a second. On a
   much larger future database this is roughly a 20% add to the backup's runtime.
   Nothing else in the system reads these files, so no other path pays it.

3. Behaviour deliberately preserved: a failed dump still exits non-zero. A fix
   that swallowed the failure would be worse than the bug, so the test asserts
   returncode != 0 on both failure paths.

4. Existing test coverage of the surrounding behaviour: there is none. `rg` over
   backend/tests finds no test that reads or runs scripts/backup.sh — this task
   creates the first. The nearest neighbours, which the new file is written to
   match, are backend/tests/test_deployment_artifact.py (reads shipped artefacts
   as text; it explicitly documents that a text check cannot prove behaviour) and
   backend/tests/test_uvicorn_proxy_headers.py (runs a shipped artefact as a
   subprocess, which is the pattern used here). Neither is modified.

5. Collision with F07. That finding is about scripts/restore.sh, and its proposed
   fix option (a) would add `--create --clean` to this same pg_dump invocation in
   backup.sh. The two changes are compatible — `--create` changes the dump's
   header, not its footer, so the marker check is unaffected — but both tasks
   edit scripts/backup.sh and must not be applied concurrently. Apply this one
   first: it is a two-line-region replacement that F07 can then rebase onto.

6. The 1.1s sleep in the retention test is load-bearing, not padding. The dump
   filename is stamped to the second, so without it the good run overwrites the
   artefact instead of joining it on disk and the test passes today for the wrong
   reason — observed before the sleep was added.

7. The gate (scripts/gate.sh) runs no shell linter, so nothing else in CI reads
   this file. The new test file is collected by plain pytest (testpaths = tests).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_backup_script.py scripts/backup.sh
git commit -m "fix(backup): rename a dump into place only on success"
```

### Task 4: Refuse a destructive eval script aimed at a real database

**Effort:** ~60 minutes.

**Files:**
- Modify: `backend/scripts/eval_round3/purge_eval.py:22-30`
- Modify: `backend/scripts/eval_round3/run.py`, `backend/scripts/eval_round3/debug_clean.py` (same guard, same place)
- Create: `backend/scripts/benchlib/tests/test_ambient_database_guard.py`

**Interfaces:**
- Consumes: `backend/scripts/benchlib/db_target.py` — `assert_destructive_target_allowed(url, *, actor)` and `resolved_database_name(url)`. Both already exist and are already used by `bench_db.reset_bench_db`. Do **not** write a second guard; the module's own docstring explains that a guard half the callers cannot import is a guard half the callers reimplement, which is how this rule came to have five readings.
- Produces: nothing new. This task adds call sites and a pinning test.

**Why this sits in the data-loss plan rather than the medium tail.** `purge_eval.py`'s
first statement is `UPDATE memories SET status='active', superseded_by=NULL WHERE
status='superseded'` — unscoped by project, unscoped by source, unscoped by anything.
It opens `app.database.async_session_factory`, which resolves the ambient
`DATABASE_URL`. On this host that default is the production database. The module
docstring tells the operator to run it from `backend/` with no environment
mentioned at all. One invocation from the wrong shell destroys every supersession
lineage in the corpus, and the ladder cannot rebuild them — supersession is decided
at ingest from a `REPLACES`-family relation, not recomputed on read.

**Owner decision this task carries.** The packaging pass recommends deleting
`backend/scripts/eval_round3/` outright: benchlib's retrieval and extraction
harnesses supersede it, and `run.py` and `debug_clean.py` both fail today at import
or first attribute read because they still reference the `llm_*` memory attributes
the baseline dropped. If the owner takes that, this task collapses to the deletion
plus the pinning test, which is strictly less work. **The pinning test is written
either way** — it is what stops the next harness from reintroducing the hazard. Do
not delete the directory without an explicit instruction; it is round-3 evaluation
history and that call is not the implementer's.

- [ ] **Step 1: Write the failing test**

```python
# backend/scripts/benchlib/tests/test_ambient_database_guard.py
"""Every script that can destroy rows must say which database it may destroy.

`purge_eval.py` resurrects every superseded memory in whatever `DATABASE_URL`
resolves to, and on this host that default is production. The guard already
exists (`db_target.assert_destructive_target_allowed`); what was missing is
anything that notices a destructive script which does not call it.

This test enumerates the population rather than asserting one call site, so the
next harness that opens the ambient session and issues a DELETE cannot land
silently — which is the failure mode the whole review found repeatedly.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[2]

# Modules that issue destructive SQL but are exempt, each with the reason.
EXEMPT = {
    # bench_db owns the guard's other side: it calls assert_destructive_target_allowed
    # itself before DROP SCHEMA, and re-checking it here would assert the guard twice.
    "benchlib/bench_db.py": "calls the guard directly before DROP SCHEMA",
    # The e2e stack builds and tears down its own disposable database by name.
    "e2e/e2e_db.py": "creates and drops the database it names, never an ambient one",
    "e2e/stack.py": "drives e2e_db, holds no SQL of its own",
}

DESTRUCTIVE = ("DELETE FROM", "DROP SCHEMA", "DROP TABLE", "TRUNCATE", "UPDATE ")


def _sql_literals(tree: ast.AST) -> list[str]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


def _names_the_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "assert_destructive_target_allowed":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "assert_destructive_target_allowed":
            return True
    return False


def _destructive_modules() -> list[tuple[str, pathlib.Path]]:
    found = []
    for path in sorted(SCRIPTS.rglob("*.py")):
        if "__pycache__" in path.parts or "/tests/" in path.as_posix():
            continue
        rel = path.relative_to(SCRIPTS).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        sql = " ".join(_sql_literals(tree)).upper()
        if any(verb in sql for verb in DESTRUCTIVE):
            found.append((rel, path))
    return found


def test_every_destructive_script_declares_its_target():
    offenders = []
    for rel, path in _destructive_modules():
        if rel in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _names_the_guard(tree):
            offenders.append(rel)
    assert offenders == [], (
        "these scripts issue destructive SQL against whatever DATABASE_URL "
        f"resolves to, with no target guard: {offenders}. Call "
        "benchlib.db_target.assert_destructive_target_allowed(url, actor=...) "
        "before opening the session, or add the module to EXEMPT with a reason."
    )


def test_the_exempt_list_names_only_modules_that_still_exist():
    """An exemption for a deleted file is an exemption nobody is reading."""
    missing = [rel for rel in EXEMPT if not (SCRIPTS / rel).exists()]
    assert missing == [], f"EXEMPT names modules that no longer exist: {missing}"


def test_the_scan_finds_the_scripts_it_is_meant_to_cover():
    """A scan that matches nothing passes for the wrong reason."""
    found = {rel for rel, _ in _destructive_modules()}
    assert "benchlib/bench_db.py" in found, (
        "the destructive-SQL scan no longer sees bench_db, so it is no longer "
        f"finding what it was written to find; it saw {sorted(found)}"
    )
```

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q scripts/benchlib/tests/test_ambient_database_guard.py
```

Expected: `test_every_destructive_script_declares_its_target` FAILS, listing
`eval_round3/purge_eval.py` (and any other module the scan catches). Note that
`pyproject.toml` sets `testpaths = ["tests"]`, so a plain `pytest -q` does **not**
collect `scripts/benchlib/tests` — the path above is required, and `./scripts/gate.sh`
is what runs this directory in CI. The other two tests should pass immediately; they
exist so a scan that silently stops matching cannot be mistaken for a clean result.

- [ ] **Step 3: Apply the guard**

In `backend/scripts/eval_round3/purge_eval.py`, replace the import block and the
head of `main()`:

Current:

```python
from sqlalchemy import text  # noqa: E402

from app.database import async_session_factory  # noqa: E402


async def main():
    async with async_session_factory() as s:
```

Replacement:

```python
from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from scripts.benchlib.db_target import assert_destructive_target_allowed  # noqa: E402


async def main():
    # Statement 0 below resurrects every superseded memory in whatever database
    # DATABASE_URL resolves to, which on the host that runs the live instance is
    # production. The lineage it destroys is decided at ingest and is not
    # recomputed on read, so there is nothing to rebuild it from.
    assert_destructive_target_allowed(
        get_settings().database_url, actor="eval_round3/purge_eval"
    )
    async with async_session_factory() as s:
```

Apply the identical three-line addition (import, then the `assert_` call as the
first statement of the entry point) to `backend/scripts/eval_round3/run.py` and
`backend/scripts/eval_round3/debug_clean.py`.

- [ ] **Step 4: Run the same command and confirm it passes**

Expected: `3 passed`. Then confirm the guard actually refuses, rather than only
being present:

```bash
cd /root/repositories/darkmem/backend &&   DATABASE_URL='postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem'   .venv/bin/python scripts/eval_round3/purge_eval.py
```

Expected: a `RuntimeError` naming `darkmem` and refusing, printed before any
statement runs. **Nothing is written.** Do not run this command without the
`DATABASE_URL` override in place first — that is the whole point of the task.

- [ ] **Step 5: Run the surrounding suite for regressions**

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q scripts/benchlib/tests
```

Risk is low and one-directional: the guard only ever refuses. The one way to break
something is to place the call after the session opens, which would let the first
statement run before the refusal. `db_target.py` itself is unchanged, so
`bench_db.reset_bench_db`'s existing behaviour is untouched.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/eval_round3/ backend/scripts/benchlib/tests/test_ambient_database_guard.py
git commit -m "fix(eval): refuse a purge aimed at a real database"
```

**No redeploy.** The Dockerfile's runtime stage copies `backend/app/`,
`backend/migrations/`, `alembic.ini`, `entrypoint.sh` and the built SPA — nothing
under `backend/scripts/`. This task changes operator and harness behaviour only.

---

## Finishing this plan

- [ ] Run the full floor: `./scripts/gate.sh` from the repo root. Expect green; the backend baseline moves from 6179 to 6179 + the tests this plan adds.
- [ ] Redeploy for Task 1 only: `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → wait for `healthy` → `docker exec darkmem-prod-darkmem-1 grep -n 'ff-only' app/services/repo_manager.py`. If that grep finds nothing, the build did not happen and compose redeployed the previous image.
- [ ] Answer the two owner decisions this plan surfaced before starting R2 — they are recorded in the spec's decision register.
