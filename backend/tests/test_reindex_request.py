"""The shared reindex entry point: refusals, ordering, journalling."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.reindex_request import (
    ReindexRefused,
    journal_reindex_outcome,
    prepare_reindex,
)
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
    first = _git_repo(tmp_path)
    second = _second_commit(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=first,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "head_mismatch"
    assert exc.value.detail["actual"] == second
    assert exc.value.detail["expected"] == first


async def test_a_sha_not_in_this_repository_is_unknown_commit(session, tmp_path):
    """A sha that is syntactically valid but not an object here is a different
    operator situation than a stale HEAD: it names the wrong repository, or --
    the common case -- a clone that has not yet fetched the commit the agent
    just pushed, where a sync IS exactly the retry."""
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    wrong = "0" * 40

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=wrong,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "unknown_commit"
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
    """Before repo_working_dir is even consulted -- a busy repo gets the
    honest repo_busy rather than whatever repo_working_dir raises first."""
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path, status="cloning")

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=None,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "repo_busy"


async def test_cloning_with_missing_work_dir_refuses_busy_not_unavailable(session, tmp_path):
    """Discriminates the precheck ORDER, not just its presence. A healthy
    working tree gives `repo_busy` under either order, so it cannot tell a
    correct precheck from one moved after `repo_working_dir`. Pairing
    `status="cloning"` with a `local_path` that does not exist on disk does:
    the status check must win, or this answers `repo_unavailable` instead."""
    missing = tmp_path / "not-cloned-yet"
    repo = Repository(
        name=f"rr-{uuid.uuid4().hex[:8]}",
        local_path=str(missing),
        provider="local",
        status="cloning",
    )
    session.add(repo)
    await session.commit()

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
    assert payloads[0]["outcome"] == "unknown_commit"


async def test_the_door_makes_no_mutating_git_call(session, tmp_path, monkeypatch):
    """Spec §4.1. `pull_repo` runs `reset --hard` on a clone and can re-clone
    the directory outright, so firing it from this unclaimed path would reset
    the tree under a concurrent run's parser.

    An uncommitted-file survival check alone cannot pin this: on a local-path
    repository with no remote, even a real `pull_repo` call fails its `fetch`
    (no remote configured) and returns early with the tree untouched, so the
    assertion below passes whether or not the door calls it. A spy on the one
    git entry point the door and `pull_repo` both go through is what actually
    tells the two apart."""
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    (tmp_path / "src" / "dirty.py").write_text("uncommitted = True\n")

    calls: list[list[str]] = []
    real_run_git = RepoManager._run_git

    async def spy(cwd, cmd, env=None):
        calls.append(cmd)
        return await real_run_git(cwd, cmd, env=env)

    monkeypatch.setattr(RepoManager, "_run_git", spy)

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert calls == [["git", "rev-parse", "HEAD"]]
    mutating = {"fetch", "reset", "merge", "checkout", "clone"}
    for recorded in calls:
        assert not (mutating & set(recorded)), recorded

    assert (tmp_path / "src" / "dirty.py").exists(), (
        "the door reset or re-cloned the working tree"
    )
    still = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert still == head


async def test_acceptance_is_not_journalled_by_prepare_reindex(session, tmp_path):
    """The claim that turns a validated request into `indexing` happens
    downstream, in the door, after `prepare_reindex` returns -- and it can
    still lose to a concurrent run. Journalling "indexing" in here would lie
    on that losing path, so acceptance writes no row at all until the door
    calls `journal_reindex_outcome` itself with the real outcome."""
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="agent", api_key_id=None, source="reindex_api",
    )

    payloads = await _events(session, repo.id)
    assert payloads == []


async def test_journal_reindex_outcome_stamps_actor_and_api_key_id(session, tmp_path):
    """Spec §7: every row stamps the caller's actor and api_key_id. Every
    other test in this module passes `api_key_id=None`, which cannot catch a
    dropped or misthreaded field -- this is the one door callers will use to
    write the row `prepare_reindex` itself no longer writes on success."""
    repo = await _repo_row(session, tmp_path)
    key_id = uuid.uuid4()

    await journal_reindex_outcome(
        session, repo.id, outcome="indexing", file_count=1,
        commit=None, actor="agent-42", api_key_id=key_id, source="reindex_api",
    )
    await session.commit()

    row = (await session.execute(
        text("""
            SELECT actor, api_key_id, payload FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND object_id = CAST(:r AS uuid)
        """),
        {"r": str(repo.id)},
    )).one()

    assert row.actor == "agent-42"
    assert row.api_key_id == key_id
    assert row.payload["outcome"] == "indexing"
