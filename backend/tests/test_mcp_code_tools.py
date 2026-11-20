"""MCP code tools against an indexed repository, driven through `/mcp/`.

Each test seeds the code-graph tables directly (no parser run) and calls the
tool over JSON-RPC with the suite's keyed client.
"""
from __future__ import annotations

import json
import uuid

import pytest

from app.models.code import CodeFile, CodeSymbol, Repository

pytestmark = pytest.mark.asyncio


async def _repo(session, name: str) -> Repository:
    repo = Repository(name=name)
    session.add(repo)
    await session.flush()
    return repo


async def _file(session, repo: Repository, path: str) -> CodeFile:
    code_file = CodeFile(
        id=uuid.uuid4(), repo_id=repo.id, file_path=path,
        language="python", content_hash=f"h-{uuid.uuid4()}",
    )
    session.add(code_file)
    await session.flush()
    return code_file


async def _symbol(session, code_file: CodeFile, name: str, *, line: int = 1, parent=None):
    symbol = CodeSymbol(
        id=uuid.uuid4(), file_id=code_file.id, name=name, kind="function",
        line_start=line, line_end=line + 1, source_code=f"def {name}(): ...",
        parent_symbol_id=parent.id if parent is not None else None,
    )
    session.add(symbol)
    await session.flush()
    return symbol


async def _call(client, name: str, arguments: dict) -> dict:
    response = await client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    assert response.status_code == 200, response.text
    return response.json()["result"]


async def test_code_symbol_answers_for_an_indexed_repository(mcp_http_client, session):
    repo = await _repo(session, f"symbols-{uuid.uuid4().hex[:6]}")
    code_file = await _file(session, repo, "pkg/mod.py")
    for index in range(55):
        await _symbol(session, code_file, "parse_config", line=index * 3 + 1)

    result = await _call(
        mcp_http_client, "code_symbol",
        {"name": "parse_config", "repo_name": repo.name},
    )

    assert not result.get("isError"), result
    rows = json.loads(result["content"][0]["text"])
    assert 0 < len(rows) <= 50
    assert {row["name"] for row in rows} == {"parse_config"}
    assert {row["kind"] for row in rows} == {"function"}
    assert {row["file_path"] for row in rows} == {"pkg/mod.py"}


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("code_symbol", {"name": "handler"}),
        ("code_file_symbols", {"file_path": "src/app.py"}),
        ("code_context", {"symbol_name": "handler"}),
        ("code_dependencies", {}),
        ("code_processes", {}),
        ("code_communities", {}),
    ],
)
async def test_repo_named_tools_refuse_an_ambiguous_name(
    mcp_http_client, session, tool, arguments,
):
    name = f"app-{uuid.uuid4().hex[:6]}"
    first = await _repo(session, name)
    second = await _repo(session, name)
    for repo in (first, second):
        await _symbol(session, await _file(session, repo, "src/app.py"), "handler")

    result = await _call(mcp_http_client, tool, {**arguments, "repo_name": name})

    assert not result.get("isError"), result
    envelope = json.loads(result["content"][0]["text"])
    assert envelope["status"] == "ambiguous"
    assert {candidate["id"] for candidate in envelope["candidates"]} == {
        str(first.id), str(second.id),
    }
