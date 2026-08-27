"""The extraction prompt must not contradict itself.

Rules that fight produce whichever answer the model reached first, and for
the REPLACES family that is a stored write: a REPLACES edge triggers
supersession, so a wrong one retires a live memory.
"""
from __future__ import annotations

from app import taxonomy
from app.services import prompt


def test_no_rule_orders_replaces_for_a_selection():
    """Rule 3a governs: a selection is not a replacement.

    Rule 10's worked example ordered `OpenAI REPLACES Anthropic` for
    "considered Anthropic but went with OpenAI" - the exact phrasing rule 3a
    lists as IMPROVES_ON. The deterministic backstop's _SELECTION_RE does not
    match that wording, so the wrong edge landed unrepaired.
    """
    text = prompt.PROMPTS["extraction"]
    assert "REPLACES Anthropic" not in text
    assert "IMPROVES_ON Anthropic" in text
