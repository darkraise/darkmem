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
    _CAUSAL_BETWEEN_RE,
    _FUTURE_RE,
    _REPLACE_EVIDENCE_RE,
    _SELECTION_RE,
    _TEMPORAL_BETWEEN_RE,
    _downgrade_future_to_mentions,
    _drop_date_misuse,
    _gate_replaces_requires_verb,
    _gate_replaces_selection,
    _suppress_temporal_edges,
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


# ── The temporal trio (doc 06 §4 S4 box D3) ──────────────────────────

_TEMPORAL_CONNECTORS: dict[str, str] = {
    "after": "the outage happened after the deploy",
    "before": "the outage happened before the deploy",
    "since": "the outage has been quiet since the deploy",
    "following": "the outage occurred following the deploy",
    "prior to": "the outage occurred prior to the deploy",
    "then": "the outage landed and then the deploy",
    "once": "the outage cleared once the deploy",
    "later": "the outage came, later the deploy",
}

_FUTURE_MARKERS: dict[str, str] = {
    r"plan(?:s|ned|ning)?\s+to": "we plan to adopt redis next quarter",
    r"will\s+(?:add|support|build|introduce|ship)": "we will add redis next quarter",
    r"going\s+to": "we are going to adopt redis next quarter",
    r"intend(?:s|ed)?\s+to": "we intend to adopt redis next quarter",
    "upcoming": "the upcoming release brings redis",
    r"on\s+the\s+roadmap": "on the roadmap: redis for session state",
    "considering": "we are considering redis for session state",
    r"may\s+add": "we may add redis for session state",
    r"to\s+be\s+added": "to be added: redis for session state",
}


def _related(source="outage", target="deploy", rtype="RELATED_TO"):
    return [{"source": source, "target": target, "type": rtype, "weight": 0.8}]


def test_every_temporal_connector_has_a_worked_example():
    (body,) = _top_level_groups(_TEMPORAL_BETWEEN_RE.pattern)
    assert set(_alternatives(body)) == set(_TEMPORAL_CONNECTORS)


@pytest.mark.parametrize("content", sorted(_TEMPORAL_CONNECTORS.values()))
def test_a_purely_temporal_join_drops_the_edge(content):
    assert _suppress_temporal_edges(_related(), content) == []


def test_a_causal_verb_in_the_same_span_rescues_the_edge():
    causal = "the deploy then caused the outage"
    bare = "the deploy, then the outage"
    assert _triples(_suppress_temporal_edges(_related(), causal)) == {
        ("outage", "RELATED_TO", "deploy")
    }
    assert _suppress_temporal_edges(_related(), bare) == []


def test_every_causal_verb_alternative_rescues_the_edge():
    (body,) = _top_level_groups(_CAUSAL_BETWEEN_RE.pattern)
    for alt in _alternatives(body):
        verb = alt.replace(r"\w*", "ed")
        content = f"the deploy then {verb} the outage"
        assert _triples(_suppress_temporal_edges(_related(), content)) == {
            ("outage", "RELATED_TO", "deploy")
        }, alt


@pytest.mark.parametrize("rtype", ["RELATED_TO", "CAUSES"])
def test_only_related_to_and_causes_are_candidates(rtype):
    content = "the outage happened after the deploy"
    assert _suppress_temporal_edges(_related(rtype=rtype), content) == []


@pytest.mark.parametrize("rtype", ["USES", "DEPLOYED_ON", "MENTIONS", "REPLACES"])
def test_other_relation_types_survive_a_temporal_join(rtype):
    content = "the outage happened after the deploy"
    out = _suppress_temporal_edges(_related(rtype=rtype), content)
    assert _triples(out) == {("outage", rtype, "deploy")}


def test_the_guard_runs_on_the_closest_mention_pair_not_the_first():
    # The subject recurs, which is the common case for a project name. Its
    # FIRST mention spans an unrelated temporal window; its nearest one does
    # not, and the edge must survive on the nearest.
    recurring = "darkmem was rebuilt after the february outage. darkmem uses pgvector."
    single = "darkmem was rebuilt after the february outage. pgvector is the store."
    edge = _related("darkmem", "pgvector")
    assert _triples(_suppress_temporal_edges(edge, recurring)) == {
        ("darkmem", "RELATED_TO", "pgvector")
    }
    assert _suppress_temporal_edges(edge, single) == []


def test_the_temporal_span_search_matches_endpoint_names_as_bare_substrings():
    # Characterisation, not endorsement. This pass spans mentions with a
    # bare ``re.escape`` substring search, while ``_validate_directions``
    # deliberately uses word boundaries via ``_entity_matches`` after a
    # recorded ``postgres`` / ``postgres 17`` regression. Whether the
    # looser matching here is intentional is an open question routed to
    # the controller; this test pins today's behaviour so a change to it
    # is a decision rather than an accident.
    inside = "postgresql was patched after the outage"
    absent = "mysql was patched after the outage"
    edge = _related("postgres", "outage")
    assert _suppress_temporal_edges(edge, inside) == []
    assert _triples(_suppress_temporal_edges(edge, absent)) == {
        ("postgres", "RELATED_TO", "outage")
    }


def test_the_temporal_pass_does_not_mutate_its_input():
    rels = _related()
    before = copy.deepcopy(rels)
    _suppress_temporal_edges(rels, "the outage happened after the deploy")
    assert rels == before


def test_every_future_marker_has_a_worked_example():
    (body,) = _top_level_groups(_FUTURE_RE.pattern)
    assert set(_alternatives(body)) == set(_FUTURE_MARKERS)


@pytest.mark.parametrize("content", sorted(_FUTURE_MARKERS.values()))
def test_a_future_marker_downgrades_the_edge_to_mentions(content):
    out = _downgrade_future_to_mentions(
        [{"source": "darkmem", "target": "redis", "type": "USES", "weight": 0.9}],
        content,
    )
    assert _triples(out) == {("darkmem", "MENTIONS", "redis")}


@pytest.mark.parametrize("rtype", ["USES", "IMPLEMENTS", "EXTENDS", "DEPENDS_ON"])
def test_only_the_four_usage_predicates_downgrade(rtype):
    content = "we plan to adopt redis next quarter"
    out = _downgrade_future_to_mentions(
        [{"source": "darkmem", "target": "redis", "type": rtype, "weight": 0.9}],
        content,
    )
    assert _triples(out) == {("darkmem", "MENTIONS", "redis")}


@pytest.mark.parametrize("rtype", ["RELATED_TO", "HAPPENED_ON", "REPLACES", "CAUSES"])
def test_other_predicates_are_left_alone_in_the_future_zone(rtype):
    content = "we plan to adopt redis next quarter"
    out = _downgrade_future_to_mentions(
        [{"source": "darkmem", "target": "redis", "type": rtype, "weight": 0.9}],
        content,
    )
    assert _triples(out) == {("darkmem", rtype, "redis")}


@pytest.mark.parametrize(("weight", "expected"), [(0.9, 0.5), (0.5, 0.5), (0.3, 0.3)])
def test_the_downgrade_clamps_the_weight_without_raising_it(weight, expected):
    out = _downgrade_future_to_mentions(
        [{"source": "darkmem", "target": "redis", "type": "USES", "weight": weight}],
        "we plan to adopt redis next quarter",
    )
    assert out[0]["weight"] == expected


def test_the_future_zone_runs_from_the_marker_to_the_end_of_content():
    # Characterisation of a document-scoped rule: a target named BEFORE the
    # marker is untouched, one named after it is downgraded however far away.
    content = "redis was removed last year; we plan to adopt valkey next quarter."
    out = _downgrade_future_to_mentions(
        [
            {"source": "darkmem", "target": "redis", "type": "USES", "weight": 0.9},
            {"source": "darkmem", "target": "valkey", "type": "USES", "weight": 0.9},
        ],
        content,
    )
    assert _triples(out) == {
        ("darkmem", "USES", "redis"),
        ("darkmem", "MENTIONS", "valkey"),
    }


def test_the_future_pass_does_not_mutate_its_input():
    rels = [{"source": "darkmem", "target": "redis", "type": "USES", "weight": 0.9}]
    before = copy.deepcopy(rels)
    _downgrade_future_to_mentions(rels, "we plan to adopt redis next quarter")
    assert rels == before


@pytest.mark.parametrize("rtype", ["USES", "DEPLOYED_ON", "AUTHORED_BY", "RELATED_TO"])
def test_a_bare_date_endpoint_is_dropped_from_a_non_happened_on_edge(rtype):
    as_target = [{"source": "darkmem", "target": "2026-05-12", "type": rtype}]
    as_source = [{"source": "2026-05-12", "target": "darkmem", "type": rtype}]
    assert _drop_date_misuse(as_target) == []
    assert _drop_date_misuse(as_source) == []


def test_a_date_survives_as_a_happened_on_target():
    rels = [{"source": "outage", "target": "2026-05-12", "type": "HAPPENED_ON"}]
    assert _triples(_drop_date_misuse(rels)) == {("outage", "HAPPENED_ON", "2026-05-12")}


def test_a_name_that_merely_contains_a_date_is_not_a_date_endpoint():
    # ``fullmatch``, not ``search``. With ``search`` this would delete every
    # edge hanging off a dated event name, which the bench cannot see.
    rels = [{"source": "2026-05-12 outage", "target": "disk", "type": "CAUSES"}]
    assert _triples(_drop_date_misuse(rels)) == {
        ("2026-05-12 outage", "CAUSES", "disk")
    }


def test_the_date_pass_does_not_mutate_its_input():
    rels = [{"source": "darkmem", "target": "2026-05-12", "type": "USES"}]
    before = copy.deepcopy(rels)
    _drop_date_misuse(rels)
    assert rels == before
