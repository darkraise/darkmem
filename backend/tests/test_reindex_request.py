"""The shared reindex entry point: refusals, ordering, journalling."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.reindex_request import ReindexRefused, prepare_reindex


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


async def _repo_row(session, tmp_path, status="ready") -> Repository:
    repo = Repository(
        name=f"rr-{uuid.uuid4().hex[:8]}",
        local_path=str(tmp_path),
        provider="local",
        status=status,
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


async def test_matching_commit_is_accepted(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    accepted = await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert accepted.union_files == ["src/a.py"]
    assert accepted.head == head


async def test_head_mismatch_refuses_with_both_shas(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    wrong = "0" * 40

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=wrong,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "head_mismatch"
    assert exc.value.detail["actual"] == head
    assert exc.value.detail["expected"] == wrong


async def test_escaping_path_hard_refuses_the_request(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py", "../outside.py"], commit=None,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "invalid_files"


async def test_absent_path_is_soft_skipped_not_refused(session, tmp_path):
    """A clone's tree is stale; the most ordinary push names a file it lacks."""
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    accepted = await prepare_reindex(
        session, repo, files=["src/added.py"], commit=None,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert accepted.union_files == ["src/added.py"]


async def test_cloning_repo_refuses_at_the_precheck(session, tmp_path):
    """Before canonicalisation, which would otherwise fail inside an rglob."""
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path, status="cloning")

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=None,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "repo_busy"


async def test_over_cap_list_is_refused(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=[f"src/f{i}.py" for i in range(1001)],
            commit=None, actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "too_many_files"


async def test_malformed_commit_is_refused_before_any_git_call(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit="not-a-sha; rm -rf /",
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "malformed_commit"


async def test_a_refusal_is_journalled(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused):
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit="0" * 40,
            actor="agent", api_key_id=None, source="reindex_api",
        )

    payloads = await _events(session, repo.id)
    assert len(payloads) == 1
    assert payloads[0]["outcome"] == "head_mismatch"


async def test_the_door_makes_no_mutating_git_call(session, tmp_path):
    """Spec §4.1. `pull_repo` runs `reset --hard` on a clone and can re-clone
    the directory outright, so firing it from this unclaimed path would reset
    the tree under a concurrent run's parser."""
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    (tmp_path / "src" / "dirty.py").write_text("uncommitted = True\n")

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert (tmp_path / "src" / "dirty.py").exists(), (
        "the door reset or re-cloned the working tree"
    )
    still = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert still == head


async def test_acceptance_is_journalled(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="agent", api_key_id=None, source="reindex_api",
    )

    payloads = await _events(session, repo.id)
    assert len(payloads) == 1
    assert payloads[0]["outcome"] == "indexing"
    assert payloads[0]["file_count"] == 1
