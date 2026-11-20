"""MCP code tools against an indexed repository, driven through `/mcp/`.

Each test seeds the code-graph tables directly (no parser run) and calls the
tool over JSON-RPC with the suite's keyed client.
"""
from __future__ import annotations

import ast
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

import app.api.mcp.server as mcp_server
from app.models.code import CodeEdge, CodeFile, CodeGraphNode, CodeSymbol, Repository


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


async def test_code_search_without_an_embedder_answers_from_the_keyword_arm(
    mcp_http_client, session, monkeypatch,
):
    monkeypatch.setattr(mcp_server, "_pipeline", None)
    repo = await _repo(session, f"search-{uuid.uuid4().hex[:6]}")
    await _symbol(session, await _file(session, repo, "cfg.py"), "parse_config")

    result = await _call(
        mcp_http_client, "code_search",
        {"query": "parse_config", "repo_name": repo.name},
    )

    assert not result.get("isError"), result
    reply = json.loads(result["content"][0]["text"])
    assert reply["degraded"] is True
    assert "semantic" in reply["reason"]
    assert [row["symbol_name"] for row in reply["results"]] == ["parse_config"]


def _edge(repo: Repository, source: str, target: str, edge_type: str, **properties) -> CodeEdge:
    return CodeEdge(
        repo_id=repo.id, source_kind="symbol", source_key=source,
        target_kind="symbol", target_key=target, edge_type=edge_type,
        properties=properties,
    )


async def test_code_rename_treats_underscore_and_percent_literally(
    mcp_http_client, session,
):
    repo = await _repo(session, f"rename-{uuid.uuid4().hex[:6]}")
    code_file = await _file(session, repo, "users.py")
    for name in ("get_user", "getXuser", "a%b", "axxb"):
        await _symbol(session, code_file, name)
    session.add_all([
        _edge(repo, "call_get::main.py", "get_user::users.py", "calls", line=3),
        _edge(repo, "call_getx::main.py", "getXuser::users.py", "calls", line=4),
        _edge(repo, "call_pct::main.py", "a%b::users.py", "calls", line=5),
        _edge(repo, "call_axxb::main.py", "axxb::users.py", "calls", line=6),
    ])
    await session.flush()

    for name, caller in (("get_user", "call_get"), ("a%b", "call_pct")):
        result = await _call(
            mcp_http_client, "code_rename",
            {"symbol_name": name, "repo_name": repo.name},
        )
        assert not result.get("isError"), result
        reply = json.loads(result["content"][0]["text"])
        calls = [ref["caller"] for ref in reply["references"] if ref["kind"] == "call"]
        assert calls == [caller], (name, calls)


async def test_code_processes_runs_a_bounded_number_of_statements(session, monkeypatch):
    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    repo = await _repo(session, f"procs-{uuid.uuid4().hex[:6]}")
    for index in range(12):
        key = f"process::flow{index:02d}"
        session.add(CodeGraphNode(
            repo_id=repo.id, kind="process", key=key, label=f"flow{index:02d}",
            properties={"entry_kind": "route", "entry_file": "app.py"},
        ))
        session.add_all([
            _edge(repo, f"step{step}::app.py", key, "step_in_process", step=step)
            for step in (1, 0)
        ])
    await session.flush()

    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        if "SAVEPOINT" not in statement.upper():
            statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _capture)
    try:
        reply = json.loads(await mcp_server.code_processes(repo.name))
    finally:
        event.remove(Engine, "before_cursor_execute", _capture)

    assert len(reply) == 12
    assert reply[0]["steps"] == ["step0", "step1"]
    assert len(statements) <= 3, statements


_SQL_CALLS = {"select", "text"}


def _code_tool_bodies():
    tree = ast.parse(Path(mcp_server.__file__).read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name.startswith("code_")
            # The one write door into the code subsystem keeps its own lookup.
            and node.name != "code_reindex"
        ):
            yield node


def test_mcp_code_tools_hold_no_sql():
    bodies = list(_code_tool_bodies())
    assert len(bodies) >= 10
    offenders = {}
    for tool in bodies:
        found = []
        for node in ast.walk(tool):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in _SQL_CALLS:
                found.append(f"{func.id}(")
            elif (
                isinstance(func, ast.Attribute)
                and func.attr in {"execute", "get", "scalar", "scalars"}
                and isinstance(func.value, ast.Name)
                and "session" in func.value.id
            ):
                found.append(f"{func.value.id}.{func.attr}")
        if not any(
            isinstance(node, ast.Name) and node.id == "CodeQueryService"
            for node in ast.walk(tool)
        ):
            found.append("no CodeQueryService")
        if found:
            offenders[tool.name] = found
    assert offenders == {}
