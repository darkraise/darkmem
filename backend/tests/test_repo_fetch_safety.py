"""The fetch path never destroys a healthy tree or moves a branch it does not
own, and a task is cancelled only through its own repository."""
from __future__ import annotations

import asyncio
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

import app.services.repo_manager as repo_manager_module
from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager
from app.services.task_registry import TaskRegistry


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _upstream(root: Path) -> Path:
    upstream = root / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "a.py").write_text("x = 1\n")
    _git(upstream, "add", "a.py")
    _git(upstream, "commit", "-qm", "init")
    return upstream


async def _managed_clone(session, tmp_path, monkeypatch) -> tuple[Repository, Path]:
    """A managed (url) repository whose clone sits under REPOS_BASE_DIR."""
    base = tmp_path / "clones"
    base.mkdir()
    monkeypatch.setattr(repo_manager_module, "REPOS_BASE_DIR", base)
    upstream = _upstream(tmp_path)
    repo = Repository(
        name=f"managed-{uuid.uuid4().hex[:6]}", url="https://example.invalid/o/r.git",
        default_branch="main", provider="github", status="ready",
    )
    session.add(repo)
    await session.flush()
    clone = base / str(repo.id)
    _git(tmp_path, "clone", "-q", str(upstream), str(clone))
    return repo, clone


async def _status(session, repo_id) -> str:
    return (await session.execute(
        select(Repository.status).where(Repository.id == repo_id)
    )).scalar_one()


async def test_failed_fetch_keeps_a_healthy_clone(session, tmp_path, monkeypatch):
    repo, clone = await _managed_clone(session, tmp_path, monkeypatch)
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "unreachable"))
    head = _git(clone, "rev-parse", "HEAD")
    clones: list = []

    async def _spy_clone(self, _repo):
        clones.append(_repo.id)

    monkeypatch.setattr(RepoManager, "_clone_repo", _spy_clone)

    with pytest.raises(RuntimeError, match="clone kept"):
        await RepoManager(session).pull_repo(repo, take_claim=True)

    assert clones == []
    assert (clone / ".git").is_dir() and (clone / "a.py").is_file()
    assert _git(clone, "rev-parse", "HEAD") == head


async def test_corrupt_clone_is_recloned_under_a_claim(session, tmp_path, monkeypatch):
    repo, clone = await _managed_clone(session, tmp_path, monkeypatch)
    upstream = tmp_path / "upstream"
    (clone / ".git" / "HEAD").unlink()
    seen: dict = {}

    async def _fake_clone(self, _repo):
        seen["status"] = await _status(session, _repo.id)
        seen["concurrent_claim"] = await RepoManager(session).claim_for_indexing(
            _repo.id, message="concurrent reindex",
        )
        _git(tmp_path, "clone", "-q", str(upstream), str(clone))

    monkeypatch.setattr(RepoManager, "_clone_repo", _fake_clone)

    head = await RepoManager(session).pull_repo(repo, take_claim=True)

    assert seen == {"status": "cloning", "concurrent_claim": False}
    assert head == _git(upstream, "rev-parse", "HEAD")
    assert await _status(session, repo.id) == "ready"


async def test_reindex_surfaces_a_failed_fetch(session, tmp_path, monkeypatch):
    repo, clone = await _managed_clone(session, tmp_path, monkeypatch)
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "unreachable"))
    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )

    with pytest.raises(RuntimeError, match="fetch failed"):
        await pipeline.run(repo.id)

    assert (clone / ".git").is_dir()


async def test_a_failed_reclone_releases_its_claim(session, tmp_path, monkeypatch):
    repo, clone = await _managed_clone(session, tmp_path, monkeypatch)
    (clone / ".git" / "HEAD").unlink()

    async def _failing_clone(self, _repo):
        raise RuntimeError("clone failed")

    monkeypatch.setattr(RepoManager, "_clone_repo", _failing_clone)

    with pytest.raises(RuntimeError, match="clone failed"):
        await RepoManager(session).pull_repo(repo, take_claim=True)

    assert await _status(session, repo.id) == "ready"


async def test_fetch_lane_leaves_a_feature_branch_alone(session, tmp_path):
    upstream = _upstream(tmp_path)
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(upstream), str(work))
    # A fresh branch with no commit of its own: a branch that has diverged
    # is already refused by --ff-only, but this one can be fast-forwarded.
    _git(work, "checkout", "-q", "-b", "feature")
    feature_head = _git(work, "rev-parse", "HEAD")
    (upstream / "a.py").write_text("x = 2\n")
    _git(upstream, "commit", "-qam", "upstream moves")
    upstream_head = _git(upstream, "rev-parse", "HEAD")

    repo = Repository(
        name=f"local-{uuid.uuid4().hex[:6]}", local_path=str(work),
        default_branch="main", provider="local", status="ready",
    )
    session.add(repo)
    await session.flush()
    manager = RepoManager(session)

    await manager.pull_repo(repo)
    assert _git(work, "rev-parse", "feature") == feature_head
    assert _git(work, "rev-parse", "HEAD") == feature_head

    _git(work, "checkout", "-q", "main")
    await manager.pull_repo(repo)
    assert _git(work, "rev-parse", "main") == upstream_head


async def test_cancel_refuses_a_task_of_another_repository(client, auth_headers, session):
    repo_a = Repository(name=f"a-{uuid.uuid4().hex[:6]}", status="indexing")
    repo_b = Repository(name=f"b-{uuid.uuid4().hex[:6]}", status="indexing")
    session.add_all([repo_a, repo_b])
    await session.flush()

    task = asyncio.create_task(asyncio.sleep(30))
    task_id = TaskRegistry.register(repo_b.id, "index", task)
    try:
        response = await client.delete(
            f"/api/v1/repos/{repo_a.id}/tasks/{task_id}", headers=auth_headers,
        )

        assert response.status_code == 404, response.text
        assert not task.done()
        assert await _status(session, repo_a.id) == "indexing"
        assert await _status(session, repo_b.id) == "indexing"
    finally:
        task.cancel()
