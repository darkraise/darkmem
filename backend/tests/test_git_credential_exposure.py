"""Git credentials never ride the argv, and stored failure text never carries one."""
from __future__ import annotations

import base64
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

import app.services.repo_manager as repo_manager_module
from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager

TOKEN = "tok123secretvalue"


@pytest.fixture
def git_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_manager_module, "REPOS_BASE_DIR", tmp_path)
    calls: list[tuple[list[str], dict]] = []

    def fake_run(cmd, cwd=None, capture_output=False, env=None, timeout=None):
        calls.append((list(cmd), dict(env or {})))
        if cmd[:2] == ["git", "clone"]:
            Path(cmd[-1], ".git").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(cmd, 0, stdout=b"abc123\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def _manager(session, provider="github"):
    manager = RepoManager(session)

    async def credential(_repo):
        return TOKEN, provider

    manager.get_credential = credential
    return manager


def _carries_token(env: dict) -> bool:
    for key, value in env.items():
        if not key.startswith("GIT_CONFIG_VALUE_"):
            continue
        _, _, encoded = value.partition("Basic ")
        if encoded and TOKEN in base64.b64decode(encoded).decode():
            return True
    return False


@pytest.mark.asyncio
async def test_token_never_appears_in_git_argv(session, git_calls):
    repo = Repository(
        id=uuid.uuid4(), name="r", url="https://github.com/o/r.git", default_branch="main",
    )
    manager = _manager(session)

    await manager._clone_repo(repo)
    await manager.pull_repo(repo)

    assert any(c[0][:2] == ["git", "clone"] for c in git_calls)
    assert any(c[0][:2] == ["git", "fetch"] for c in git_calls)
    for argv, _env in git_calls:
        assert not any(TOKEN in arg for arg in argv), argv
    network = [env for argv, env in git_calls if argv[1] in ("clone", "fetch")]
    assert network and all(_carries_token(env) for env in network)


@pytest.mark.asyncio
async def test_stored_failure_text_is_sanitised(session, tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()
    manager = RepoManager(session)

    async def _pull(_repo):
        return "sha-1"

    manager.pull_repo = _pull
    sent: list[tuple[str, dict]] = []

    async def capture(event_type, data):
        sent.append((event_type, data))

    from app.api.websocket import event_manager
    monkeypatch.setattr(event_manager, "broadcast", capture)

    pipe = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)

    async def _git_step():
        raise RuntimeError("fatal: https://user:tok123@host/x.git not found")

    monkeypatch.setattr(pipe, "phase_06_call_tracing", _git_step)

    with pytest.raises(RuntimeError):
        await pipe.run(repo.id, full=True)

    await session.refresh(repo)
    stored = (await session.execute(
        text("SELECT error_message FROM pipeline_failures WHERE entity_id = :r"),
        {"r": str(repo.id)},
    )).scalars().all()

    assert repo.status_message and "tok123" not in repo.status_message
    assert stored and all("tok123" not in m for m in stored)
    assert sent and all("tok123" not in repr(data) for _t, data in sent)
