"""code_reindex: the first MCP write door into the code subsystem (spec §6.1)."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.api.mcp import server as mcp_server
from app.api.mcp.scopes import ADMIN_TOOLS, CAPTURE_TOOLS, READ_TOOLS, TOOL_SCOPES
from app.api.mcp.server import code_reindex
from app.api.routes import repos as repos_module
from app.services.repo_manager import RepoManager
from tests.test_reindex_route import (
    _capture_background_tasks,
    _git_repo,
    _mock_run,
    _repo,
)


def test_code_reindex_is_an_admin_tool():
    """Not capture: triggering an index spends embedder budget and can reset a
    clone's working tree, which is repository control, not memory writing."""
    assert "code_reindex" in ADMIN_TOOLS
    assert TOOL_SCOPES["code_reindex"] == "admin"
    assert "code_reindex" not in CAPTURE_TOOLS
    assert "code_reindex" not in READ_TOOLS


def test_the_three_sets_are_disjoint():
    assert not (CAPTURE_TOOLS & READ_TOOLS)
    assert not (CAPTURE_TOOLS & ADMIN_TOOLS)
    assert not (READ_TOOLS & ADMIN_TOOLS)


def test_every_declared_tool_is_classified():
    from tests.test_mcp import _declared_tool_names

    declared = _declared_tool_names()
    assert set(TOOL_SCOPES) == declared
    assert (
        len(CAPTURE_TOOLS) + len(READ_TOOLS) + len(ADMIN_TOOLS) == len(declared)
    )


# ---------------------------------------------------------------------------
# Behaviour: the door owns the terminal journal write on every path
# `prepare_reindex` does not already cover, exactly one row per request.
# ---------------------------------------------------------------------------


class _FakePipeline:
    """Stands in for the real `CodePipeline` DI object; `_spawn_repo_index`
    reads only `.llm` and `.vector_repo` off it before `CodePipeline.run`
    itself is monkeypatched by `_mock_run`."""

    llm = None
    vector_repo = None


@pytest.fixture(autouse=True)
def mcp_session(session, monkeypatch):
    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", _FakePipeline())
    return session


async def _last_outcome(session, outcome: str) -> dict | None:
    row = (await session.execute(
        text("""
            SELECT payload, object_id FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND payload->>'outcome' = :outcome
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"outcome": outcome},
    )).first()
    if row is None:
        return None
    payload, object_id = row
    return {**payload, "object_id": object_id}


async def test_accepts_and_spawns_by_repo_path(session, tmp_path, monkeypatch):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    run_mock = _mock_run(monkeypatch)
    tasks = _capture_background_tasks(monkeypatch)

    result = json.loads(await code_reindex(
        repo_path=str(tmp_path), files=["src/a.py"], commit=head,
    ))

    assert result["status"] == "indexing"
    assert result["accepted"] == 1
    assert result["commit"] == head

    assert len(tasks) == 1
    await asyncio.gather(*tasks)
    run_mock.assert_awaited_once()
    assert run_mock.await_args.kwargs.get("union_files") == ["src/a.py"]

    row = await _last_outcome(session, "indexing")
    assert row is not None
    assert row["object_id"] == repo.id
    assert row["file_count"] == 1


async def test_resolves_by_repo_name_too(session, tmp_path, monkeypatch):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)

    result = json.loads(await code_reindex(repo_name=repo.name, files=["src/a.py"]))

    assert result["status"] == "indexing"


async def test_no_repo_reference_raises_before_touching_the_database(session):
    with pytest.raises(ValueError, match="repo_path or repo_name"):
        await code_reindex()


async def test_unknown_repo_journals_not_found_and_raises(session, tmp_path):
    with pytest.raises(ValueError, match="not found"):
        await code_reindex(repo_name="no-such-repo")

    row = await _last_outcome(session, "not_found")
    assert row is not None
    assert row["object_id"] is None
    assert row["file_count"] == 0


async def test_ambiguous_repo_journals_and_raises(session, tmp_path):
    """`name` and `local_path` carry no uniqueness, so two rows can share one
    reference and the door must refuse rather than guess."""
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    r1 = await _repo(session, tmp_path / "one")
    r2 = await _repo(session, tmp_path / "two")
    r2.name = r1.name
    await session.commit()

    with pytest.raises(ValueError, match="ambiguous"):
        await code_reindex(repo_name=r1.name, files=["a.py"])

    row = await _last_outcome(session, "ambiguous_repo")
    assert row is not None
    assert row["object_id"] is None
    assert row["file_count"] == 1


async def test_no_embedder_configured_is_a_typed_refusal_not_a_crash(
    session, tmp_path, monkeypatch,
):
    """Correction 1: `_spawn_repo_index` dereferences `pipeline.vector_repo`
    immediately, so an unconfigured instance must never reach it."""
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)
    monkeypatch.setattr(mcp_server, "_pipeline", None)

    result = json.loads(await code_reindex(repo_name=repo.name, files=["a.py"]))

    assert result == {"status": "refused", "reason": "embedder_not_configured"}

    row = await _last_outcome(session, "embedder_not_configured")
    assert row is not None
    assert row["object_id"] == repo.id
    assert row["file_count"] == 1

    fresh = await session.get(type(repo), repo.id)
    assert fresh.status != "indexing", "an unconfigured embedder must never claim the repo"


async def test_repo_busy_precheck_is_a_typed_refusal(session, tmp_path):
    """A repository already `indexing` trips `prepare_reindex`'s own precheck,
    which journals its own refusal -- the door must not journal a second row."""
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path, status="indexing")

    result = json.loads(await code_reindex(repo_name=repo.name, files=["a.py"]))

    assert result["status"] == "refused"
    assert result["reason"] == "repo_busy"

    rows = (await session.execute(
        text("""
            SELECT payload FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND object_id = CAST(:r AS uuid)
        """),
        {"r": str(repo.id)},
    )).scalars().all()
    assert len(rows) == 1, "prepare_reindex already journalled; the door must not double-journal"
    assert rows[0]["outcome"] == "repo_busy"


async def test_claim_lost_after_verification_journals_exactly_one_row(
    session, tmp_path, monkeypatch,
):
    """Mirrors the REST regression test: a request that clears verification
    but loses the claim to a concurrent run must end in exactly one
    `repo_busy` row, never a stray `indexing` one."""
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path, status="ready")
    monkeypatch.setattr(
        RepoManager, "claim_for_indexing", AsyncMock(return_value=False),
    )

    result = json.loads(await code_reindex(repo_name=repo.name, files=["a.py"]))

    assert result == {"status": "refused", "reason": "repo_busy"}

    rows = (await session.execute(
        text("""
            SELECT payload FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND object_id = CAST(:r AS uuid)
        """),
        {"r": str(repo.id)},
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0]["outcome"] == "repo_busy"


async def test_spawn_failure_journals_and_resets_repo_status(
    session, tmp_path, monkeypatch,
):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    def _raise(*_args, **_kwargs):
        raise RuntimeError("scheduling exploded")

    monkeypatch.setattr(repos_module, "_spawn_repo_index", _raise)

    result = json.loads(await code_reindex(repo_name=repo.name, files=["a.py"]))

    assert result == {"status": "refused", "reason": "spawn_failed"}

    row = await _last_outcome(session, "spawn_failed")
    assert row is not None
    assert row["object_id"] == repo.id

    fresh = await session.get(type(repo), repo.id)
    assert fresh.status == "error"
