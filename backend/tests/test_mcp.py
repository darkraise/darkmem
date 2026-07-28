from contextlib import asynccontextmanager

import app.api.mcp.server as mcp_module
from app.api.mcp.server import code_search, mcp


async def test_mcp_tools_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "memory_add" in tool_names
    assert "memory_search" in tool_names
    assert "memory_get" in tool_names
    assert "memory_update" in tool_names
    assert "memory_delete" in tool_names
    assert "memory_batch_add" in tool_names
    assert "memory_reason" in tool_names
    assert "memory_find_duplicates" in tool_names
    assert "memory_stats" in tool_names
    assert "memory_tags" in tool_names
    assert len(tool_names) >= 10
    assert len(tool_names) == len(set(tool_names))


async def test_code_search_clamps_limit(session, monkeypatch):
    """code_search must clamp `limit` to [1, _MAX_LIMIT] before it reaches the
    shared query service, like every other limit-bearing tool. An unclamped
    negative value raises a Postgres error; a huge value defeats the result-set
    cap.

    The assertion sits on the tool-to-service boundary rather than on the
    vector repository, because the clamp is the tool's and the service is free
    to fan the bound out across its own channels (it asks each arm for
    ``limit * 2`` before fusing).
    """
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())

    class _FakeLLM:
        async def embed(self, _query):
            return ([0.1, 0.2], "fp-test")

    class _FakePipeline:
        llm = _FakeLLM()

    monkeypatch.setattr(mcp_module, "_pipeline", _FakePipeline())

    captured = {}
    from app.services import code_query as code_query_mod

    async def _fake_search(self, query, limit=20, repo_id=None, language=None):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(code_query_mod.CodeQueryService, "search_code", _fake_search)

    await code_search("hello", limit=-5)
    assert captured["limit"] == 1

    await code_search("hello", limit=10_000)
    assert captured["limit"] == mcp_module._MAX_LIMIT


from sqlalchemy import select

from app.models.memory import Memory


def _tool_call(name: str, arguments: dict, request_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


async def _post_tool(client, name: str, arguments: dict, headers: dict | None = None) -> dict:
    response = await client.post("/", json=_tool_call(name, arguments), headers=headers or {})
    assert response.status_code == 200, response.text
    body = response.json()
    assert not body["result"].get("isError"), body
    return body


async def _get_memory(session, content: str) -> Memory:
    result = await session.execute(select(Memory).where(Memory.content == content))
    return result.scalar_one()


async def test_memory_add_source_from_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "header attribution probe", "wait_process": True},
                     headers={"X-Darkmem-Client": "Codex!"})
    memory = await _get_memory(session, "header attribution probe")
    assert memory.source == "codex"


async def test_memory_add_source_from_claude_code_user_agent(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "ua attribution probe", "wait_process": True},
                     headers={"User-Agent": "claude-code/2.1.172 (cli)"})
    memory = await _get_memory(session, "ua attribution probe")
    assert memory.source == "claude-code"
    assert memory.source_agent == "claude-code/2.1.172 (cli)"


async def test_memory_add_generic_ua_falls_back_to_mcp(mcp_http_client, session):
    # httpx's default python-httpx/<ver> UA must stay on the denylist: every
    # in-process test and raw-httpx harness rides on that entry.
    await _post_tool(mcp_http_client, "memory_add", {"content": "generic ua probe", "wait_process": True})
    memory = await _get_memory(session, "generic ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent.startswith("python-httpx/")


async def test_memory_add_no_ua_leaves_source_agent_null(mcp_http_client, session):
    del mcp_http_client.headers["user-agent"]
    await _post_tool(mcp_http_client, "memory_add", {"content": "no ua probe", "wait_process": True})
    memory = await _get_memory(session, "no ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent is None


async def test_memory_add_explicit_source_beats_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "explicit override probe", "source": "my-orchestrator", "wait_process": True},
                     headers={"X-Darkmem-Client": "codex"})
    memory = await _get_memory(session, "explicit override probe")
    assert memory.source == "my-orchestrator"


async def test_memory_update_tags_only_preserves_content(mcp_http_client, session):
    # Updating only tags must replace tags and leave content untouched. The MCP
    # wrapper used to pass content=None explicitly, defeating the service's
    # exclude_unset guard and clobbering the NOT NULL content column (which also
    # aborted before tags were applied).
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "update tags-only probe", "tags": ["keep/a"], "wait_process": True})
    mem = await _get_memory(session, "update tags-only probe")

    await _post_tool(mcp_http_client, "memory_update",
                     {"memory_id": str(mem.id), "tags": ["new/b"]})

    session.expire_all()
    updated = await _get_memory(session, "update tags-only probe")
    assert updated.content == "update tags-only probe"
    assert {t.name for t in updated.tags} == {"new/b"}


async def test_memory_update_type_only_preserves_content_and_tags(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "update type-only probe", "tags": ["keep/c"],
                      "memory_type": "fact", "wait_process": True})
    mem = await _get_memory(session, "update type-only probe")

    await _post_tool(mcp_http_client, "memory_update",
                     {"memory_id": str(mem.id), "memory_type": "decision"})

    session.expire_all()
    updated = await _get_memory(session, "update type-only probe")
    assert updated.content == "update type-only probe"
    assert updated.memory_type == "decision"
    assert {t.name for t in updated.tags} == {"keep/c"}


async def test_memory_batch_add_resolves_per_entry(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_batch_add", {
        "wait_process": True,
        "entries": [
            {"content": "batch omitted source"},
            {"content": "batch explicit api", "source": "api"},
            {"content": "batch explicit mcp", "source": "mcp", "source_agent": "eval-r3"},
        ],
    }, headers={"X-Darkmem-Client": "codex"})
    omitted = await _get_memory(session, "batch omitted source")
    assert omitted.source == "codex"
    assert omitted.source_agent.startswith("python-httpx/")
    assert (await _get_memory(session, "batch explicit api")).source == "api"
    explicit = await _get_memory(session, "batch explicit mcp")
    assert explicit.source == "codex"
    assert explicit.source_agent == "eval-r3"


import json
import uuid


def _tool_payload(body: dict) -> dict:
    return json.loads(body["result"]["content"][0]["text"])


async def test_memory_get_reports_supersession(mcp_http_client, session):
    """An MCP reader must be able to tell a superseded memory from a live one.

    Doc 07 §7 requires a superseded row to be labelled and reachable through
    its successor. The MCP row carried neither field, so an autonomous agent
    read a retired memory as current with no badge and no human in the loop.
    """
    replacement = Memory(
        id=uuid.uuid4(), content="mcp supersession replacement",
        source="test", metadata_={}, project="lane-f",
    )
    session.add(replacement)
    await session.flush()

    retired = Memory(
        id=uuid.uuid4(), content="mcp supersession probe", source="test",
        metadata_={}, project="lane-f", status="superseded",
        superseded_by=replacement.id, technologies=["postgres"],
    )
    session.add(retired)
    await session.flush()

    row = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(retired.id)})
    )
    assert row["status"] == "superseded"
    assert row["superseded_by"] == str(replacement.id)
    assert row["project"] == "lane-f"
    assert row["technologies"] == ["postgres"]

    live = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(replacement.id)})
    )
    assert live["status"] == "active"
    assert live["superseded_by"] is None


async def test_memory_search_rows_carry_the_lifecycle_label(mcp_http_client, session):
    memory = Memory(
        id=uuid.uuid4(), content="mcp search label probe", source="test",
        metadata_={}, project="lane-f",
    )
    session.add(memory)
    await session.flush()

    rows = _tool_payload(
        await _post_tool(mcp_http_client, "memory_search", {"query": "label probe"})
    )
    assert rows, "search returned nothing to inspect"
    for row in rows:
        assert row["status"] in {"active", "superseded", "deprecated"}
        assert "superseded_by" in row
        assert "project" in row
