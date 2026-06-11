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
    raw SQL LIMIT, like every other limit-bearing tool. An unclamped negative
    value raises a Postgres error; a huge value defeats the result-set cap."""
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
    from app.repositories import vector as vector_mod

    async def _fake_search(self, query_vector, *, fingerprint, limit, repo_id=None, language=None):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(vector_mod.PostgresVectorRepository, "search_code_chunks", _fake_search)

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
                     {"content": "header attribution probe"},
                     headers={"X-Darkmem-Client": "Codex!"})
    memory = await _get_memory(session, "header attribution probe")
    assert memory.source == "codex"


async def test_memory_add_source_from_claude_code_user_agent(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "ua attribution probe"},
                     headers={"User-Agent": "claude-code/2.1.172 (cli)"})
    memory = await _get_memory(session, "ua attribution probe")
    assert memory.source == "claude-code"
    assert memory.source_agent == "claude-code/2.1.172 (cli)"


async def test_memory_add_generic_ua_falls_back_to_mcp(mcp_http_client, session):
    # httpx's default python-httpx/<ver> UA must stay on the denylist: every
    # in-process test and raw-httpx harness rides on that entry.
    await _post_tool(mcp_http_client, "memory_add", {"content": "generic ua probe"})
    memory = await _get_memory(session, "generic ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent.startswith("python-httpx/")


async def test_memory_add_no_ua_leaves_source_agent_null(mcp_http_client, session):
    del mcp_http_client.headers["user-agent"]
    await _post_tool(mcp_http_client, "memory_add", {"content": "no ua probe"})
    memory = await _get_memory(session, "no ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent is None


async def test_memory_add_explicit_source_beats_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "explicit override probe", "source": "my-orchestrator"},
                     headers={"X-Darkmem-Client": "codex"})
    memory = await _get_memory(session, "explicit override probe")
    assert memory.source == "my-orchestrator"
