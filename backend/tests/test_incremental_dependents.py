"""Incremental reindex must re-trace callers of changed files.

Phase 02 parses only changed files, so a caller in an unchanged file that
targets a renamed/moved symbol in a changed file loses its call edge
(_delete_files_data drops it) and never regains it until a full reindex.
_find_dependent_caller_files identifies those callers so they get added to the
changed set and re-traced.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import _find_dependent_caller_files


async def _edge(session, repo_id, source_key, target_key, edge_type="calls"):
    await session.execute(
        text("""
            INSERT INTO code_edges
                (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
            VALUES (:rid, 'symbol', :sk, 'symbol', :tk, :et, '{}'::jsonb)
        """),
        {"rid": str(repo_id), "sk": source_key, "tk": target_key, "et": edge_type},
    )


async def _repo(session, name):
    repo = Repository(name=name)
    session.add(repo)
    await session.flush()
    return repo


@pytest.mark.asyncio
async def test_finds_caller_of_changed_file(session):
    repo = await _repo(session, "dep-1")
    await _edge(session, repo.id, "callerFn::caller.py", "targetFn::target.py")
    await _edge(session, repo.id, "other::x.py", "y::unrelated.py")

    deps, overflow = await _find_dependent_caller_files(session, repo.id, ["target.py"])
    assert deps == ["caller.py"]
    assert overflow == []


@pytest.mark.asyncio
async def test_excludes_changed_files_themselves(session):
    repo = await _repo(session, "dep-2")
    await _edge(session, repo.id, "callerFn::caller.py", "targetFn::target.py")
    deps, _ = await _find_dependent_caller_files(session, repo.id, ["target.py", "caller.py"])
    assert deps == []


@pytest.mark.asyncio
async def test_ignores_non_call_edges(session):
    repo = await _repo(session, "dep-3")
    await _edge(session, repo.id, "a.py", "b::target.py", edge_type="imports")
    deps, _ = await _find_dependent_caller_files(session, repo.id, ["target.py"])
    assert deps == []


@pytest.mark.asyncio
async def test_caps_and_names_the_overflow(session):
    repo = await _repo(session, "dep-4")
    for i in range(5):
        await _edge(session, repo.id, f"c{i}::caller{i}.py", "t::target.py")
    deps, overflow = await _find_dependent_caller_files(session, repo.id, ["target.py"], cap=3)
    assert len(deps) == 3
    # The work past the cap is named, not counted: it becomes index debt.
    assert overflow == ["caller3.py", "caller4.py"]
    assert set(deps) | set(overflow) == {f"caller{i}.py" for i in range(5)}
