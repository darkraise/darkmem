from app.api.mcp.server import mcp


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
    assert len(tool_names) == 10
