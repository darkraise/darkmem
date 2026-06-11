"""The agent_instructions prompt is served as the MCP initialize 'instructions'
and edits to it must reach the live server. Two invariants:

1. Every tool the prompt tells an agent to call must actually be registered,
   or an agent following the instructions hits tool-not-found.
2. A UI edit to agent_instructions must update what the MCP server serves,
   not silently wait for a process restart.
"""
from __future__ import annotations

import re

import pytest

from app.api.mcp.server import mcp
from app.services import prompt as prompt_mod

_TOOL_TOKEN = re.compile(r"\b(?:memory_[a-z_]+|code_[a-z_]+|list_repos)\b")


async def test_agent_instructions_only_reference_registered_tools():
    text = prompt_mod.PROMPTS["agent_instructions"]
    registered = {t.name for t in await mcp.list_tools()}
    mentioned = set(_TOOL_TOKEN.findall(text))
    unknown = mentioned - registered
    assert not unknown, f"agent_instructions reference unregistered tools: {sorted(unknown)}"


@pytest.mark.asyncio
async def test_put_system_prompts_refreshes_mcp_instructions(client, auth_headers):
    prompt_mod.set_overrides({})
    try:
        custom = "Custom agent guidance: always call memory_search first."
        resp = await client.put(
            "/api/v1/config/system-prompts",
            headers=auth_headers,
            json={"overrides": {"agent_instructions": custom}},
        )
        assert resp.status_code == 200, resp.text
        assert mcp._mcp_server.instructions == custom

        # Clearing the override restores the in-code default on the live server.
        resp = await client.put(
            "/api/v1/config/system-prompts",
            headers=auth_headers,
            json={"overrides": {"agent_instructions": ""}},
        )
        assert resp.status_code == 200
        assert mcp._mcp_server.instructions == prompt_mod.PROMPTS["agent_instructions"]
    finally:
        prompt_mod.set_overrides({})
