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
