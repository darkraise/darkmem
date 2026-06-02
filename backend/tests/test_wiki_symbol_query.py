"""Wiki generation must fetch symbols in one query, not one per file.

The module loop issued a `SELECT CodeSymbol WHERE file_id = :id` per file — a
classic N+1 that scales queries with repo size. One grouped query suffices.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.code import CodeFile, CodeSymbol, Repository
from app.services.wiki_generator import WikiGenerator


@pytest.mark.asyncio
async def test_wiki_fetches_symbols_in_one_query(session, monkeypatch):
    repo = Repository(name="r")
    session.add(repo)
    await session.flush()

    for i in range(4):
        cf = CodeFile(
            id=uuid.uuid4(), repo_id=repo.id, file_path=f"pkg/m{i}.py",
            language="python", content_hash="h",
        )
        session.add(cf)
        session.add(CodeSymbol(
            id=uuid.uuid4(), file_id=cf.id, name=f"fn{i}", kind="function",
            line_start=1, line_end=2, source_code=f"def fn{i}(): pass",
        ))
    await session.flush()

    counter = {"symbol_selects": 0}
    orig_execute = session.execute

    async def counting_execute(stmt, *a, **k):
        if "code_symbols" in str(stmt).lower():
            counter["symbol_selects"] += 1
        return await orig_execute(stmt, *a, **k)

    monkeypatch.setattr(session, "execute", counting_execute)

    result = await WikiGenerator(session, llm=None).generate(repo.id)

    # One grouped symbol query for the whole repo, not one per file (4 files).
    assert counter["symbol_selects"] <= 1
    # And the wiki still reflects the symbols.
    assert result.get("total_symbols", 0) >= 4 or any(
        m.get("symbol_count", 0) > 0 for m in result.get("modules", [])
    )
