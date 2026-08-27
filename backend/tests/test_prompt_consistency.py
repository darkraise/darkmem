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


def test_no_system_is_exemplified_under_two_entity_types():
    """Type-constrained dedup never merges across types.

    `service` exemplified 'PostgreSQL' while `database` exemplified
    'Postgres' on adjacent lines, under a "pick the FIRST type that fits"
    rule where service comes first. One system, two permanent nodes.
    """
    text = prompt.PROMPTS["extraction"]
    assert not ("'PostgreSQL'" in text and "'Postgres'" in text)
    assert "storing data is `database`" in text


def test_the_prompt_still_names_every_closed_type():
    """Editing examples must not drop a type out of the prompt."""
    text = prompt.PROMPTS["extraction"]
    for name in taxonomy.ENTITY_TYPES:
        assert name in text, f"entity type dropped from the prompt: {name}"
    for name in taxonomy.RELATIONSHIP_TYPES:
        assert name in text, f"relation type dropped from the prompt: {name}"
