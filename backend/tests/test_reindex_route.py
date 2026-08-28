"""POST /repos/{id}/reindex-files (spec §6)."""
from __future__ import annotations

import asyncio
import subprocess
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

from sqlalchemy import text

from app.api.routes import repos as repos_module
from app.models.code import Repository
from app.services.api_keys import issue_key, mint_credential, revoke_key
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager


def _git_repo(tmp_path: Path) -> str:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _second_commit(tmp_path: Path) -> str:
    """Add a second commit and return its sha -- a real object that is not HEAD."""
    (tmp_path / "src" / "b.py").write_text("y = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "second"],
        cwd=tmp_path, check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


async def _repo(session, tmp_path, status="ready") -> Repository:
    repo = Repository(
        name=f"rt-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path),
        provider="local", status=status,
    )
    session.add(repo)
    await session.commit()
    return repo


async def _events(session, repo_id) -> list[dict]:
    rows = (await session.execute(
        text("""
            SELECT payload FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND object_id = CAST(:r AS uuid)
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return list(rows)


def _mock_run(monkeypatch, **result) -> AsyncMock:
    """Stand in for `CodePipeline.run` (`tests/test_push_webhook.py`'s own
    pattern). Without this, `asyncio.create_task(_run_index())` fires a real
    pipeline run against the shared test database on a detached background
    session, outside the calling test's rolled-back transaction."""
    mock = AsyncMock(return_value={"status": "indexed", "commit": "deadbeef", **result})
    monkeypatch.setattr(CodePipeline, "run", mock)
    return mock


def _capture_background_tasks(monkeypatch) -> list[asyncio.Task]:
    """Same pattern as `tests/test_push_webhook.py`: capture the task
    `_spawn_repo_index` hands `TaskRegistry.register` so it can be awaited
    before a test asserts on its effects -- the route itself returns as soon
    as the task is scheduled, not when it finishes."""
    captured: list[asyncio.Task] = []
    real_register = repos_module.TaskRegistry.register

    def _capturing_register(repo_id, kind, task, message=""):
        captured.append(task)
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(repos_module.TaskRegistry, "register", _capturing_register)
    return captured


async def test_accepts_and_returns_202(
    client, session, auth_headers, tmp_path, monkeypatch,
):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    run_mock = _mock_run(monkeypatch)
    tasks = _capture_background_tasks(monkeypatch)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": head},
        headers=auth_headers,
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "indexing"
    assert body["accepted"] == 1
    assert body["commit"] == head

    assert len(tasks) == 1
    await asyncio.gather(*tasks)
    run_mock.assert_awaited_once()
    # The door's entire purpose: the canonicalised file list must actually
    # reach CodePipeline.run, not just be counted in the response.
    assert run_mock.await_args.kwargs.get("union_files") == ["src/a.py"]

    events = await _events(session, repo.id)
    assert len(events) == 1
    assert events[0]["outcome"] == "indexing"


async def test_no_files_named_omits_union_files_from_the_spawn(
    client, session, auth_headers, tmp_path, monkeypatch,
):
    """A caller naming no files must produce the same bare call shape
    polling and `reindex_repo` use -- not an explicit empty `union_files`,
    which is a different, narrower diff than "nothing named"."""
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    run_mock = _mock_run(monkeypatch)
    tasks = _capture_background_tasks(monkeypatch)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": []},
        headers=auth_headers,
    )

    assert resp.status_code == 202
    assert resp.json()["accepted"] == 0

    assert len(tasks) == 1
    await asyncio.gather(*tasks)
    run_mock.assert_awaited_once()
    assert "union_files" not in run_mock.await_args.kwargs


async def test_head_mismatch_is_409_with_both_shas(
    client, session, auth_headers, tmp_path,
):
    first = _git_repo(tmp_path)
    second = _second_commit(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": first},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["reason"] == "head_mismatch"
    assert detail["expected"] == first
    assert detail["actual"] == second


async def test_unknown_commit_is_409(client, session, auth_headers, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": "0" * 40},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["reason"] == "unknown_commit"
    assert detail["actual"] == head


async def test_escaping_path_is_400(client, session, auth_headers, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["../outside.py"]},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["reason"] == "invalid_files"


async def test_unknown_repo_is_404(client, session, auth_headers):
    repo_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    events = await _events(session, repo_id)
    assert len(events) == 1
    assert events[0]["outcome"] == "not_found"


async def test_requires_credentials(client, session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
    )
    assert resp.status_code == 401


async def test_busy_repo_precheck_refusal_is_409_with_one_journal_row(
    client, session, auth_headers, tmp_path,
):
    """A repository already `indexing` trips `prepare_reindex`'s own busy
    precheck, which journals and refuses *before* the route ever reaches
    `manager.claim_for_indexing` -- distinct from
    `test_claim_lost_after_verification_is_409_with_exactly_one_journal_row`
    below, which drives the route's own claim-loss branch instead."""
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path, status="indexing")

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["reason"] == "repo_busy"

    events = await _events(session, repo.id)
    assert len(events) == 1
    assert events[0]["outcome"] == "repo_busy"


async def test_claim_lost_after_verification_is_409_with_exactly_one_journal_row(
    client, session, auth_headers, tmp_path, monkeypatch,
):
    """Regression test for the defect Correction 1 exists to fix: a request
    that clears verification (repo status is `ready`, `prepare_reindex`
    succeeds) but then loses the claim to a concurrent run must end with a
    409 AND a single audit row saying `repo_busy` -- never a row still
    saying `indexing`, and never two rows for one request.

    `RepoManager.claim_for_indexing` is monkeypatched directly so the claim
    fails only *after* verification has already succeeded -- the precheck
    test above cannot exercise this branch, because a busy `repo.status`
    trips `prepare_reindex`'s own precheck first and the route never reaches
    `claim_for_indexing` at all.
    """
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path, status="ready")
    monkeypatch.setattr(RepoManager, "claim_for_indexing", AsyncMock(return_value=False))

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["reason"] == "repo_busy"

    events = await _events(session, repo.id)
    assert len(events) == 1
    assert events[0]["outcome"] == "repo_busy"


# ---------------------------------------------------------------------------
# API-key reachability (spec §6.1's whole rationale for `_require_repo_admin`
# over `require_auth`): mirrors tests/test_push_webhook.py's
# TestSignatureVerification for this route.
# ---------------------------------------------------------------------------


async def test_capture_only_key_is_403(client, session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    _, token = await issue_key(session, name="ci", scopes=["capture"])

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_forged_credential_is_401(client, session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers={"Authorization": f"Bearer {mint_credential().token}"},
    )
    assert resp.status_code == 401


async def test_revoked_key_is_401(client, session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    row, token = await issue_key(session, name="ci", scopes=["admin"])
    await revoke_key(session, row.id)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_valid_admin_key_is_admitted_and_calls_pipeline_run_once(
    client, session, tmp_path, monkeypatch,
):
    """The door's whole point: a git hook holds no browser session, so a
    valid `admin` key -- not a login JWT -- must be enough to reach it."""
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    run_mock = _mock_run(monkeypatch)
    tasks = _capture_background_tasks(monkeypatch)
    _, token = await issue_key(session, name="ci", scopes=["admin"])

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": head},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 202, resp.text
    assert len(tasks) == 1
    await asyncio.gather(*tasks)
    run_mock.assert_awaited_once()
    assert run_mock.await_args.kwargs.get("union_files") == ["src/a.py"]
