"""CodeQueryService.search_code keyword pass must rank by relevance.

With no ORDER BY, the ILIKE pass assigned RRF ranks from arbitrary heap order, so
an exact name match could rank below an incidental substring hit in some other
function's body. With the LLM absent the keyword pass is the only signal, so its
order fully determines results. Order exact name > prefix > substring > body.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.code import CodeFile, CodeSymbol, Repository
from app.services.code_query import CodeQueryService


async def _seed_symbol(session, repo_id, file_id, name, source, line):
    session.add(CodeSymbol(
        id=uuid.uuid4(), file_id=file_id, name=name, kind="function",
        line_start=line, line_end=line + 1, source_code=source,
    ))


@pytest.mark.asyncio
async def test_search_code_ranks_exact_name_first(session):
    repo = Repository(name="r")
    session.add(repo)
    await session.flush()
    cf = CodeFile(id=uuid.uuid4(), repo_id=repo.id, file_path="a.py", language="python", content_hash="h")
    session.add(cf)
    await session.flush()

    # All three match "parse" via ILIKE; only ordering distinguishes them.
    await _seed_symbol(session, repo.id, cf.id, "helper", "def helper(): return parse_thing()", 10)  # body hit
    await _seed_symbol(session, repo.id, cf.id, "parse_config", "def parse_config(): ...", 20)        # prefix
    await _seed_symbol(session, repo.id, cf.id, "parse", "def parse(): ...", 30)                      # exact name
    await session.flush()

    svc = CodeQueryService(session, llm=None)  # no LLM => keyword pass only
    results = (await svc.search_code("parse", limit=10, repo_id=repo.id)).results

    names = [r["symbol_name"] for r in results]
    assert names[0] == "parse"
    assert names.index("parse_config") < names.index("helper")
