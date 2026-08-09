"""T2.15 — proof for the five memory-relation types and their normaliser.

`backend/app/taxonomy.py` already carries `MEMORY_RELATION_TYPES`,
`PROJECTED_MEMORY_RELATION_TYPES`, `LEGACY_MEMORY_RELATION_TYPE_MAP`,
`normalize_memory_relation_type` and `is_projected_memory_relation_type`
(landed by T1.23). This file is the missing proof, not the build: it asserts
the three Done-when clauses concrete task T2.15 names —

1. Only the five (`CONTRADICTS`, `ELABORATES`, `DEPENDS_ON`, `FOLLOWS`,
   `RELATES_TO`) are storable.
2. `SUPERSEDES` is rejected — it stays the projected `superseded_by`
   pointer and can never reach the normaliser's output.
3. Unknown types fall back within the closed set.

`backend/tests/test_taxonomy.py` already covers some of this ground with
generic, four-vocabulary-wide parametrisation; the tests here stay
memory-relation-specific and exercise the normaliser end to end (calling it
on every legacy alias and every casing/padding variant) rather than
re-asserting the same map-shape checks structurally.
"""
from __future__ import annotations

import pytest

from app.taxonomy import (
    LEGACY_MEMORY_RELATION_TYPE_MAP,
    MEMORY_RELATION_TYPES,
    PROJECTED_MEMORY_RELATION_TYPES,
    is_projected_memory_relation_type,
    normalize_memory_relation_type,
)


def test_memory_relation_types_are_exactly_the_five():
    # Set equality, not just a count: a swap (e.g. CONTRADICTS -> CONFLICTS)
    # keeps len() == 5 but must still fail this.
    assert set(MEMORY_RELATION_TYPES) == {
        "CONTRADICTS",
        "ELABORATES",
        "DEPENDS_ON",
        "FOLLOWS",
        "RELATES_TO",
    }


def test_stored_and_projected_vocabularies_are_disjoint():
    # SUPERSEDES (and anything else read-time-projected) must never double
    # as a storable type, or a write could reach it by coincidence.
    assert set(MEMORY_RELATION_TYPES).isdisjoint(PROJECTED_MEMORY_RELATION_TYPES)


@pytest.mark.parametrize("mrtype", MEMORY_RELATION_TYPES)
def test_each_type_round_trips_lowercase_and_padded(mrtype):
    assert normalize_memory_relation_type(mrtype.lower()) == mrtype
    assert normalize_memory_relation_type(f"  {mrtype}  ") == mrtype
    assert normalize_memory_relation_type(f"  {mrtype.lower()}  ") == mrtype


def test_supersedes_and_precedes_never_reach_the_stored_vocabulary():
    # SUPERSEDES stays the projected superseded_by pointer.
    assert normalize_memory_relation_type("SUPERSEDES") == "RELATES_TO"
    assert "SUPERSEDES" not in MEMORY_RELATION_TYPES
    assert is_projected_memory_relation_type("SUPERSEDES") is True
    assert is_projected_memory_relation_type("supersedes") is True

    # PRECEDES has no alias, deliberately (taxonomy.py:300-305): "A PRECEDES
    # B" asserts A is earlier, and a pure type-string normaliser cannot swap
    # endpoints, so aliasing it to FOLLOWS would silently invert temporal
    # order. It must lose the direction claim (fall to RELATES_TO), never
    # gain a reversed one (FOLLOWS).
    assert normalize_memory_relation_type("PRECEDES") == "RELATES_TO"
    assert normalize_memory_relation_type("PRECEDES") != "FOLLOWS"
    assert "PRECEDES" not in LEGACY_MEMORY_RELATION_TYPE_MAP
    assert is_projected_memory_relation_type("PRECEDES") is False


@pytest.mark.parametrize(
    "junk",
    [
        "bogus",
        "xyz123",
        "not-a-relation",
        "0",
        "SUPERSEDES",
        "PRECEDES",
        None,
        "",
        "   ",
    ],
)
def test_unknown_projected_and_blank_inputs_all_fall_back_to_relates_to(junk):
    result = normalize_memory_relation_type(junk)
    assert result == "RELATES_TO"
    assert result in set(MEMORY_RELATION_TYPES)


@pytest.mark.parametrize(
    "alias, expected", sorted(LEGACY_MEMORY_RELATION_TYPE_MAP.items())
)
def test_every_legacy_alias_normalises_into_the_closed_set(alias, expected):
    # If a future alias's target is not one of the five, this fails the
    # build rather than silently rewriting rows to an untabled type.
    assert expected in MEMORY_RELATION_TYPES
    assert normalize_memory_relation_type(alias) == expected
    assert normalize_memory_relation_type(alias.lower()) == expected
