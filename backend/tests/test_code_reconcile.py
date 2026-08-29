"""T1.40 / spec 2026-08-29 — working-tree drift detection.

A `local_path` repo with no fetchable remote can be edited directly without
ever moving HEAD, so a bare HEAD-sha comparison sees the repo as perpetually
up to date even while its content diverges from the indexed graph.
`compute_working_tree_drift` hashes the working tree independently of HEAD
and feeds any mismatch through `CodePipeline.run`'s existing incremental
path via `forced_files`.

The standalone `code_reconcile` job this used to describe is retired
(spec 2026-08-29, task 3): the same drift scan now runs per repo inside the
single `repo_sync` loop, gated by `index_uncommitted`, and is covered there
(`tests/test_repo_indexing_modes.py`). This file keeps only the pure
`compute_working_tree_drift` coverage, since that function is unchanged.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.code_reconcile import compute_working_tree_drift
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


