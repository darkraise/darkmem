"""Tests for generate_data span computation."""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_data import build_example
from config.templates import Template


def test_substring_entity_names_get_correct_spans():
    """When one entity name is a substring of another, each gets its own span."""
    rng = random.Random(42)
    tmpl: Template = (
        "We use {0}, {1}, and {2} for different parts of the stack.",
        [(0, "language"), (1, "language"), (2, "language")],
        [],
        "fact",
    )

    import scripts.generate_data as gen_mod

    original_pick = gen_mod.pick_entity

    names_to_return = iter(["JavaScript", "Java", "TypeScript"])

    def fake_pick(rng, etype, used):
        return next(names_to_return)

    gen_mod.pick_entity = fake_pick
    try:
        ex = build_example(rng, tmpl, "test", "test-0001")
    finally:
        gen_mod.pick_entity = original_pick

    text = ex["text"]
    entities = ex["entities"]

    assert len(entities) == 3, f"Expected 3 entities, got {len(entities)}: {entities}"

    for ent in entities:
        actual = text[ent["start"] : ent["end"]]
        assert actual == ent["name"], (
            f"Span mismatch for '{ent['name']}': "
            f"text[{ent['start']}:{ent['end']}] = '{actual}'"
        )

    spans = sorted((e["start"], e["end"]) for e in entities)
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i + 1][0], (
            f"Overlapping spans: {spans[i]} and {spans[i + 1]}"
        )


def test_duplicate_entity_name_across_slots():
    """When two slots get the same entity name, only one entity is emitted."""
    rng = random.Random(42)
    tmpl: Template = (
        "Switched from {0} to {1}.",
        [(0, "language"), (1, "language")],
        [(1, 0, "REPLACES")],
        "decision",
    )

    import scripts.generate_data as gen_mod

    original_pick = gen_mod.pick_entity

    def fake_pick(rng, etype, used):
        return "Python"

    gen_mod.pick_entity = fake_pick
    try:
        ex = build_example(rng, tmpl, "test", "test-0002")
    finally:
        gen_mod.pick_entity = original_pick

    assert len(ex["entities"]) == 1
    assert len(ex["relationships"]) == 0
