"""Loading a repository row must not load its files and symbols with it.

Every repo route, every `repo_sync` tick and the repository list load
`Repository` rows. With the child collections eager, each of those reads pulled
every `code_files` row and every `code_symbols` row of the repository, source
text included, to serve a caller that never looks at them.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, inspect, select

from app.models.code import CodeFile, CodeSymbol, Repository

pytestmark = pytest.mark.asyncio


async def _seed(session) -> tuple[uuid.UUID, uuid.UUID]:
    repo = Repository(name=f"rel-{uuid.uuid4().hex[:8]}", local_path="/tmp/rel")
    session.add(repo)
    await session.flush()
    code_file = CodeFile(repo_id=repo.id, file_path="src/main.py", language="python")
    session.add(code_file)
    await session.flush()
    session.add(CodeSymbol(
        file_id=code_file.id, name="target", kind="function",
        line_start=1, line_end=2, source_code="def target(): ...",
    ))
    await session.flush()
    session.expunge_all()
    return repo.id, code_file.id


async def test_a_repository_row_loads_without_its_files_and_symbols(session):
    repo_id, file_id = await _seed(session)

    repo = (await session.execute(select(Repository).where(Repository.id == repo_id))).scalar_one()
    code_file = (await session.execute(select(CodeFile).where(CodeFile.id == file_id))).scalar_one()

    assert "files" in inspect(repo).unloaded
    assert "symbols" in inspect(code_file).unloaded


async def test_deleting_a_repository_still_removes_its_files_and_symbols(session):
    repo_id, file_id = await _seed(session)

    await session.delete(await session.get(Repository, repo_id))
    await session.flush()

    files = (await session.execute(
        select(func.count()).select_from(CodeFile).where(CodeFile.repo_id == repo_id)
    )).scalar_one()
    symbols = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.file_id == file_id)
    )).scalar_one()
    assert (files, symbols) == (0, 0)
