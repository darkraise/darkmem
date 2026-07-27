"""T1.40 — code_reconcile: periodic working-tree drift detection.

`repo_sync` (and the reindex endpoint it wraps) only ever compares HEAD shas.
A `local_path` repo with no fetchable remote can be edited directly without
ever moving HEAD, so that comparison sees the repo as perpetually up to date
even while its content diverges from the indexed graph. `code_reconcile`
hashes the working tree independently of HEAD and feeds any mismatch through
`CodePipeline.run`'s existing incremental path via `forced_files`.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.code_reconcile import (
    CODE_RECONCILE_JOB_KEY,
    compute_working_tree_drift,
)
from app.services.job_registry import is_valid_cron
from app.services.job_runners import make_code_reconcile_runner
from app.services.repo_manager import RepoManager


def _write_files(tmp_path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = Path(tmp_path) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


async def _symbol_names(session, repo_id) -> set[str]:
    rows = (await session.execute(
        text("""
            SELECT cs.name FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cf.repo_id = :r
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return set(rows)


async def _make_indexed_repo(session, tmp_path, files: dict[str, str], sha: str):
    """A repo indexed once via `full=True`, its `pull_repo` stubbed so its sha
    never changes underneath a test — the same drift-without-a-commit shape a
    `local_path` repo with no remote produces in production."""
    _write_files(tmp_path, files)
    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()

    manager = RepoManager(session)

    async def _pull(_repo, _sha=sha):
        return _sha
    manager.pull_repo = _pull

    pipe = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    result = await pipe.run(repo.id, full=True)
    assert result["status"] == "indexed"
    await session.refresh(repo)
    assert repo.status == "ready"
    assert repo.last_indexed_commit == sha
    return repo, manager


# ── JobRegistry contract: cron, floor, lock ────────────────────────────────


def test_main_registers_the_code_reconcile_job():
    """The job has to be wired into the process that actually runs, not only
    be constructible — the lifespan is where every other job is registered."""
    import inspect

    import app.main as main

    source = inspect.getsource(main)
    assert "make_code_reconcile_runner" in source
    assert "CODE_RECONCILE_JOB_KEY" in source
    assert "CODE_RECONCILE_MIN_INTERVAL_SECONDS" in source


def test_code_reconcile_cron_and_floor_are_valid():
    from app.services.code_reconcile import (
        CODE_RECONCILE_CRON,
        CODE_RECONCILE_MIN_INTERVAL_SECONDS,
    )

    assert is_valid_cron(CODE_RECONCILE_CRON)
    assert CODE_RECONCILE_MIN_INTERVAL_SECONDS > 0


@pytest.mark.asyncio
async def test_code_reconcile_shares_lock_with_manual_trigger():
    """Registering through the real `Job`/`JobRegistry` contract gives
    code_reconcile the same per-job lock the scheduled loop and manual
    trigger share — a trigger while it's held must busy-error, never queue."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.services.job_registry import Job, JobBusyError, JobRegistry
    from app.services.code_reconcile import (
        CODE_RECONCILE_CRON,
        CODE_RECONCILE_MIN_INTERVAL_SECONDS,
        CODE_RECONCILE_MAX_RUN_SECONDS,
    )

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)

    class _FakeApp:
        class state:
            llm = None

    async def _noop():
        return None

    registry.register(Job(
        key=CODE_RECONCILE_JOB_KEY,
        display_name="Code Reconcile",
        description="d",
        default_cron=CODE_RECONCILE_CRON,
        min_interval_seconds=CODE_RECONCILE_MIN_INTERVAL_SECONDS,
        runner=_noop,
        max_run_seconds=CODE_RECONCILE_MAX_RUN_SECONDS,
    ))
    job = registry.get(CODE_RECONCILE_JOB_KEY)
    await job.lock.acquire()
    try:
        with pytest.raises(JobBusyError):
            await registry.trigger(CODE_RECONCILE_JOB_KEY)
    finally:
        job.lock.release()
        await registry.stop_all()
        await engine.dispose()
    _ = _FakeApp  # constructed only to document the runner's app.state.llm read


# ── Drift detection ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unchanged_tree_has_no_drift(session, tmp_path):
    repo, manager = await _make_indexed_repo(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-1",
    )
    work_dir = manager.repo_working_dir(repo)
    changed, deleted = await compute_working_tree_drift(session, repo, work_dir)
    assert changed == []
    assert deleted == []


@pytest.mark.asyncio
async def test_edited_file_is_drift(session, tmp_path):
    repo, manager = await _make_indexed_repo(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-1",
    )
    (Path(tmp_path) / "svc.py").write_text(
        "class Svc:\n    def start(self):\n        return 2\n", encoding="utf-8",
    )
    work_dir = manager.repo_working_dir(repo)
    changed, deleted = await compute_working_tree_drift(session, repo, work_dir)
    assert changed == ["svc.py"]
    assert deleted == []


@pytest.mark.asyncio
async def test_added_file_is_drift(session, tmp_path):
    repo, manager = await _make_indexed_repo(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-1",
    )
    (Path(tmp_path) / "new_mod.py").write_text(
        "def helper():\n    return 3\n", encoding="utf-8",
    )
    work_dir = manager.repo_working_dir(repo)
    changed, deleted = await compute_working_tree_drift(session, repo, work_dir)
    assert changed == ["new_mod.py"]
    assert deleted == []


@pytest.mark.asyncio
async def test_removed_file_is_drift(session, tmp_path):
    repo, manager = await _make_indexed_repo(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-1",
    )
    (Path(tmp_path) / "svc.py").unlink()
    work_dir = manager.repo_working_dir(repo)
    changed, deleted = await compute_working_tree_drift(session, repo, work_dir)
    assert changed == []
    assert deleted == ["svc.py"]


# ── End to end: drift feeds the incremental path, unchanged tree no-ops ────


@pytest.mark.asyncio
async def test_drifted_tree_is_reconciled_incrementally(session, tmp_path):
    """A working-tree edit with HEAD unchanged must still update the graph
    when fed through `forced_files`, and must not touch `last_indexed_commit`
    (no commit happened) or wipe unrelated files' data."""
    repo, manager = await _make_indexed_repo(
        session, tmp_path,
        {
            "svc.py": (
                "class Svc:\n"
                "    def start(self):\n"
                "        return 1\n"
            ),
            "other.py": "class Other:\n    def run(self):\n        return 9\n",
        },
        sha="sha-1",
    )
    names_before = await _symbol_names(session, repo.id)
    assert {"Svc", "start", "Other", "run"} <= names_before

    (Path(tmp_path) / "svc.py").write_text(
        "class Svc:\n    def start(self):\n        return 1\n    def stop(self):\n        return 0\n",
        encoding="utf-8",
    )
    work_dir = manager.repo_working_dir(repo)
    changed, deleted = await compute_working_tree_drift(session, repo, work_dir)
    assert changed == ["svc.py"]
    assert deleted == []

    pipe = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    result = await pipe.run(repo.id, forced_files=(changed, deleted))
    assert result["status"] == "indexed"

    await session.refresh(repo)
    # HEAD never moved — reconcile must not fabricate a new commit.
    assert repo.last_indexed_commit == "sha-1"
    assert repo.status == "ready"

    names_after = await _symbol_names(session, repo.id)
    assert "stop" in names_after, "the drifted file's new symbol must be indexed"
    assert {"Other", "run"} <= names_after, "untouched files must survive reconcile"

    changed_after, deleted_after = await compute_working_tree_drift(session, repo, work_dir)
    assert changed_after == []
    assert deleted_after == []


@pytest.mark.asyncio
async def test_unchanged_tree_short_circuits_with_no_work(setup_database, monkeypatch):
    """`CodePipeline.run` must never be invoked by the real job runner when
    there is no drift — this exercises `make_code_reconcile_runner` itself
    (not a hand-rolled copy of its gate), so a regression that deletes the
    runner's no-work check fails this test, not just the pure detector one."""
    import tempfile

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    called = {"run": False}
    orig_run = CodePipeline.run

    async def _tracking_run(self, *args, **kwargs):
        called["run"] = True
        return await orig_run(self, *args, **kwargs)

    monkeypatch.setattr(CodePipeline, "run", _tracking_run)

    with tempfile.TemporaryDirectory() as clean_dir:
        _git_init_repo(Path(clean_dir), {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"})

        async with factory() as session:
            repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=clean_dir)
            session.add(repo)
            await session.flush()
            repo_id = repo.id
            pipe = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session))
            result = await pipe.run(repo.id, full=True)
            assert result["status"] == "indexed"
            await session.commit()

        assert called["run"] is True  # the initial full index itself
        called["run"] = False

        try:
            class _FakeApp:
                class state:
                    llm = None

            runner = make_code_reconcile_runner(_FakeApp, factory)
            await runner()

            assert called["run"] is False, "an unchanged tree must never invoke CodePipeline.run"
        finally:
            async with factory() as session:
                await session.execute(delete(Repository).where(Repository.id == repo_id))
                await session.commit()


def _git_init_repo(path: Path, files: dict[str, str]) -> None:
    """A real, minimal git repo with no `origin` remote — exactly the shape a
    `local_path` repo has when nothing was ever cloned. `RepoManager.pull_repo`
    fails its fetch against this (no remote to fetch from) and, being local,
    leaves the working tree untouched and falls back to reading HEAD directly
    — the real code path a stubbed `pull_repo` would only approximate.
    """
    import subprocess

    _write_files(path, files)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(path), check=True)
    subprocess.run(
        [
            "git", "-c", "user.email=test@test.local", "-c", "user.name=Test",
            "commit", "-q", "-m", "init",
        ],
        cwd=str(path), check=True,
    )


@pytest.mark.asyncio
async def test_runner_reconciles_drifted_repo_and_skips_clean_one(setup_database):
    """The actual job runner, against a real committing session factory and
    real (remote-less) git checkouts: one repo drifted, one repo clean. Only
    the drifted repo gets reprocessed; the clean one costs nothing.

    Uses its own `async_sessionmaker` bound to `tests.conftest.test_engine`
    (see `test_buffer_flush.py`) rather than the `session` fixture, because
    `make_code_reconcile_runner` opens its own sessions via a session factory
    — those need to see committed rows from a genuinely separate connection,
    which the `session` fixture's rollback-only transaction never produces.
    """
    import tempfile

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    with tempfile.TemporaryDirectory() as dirty_dir, tempfile.TemporaryDirectory() as clean_dir:
        _git_init_repo(Path(dirty_dir), {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"})
        _git_init_repo(Path(clean_dir), {"other.py": "class Other:\n    def run(self):\n        return 1\n"})

        async with factory() as session:
            dirty_repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=dirty_dir)
            clean_repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=clean_dir)
            session.add_all([dirty_repo, clean_repo])
            await session.flush()
            dirty_id, clean_id = dirty_repo.id, clean_repo.id

            for repo in (dirty_repo, clean_repo):
                pipe = CodePipeline(
                    session=session, llm=None, vector_repo=None,
                    repo_manager=RepoManager(session),
                )
                result = await pipe.run(repo.id, full=True)
                assert result["status"] == "indexed"
            await session.commit()

        try:
            (Path(dirty_dir) / "svc.py").write_text(
                "class Svc:\n    def start(self):\n        return 1\n    def stop(self):\n        return 0\n",
                encoding="utf-8",
            )

            class _FakeApp:
                class state:
                    llm = "must-not-be-used"

            runner = make_code_reconcile_runner(_FakeApp, factory)
            await runner()

            async with factory() as session:
                dirty_names = await _symbol_names(session, dirty_id)
                assert "stop" in dirty_names

                clean_names = await _symbol_names(session, clean_id)
                assert clean_names == {"Other", "run"}
        finally:
            async with factory() as session:
                await session.execute(delete(Repository).where(Repository.id.in_([dirty_id, clean_id])))
                await session.commit()
