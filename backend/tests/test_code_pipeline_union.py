"""union_files: added to the diff, never replacing it (spec §3.1, §3.4)."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager


async def _make_indexed_repo(session, tmp_path) -> Repository:
    """A local_path repo with one committed, indexed file."""
    import subprocess

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("def alpha():\n    return 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )

    repo = Repository(
        name=f"union-{uuid.uuid4().hex[:8]}",
        local_path=str(tmp_path),
        provider="local",
        status="ready",
    )
    session.add(repo)
    await session.commit()

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id)
    await session.refresh(repo)
    return repo


async def _indexed_symbols(session, repo_id) -> set[str]:
    rows = (await session.execute(
        text("""
            SELECT cs.name FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cf.repo_id = :r
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return set(rows)


async def test_union_file_is_indexed_when_head_has_not_moved(session, tmp_path):
    """The headline case. An uncommitted edit leaves HEAD equal to
    last_indexed_commit, so without the short-circuit amendment the run returns
    up_to_date and the named file is never looked at."""
    repo = await _make_indexed_repo(session, tmp_path)
    (tmp_path / "src" / "a.py").write_text("def beta():\n    return 2\n")

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/a.py"])

    assert result["status"] != "up_to_date"
    assert "beta" in await _indexed_symbols(session, repo.id)


async def test_first_index_reports_union_stats(session, tmp_path):
    """Interfaces: the four union_* keys appear \"whenever union_files was
    passed\" -- including a repository that has never been indexed
    (last_indexed_commit is NULL), which takes phase_01's `if not old_sha:`
    branch rather than the incremental one. That branch already indexes
    every file regardless of the union (it lists the whole tree), so this
    guards the *stats shape*, not the indexing outcome: a consumer reading
    result["union_accepted"] on a freshly added, never-indexed repository
    must not KeyError."""
    import subprocess

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("def alpha():\n    return 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )

    repo = Repository(
        name=f"union-first-{uuid.uuid4().hex[:8]}",
        local_path=str(tmp_path),
        provider="local",
        status="ready",
    )
    session.add(repo)
    await session.commit()
    assert repo.last_indexed_commit is None

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/a.py"])

    assert result["status"] == "indexed"
    for key in (
        "union_accepted", "union_skipped_unchanged",
        "union_skipped_missing", "union_skipped_unindexable",
    ):
        assert key in result, f"missing {key} on a first-index union run"
    assert result["union_accepted"] == 1
    assert "alpha" in await _indexed_symbols(session, repo.id)


async def test_unchanged_union_file_takes_the_early_exit(
    session, session_factory, tmp_path,
):
    """Nothing changed, so the run must not buy a repo-global pass."""
    repo = await _make_indexed_repo(session, tmp_path)

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/a.py"])

    assert result["status"] == "up_to_date"
    assert result["union_skipped_unchanged"] == 1

    # A refresh through the SAME session that made the change would pass
    # whether the code commits or merely mutates the ORM object and lets that
    # session's own autoflush carry it along on the next query -- it shares
    # the writer's identity map. A second session on its own connection has
    # no visibility into the first session's unflushed state, so this only
    # sees "ready" if the pipeline actually persisted it.
    async with session_factory() as verify:
        refreshed = await verify.get(Repository, repo.id)
        assert refreshed.status == "ready"


async def test_missing_union_file_deletes_nothing(session, tmp_path):
    """Spec §3.3: this door never removes graph rows."""
    repo = await _make_indexed_repo(session, tmp_path)
    before = await _indexed_symbols(session, repo.id)

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/never_existed.py"])

    assert result["union_skipped_missing"] == 1
    assert await _indexed_symbols(session, repo.id) == before


async def test_union_does_not_replace_the_diff(session, tmp_path):
    """diff ∪ named, never just named. b.py is committed and named nowhere."""
    import subprocess
    repo = await _make_indexed_repo(session, tmp_path)

    (tmp_path / "src" / "a.py").write_text("def alpha2():\n    return 1\n")
    (tmp_path / "src" / "b.py").write_text("def gamma():\n    return 3\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "two"],
        cwd=tmp_path, check=True,
    )

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=["src/a.py"])

    symbols = await _indexed_symbols(session, repo.id)
    assert "gamma" in symbols, "the diff's own file must still be indexed"
    assert "alpha2" in symbols


async def test_last_indexed_commit_advances_on_a_union_run(session, tmp_path):
    """Spec §3.5. The diff still ran, so the stamp is honest. If a union run
    ever skipped the diff, this advance would strand every unnamed changed
    file: the short-circuit would then report up_to_date forever."""
    import subprocess
    repo = await _make_indexed_repo(session, tmp_path)

    (tmp_path / "src" / "a.py").write_text("def delta():\n    return 4\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "second"],
        cwd=tmp_path, check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=["src/a.py"])

    await session.refresh(repo)
    assert repo.last_indexed_commit == head


async def test_a_variant_spelling_makes_no_second_code_file_row(
    session, tmp_path,
):
    """Spec §6.2. `_apply_union_files` performs no canonicalisation itself --
    it trusts the door to have already resolved every name to the one
    spelling `_list_all_files` produces. `code_files` has no uniqueness on
    (repo_id, file_path) and phase 03 looks its row up by exact string match,
    so feeding a raw, uncanonicalised spelling straight to `run()` would
    genuinely insert a duplicate row and duplicate symbols for one file. This
    pairs the two halves: canonicalise here exactly as the door would, then
    confirm the pipeline trusts that output."""
    from app.services.reindex_files import canonicalise_paths

    repo = await _make_indexed_repo(session, tmp_path)
    (tmp_path / "src" / "a.py").write_text("def epsilon():\n    return 5\n")

    canonical, _ = canonicalise_paths(Path(tmp_path), ["./src/a.py"])
    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=canonical)

    count = (await session.execute(
        text("""
            SELECT count(*) FROM code_files
            WHERE repo_id = CAST(:r AS uuid) AND file_path LIKE '%a.py'
        """),
        {"r": str(repo.id)},
    )).scalar_one()
    assert count == 1
