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

from app.services.extraction_clean import (
    PASS_REGISTRY,
    STAGE_COLLAPSE_AND_FANOUT,
    STAGE_RELATION_GATING,
    STAGE_RELATION_SYNTHESIS,
    CleanState,
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
