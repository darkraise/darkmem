"""POST /repos/{id}/reindex-files (spec §6)."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from sqlalchemy import text

from app.models.code import Repository


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


async def test_accepts_and_returns_202(client, session, auth_headers, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

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

    events = await _events(session, repo.id)
    assert len(events) == 1
    assert events[0]["outcome"] == "indexing"


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


async def test_lost_claim_is_409_with_exactly_one_journal_row(
    client, session, auth_headers, tmp_path,
):
    """Regression test for the defect Correction 1 exists to fix: a request
    that clears verification but then loses the claim to a concurrent run
    must end with a 409 AND a single audit row saying `repo_busy`, never a
    409 next to a row still saying `indexing` (or two rows for one request).
    """
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
