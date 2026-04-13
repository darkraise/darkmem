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


def test_all_templates_reference_declared_slots():
    """Every slot in entity_slots must appear as {N} in the template string."""
    import re
    from config.templates import (
        TECHNICAL_TEMPLATES, AI_CODING_TEMPLATES,
        PERSONAL_TEMPLATES, KNOWLEDGE_TEMPLATES, CROSS_DOMAIN_TEMPLATES,
    )

    errors = []
    all_groups = [
        ("TECHNICAL", TECHNICAL_TEMPLATES),
        ("AI_CODING", AI_CODING_TEMPLATES),
        ("PERSONAL", PERSONAL_TEMPLATES),
        ("KNOWLEDGE", KNOWLEDGE_TEMPLATES),
    ]

    for group_name, templates in all_groups:
        for cat_name, cat_templates in templates.items():
            for i, (tmpl_str, entity_slots, rel_specs, _) in enumerate(cat_templates):
                format_slots = {int(m) for m in re.findall(r"\{(\d+)\}", tmpl_str)}
                for slot_idx, etype in entity_slots:
                    if slot_idx not in format_slots:
                        errors.append(
                            f"{group_name}/{cat_name}[{i}]: slot {slot_idx} ({etype}) "
                            f"not in template string"
                        )

    for i, (tmpl_str, entity_slots, rel_specs, _) in enumerate(CROSS_DOMAIN_TEMPLATES):
        format_slots = {int(m) for m in re.findall(r"\{(\d+)\}", tmpl_str)}
        for slot_idx, etype in entity_slots:
            if slot_idx not in format_slots:
                errors.append(
                    f"CROSS_DOMAIN[{i}]: slot {slot_idx} ({etype}) "
                    f"not in template string"
                )

    assert not errors, "Templates with undeclared slots:\n" + "\n".join(errors)
