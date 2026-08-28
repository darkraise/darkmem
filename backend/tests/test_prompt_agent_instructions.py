"""The MCP door's instructions must describe the roster it actually serves.

A tool absent from the instructions is invisible to an agent that reads them
as its map of the system - which is what steered agents to file documents
through memory_add rather than document_put.
"""
import ast
from pathlib import Path

from app.api.mcp.scopes import TOOL_SCOPES
from app.services import prompt

_SERVER = Path(__file__).resolve().parents[1] / "app" / "api" / "mcp" / "server.py"


def _registered_tools() -> set[str]:
    tree = ast.parse(_SERVER.read_text())
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if any("tool" in ast.dump(d) for d in node.decorator_list):
            names.add(node.name)
    return names


def test_every_registered_tool_is_named_in_the_instructions():
    text = prompt.PROMPTS["agent_instructions"]
    missing = sorted(name for name in _registered_tools() if name not in text)
    assert missing == [], f"tools absent from agent_instructions: {missing}"


def test_the_instructions_explain_the_scope_refusal():
    text = prompt.PROMPTS["agent_instructions"]
    assert "scope" in text.lower()
    assert "-32003" in text, "the SCOPE_DENIED code must be documented"


def test_the_instructions_fit_the_override_cap():
    assert len(prompt.PROMPTS["agent_instructions"]) <= 20_000


def test_scopes_and_instructions_agree_on_the_roster():
    assert _registered_tools() == set(TOOL_SCOPES)


def test_every_tool_carries_a_usable_description():
    """Assert on what the SDK actually serves, not on the docstring.

    A ``description=`` on the decorator OVERRIDES the docstring entirely
    (verified against mcp 2.1.1), so a tool can carry a rich docstring and
    still reach the agent as one terse line. The effective text is what an
    agent gets, so it is what this measures.
    """
    import asyncio

    from app.api.mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    thin = sorted(
        (t.name, len(t.description or ""))
        for t in tools
        if len(t.description or "") < 80
    )
    assert thin == [], f"tools whose served description is too thin: {thin}"


def test_the_instructions_bound_a_memory_to_one_fact():
    """Nothing else bounds memory length.

    ``MemoryCreate.content`` carries only ``min_length=1``, so the prompt is
    the whole of the pressure toward one-fact rows. Without it agents file
    multi-topic essays, which retrieve poorly (one embedding per row) and can
    never be superseded (supersession retires a row whole).
    """
    text = prompt.PROMPTS["agent_instructions"]
    assert "One memory holds one fact" in text
    assert "memory_batch_add" in text
    assert "document_put" in text, "long-form content must be routed off this door"


def test_the_capture_tools_serve_the_one_fact_rule():
    """The served text, not the docstring.

    A ``description=`` on the decorator overrides the docstring, and the
    docstring's ``Args:`` block reaches no agent at all - ``content`` had no
    served description whatsoever before this rule landed.
    """
    import asyncio

    from app.api.mcp.server import mcp

    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}

    content = tools["memory_add"].input_schema["properties"]["content"]
    assert "one fact" in (content.get("description") or "").lower(), (
        "memory_add.content must carry a served granularity rule"
    )

    for name in ("memory_add", "memory_batch_add"):
        served = (tools[name].description or "").lower()
        assert "one fact" in served, f"{name} must state the granularity rule"

    assert "never append" in (tools["memory_update"].description or "").lower()
