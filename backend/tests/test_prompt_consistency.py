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


def test_the_extraction_prompt_stays_within_its_budget():
    """It runs on every ingest; its size is a recurring cost, not a constant.

    The bound is 33,000 rather than the 27,000 the plan proposed. Reaching
    27,000 needed an 8,200-char cut, and the four backstopped targets only
    total ~6,600 - the rest would have had to come from rules the
    extraction_clean pass chain does not backstop. The largest single item
    on the review's list was deleting Example 5 outright; its demonstration
    is kept because it is the only place the star-shape relation failure is
    shown rather than described, and the 39-relation bench is too small to
    detect that regression reliably. Its prose notes were compressed instead.
    """
    assert len(prompt.PROMPTS["extraction"]) < 33_000
