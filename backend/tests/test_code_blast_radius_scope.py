"""Blast radius resolves its symbol inside one repository and one owner."""
from __future__ import annotations

import json
import uuid

import pytest

from app.models.code import CodeEdge, CodeFile, CodeSymbol, Repository
from app.utils.graph_keys import compose_key

pytestmark = pytest.mark.asyncio

PATH = "src/main.py"


async def _repo(session, name: str) -> Repository:
    repo = Repository(name=name)
    session.add(repo)
    await session.flush()
    return repo


async def _file(session, repo: Repository) -> CodeFile:
    code_file = CodeFile(
        id=uuid.uuid4(), repo_id=repo.id, file_path=PATH,
        language="python", content_hash=f"h-{uuid.uuid4()}",
    )
    session.add(code_file)
    await session.flush()
    return code_file


async def _symbol(session, code_file: CodeFile, name: str, *, kind="function", parent=None):
    symbol = CodeSymbol(
        id=uuid.uuid4(), file_id=code_file.id, name=name, kind=kind,
        line_start=1, line_end=2, source_code=f"def {name}(): ...",
        parent_symbol_id=parent.id if parent is not None else None,
    )
    session.add(symbol)
    await session.flush()
    return symbol


def _calls(repo: Repository, caller: str, target_key: str) -> CodeEdge:
    return CodeEdge(
        repo_id=repo.id, source_kind="symbol", source_key=compose_key("symbol", caller, PATH),
        target_kind="symbol", target_key=target_key, edge_type="calls",
    )


async def _two_runs(session):
    """`Worker.run` and `Scheduler.run` in R1, a top-level `run` in R2."""
    r1 = await _repo(session, f"r1-{uuid.uuid4().hex[:6]}")
    r2 = await _repo(session, f"r2-{uuid.uuid4().hex[:6]}")
    f1 = await _file(session, r1)
    worker = await _symbol(session, f1, "Worker", kind="class")
    scheduler = await _symbol(session, f1, "Scheduler", kind="class")
    await _symbol(session, f1, "run", kind="method", parent=worker)
    await _symbol(session, f1, "run", kind="method", parent=scheduler)
    await _symbol(session, await _file(session, r2), "run")

    worker_key = compose_key("symbol", "run", PATH, owner="Worker")
    scheduler_key = compose_key("symbol", "run", PATH, owner="Scheduler")
    session.add_all([
        _calls(r1, "start_worker", worker_key),
        _calls(r1, "start_scheduler", scheduler_key),
        _calls(r2, "main", compose_key("symbol", "run", PATH)),
    ])
    await session.flush()
    return r1, r2, worker_key, scheduler_key


async def test_blast_radius_honours_repository_and_owner(client, auth_headers, session):
    r1, _r2, worker_key, _ = await _two_runs(session)

    response = await client.post("/api/v1/code/blast-radius", json={
        "symbol_id": worker_key, "repo_id": str(r1.id),
    }, headers=auth_headers)

    assert response.status_code == 200, response.text
    affected = {row["name"] for row in response.json()["affected"]}
    assert affected == {"start_worker"}


async def test_ambiguous_symbol_lists_candidates(
    client, auth_headers, mcp_http_client, session,
):
    r1, _r2, worker_key, scheduler_key = await _two_runs(session)

    response = await mcp_http_client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "code_blast_radius",
            "arguments": {"symbol_name": "run", "repo_name": r1.name},
        },
    })
    result = response.json()["result"]
    assert not result.get("isError"), result
    envelope = json.loads(result["content"][0]["text"])
    assert envelope["status"] == "ambiguous"
    assert {c["key"] for c in envelope["candidates"]} == {worker_key, scheduler_key}

    rest = await client.post("/api/v1/code/blast-radius", json={
        "symbol_id": compose_key("symbol", "run", PATH), "repo_id": str(r1.id),
    }, headers=auth_headers)
    assert rest.status_code == 409, rest.text
    error = rest.json()["error"]
    assert error["code"] == "symbol_ambiguous"
    assert {c["key"] for c in error["candidates"]} == {worker_key, scheduler_key}


async def test_blast_radius_requires_a_repo_id(client, auth_headers, session):
    _r1, _r2, worker_key, _ = await _two_runs(session)

    response = await client.post("/api/v1/code/blast-radius", json={"symbol_id": worker_key}, headers=auth_headers)

    assert response.status_code == 422, response.text
