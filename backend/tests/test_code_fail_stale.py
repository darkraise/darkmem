"""T1.38 — a pipeline exception must never wipe the code graph.

Before this fix, any exception raised anywhere in ``CodePipeline.run`` (after
file discovery started) hit a bare ``except Exception`` that unconditionally
deleted every row for the repo via ``_delete_all_repo_data`` before
re-raising. A transient failure — a flaky LLM call, a git hiccup, an OOM mid
parse — therefore destroyed a working code graph with no way back short of a
full re-index, and the user's only visible symptom was "my code search went
empty" with no error surfaced anywhere.

The fix: a run that fails after a prior successful index exists must leave
that graph queryable and mark the repo ``stale``, naming the last-good commit
and the failure cause. Only a repo with no prior successful index (nothing to
protect) still gets the destructive cleanup on failure.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

import app.services.code_pipeline as code_pipeline_module
from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
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


async def _make_repo_with_manager(session, tmp_path, files: dict[str, str], sha: str):
    _write_files(tmp_path, files)
    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()

    manager = RepoManager(session)

    async def _pull(_repo, _sha=sha):
        return _sha
    manager.pull_repo = _pull
    return repo, manager


@pytest.mark.asyncio
async def test_mid_index_failure_marks_stale_and_keeps_prior_graph(session, tmp_path, monkeypatch):
    repo, manager = await _make_repo_with_manager(
        session, tmp_path,
        {
            "svc.py": (
                "class Svc:\n"
                "    def start(self):\n"
                "        return self.helper()\n"
                "    def helper(self):\n"
                "        return 1\n"
            ),
        },
        sha="sha-good-1",
    )

    pipe1 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    result = await pipe1.run(repo.id, full=True)
    assert result["status"] == "indexed"
    await session.refresh(repo)
    assert repo.status == "ready"
    assert repo.last_indexed_commit == "sha-good-1"

    names_before = await _symbol_names(session, repo.id)
    assert {"Svc", "start", "helper"} <= names_before

    async def _pull2(_repo):
        return "sha-bad-2"
    manager.pull_repo = _pull2

    pipe2 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)

    async def _boom():
        raise RuntimeError("simulated transient failure in phase 06")
    monkeypatch.setattr(pipe2, "phase_06_call_tracing", _boom)

    with pytest.raises(RuntimeError):
        await pipe2.run(repo.id, full=True)

    await session.refresh(repo)
    # The stale label names both the last-good sha and the cause — this is
    # the contract T1.46's banner reads.
    assert repo.status == "stale"
    assert "sha-good-1" in repo.status_message
    assert "simulated transient failure in phase 06" in repo.status_message
    # last_indexed_commit is only ever advanced on full success, so it still
    # names the last graph that was actually built — the failed run's sha
    # never lands here.
    assert repo.last_indexed_commit == "sha-good-1"

    names_after = await _symbol_names(session, repo.id)
    assert names_after == names_before, "prior graph must stay queryable, untouched by the failed run"


@pytest.mark.asyncio
async def test_first_index_failure_still_cleans_up(session, tmp_path, monkeypatch):
    """A repo with no prior successful index has no graph worth protecting;
    a failure there still clears whatever partial junk it produced and marks
    the repo 'error', not 'stale' (there is no last-good commit to name)."""
    repo, manager = await _make_repo_with_manager(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-first",
    )

    pipe = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)

    async def _boom():
        raise RuntimeError("first-index failure")
    monkeypatch.setattr(pipe, "phase_06_call_tracing", _boom)

    with pytest.raises(RuntimeError):
        await pipe.run(repo.id, full=True)

    await session.refresh(repo)
    assert repo.status == "error"
    assert repo.last_indexed_commit is None

    names_after = await _symbol_names(session, repo.id)
    assert names_after == set()


@pytest.mark.asyncio
async def test_diff_failure_falls_back_to_full_index_not_wipe(session, tmp_path, monkeypatch):
    """A git-diff failure on an otherwise-healthy incremental reindex must
    fall back to a full pass, not degrade into a wipe."""
    repo, manager = await _make_repo_with_manager(
        session, tmp_path,
        {
            "svc.py": (
                "class Svc:\n"
                "    def start(self):\n"
                "        return self.helper()\n"
                "    def helper(self):\n"
                "        return 1\n"
            ),
        },
        sha="sha-good-1",
    )

    pipe1 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    await pipe1.run(repo.id, full=True)
    await session.refresh(repo)
    assert repo.status == "ready"
    names_before = await _symbol_names(session, repo.id)

    async def _pull2(_repo):
        return "sha-good-2"
    manager.pull_repo = _pull2

    async def _raising_diff(*args, **kwargs):
        raise RuntimeError("git diff --name-status failed: corrupt object")
    monkeypatch.setattr(code_pipeline_module, "_diff_files", _raising_diff)

    pipe2 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    result = await pipe2.run(repo.id, full=False)

    assert result["status"] == "indexed"
    await session.refresh(repo)
    assert repo.status == "ready"
    assert repo.last_indexed_commit == "sha-good-2"

    names_after = await _symbol_names(session, repo.id)
    assert names_after == names_before


@pytest.mark.asyncio
async def test_forced_full_reindex_of_existing_repo_does_not_wipe_upfront(session, tmp_path):
    """A `full=True` reindex of an already-indexed repo must reprocess every
    file in place (delete+recreate paired per file), never nuke the whole
    repo's graph before the new pass has written anything."""
    repo, manager = await _make_repo_with_manager(
        session, tmp_path,
        {"svc.py": "class Svc:\n    def start(self):\n        return 1\n"},
        sha="sha-good-1",
    )
    pipe1 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    await pipe1.run(repo.id, full=True)

    async def _pull2(_repo):
        return "sha-good-2"
    manager.pull_repo = _pull2

    calls: list[str] = []
    real_delete_all = CodePipeline._delete_all_repo_data

    async def _tracking_delete_all(self, repo_id):
        calls.append("wipe")
        await real_delete_all(self, repo_id)

    pipe2 = CodePipeline(session=session, llm=None, vector_repo=None, repo_manager=manager)
    pipe2._delete_all_repo_data = _tracking_delete_all.__get__(pipe2, CodePipeline)

    result = await pipe2.run(repo.id, full=True)

    assert result["status"] == "indexed"
    assert calls == [], "a forced full reindex of an existing repo must not call the repo-wide wipe"

    names_after = await _symbol_names(session, repo.id)
    assert names_after == {"Svc", "start"}
