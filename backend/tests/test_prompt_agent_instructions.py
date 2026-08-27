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
