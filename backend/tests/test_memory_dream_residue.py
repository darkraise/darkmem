"""T4.11 — regression: a durably-seeded, half-registered embedder fingerprint
must never survive `test_memory_dream.py` into a later suite.

This file is deliberately named to sort **immediately** after
`test_memory_dream.py`, so a default pytest run collects and executes it in
the same session, on the same schema, right after that suite's `committing`
fixture has had a chance to leave residue behind. T4.11 originally put these
two tests in `test_push_webhook.py` for the same ordering reason; T4.05 then
landed a real webhook suite under that name, so they moved here — which is a
tighter guarantee anyway, since nothing can now sort between the two files.

`test_memory_dream.py`'s `committing` fixture drives real, per-batch commits
(the rollback-isolated `session` fixture cannot express what a dream cycle
does), and its helper `seed_partition` durably registers an `embedders` row
for a fingerprint (`t212-embedder|...`) while creating only the
`memory_embeddings__<slug>` child table — not the full set
`embedder_registry.register` guarantees in production. Any repository method
that loops every `embedders` row and assumes the full partition set (for
example `PostgresVectorRepository.delete_code_chunks_by_repo`) then crashes
against that fingerprint's missing `code_chunk_embeddings__<slug>` table.

`CodePipeline.run`'s first-index path (`phase_01_file_discovery`) calls
exactly that method whenever `vector_repo` is live, so a genuine first index
run anywhere after `test_memory_dream.py` is where this actually bites.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.models.code import Repository
from app.repositories.vector import PostgresVectorRepository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager


async def _first_index_pipeline(session, tmp_path, vector_repo) -> tuple[CodePipeline, Repository]:
    file_path = Path(tmp_path) / "svc.py"
    file_path.write_text("def handler():\n    return 1\n", encoding="utf-8")

    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()

    manager = RepoManager(session)

    async def _pull(_repo, _sha="deadbeef"):
        return _sha

    manager.pull_repo = _pull

    pipe = CodePipeline(session=session, llm=None, vector_repo=vector_repo, repo_manager=manager)
    return pipe, repo


@pytest.mark.asyncio
async def test_first_index_survives_prior_suite_embedder_residue(session, tmp_path):
    """A real first-index `CodePipeline.run` with a live `vector_repo`, run in
    the same schema `test_memory_dream.py` just finished in, must not crash on
    a fingerprint that suite seeded but never fully registered."""
    vector_repo = PostgresVectorRepository(session)
    pipe, repo = await _first_index_pipeline(session, tmp_path, vector_repo)

    result = await pipe.run(repo.id, full=True)

    assert result["status"] == "indexed"
    await session.refresh(repo)
    assert repo.status == "ready"
    assert repo.last_indexed_commit == "deadbeef"


@pytest.mark.asyncio
async def test_first_index_cleanup_failure_reports_the_real_cause(session, tmp_path, monkeypatch):
    """`CodePipeline.run`'s exception-cleanup path must surface whatever
    broke `_delete_all_repo_data`, not a secondary `MissingGreenlet` from
    touching an expired `repo` object after `session.rollback()`.

    Independent of the embedder-residue scenario above: any *SQL-level*
    failure inside a first index's cleanup step re-fetches `repo`
    post-rollback, and that re-fetch can legitimately come back `None` in
    this test harness (the rollback can undo the row's own creation, since
    it was never committed outside this test's transaction). Falling back
    to the original, now-expired `repo` object and touching its attributes
    is what raised `MissingGreenlet` — pin that regardless of what triggers
    the underlying failure, so this stays covered if T4.11's embedder-residue
    fix ever makes that trigger disappear. A synthetic *Python* exception
    (no SQL involved) does not reproduce this: it never poisons the DBAPI
    transaction the way a real failed statement does, so the mutation only
    bites for a genuine SQL-level failure, matching the embedder-residue case.
    """
    from sqlalchemy import text

    vector_repo = PostgresVectorRepository(session)

    async def _boom(self, repo_id):
        await self.session.execute(
            text("DELETE FROM this_table_does_not_exist_t4_11 WHERE repo_id = :rid"),
            {"rid": str(repo_id)},
        )

    monkeypatch.setattr(PostgresVectorRepository, "delete_code_chunks_by_repo", _boom)

    pipe, repo = await _first_index_pipeline(session, tmp_path, vector_repo)

    with pytest.raises(Exception) as excinfo:
        await pipe.run(repo.id, full=True)
    assert "this_table_does_not_exist_t4_11" in str(excinfo.value)
