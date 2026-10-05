"""The MCP call log: what the door records per ``tools/call``, and the REST
read over it."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mcp.types import CallToolResult, TextContent
from sqlalchemy import delete as sa_delete
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.services.mcp_call_log as mcp_call_log
from app.models.api_key import ApiKey
from app.models.config import Config
from app.services.api_keys import issue_key
from app.services.mcp_call_log import (
    MCP_CALL_CLEANUP_JOB_KEY,
    summarise_arguments,
    summarise_result,
)
from tests.conftest import test_engine


# --- Minimisation ------------------------------------------------------------


def test_content_arguments_are_stored_as_a_size_only():
    out = summarise_arguments(
        {
            "content": "my secret note",
            "entries": [{"content": "a"}, {"content": "b"}],
            "text": "block text",
            "properties": {"checked": True},
            "project": "darkmem",
        },
        log_query_text=True,
    )

    assert out == {
        "content": {"chars": 14},
        "entries": {"items": 2},
        "text": {"chars": 10},
        "properties": {"items": 1},
        "project": "darkmem",
    }


def test_query_text_is_stored_only_when_switched_on():
    args = {"query": "how do we deploy", "question": "why?", "limit": 5}

    assert summarise_arguments(args, log_query_text=False) == {
        "query": {"chars": 16}, "question": {"chars": 4}, "limit": 5,
    }
    assert summarise_arguments(args, log_query_text=True) == args


def test_long_strings_and_long_lists_are_bounded():
    out = summarise_arguments(
        {"uri": "x" * 500, "tags_any": [f"t{i}" for i in range(25)]},
        log_query_text=False,
    )

    assert out["uri"] == {"chars": 500}
    assert out["tags_any"][:2] == ["t0", "t1"]
    assert out["tags_any"][-1] == {"more": 5}
    assert len(out["tags_any"]) == 21


def _text_result(payload) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))])


def test_a_list_result_yields_its_count_and_ids():
    a, b = str(uuid.uuid4()), str(uuid.uuid4())

    count, ids = summarise_result(_text_result([{"id": a}, {"id": b}, {"id": a}]))

    assert count == 3
    assert ids == [a, b]


def test_a_section_hit_names_its_document_not_its_block():
    count, ids = summarise_result(_text_result([
        {"block_id": "blk", "document_id": "doc-1", "text": "..."},
    ]))

    assert (count, ids) == (1, ["doc-1"])


def test_an_enveloped_result_reads_its_list():
    count, ids = summarise_result(_text_result({"results": [{"memory_id": "m1"}]}))
    assert (count, ids) == (1, ["m1"])

    count, ids = summarise_result(_text_result({"sections": {"facts": [{"id": "f1"}], "memories": [{"id": "m2"}]}}))
    assert (count, ids) == (2, ["f1", "m2"])


def test_a_single_object_result_counts_as_one():
    assert summarise_result(_text_result({"id": "abc", "content": "x"})) == (1, ["abc"])


def test_an_unreadable_result_records_nothing_and_never_raises():
    assert summarise_result(CallToolResult(content=[TextContent(type="text", text="not json")])) == (None, [])
    assert summarise_result(object()) == (None, [])
    assert summarise_result(None) == (None, [])


# --- Through the door --------------------------------------------------------


def _call(name: str, **args) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": args,
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
                "io.modelcontextprotocol/clientCapabilities": {},
            },
        },
    }


@pytest_asyncio.fixture
async def read_key(setup_database):
    """Committed, so the token verifier sees it. Request it before ``door``:
    teardown runs in reverse, and deleting the key while the test's open
    transaction holds log rows referencing it would wait on that lock."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        row, credential = await issue_key(s, name="reader-agent", scopes=["read"])
        row_id = row.id
        await s.commit()
    yield row_id, credential
    async with factory() as s:
        await s.execute(sa_delete(ApiKey).where(ApiKey.id == row_id))
        await s.commit()


@pytest_asyncio.fixture
async def door(mcp_streamable_app, session, monkeypatch):
    from contextlib import asynccontextmanager

    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())
    async with AsyncClient(
        transport=ASGITransport(app=mcp_streamable_app),
        base_url="http://localhost:8000",
        headers={"Accept": "application/json"},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def committed(setup_database):
    """A factory on its own connection, emptied of log rows around the test.

    The door tests drain onto this rather than the rollback-isolated
    ``session``: a tool's error path rolls that session back, which ends the
    fixture's isolation boundary (see ``tests/conftest.py``), so rows drained
    after it would commit anyway. Owning the cleanup is the honest shape.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _clean():
        async with factory() as s:
            await s.execute(text("DELETE FROM mcp_tool_calls"))
            await s.execute(text("DELETE FROM config WHERE key = :k"),
                            {"k": f"job:{MCP_CALL_CLEANUP_JOB_KEY}"})
            await s.commit()

    await _clean()
    yield factory
    await _clean()


async def _rows(session_or_factory) -> list[dict]:
    sql = text("SELECT * FROM mcp_tool_calls ORDER BY occurred_at, tool")
    if isinstance(session_or_factory, async_sessionmaker):
        async with session_or_factory() as s:
            result = (await s.execute(sql)).mappings().all()
    else:
        result = (await session_or_factory.execute(sql)).mappings().all()
    return [dict(r) for r in result]


async def test_each_kind_of_call_lands_one_row(read_key, committed, door):
    row_id, credential = read_key
    headers = {"Authorization": f"Bearer {credential}", "X-Darkmem-Client": "codex"}
    missing = str(uuid.uuid4())

    ok = await door.post("/", json=_call("memory_stats"), headers=headers)
    failed = await door.post("/", json=_call("memory_get", memory_id=missing), headers=headers)
    denied = await door.post(
        "/", json=_call("memory_add", content="secret words", project="p"), headers=headers,
    )
    assert ok.status_code == failed.status_code == denied.status_code == 200

    await mcp_call_log.drain(committed)
    rows = {r["tool"]: r for r in await _rows(committed)}

    assert set(rows) == {"memory_stats", "memory_get", "memory_add"}
    for row in rows.values():
        assert row["api_key_id"] == row_id
        assert row["key_name"] == "reader-agent"
        assert row["client"] == "codex"
        assert row["duration_ms"] >= 0

    assert rows["memory_stats"]["status"] == "ok"
    assert rows["memory_stats"]["scope"] == "read"
    assert rows["memory_get"]["status"] == "error"
    assert "memory_get" in rows["memory_get"]["error"]
    assert rows["memory_get"]["arguments"] == {"memory_id": missing}
    assert rows["memory_add"]["status"] == "denied"
    assert rows["memory_add"]["project"] == "p"
    # A refused capture still never stores what it tried to write.
    assert rows["memory_add"]["arguments"]["content"] == {"chars": 12}


async def test_query_text_follows_the_retention_jobs_switch(read_key, committed, door):
    _row_id, credential = read_key
    headers = {"Authorization": f"Bearer {credential}"}
    async with committed() as s:
        s.add(Config(
            key=f"job:{MCP_CALL_CLEANUP_JOB_KEY}",
            value={"enabled": True, "cron": "15 4 * * *", "min_interval_seconds": 3600,
                   "config": {"log_query_text": 1}},
        ))
        await s.commit()

    await door.post("/", json=_call("memory_search", query="deploy steps", limit=3), headers=headers)
    await mcp_call_log.drain(committed)

    (row,) = await _rows(committed)
    assert row["arguments"]["query"] == "deploy steps"
    assert row["arguments"]["limit"] == 3


async def test_query_text_is_withheld_by_default(read_key, committed, door):
    _row_id, credential = read_key

    await door.post(
        "/", json=_call("memory_search", query="deploy steps"),
        headers={"Authorization": f"Bearer {credential}"},
    )
    await mcp_call_log.drain(committed)

    (row,) = await _rows(committed)
    assert row["arguments"]["query"] == {"chars": 12}


async def test_read_only_mode_records_nothing(monkeypatch):
    monkeypatch.setattr(mcp_call_log.settings, "read_only", True)

    mcp_call_log.record_call(
        tool="memory_stats", scope="read", status="ok", duration_ms=1,
        api_key_id=None, key_name=None, client=None, arguments={},
    )

    assert len(mcp_call_log._buffer) == 0


# --- The REST read -----------------------------------------------------------


async def _seed(session, **overrides) -> None:
    row = {
        "occurred_at": datetime.now(timezone.utc),
        "tool": "memory_search", "scope": "read", "status": "ok",
        "duration_ms": 10, "key_name": "agent", "client": "claude-code",
        "project": "darkmem", "arguments": "{}", "result_count": 2,
        "result_ids": ["m1", "m2"], "error": None,
    }
    row.update(overrides)
    await session.execute(text(
        """
        INSERT INTO mcp_tool_calls
            (occurred_at, tool, scope, status, duration_ms, key_name, client,
             project, arguments, result_count, result_ids, error)
        VALUES (:occurred_at, :tool, :scope, :status, :duration_ms, :key_name,
                :client, :project, CAST(:arguments AS jsonb), :result_count,
                CAST(:result_ids AS text[]), :error)
        """
    ), row)


async def test_the_list_is_newest_first_and_filterable(client, auth_headers, session):
    now = datetime.now(timezone.utc)
    await _seed(session, occurred_at=now - timedelta(minutes=2))
    await _seed(session, occurred_at=now - timedelta(minutes=1), tool="document_get",
                result_ids=["d1"], result_count=1)
    await _seed(session, occurred_at=now, status="error", error="boom",
                result_ids=[], result_count=None)
    await session.flush()

    everything = (await client.get("/api/v1/mcp-calls", headers=auth_headers)).json()
    assert everything["total"] == 3
    assert [r["status"] for r in everything["items"]] == ["error", "ok", "ok"]

    docs = (await client.get(
        "/api/v1/mcp-calls", params={"tool": "document_get"}, headers=auth_headers,
    )).json()
    assert [r["result_ids"] for r in docs["items"]] == [["d1"]]

    by_object = (await client.get(
        "/api/v1/mcp-calls", params={"object_id": "m2"}, headers=auth_headers,
    )).json()
    assert by_object["total"] == 1

    errors = (await client.get(
        "/api/v1/mcp-calls", params={"status": "error"}, headers=auth_headers,
    )).json()
    assert errors["items"][0]["error"] == "boom"


async def test_the_summary_answers_per_tool_caller_and_object(client, auth_headers, session):
    await _seed(session)
    await _seed(session, duration_ms=30)
    await _seed(session, tool="document_get", client="codex", key_name="other",
                result_ids=["m1"], result_count=1)
    await _seed(session, tool="memory_add", status="denied", scope="capture",
                result_ids=[], result_count=None)
    await session.flush()

    body = (await client.get("/api/v1/mcp-calls/summary", headers=auth_headers)).json()

    assert body["total"] == 4
    assert body["denied"] == 1
    assert body["query_text_logged"] is False
    tools = {t["tool"]: t for t in body["tools"]}
    assert tools["memory_search"]["calls"] == 2
    assert tools["memory_search"]["avg_duration_ms"] == 20
    assert tools["memory_add"]["denied"] == 1
    top = body["top_objects"][0]
    assert (top["id"], top["hits"]) == ("m1", 3)
    assert top["tools"] == ["document_get", "memory_search"]
    callers = {c["client"]: c for c in body["callers"]}
    assert callers["claude-code"]["calls"] == 3
    assert callers["claude-code"]["top_tool"] == "memory_search"
    assert sum(b["calls"] for b in body["series"]) == 4


async def test_the_summary_refuses_an_inverted_window(client, auth_headers):
    now = datetime.now(timezone.utc)
    response = await client.get(
        "/api/v1/mcp-calls/summary",
        params={"since": now.isoformat(), "until": (now - timedelta(days=1)).isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_the_read_needs_a_login(client):
    assert (await client.get("/api/v1/mcp-calls")).status_code == 401


async def test_the_cleanup_job_prunes_by_age(session, session_factory):
    from types import SimpleNamespace

    from app.services.mcp_call_log import make_mcp_call_cleanup_runner

    now = datetime.now(timezone.utc)
    await _seed(session, occurred_at=now - timedelta(days=45), tool="old")
    await _seed(session, occurred_at=now - timedelta(days=1), tool="recent")
    await session.flush()

    runner = make_mcp_call_cleanup_runner(SimpleNamespace(state=SimpleNamespace()), session_factory)
    result = await runner()

    assert result == {"deleted": 1, "retention_days": 30}
    assert [r["tool"] for r in await _rows(session)] == ["recent"]
