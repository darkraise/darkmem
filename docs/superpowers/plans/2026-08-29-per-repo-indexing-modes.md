# Per-Repo Indexing Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every recurring indexing behaviour a per-repository opt-in switch, with `HEAD` as the single trigger for indexing and fetching as a separate concern that only moves it.

**Architecture:** Five columns on `repositories` replace `auto_sync`. One job loop (`repo_sync`) ticks every 30 seconds and, per repository, evaluates three independent due-times: fetch, HEAD-poll, and an optional working-tree drift scan that widens the HEAD-poll. `code_reconcile`'s job registration is retired and its scan folded into that loop. The `HEAD` sha is resolved by reading git's own ref files, never by an mtime heuristic.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, pytest/pytest-asyncio, React + TanStack Form, `darkraise-ui`, vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-per-repo-indexing-modes-design.md`

## Global Constraints

- **The schema is ONE revision.** A schema change regenerates `backend/migrations/versions/0001_baseline.py` in place; it never appends a `0002`. `./scripts/gate.sh` asserts exactly one revision.
- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q`. Needs `darkmem_test` on 127.0.0.1:5433.
- **Frontend:** from `frontend/`, `npm run typecheck` (= `tsc -b`), `npm test`, `npm run build`.
- **Merge gate:** `./scripts/gate.sh` from the repo root. Must be green before the final commit.
- **Interval floors:** `fetch_interval_seconds` ≥ 30, `commit_poll_seconds` ≥ 15. Enforced in the Pydantic schema as `Field(ge=...)`.
- **Defaults:** `fetch_enabled=False`, `fetch_interval_seconds=300`, `index_on_commit_enabled=False`, `commit_poll_seconds=60`, `index_uncommitted=False`.
- **Commits:** `<type>(<scope>): <subject>`, subject ≤ 50 chars, imperative, no period. A `feat` or `fix` on master cuts a release, so the final task writes the CHANGELOG section.
- **UI components come from `darkraise-ui` first.** `switch` and `number-input` both exist at `frontend/node_modules/darkraise-ui/dist/components/`. Do not hand-roll either.
- **Comments:** only where the WHY is non-obvious. Never explain WHAT the code does.

---

### Task 1: Schema — five columns replace `auto_sync`

**Files:**
- Modify: `backend/app/models/code.py:30` (the `auto_sync` line on `Repository`)
- Modify: `backend/migrations/versions/0001_baseline.py` (regenerate in place)
- Test: `backend/tests/test_repo_indexing_modes.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `Repository.fetch_enabled: bool`, `Repository.fetch_interval_seconds: int`, `Repository.index_on_commit_enabled: bool`, `Repository.commit_poll_seconds: int`, `Repository.index_uncommitted: bool`. `Repository.auto_sync` no longer exists.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_repo_indexing_modes.py`:

```python
"""Per-repo indexing modes (spec 2026-08-29).

Every recurring indexing behaviour is a switch the operator sets. The bug
these replace: `code_reconcile` selected every indexed repo and never read
`auto_sync`, so there was no setting that stopped darkmem reindexing a
working tree another agent was editing.
"""
import pytest

from app.models.code import Repository


async def test_a_new_repository_opts_into_nothing(session):
    """Opt-in means opt-in: adding a row arms no recurring work."""
    repo = Repository(name="fresh", local_path=None, url=None)
    session.add(repo)
    await session.flush()

    assert repo.fetch_enabled is False
    assert repo.index_on_commit_enabled is False
    assert repo.index_uncommitted is False
    assert repo.fetch_interval_seconds == 300
    assert repo.commit_poll_seconds == 60


def test_auto_sync_is_gone():
    """Kept as a synonym it would recreate the confusion it caused: a name
    suggesting it governs all automatic behaviour while governing one loop
    of two."""
    assert not hasattr(Repository, "auto_sync")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q`
Expected: FAIL — `AttributeError: 'Repository' object has no attribute 'fetch_enabled'`.

- [ ] **Step 3: Edit the model**

In `backend/app/models/code.py`, replace the `auto_sync` line on `Repository` with:

```python
    fetch_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    fetch_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, server_default="300")
    index_on_commit_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    commit_poll_seconds: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    index_uncommitted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
```

`server_default` is not decoration: `conftest` builds the test schema through alembic, so a column without one is NULL on rows inserted by raw SQL.

- [ ] **Step 4: Regenerate the baseline**

```bash
cd backend
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "DROP DATABASE IF EXISTS darkmem_regen;"
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_regen OWNER darkmem;"
rm migrations/versions/0001_baseline.py
DATABASE_URL='postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_regen' \
  .venv/bin/python -m alembic revision --autogenerate -m "baseline" --rev-id 0001
mv migrations/versions/*_baseline.py migrations/versions/0001_baseline.py
```

Then open the file and confirm the `repositories` `create_table` carries the five columns and no `auto_sync`. Autogenerate against an empty database emits the whole schema; diff it against the previous version and confirm `repositories` is the ONLY table that changed:

```bash
git diff --stat backend/migrations/versions/0001_baseline.py
git diff backend/migrations/versions/0001_baseline.py | grep -E '^[-+].*(auto_sync|fetch_enabled|index_on_commit|commit_poll|index_uncommitted)'
```

If any other table appears in the diff, the autogenerate drifted — stop and reconcile before continuing.

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q
```

Expected: PASS. conftest drops and re-migrates `darkmem_test`, so the new columns arrive automatically.

- [ ] **Step 6: Run the full backend suite to find every `auto_sync` reader**

```bash
cd backend && .venv/bin/python -m pytest -q 2>&1 | tail -30
grep -rn "auto_sync" backend/app backend/tests
```

Expected: failures in `app/services/repo_manager.py`, `app/services/job_runners.py`, `app/api/routes/repos.py`, `app/schemas/code.py`. Leave them failing — Tasks 3-5 fix them. Record the list.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/code.py backend/migrations/versions/0001_baseline.py backend/tests/test_repo_indexing_modes.py
git commit -m "feat(code): add per-repo indexing mode columns"
```

---

### Task 2: Resolve `HEAD` by reading git's ref files

**Files:**
- Create: `backend/app/services/git_head.py`
- Test: `backend/tests/test_git_head.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `async def resolve_head_sha(work_dir: Path) -> str | None` — the 40-char sha `HEAD` points at, or `None` when the directory is not a readable git repository.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_git_head.py`:

```python
"""Resolving HEAD without a subprocess in the common case.

The first draft of the spec proposed an mtime gate on `.git/HEAD`. That is
wrong and the test below is the reason: a commit on a branch never touches
that file — it holds `ref: refs/heads/<branch>` and only the branch's loose
ref moves — so the gate would miss every ordinary commit while looking like
it worked.
"""
import subprocess

import pytest

from app.services.git_head import resolve_head_sha


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f.txt").write_text("one")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "one")
    return tmp_path


def _rev_parse(cwd) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout.strip()


async def test_resolves_a_loose_ref(tmp_path):
    work = _repo(tmp_path)

    assert await resolve_head_sha(work) == _rev_parse(work)


async def test_sees_a_new_commit(tmp_path):
    """The whole point: a commit must change the answer."""
    work = _repo(tmp_path)
    first = await resolve_head_sha(work)

    (work / "f.txt").write_text("two")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "two")

    second = await resolve_head_sha(work)
    assert second != first
    assert second == _rev_parse(work)


async def test_resolves_a_packed_ref(tmp_path):
    """`git gc` moves the loose ref into packed-refs and deletes the file.
    The read path must fall back rather than report None, which would read
    as 'not a repository' and stall indexing forever."""
    work = _repo(tmp_path)
    expected = _rev_parse(work)
    _git(work, "pack-refs", "--all")
    assert not (work / ".git" / "refs" / "heads" / "main").exists()

    assert await resolve_head_sha(work) == expected


async def test_resolves_a_detached_head(tmp_path):
    work = _repo(tmp_path)
    sha = _rev_parse(work)
    _git(work, "checkout", "-q", "--detach", sha)

    assert await resolve_head_sha(work) == sha


async def test_a_directory_that_is_not_a_repository_is_none(tmp_path):
    assert await resolve_head_sha(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_git_head.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.git_head'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/git_head.py`:

```python
"""Resolve a working directory's HEAD to a sha.

Read git's own files rather than shelling out, so the poll that runs every
few seconds per repository costs two small reads instead of a subprocess.

Do NOT replace this with an mtime check on `.git/HEAD`. A commit on a branch
does not touch that file -- it holds `ref: refs/heads/<branch>` and only the
branch's loose ref moves -- so an mtime gate there misses every ordinary
commit while appearing to work.
"""
from __future__ import annotations

import re
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None


async def resolve_head_sha(work_dir: Path) -> str | None:
    git_dir = work_dir / ".git"
    head = _read(git_dir / "HEAD")
    if head is None:
        return None

    if _SHA.match(head):
        return head

    if not head.startswith("ref: "):
        return None

    ref = head[len("ref: "):].strip()
    loose = _read(git_dir / ref)
    if loose is not None and _SHA.match(loose):
        return loose

    # Packed: `git gc` deletes the loose ref. Falling back to the subprocess
    # here rather than returning None matters -- None reads as "not a
    # repository" to the caller, which would stall indexing on a repo that is
    # merely well packed.
    from app.services.repo_manager import RepoManager

    try:
        out = await RepoManager._run_git(work_dir, ["git", "rev-parse", "HEAD"])
    except Exception:
        return None
    out = out.strip()
    return out if _SHA.match(out) else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_git_head.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/git_head.py backend/tests/test_git_head.py
git commit -m "feat(code): resolve HEAD from git's ref files"
```

---

### Task 3: One loop — fetch, poll, optional drift

**Files:**
- Modify: `backend/app/services/job_runners.py:22-87` (`make_repo_sync_runner`), delete `make_code_reconcile_runner` (lines 88-168)
- Modify: `backend/app/main.py:288-300` (the `repo_sync` registration) and `:369-382` (the `code_reconcile` registration)
- Test: `backend/tests/test_repo_indexing_modes.py` (extend)

**Interfaces:**
- Consumes: `resolve_head_sha(work_dir)` from Task 2; the Task 1 columns.
- Produces: `make_repo_sync_runner(app, session_factory)` unchanged in signature; a module-level `_DUE: dict[UUID, dict[str, float]]` and `_due_reset()` test hook.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_repo_indexing_modes.py`:

```python
import subprocess
from pathlib import Path

from app.models.code import Repository
from app.services import job_runners


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def _commit(work: Path, text: str, message: str):
    (work / "f.py").write_text(text)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", message)


def _make_repo_dir(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "def alpha():\n    return 1\n", "one")
    return tmp_path


@pytest.fixture
def indexed_repo(session, tmp_path):
    """A repo row whose graph is current with its HEAD, all switches off."""
    work = _make_repo_dir(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()
    repo = Repository(
        name="watched", local_path=str(work), provider="local",
        last_indexed_commit=head, status="ready",
    )
    session.add(repo)
    return repo


class _Runs:
    """Records what the loop decided to do, without running a pipeline."""

    def __init__(self):
        self.indexed: list[tuple] = []
        self.fetched: list = []


@pytest.fixture
def spy(monkeypatch):
    runs = _Runs()

    async def fake_run(self, repo_id, **kwargs):
        runs.indexed.append((repo_id, kwargs.get("forced_files")))
        return {"status": "indexed"}

    async def fake_pull(self, repo):
        runs.fetched.append(repo.id)
        return None

    from app.services.code_pipeline import CodePipeline
    from app.services.repo_manager import RepoManager

    monkeypatch.setattr(CodePipeline, "run", fake_run)
    monkeypatch.setattr(RepoManager, "pull_repo", fake_pull)
    job_runners._due_reset()
    return runs


async def test_all_switches_off_does_nothing(session, session_factory, indexed_repo, spy):
    """The bug this feature exists for: a repo darkmem must not touch."""
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []
    assert spy.fetched == []


async def test_index_on_commit_indexes_a_new_commit(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert [r[0] for r in spy.indexed] == [indexed_repo.id]
    assert spy.indexed[0][1] is None


async def test_index_on_commit_is_quiet_when_head_has_not_moved(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []


async def test_fetch_on_and_index_off_leaves_the_graph_behind(
    session, session_factory, indexed_repo, spy,
):
    """A legal combination -- track the remote, index on my say-so -- that the
    loop must not second-guess."""
    indexed_repo.fetch_enabled = True
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.fetched == [indexed_repo.id]
    assert spy.indexed == []


async def test_index_uncommitted_off_ignores_a_dirty_tree(
    session, session_factory, indexed_repo, spy,
):
    """Another agent's half-saved file is not an assertion darkmem makes."""
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    (Path(indexed_repo.local_path) / "f.py").write_text("def dirty():\n    return 3\n")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []


async def test_index_uncommitted_on_indexes_a_dirty_tree(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.index_uncommitted = True
    await session.commit()
    (Path(indexed_repo.local_path) / "f.py").write_text("def dirty():\n    return 3\n")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert len(spy.indexed) == 1
    assert spy.indexed[0][1] is not None


async def test_a_fetch_never_rewinds_a_local_checkout(session, session_factory, tmp_path):
    """Spec 3.2. `pull_repo` advances a local_path repo with `merge --ff-only`
    and never `reset --hard`, so darkmem cannot discard a commit another agent
    has not pushed. Unchanged behaviour, pinned here because this loop is now
    what calls it on a schedule."""
    work = _make_repo_dir(tmp_path)
    _commit(work, "def unpushed():\n    return 9\n", "local only")
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()

    repo = Repository(
        name="local-only", local_path=str(work), provider="local",
        url=None, fetch_enabled=True, status="ready",
    )
    session.add(repo)
    await session.commit()

    # No remote at all: the fetch fails, and the tree must survive it.
    await job_runners.make_repo_sync_runner(None, session_factory)()

    after = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert after == before
    assert (work / "f.py").read_text() == "def unpushed():\n    return 9\n"


async def test_an_interval_is_honoured(session, session_factory, indexed_repo, spy):
    """Two ticks inside one interval must examine the repo once."""
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.commit_poll_seconds = 3600
    await session.commit()
    runner = job_runners.make_repo_sync_runner(None, session_factory)

    await runner()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")
    await runner()

    assert spy.indexed == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q`
Expected: FAIL — `AttributeError: module 'app.services.job_runners' has no attribute '_due_reset'`.

- [ ] **Step 3: Rewrite `make_repo_sync_runner`**

In `backend/app/services/job_runners.py`, replace `make_repo_sync_runner` and delete `make_code_reconcile_runner` entirely. `compute_working_tree_drift` and `_file_hash` stay in `app/services/code_reconcile.py` — `reindex_files` imports the latter.

```python
# Per-repo due-times, keyed by repo id then by lane. Invariant 13 fixes the
# worker count at one, so an in-process map needs no cross-process
# serialisation. The accepted cost is that a restart makes every repo
# immediately due: one burst of fetches at boot, which at homelab repo counts
# is not worth a column to avoid.
_DUE: dict[UUID, dict[str, float]] = {}


def _due_reset() -> None:
    """Test hook only."""
    _DUE.clear()


def _claim_due(repo_id: UUID, lane: str, interval: int, now: float) -> bool:
    lanes = _DUE.setdefault(repo_id, {})
    if now < lanes.get(lane, 0.0):
        return False
    lanes[lane] = now + interval
    return True


def make_repo_sync_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """The one recurring indexing loop.

    HEAD is the single trigger: a pull, another agent's commit and the
    operator's own commit are the same event by the time this sees them.
    Fetching is a separate lane whose only job is to move HEAD.
    """
    async def run() -> None:
        import time

        from app.models.code import Repository
        from app.services.code_pipeline import CodePipeline
        from app.services.code_reconcile import compute_working_tree_drift
        from app.services.git_head import resolve_head_sha
        from app.services.repo_manager import RepoManager
        from app.repositories.vector import PostgresVectorRepository
        from app.api.websocket import event_manager

        active_llm = getattr(app, "state", None) and getattr(app.state, "llm", None)
        now = time.monotonic()

        async with session_factory() as list_session:
            repos = (await list_session.execute(
                select(Repository).where(
                    (Repository.fetch_enabled == True)  # noqa: E712
                    | (Repository.index_on_commit_enabled == True)  # noqa: E712
                )
            )).scalars().all()
            candidates = [(r.id, r.name) for r in repos]

        for repo_id, repo_name in candidates:
            async with session_factory() as repo_session:
                try:
                    manager = RepoManager(repo_session)
                    repo = await manager.get(repo_id)
                    if repo is None:
                        continue

                    if repo.fetch_enabled and _claim_due(
                        repo_id, "fetch", repo.fetch_interval_seconds, now,
                    ):
                        await manager.pull_repo(repo)

                    if not repo.index_on_commit_enabled:
                        continue
                    if not _claim_due(
                        repo_id, "index", repo.commit_poll_seconds, now,
                    ):
                        continue

                    work_dir = manager.repo_working_dir(repo)
                    if not work_dir.exists():
                        continue

                    head = await resolve_head_sha(work_dir)
                    forced: tuple[list[str], list[str]] | None = None
                    if head is None or head == repo.last_indexed_commit:
                        if not repo.index_uncommitted:
                            continue
                        drift = await compute_working_tree_drift(
                            repo_session, repo, work_dir,
                        )
                        if not drift[0] and not drift[1]:
                            continue
                        forced = drift

                    # Losing the claim is the ordinary case, not an error: the
                    # run that holds it is doing this tick's work.
                    if not await manager.claim_for_indexing(
                        repo_id, message="Indexing new commit...",
                    ):
                        continue

                    pipeline = CodePipeline(
                        session=repo_session, llm=active_llm,
                        vector_repo=PostgresVectorRepository(repo_session, "code_chunks"),
                        repo_manager=manager,
                    )
                    await pipeline.run(repo_id, forced_files=forced)
                    await repo_session.commit()
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Indexing loop failed for %s: %s", repo_name, e)
                    try:
                        async with session_factory() as fail_session:
                            updated = await RepoManager(
                                fail_session
                            ).mark_periodic_sync_failure(repo_id, e)
                        if updated is not None:
                            await event_manager.broadcast(
                                "repo.auto_sync_disabled",
                                {
                                    "repo_id": str(repo_id),
                                    "name": updated.name,
                                    "status_message": updated.status_message or "",
                                },
                            )
                    except Exception as inner_e:
                        logger.error("Failed to mark repo %s errored: %s", repo_id, inner_e)
    return run
```

Add `from uuid import UUID` to the module imports if absent.

- [ ] **Step 4: Point `mark_periodic_sync_failure` at the new column**

In `backend/app/services/repo_manager.py`, change the line setting `repo.auto_sync = False` to `repo.index_on_commit_enabled = False` and update the docstring: it disables the indexing lane, not a field that no longer exists. Leave `fetch_enabled` alone — a fetch failure and an index failure are different faults, and disabling the fetch would hide a transient network problem as a permanent setting change.

- [ ] **Step 5: Retire the `code_reconcile` registration**

In `backend/app/main.py`, delete the whole `job_registry.register(Job(key=CODE_RECONCILE_JOB_KEY, ...))` block (lines 369-382) and the now-unused imports of `CODE_RECONCILE_JOB_KEY`, `CODE_RECONCILE_CRON`, `CODE_RECONCILE_MIN_INTERVAL_SECONDS`, `CODE_RECONCILE_MAX_RUN_SECONDS` and `make_code_reconcile_runner`.

Change the `repo_sync` registration to:

```python
    job_registry.register(Job(
        key="repo_sync",
        display_name="Repository Sync",
        description=(
            "Per repo, on that repo's own intervals: fetches when Fetch from "
            "remote is on, and indexes when Index on new commit is on and HEAD "
            "has moved. Every switch is off by default. Manual reindex, the "
            "webhook and the code_reindex MCP tool bypass this loop entirely."
        ),
        default_cron="*/30 * * * * *",
        min_interval_seconds=15,
        runner=make_repo_sync_runner(app, async_session_factory),
        max_run_seconds=1800,
    ))
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py tests/test_git_head.py -q`
Expected: PASS.

- [ ] **Step 7: Update the roster test and run it**

`backend/tests/test_code_deriver.py` derives the job roster from `app/main.py`'s AST. Run it, read the failure, and update the expected roster to twenty-three keys without `code_reconcile`:

```bash
cd backend && .venv/bin/python -m pytest tests/test_code_deriver.py -q
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/job_runners.py backend/app/main.py backend/app/services/repo_manager.py backend/tests/
git commit -m "feat(code): drive indexing from one per-repo loop"
```

---

### Task 4: API surface

**Files:**
- Modify: `backend/app/schemas/code.py:44` (`RepoCreate.auto_sync`), `:57-62` (`RepoUpdate`), `:123` (`RepoResponse`)
- Modify: `backend/app/api/routes/repos.py:54` (`_to_response`), `:148-157` (the wake-up condition)
- Modify: `backend/app/services/repo_manager.py:170` (`auto_sync=data.auto_sync` in `create`)
- Test: `backend/tests/test_repo_indexing_modes.py` (extend)

**Interfaces:**
- Consumes: the Task 1 columns.
- Produces: the five fields on `RepoCreate` (all optional with the Global Constraints defaults), on `RepoUpdate` (all `| None = None`), and on `RepoResponse` (all required).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_repo_indexing_modes.py`:

```python
async def test_create_defaults_every_switch_off(client):
    r = await client.post("/api/v1/repos", json={"name": "api-default", "local_path": None})

    assert r.status_code == 201
    body = r.json()
    assert body["fetch_enabled"] is False
    assert body["index_on_commit_enabled"] is False
    assert body["index_uncommitted"] is False
    assert body["fetch_interval_seconds"] == 300
    assert body["commit_poll_seconds"] == 60


async def test_a_below_floor_interval_is_refused_at_the_door(client):
    """A two-second interval would spin the loop, so it is a 422 rather than a
    value the scheduler has to defend against."""
    r = await client.post(
        "/api/v1/repos",
        json={"name": "too-fast", "index_on_commit_enabled": True, "commit_poll_seconds": 2},
    )

    assert r.status_code == 422


async def test_update_round_trips_the_switches(client):
    created = (await client.post("/api/v1/repos", json={"name": "api-update"})).json()

    r = await client.put(
        f"/api/v1/repos/{created['id']}",
        json={"index_on_commit_enabled": True, "commit_poll_seconds": 30},
    )

    assert r.status_code == 200
    assert r.json()["index_on_commit_enabled"] is True
    assert r.json()["commit_poll_seconds"] == 30
```

These use the `client` fixture (`tests/conftest.py:141`) and `auth_headers`
(`:191`). Add `auth_headers` to each signature and pass `headers=auth_headers`
on every request — the repo routes sit behind `require_auth`. Note the `client`
fixture already registers a stub `repo_sync` job on `app.state.job_registry`,
which is what the update route's wake-up call reaches for.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q -k api or floor or round_trips`
Expected: FAIL — the response has no `fetch_enabled` key.

- [ ] **Step 3: Edit the schemas**

In `backend/app/schemas/code.py`, replace `auto_sync: bool = True` on `RepoCreate` with:

```python
    fetch_enabled: bool = False
    fetch_interval_seconds: int = Field(default=300, ge=30)
    index_on_commit_enabled: bool = False
    commit_poll_seconds: int = Field(default=60, ge=15)
    index_uncommitted: bool = False
```

Replace `auto_sync: bool | None = None` on `RepoUpdate` with the same five as `| None = None`, keeping the `ge` bounds:

```python
    fetch_enabled: bool | None = None
    fetch_interval_seconds: int | None = Field(default=None, ge=30)
    index_on_commit_enabled: bool | None = None
    commit_poll_seconds: int | None = Field(default=None, ge=15)
    index_uncommitted: bool | None = None
```

Replace `auto_sync: bool` on `RepoResponse` with the five as required fields. Add `Field` to the pydantic import if absent.

- [ ] **Step 4: Edit the route and the manager**

In `backend/app/api/routes/repos.py`, replace `auto_sync=repo.auto_sync,` in `_to_response` with the five fields. Replace the wake-up snapshot and condition:

```python
    prev_armed = existing.fetch_enabled or existing.index_on_commit_enabled
    ...
    if (repo.fetch_enabled or repo.index_on_commit_enabled) and not prev_armed:
```

so switching a repository on acts immediately instead of waiting out a tick.

In `backend/app/services/repo_manager.py`, replace `auto_sync=data.auto_sync,` in `create` with the five `data.` fields.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q`
Expected: PASS.

- [ ] **Step 6: Regenerate the SDKs**

The generator reads the live OpenAPI document and refuses to emit against a field the contract does not serve.

```bash
cd sdks && make generate
git diff --stat sdks/
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/code.py backend/app/api/routes/repos.py backend/app/services/repo_manager.py backend/tests/ sdks/
git commit -m "feat(api): serve per-repo indexing mode fields"
```

---

### Task 5: Adding a repository still indexes once

**Files:**
- Modify: `backend/app/api/routes/repos.py:67-81` (`create_repo`)
- Test: `backend/tests/test_repo_indexing_modes.py` (extend)

**Interfaces:**
- Consumes: `_spawn_repo_index(repo_id, pipeline, session_factory, *, kind, ...)` at `repos.py:172`.
- Produces: nothing later tasks rely on.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_repo_indexing_modes.py`:

```python
async def test_adding_a_repository_indexes_it_once(client, monkeypatch):
    """With every recurring switch off, nothing else would ever index a new
    repo -- adding one would do nothing at all. Opt-in governs recurring work;
    asking darkmem to track a repo is the opt-in for indexing it once."""
    spawned: list = []

    from app.api.routes import repos as repos_route

    def fake_spawn(repo_id, pipeline, session_factory, **kwargs):
        spawned.append((repo_id, kwargs.get("kind")))

        class _T:
            pass

        return _T()

    monkeypatch.setattr(repos_route, "_spawn_repo_index", fake_spawn)

    r = await client.post("/api/v1/repos", json={"name": "index-once", "local_path": None})

    assert r.status_code == 201
    assert len(spawned) == 1
    assert spawned[0][1] == "initial"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q -k indexes_it_once`
Expected: FAIL — `assert 0 == 1`.

- [ ] **Step 3: Spawn the initial index**

In `create_repo` (`backend/app/api/routes/repos.py`), after `repo = await manager.create(body)` and before the return, add:

`reindex_repo` (`repos.py:259-266`) takes both through FastAPI dependencies.
Add the same two to `create_repo`'s signature:

```python
async def create_repo(
    body: RepoCreate,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
```

then, after `repo = await manager.create(body)` and before the return:

```python
    # A URL repo is still cloning; `_clone_in_background` indexes it when the
    # clone lands. Only a local_path repo has a tree to read right now.
    if not body.url:
        try:
            _spawn_repo_index(
                repo.id, pipeline, session_factory, kind="initial",
            )
        except Exception as e:
            # The row exists and the Reindex button is one click away; failing
            # the create over a scheduling error would be the worse outcome.
            logger.error("Failed to schedule initial index for %s: %s", repo.id, e)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repo_indexing_modes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/repos.py backend/tests/test_repo_indexing_modes.py
git commit -m "feat(api): index a repository once when it is added"
```

---

### Task 6: The Indexing group in both dialogs

**Files:**
- Modify: `frontend/src/features/code/components/add-repo-dialog.tsx:49,87,102,193-206`
- Modify: `frontend/src/features/code/components/real-repositories-view.tsx:217,233,341-351`
- Modify: the repo type where `auto_sync` is declared — find it with `grep -rn "auto_sync" frontend/src`
- Create: `frontend/src/features/code/components/indexing-modes-fields.tsx`
- Test: `frontend/src/features/code/__tests__/indexing-modes-fields.test.tsx` (create)

**Interfaces:**
- Consumes: the Task 4 API fields.
- Produces: `IndexingModesFields`, props `{ value: IndexingModes; onChange: (next: IndexingModes) => void }` where `IndexingModes = { fetch_enabled: boolean; fetch_interval_seconds: number; index_on_commit_enabled: boolean; commit_poll_seconds: number; index_uncommitted: boolean }`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/code/__tests__/indexing-modes-fields.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { IndexingModesFields } from "../components/indexing-modes-fields"

const OFF = {
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
}

describe("IndexingModesFields", () => {
  it("disables an interval while its switch is off", () => {
    render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)

    expect(screen.getByLabelText(/fetch interval/i)).toBeDisabled()
    expect(screen.getByLabelText(/commit poll interval/i)).toBeDisabled()
  })

  it("disables the uncommitted option until commit watching is on", () => {
    const { rerender } = render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)
    expect(screen.getByRole("switch", { name: /uncommitted/i })).toBeDisabled()

    rerender(
      <IndexingModesFields
        value={{ ...OFF, index_on_commit_enabled: true }}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByRole("switch", { name: /uncommitted/i })).not.toBeDisabled()
  })

  it("says which switch writes to the working tree", () => {
    // The asymmetry an operator sharing a checkout needs, and the one thing
    // not inferable from the switch names.
    render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)

    expect(screen.getByText(/advances your working tree/i)).toBeInTheDocument()
  })

  it("emits the whole value on a toggle", async () => {
    const onChange = vi.fn()
    render(<IndexingModesFields value={OFF} onChange={onChange} />)

    await userEvent.click(screen.getByRole("switch", { name: /fetch from remote/i }))

    expect(onChange).toHaveBeenCalledWith({ ...OFF, fetch_enabled: true })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/code/__tests__/indexing-modes-fields.test.tsx`
Expected: FAIL — cannot resolve `../components/indexing-modes-fields`.

- [ ] **Step 3: Build the component**

Create `frontend/src/features/code/components/indexing-modes-fields.tsx`.

The two library APIs, read from their `.d.ts`:

```tsx
import { Switch } from "darkraise-ui/components/switch"
import { NumberInput } from "darkraise-ui/components/number-input"

// Switch:      checked?: boolean, onCheckedChange?: (checked: boolean) => void,
//              disabled?: boolean
// NumberInput: value?: number, min?: number, max?: number, disabled?: boolean,
//              onValueChange?: (d: { valueAsNumber: number; valueAsString: string }) => void
```

`onValueChange` hands back a details object, not a bare number — read
`valueAsNumber`, and guard `Number.isNaN` for a cleared field. Layout:

```
Indexing
  [switch] Fetch from remote            every [ 5 ] min
           Advances your working tree. Fast-forward only.
  [switch] Index on new commit          every [ 60 ] sec
           Watches HEAD. Covers commits from any source.
           [switch] Also index uncommitted changes
                    Indexes saved files before they are committed.
```

Each interval input is `disabled` while its switch is off; the uncommitted switch is `disabled` while `index_on_commit_enabled` is false. The fetch interval renders in minutes over a seconds-valued field, so convert at the boundary and keep the stored value in seconds. Give every control an accessible label matching the test's queries.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/code/__tests__/indexing-modes-fields.test.tsx`
Expected: PASS, 4 tests.

- [ ] **Step 5: Wire it into both dialogs**

In `add-repo-dialog.tsx`, replace the `auto_sync` Switch block (lines ~193-206) with `<IndexingModesFields …/>` driven by the existing `form` state, and replace `auto_sync: true` in the two initial-state objects with the five defaults. Update the params builder at line ~102 to send all five.

In `real-repositories-view.tsx`, replace the `auto_sync` `form.Field` (lines ~341-351) with the same component, replace the default at line ~217, and extend the dirty-field diff at line ~233 to compare all five.

Remove every remaining reference: `grep -rn "auto_sync" frontend/src` must come back empty except the `repo.auto_sync_disabled` websocket event name, which is a separate string and stays.

**Correction (2026-08-30, final fix wave):** that event name did not stay. `repo.auto_sync_disabled` — a retired flag's name for what is now "`index_on_commit_enabled` was disabled" — was renamed to `repo.index_on_commit_disabled` and declared in `EVENT_SCHEMAS`, while no frontend listener existed to break. The Step-4 code excerpt above still shows the old string.

- [ ] **Step 6: Typecheck, test, build**

```bash
cd frontend && npm run typecheck && npx vitest run && npm run build
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(ui): switch indexing modes per repository"
```

---

### Task 7: Docs, gate, changelog

**Files:**
- Modify: `CLAUDE.md` (the Jobs section's roster and count; the Code indexing section)
- Modify: `docs/design/10-code-indexing.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-08-29-per-repo-indexing-modes-design.md` (status line)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Update CLAUDE.md's job roster**

The Jobs section says "**Twenty-four** registered jobs" and lists "The eighteen live ones" including `code_reconcile`. Change the count to twenty-three, remove `code_reconcile` from both lists, and add a sentence recording that its scan now runs inside `repo_sync` per repo. This paragraph has gone stale four times; the AST-derived test in `test_code_deriver.py` is what keeps it honest.

- [ ] **Step 2: Update CLAUDE.md's Code indexing section**

Add a paragraph stating that every recurring indexing behaviour is a per-repo switch defaulting off, that `HEAD` is the single indexing trigger, that fetching only moves it, and that manual reindex, the webhook and `code_reindex` bypass the switches entirely.

- [ ] **Step 3: Update the design doc**

`docs/design/10-code-indexing.md` describes the two-loop model. Correct it to the one-loop model, in the file's own voice, and say what changed rather than silently rewriting.

- [ ] **Step 4: Mark the spec implemented**

Change the spec's `Status:` line to `implemented 2026-08-29`.

- [ ] **Step 5: Write the CHANGELOG section**

Add a `## v1.4.0 — <today>` section above the newest one. This is a `feat`, so the release workflow derives a minor bump and **refuses to publish without this section**. Cover: the switches and their defaults; that `code_reconcile`'s always-on scan is gone; that drift-caught content is now embedded rather than structurally indexed and semantically invisible; and that `auto_sync` is removed from the API.

- [ ] **Step 6: Run the full gate**

```bash
./scripts/gate.sh
```

Expected: `GATE GREEN`. Fix anything red before continuing.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md docs/ CHANGELOG.md
git commit -m "docs: record the per-repo indexing model"
```

---

### Task 8: Deploy

**Files:** none — this is an operational task run from the repo root.

**Interfaces:**
- Consumes: a green gate on master.
- Produces: a running instance on the new schema.

- [ ] **Step 1: Confirm the precondition this task rests on**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc "select count(*) from repositories;"
```

Expected: `0`. **If this is not zero, stop.** The baseline diff modifies the `repositories` table, which the runbook's additive path explicitly refuses; with rows present the only correct route is the drop-and-restore in `docs/runbook-deployment.md` § "Recovering from schema drift". The cheap path below is licensed *only* by the table being empty, which makes the column changes provably lossless.

- [ ] **Step 2: Back up**

```bash
./scripts/backup.sh /root/darkmem-backups
```

- [ ] **Step 3: Derive the DDL from a fresh migrate, never by hand**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres -c 'CREATE DATABASE darkmem_ddlref OWNER darkmem;'
# DB_PASSWORD is in the repo-root .env; export it rather than pasting it.
cd backend && DATABASE_URL="postgresql+asyncpg://darkmem:${DB_PASSWORD}@127.0.0.1:5432/darkmem_ddlref" \
  .venv/bin/python -m alembic upgrade head
```

- [ ] **Step 4: Apply the column changes to the live database**

```bash
docker compose stop darkmem
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem -v ON_ERROR_STOP=1 <<'SQL'
ALTER TABLE repositories DROP COLUMN auto_sync;
ALTER TABLE repositories ADD COLUMN fetch_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE repositories ADD COLUMN fetch_interval_seconds integer NOT NULL DEFAULT 300;
ALTER TABLE repositories ADD COLUMN index_on_commit_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE repositories ADD COLUMN commit_poll_seconds integer NOT NULL DEFAULT 60;
ALTER TABLE repositories ADD COLUMN index_uncommitted boolean NOT NULL DEFAULT false;
SQL
```

- [ ] **Step 5: Let the guard re-adopt, then prove the schema equals a fresh migrate**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem \
  -c "DELETE FROM config WHERE key='schema_baseline_sha';"
docker compose up -d darkmem
docker logs darkmem-prod-darkmem-1 2>&1 | grep 'schema baseline'   # expect "stamped"

docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem --schema-only \
  | grep -v '^--\|^\\restrict\|^\\unrestrict\|^$' > /tmp/live.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem_ddlref --schema-only \
  | grep -v '^--\|^\\restrict\|^\\unrestrict\|^$' > /tmp/fresh.sql
diff /tmp/fresh.sql /tmp/live.sql | grep '^<'          # MUST be empty
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres -c 'DROP DATABASE darkmem_ddlref;'
```

**`diff | grep '^<'` must print nothing.** Deleting the stamp is the act the guard gives no flag for; this step is what makes it honest. Do not do step 5's first half without its second.

- [ ] **Step 6: Release and redeploy**

```bash
git push origin master
```

The release workflow derives v1.4.0, verifies, publishes, tags and releases. Then pull the published image and redeploy:

```bash
DARKMEM_VERSION=1.4.0 docker compose up -d
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
```

- [ ] **Step 7: Confirm the change is in the running image**

```bash
docker exec darkmem-prod-darkmem-1 grep -c "index_on_commit_enabled" /app/app/services/job_runners.py
curl -s http://127.0.0.1:8000/openapi.json | grep -c index_on_commit_enabled
```

Both must be non-zero. Compose reuses an image whose tag did not move, so a skipped build redeploys the old bits and still reports `Started`.
