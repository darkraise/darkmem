"""Doc 06 §4 Stage 4 — relation gating and direction, pinned (T1.24d).

Ten passes in the D1 → D5 order doc 06 §4's S4 box declares: remap and
negation stripping (D1), the two REPLACES gates (D2), the temporal trio
(D3), the two direction validators (D4), and the event-legality guard
(D5).

**Why this file exists at all.** A per-pass ablation over both gold sets
found that seven of the ten produce bit-identical output on all 36
memories when deleted, so the F1 bench cannot see them in either
direction. The passes it cannot see are exactly the ones whose failure
mode is a false ``REPLACES`` reaching ``detect_supersessions`` and
flipping a live memory out of the default ``active`` view. These
behavioural tests, not the bench, are the guard for this stage.

``tests/test_pass_registry.py`` owns the registry scaffold and the
stage-straddling event guard; ``tests/test_extraction_clean_guards.py``
owns the pre-existing unit coverage of ``_gate_replaces_requires_verb``
and ``_filter_event_edges``; ``tests/test_relation_rescue.py`` pins the
same stage-3-before-stage-4 property from the synthesis side. Overlap is
deliberate — this file states Stage 4's contract from inside the stage.
"""

from __future__ import annotations

import copy

import pytest

from app.services.extraction_clean import (
    PASS_REGISTRY,
    RELATIONSHIP_TYPES,
    REPLACES_FAMILY,
    STAGE_COLLAPSE_AND_FANOUT,
    STAGE_RELATION_GATING,
    STAGE_RELATION_SYNTHESIS,
    CleanState,
    _REPLACE_EVIDENCE_RE,
    _SELECTION_RE,
    _gate_replaces_requires_verb,
    _gate_replaces_selection,
    normalize_relation_type,
)

STAGE4_PASS_NAMES = (
    "remap_to_valid_entities",
    "drop_edges_to_negated",
    "gate_replaces_selection",
    "gate_replaces_requires_verb",
    "suppress_temporal_edges",
    "downgrade_future_to_mentions",
    "drop_date_misuse",
    "validate_directions",
    "validate_hosting_direction",
    "filter_event_edges",
)


def _state(**kw) -> CleanState:
    kw.setdefault("raw_entities", kw.get("entities", []))
    return CleanState(**kw)


def _names(entities):
    return [e["name"] for e in entities]


def _triples(relationships):
    return {(r["source"], r["type"], r["target"]) for r in relationships}


def _stage_indices(stage: str) -> list[int]:
    return [i for i, p in enumerate(PASS_REGISTRY) if p.stage == stage]


def _alternatives(fragment: str) -> list[str]:
    """Split a regex fragment on its top-level ``|``, ignoring nesting."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    i = 0
    while i < len(fragment):
        c = fragment[i]
        if c == "\\":
            buf.append(fragment[i : i + 2])
            i += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == "|" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _top_level_groups(pattern: str) -> list[str]:
    """Bodies of the pattern's outermost groups, capturing or not."""
    bodies: list[str] = []
    buf: list[str] = []
    depth = 0
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            if depth:
                buf.append(pattern[i : i + 2])
            i += 2
            continue
        if c == "(":
            depth += 1
            if depth == 1:
                buf = []
                i += 3 if pattern.startswith("(?:", i) else 1
                continue
        elif c == ")":
            depth -= 1
            if depth == 0:
                bodies.append("".join(buf))
                i += 1
                continue
        if depth:
            buf.append(c)
        i += 1
    return bodies


# ── The two REPLACES gates (doc 06 §4 S4 box D2) ─────────────────────
#
# Both are invisible to the F1 bench: dropping either changes 0 of 26
# gold and 0 of 10 held-out memories. Their shared failure mode is a
# false REPLACES surviving into ``detect_supersessions``, which flips a
# live memory to ``superseded`` and removes it from the default view.
# One worked example per regex alternative, so widening a pattern
# without widening the coverage fails ``..._has_a_worked_example``.

_SELECTION_VERBS: dict[str, str] = {
    "chose": "chose",
    "choose": "choose",
    "chosen": "have chosen",
    "pick(?:ed)?": "picked",
    "select(?:ed)?": "selected",
    "went with": "went with",
    "going with": "are going with",
    r"opt(?:ed)?\s+for": "opted for",
    "prefer(?:red)?": "preferred",
}

_SELECTION_COMPARATORS: dict[str, str] = {
    "over": "over",
    "instead of": "instead of",
    "rather than": "rather than",
    "versus": "versus",
    r"vs\.?": "vs.",
}

_REPLACE_EVIDENCE: dict[str, str] = {
    r"replac\w+": "replaced",
    r"switch\w*": "switched to",
    r"migrat\w+": "migrated to",
    r"moved\s+(?:from|off|out)": "moved off",
    r"supersed\w+": "supersedes",
    r"deprecat\w+": "deprecated",
    r"obsolete\w*": "obsoletes",
    "swapped": "swapped in for",
    "ported": "ported over",
    r"improves?\s+(?:on|upon|over)": "improves on",
    r"builds?\s+on": "builds on",
    r"instead\s+of": "is used instead of",
    r"in\s+favou?r\s+of": "was adopted in favour of",
    r"phas\w+\s+out": "phased out",
}


def _replaces(source="pgvector", target="qdrant"):
    return [{"source": source, "target": target, "type": "REPLACES", "weight": 0.9}]


def test_every_selection_verb_alternative_has_a_worked_example():
    verbs, comparators = _top_level_groups(_SELECTION_RE.pattern)
    assert set(_alternatives(verbs)) == set(_SELECTION_VERBS)
    assert set(_alternatives(comparators)) == set(_SELECTION_COMPARATORS)


@pytest.mark.parametrize("verb", sorted(_SELECTION_VERBS.values()))
@pytest.mark.parametrize("comparator", sorted(_SELECTION_COMPARATORS.values()))
def test_a_selection_downgrades_replaces_to_improves_on(verb, comparator):
    content = f"we {verb} pgvector {comparator} qdrant"
    out = _gate_replaces_selection(_replaces(), content)
    assert _triples(out) == {("pgvector", "IMPROVES_ON", "qdrant")}


def test_a_migration_verb_anywhere_in_the_memory_spares_every_replaces():
    # Characterisation of the gate's documented escape hatch, which is
    # document-scoped: the migration verb need not be in the same clause
    # as the selection phrase for the whole memory to be spared.
    content = (
        "we chose pgvector over qdrant for the new index. "
        "separately, the ingest worker migrated off celery."
    )
    out = _gate_replaces_selection(_replaces(), content)
    assert _triples(out) == {("pgvector", "REPLACES", "qdrant")}


def test_the_selection_gate_leaves_other_relation_types_alone():
    rels = [
        {"source": "darkmem", "target": "pgvector", "type": "USES"},
        {"source": "pgvector", "target": "qdrant", "type": "IMPROVES_ON"},
    ]
    out = _gate_replaces_selection(rels, "we chose pgvector over qdrant")
    assert _triples(out) == _triples(rels)


def test_the_selection_gate_is_a_no_op_without_a_selection_cue():
    content = "darkmem indexes memories with pgvector"
    assert _gate_replaces_selection(_replaces(), content) == _replaces()


def test_the_selection_gate_does_not_mutate_its_input():
    rels = _replaces()
    before = copy.deepcopy(rels)
    _gate_replaces_selection(rels, "we chose pgvector over qdrant")
    assert rels == before


def test_every_replace_evidence_alternative_has_a_worked_example():
    (body,) = _top_level_groups(_REPLACE_EVIDENCE_RE.pattern)
    assert set(_alternatives(body)) == set(_REPLACE_EVIDENCE)


@pytest.mark.parametrize("phrase", sorted(_REPLACE_EVIDENCE.values()))
def test_replacement_evidence_spares_the_replaces_edge(phrase):
    content = f"the event bus {phrase} the legacy ledger"
    out = _gate_replaces_requires_verb(_replaces("event bus", "legacy ledger"), content)
    assert _triples(out) == {("event bus", "REPLACES", "legacy ledger")}


def test_a_bare_rewrite_downgrades_an_unsupported_replaces_to_related_to():
    content = "all writes now go through the event bus"
    out = _gate_replaces_requires_verb(_replaces("event bus", "legacy ledger"), content)
    assert _triples(out) == {("event bus", "RELATED_TO", "legacy ledger")}


def test_the_verb_gate_downgrade_target_survives_the_closed_taxonomy():
    out = _gate_replaces_requires_verb(_replaces(), "the ledger was rewritten")
    downgraded = out[0]["type"]
    assert downgraded in RELATIONSHIP_TYPES
    assert normalize_relation_type(downgraded) == downgraded


def test_the_improvement_family_phrasings_are_replacement_evidence():
    # IMPROVES_ON and the legacy BUILDS_ON are REPLACES_FAMILY members, so
    # their phrasings must back a REPLACES rather than downgrade it.
    assert {"IMPROVES_ON", "BUILDS_ON"} <= set(REPLACES_FAMILY)
    for phrase in ("improves on", "builds on"):
        out = _gate_replaces_requires_verb(_replaces(), f"pgvector {phrase} qdrant")
        assert _triples(out) == {("pgvector", "REPLACES", "qdrant")}


def test_the_verb_gate_leaves_other_relation_types_alone():
    rels = [
        {"source": "darkmem", "target": "pgvector", "type": "USES"},
        {"source": "pgvector", "target": "qdrant", "type": "IMPROVES_ON"},
    ]
    out = _gate_replaces_requires_verb(rels, "all writes now go through the event bus")
    assert _triples(out) == _triples(rels)


def test_the_verb_gate_does_not_mutate_its_input():
    rels = _replaces()
    before = copy.deepcopy(rels)
    _gate_replaces_requires_verb(rels, "all writes now go through the event bus")
    assert rels == before


# ── Stage shape ──────────────────────────────────────────────────────


def test_stage_four_runs_the_ten_gating_steps_in_doc_06_s4_order():
    gating = [p.name for p in PASS_REGISTRY if p.stage == STAGE_RELATION_GATING]
    assert gating == list(STAGE4_PASS_NAMES)


def test_stage_four_follows_the_synthesis_stage():
    assert max(_stage_indices(STAGE_RELATION_SYNTHESIS)) < min(
        _stage_indices(STAGE_RELATION_GATING)
    )


def test_stage_four_precedes_the_collapse_stage():
    assert max(_stage_indices(STAGE_RELATION_GATING)) < min(
        _stage_indices(STAGE_COLLAPSE_AND_FANOUT)
    )
