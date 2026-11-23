"""T1.41 — T4 summary carry-over (doc 10 §3, over ``code_symbols.summary``).

Editing one symbol in a file used to re-bill every other symbol in that file:
``phase_03_structure`` deletes a changed file's ``code_files`` row (cascading
its ``code_symbols`` — and their ``summary`` — away) and ``_store_symbol``
recreates fresh rows with ``summary=NULL`` / ``enrichment_status='pending'``,
with no way to tell a symbol whose body did not change from one that did.
Editing one function in a 40-symbol file wiped and re-billed the other 39's
enrichment on the next enrich pass for zero content change.

``CodePipeline._snapshot_symbol_enrichment`` keys the old file's symbols by
``(name, kind, owner, source-hash)`` before ``_delete_files_data`` deletes them;
after ``_store_symbol`` recreates the fresh set, any new row whose key matches
a snapshot entry carries that old summary and enrichment status onto itself.
The source-hash in the key is what makes this safe: a renamed or edited
symbol misses the match and correctly re-enters the pending backlog instead
of keeping a summary describing code that no longer exists.

Real, committing git repos throughout (mirrors ``test_code_reconcile.py``):
``pull_repo`` is stubbed only to hand back the working tree's real current
HEAD, so ``phase_01_file_discovery``'s ``git diff --name-status`` genuinely
distinguishes the changed file from the untouched one.

Uses its own ``async_sessionmaker`` bound to ``tests.conftest.test_engine``
rather than the ``session`` fixture: ``EnrichmentWorker.process_batch`` opens
its own session via ``async_session_factory`` to reach the symbols phase 03
just committed, and that separate connection cannot see rows sitting in the
``session`` fixture's rollback-only transaction (the same reason
``test_code_reconcile.py``'s runner tests use a real committing factory).
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager
from tests.conftest import test_engine


def _write_files(path: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _git_init(path: Path, files: dict[str, str]) -> None:
    _write_files(path, files)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    _git_commit_all(path, "init")


def _git_commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=str(path), check=True)
    subprocess.run(
        [
            "git", "-c", "user.email=test@test.local", "-c", "user.name=Test",
            "commit", "-q", "-m", message,
        ],
        cwd=str(path), check=True,
    )


def _git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(path), check=True,
        capture_output=True, text=True,
    )
    return result.stdout.strip()


class _CountingLLM:
    """Stands in for the LLM orchestrator's enrichment path: counts every
    summarization call and returns a distinct value per call, so a symbol
    that was genuinely re-billed can be told apart from one that kept its
    old summary."""

    def __init__(self):
        self.calls = 0

    async def chat_completion(self, purpose, messages, **kwargs):
        self.calls += 1
        return f"summary #{self.calls}"


class _ExplodingLLM:
    """Any attribute access fails the test — standing in for the LLM
    orchestrator so a re-index that reaches enrichment anyway is caught
    structurally, not by timing (T1.12's no-model-call guard and T1.15's
    no-clone guard both use this shape)."""

    def __getattr__(self, name):
        async def _boom(*args, **kwargs):
            raise AssertionError(f"unchanged reindex must never call llm.{name}")
        return _boom


async def _symbol_rows(factory, repo_id) -> dict[str, tuple[str | None, str]]:
    """name -> (summary, enrichment_status) for every symbol in a repo."""
    async with factory() as session:
        rows = (await session.execute(
            text("""
                SELECT cs.name, cs.summary, cs.enrichment_status
                FROM code_symbols cs JOIN code_files cf ON cs.file_id = cf.id
                WHERE cf.repo_id = :r
            """),
            {"r": str(repo_id)},
        )).all()
    return {r[0]: (r[1], r[2]) for r in rows}


async def _index(factory, path: Path, files: dict[str, str], llm) -> uuid.UUID:
    _git_init(path, files)
    async with factory() as session:
        repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(path))
        session.add(repo)
        await session.flush()
        repo_id = repo.id

        manager = RepoManager(session)
        sha = _git_head(path)

        async def _pull(_repo, _sha=sha):
            return _sha
        manager.pull_repo = _pull

        pipe = CodePipeline(session=session, llm=llm, vector_repo=None, repo_manager=manager)
        result = await pipe.run(repo_id, full=True, enrich_symbols=True)
        assert result["status"] == "indexed"
        await session.commit()
    return repo_id


async def _reindex(factory, repo_id: uuid.UUID, path: Path, llm) -> dict:
    async with factory() as session:
        manager = RepoManager(session)
        sha = _git_head(path)

        async def _pull(_repo, _sha=sha):
            return _sha
        manager.pull_repo = _pull

        pipe = CodePipeline(session=session, llm=llm, vector_repo=None, repo_manager=manager)
        result = await pipe.run(repo_id, enrich_symbols=True)
        await session.commit()
    return result


# ── Done-when 1 & 2: carry-over both directions ─────────────────────────────


@pytest.mark.asyncio
async def test_unchanged_symbol_keeps_its_summary_and_changed_one_does_not(
    setup_database, tmp_path,
):
    # Top-level functions, deliberately not methods: a class symbol's own
    # source_code spans its whole body including every method, so editing one
    # method would also change the class's own hash and muddy the call count
    # this test is trying to pin down.
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    llm = _CountingLLM()
    repo_id = await _index(
        factory, tmp_path,
        {
            "svc.py": (
                "def start():\n"
                "    return 1\n"
                "\n"
                "\n"
                "def stop():\n"
                "    return 0\n"
            ),
        },
        llm,
    )
    try:
        before = await _symbol_rows(factory, repo_id)
        assert before["start"] == (before["start"][0], "completed")
        assert before["stop"] == (before["stop"][0], "completed")
        start_summary_before = before["start"][0]
        stop_summary_before = before["stop"][0]
        assert start_summary_before is not None
        assert stop_summary_before is not None
        calls_after_first_index = llm.calls
        assert calls_after_first_index == 2

        # Edit `stop`'s body only; `start` is byte-identical afterwards.
        (tmp_path / "svc.py").write_text(
            "def start():\n"
            "    return 1\n"
            "\n"
            "\n"
            "def stop():\n"
            "    return -1\n",
            encoding="utf-8",
        )
        _git_commit_all(tmp_path, "edit stop")

        result = await _reindex(factory, repo_id, tmp_path, llm)
        assert result["status"] == "indexed"

        after = await _symbol_rows(factory, repo_id)
        assert after["start"][0] == start_summary_before, (
            "an unchanged symbol body must keep its old summary across a file re-index"
        )
        assert after["start"][1] == "completed"
        assert after["stop"][0] != stop_summary_before, (
            "a changed symbol body must not keep the stale summary describing code "
            "that no longer exists"
        )
        assert after["stop"][1] == "completed"
        assert llm.calls == calls_after_first_index + 1, (
            "only the one changed symbol should have re-entered the enrichment "
            "backlog and been re-billed; reverting the carry-over key back to "
            "always-pending would re-bill `start` too"
        )
    finally:
        async with factory() as session:
            await session.execute(delete(Repository).where(Repository.id == repo_id))
            await session.commit()


@pytest.mark.asyncio
async def test_a_renamed_symbol_is_not_mistaken_for_carry_over(setup_database, tmp_path):
    """The owner half of the key: a method moved to a different class must
    not carry the old owner's summary onto itself."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    llm = _CountingLLM()
    repo_id = await _index(
        factory, tmp_path,
        {
            "svc.py": (
                "class Svc:\n"
                "    def start(self):\n"
                "        return 1\n"
                "\n"
                "class Other:\n"
                "    pass\n"
            ),
        },
        llm,
    )
    try:
        before = await _symbol_rows(factory, repo_id)
        start_summary_before = before["start"][0]
        assert start_summary_before is not None

        (tmp_path / "svc.py").write_text(
            "class Svc:\n"
            "    pass\n"
            "\n"
            "class Other:\n"
            "    def start(self):\n"
            "        return 1\n",
            encoding="utf-8",
        )
        _git_commit_all(tmp_path, "move start to Other")

        result = await _reindex(factory, repo_id, tmp_path, llm)
        assert result["status"] == "indexed"

        after = await _symbol_rows(factory, repo_id)
        assert after["start"][1] == "completed", "the moved symbol must still get re-enriched"
        assert after["start"][0] != start_summary_before, (
            "a symbol moved to a different owner must not carry the old owner's "
            "summary just because the body text is identical"
        )
    finally:
        async with factory() as session:
            await session.execute(delete(Repository).where(Repository.id == repo_id))
            await session.commit()


# ── Done-when 3: zero enrichment calls for untouched work ───────────────────


@pytest.mark.asyncio
async def test_reindex_leaves_the_untouched_files_symbols_uncharged(
    setup_database, tmp_path,
):
    """Two files; only one changes between indexes. The untouched file's
    symbols must cost nothing on the second pass, proven with a call-counter
    (not timing), and a fully unchanged third pass is proven never to reach
    the enrichment path at all via an exploding LLM stand-in.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    llm = _CountingLLM()
    repo_id = await _index(
        factory, tmp_path,
        {
            "svc.py": "def start():\n    return 1\n",
            "other.py": "def run():\n    return 9\n",
        },
        llm,
    )
    try:
        baseline_calls = llm.calls
        assert baseline_calls == 2
        before = await _symbol_rows(factory, repo_id)
        other_summary_before = before["run"][0]
        assert other_summary_before is not None

        (tmp_path / "svc.py").write_text(
            "def start():\n"
            "    return 1\n"
            "\n"
            "\n"
            "def stop():\n"
            "    return 0\n",
            encoding="utf-8",
        )
        _git_commit_all(tmp_path, "add stop")

        result = await _reindex(factory, repo_id, tmp_path, llm)
        assert result["status"] == "indexed"

        assert llm.calls == baseline_calls + 1, (
            "only the newly-added symbol in the changed file should have been "
            "billed; the untouched file's symbols must cost zero enrichment calls"
        )
        after = await _symbol_rows(factory, repo_id)
        assert after["run"] == (other_summary_before, "completed"), (
            "the untouched file's symbol must keep its old summary and status"
        )

        # A third pass with nothing changed at all must never reach enrichment,
        # proven structurally rather than by call count staying flat by luck.
        result2 = await _reindex(factory, repo_id, tmp_path, _ExplodingLLM())
        assert result2["status"] == "up_to_date"
    finally:
        async with factory() as session:
            await session.execute(delete(Repository).where(Repository.id == repo_id))
            await session.commit()
