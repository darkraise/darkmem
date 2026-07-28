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
    ORDERING_CONSTRAINTS,
    PASS_REGISTRY,
    RELATIONSHIP_TYPES,
    REPLACES_FAMILY,
    RunsBefore,
    STAGE_COLLAPSE_AND_FANOUT,
    STAGE_RELATION_GATING,
    STAGE_RELATION_SYNTHESIS,
    CleanState,
    _CAUSAL_BETWEEN_RE,
    _EVENT_ALLOWED_RELS,
    _FUTURE_RE,
    _HARDWARE_TOKENS,
    _IMPROVES_PATTERNS,
    _REPLACE_EVIDENCE_RE,
    _REPLACES_PATTERNS,
    _SELECTION_RE,
    _TEMPORAL_BETWEEN_RE,
    _downgrade_future_to_mentions,
    _drop_date_misuse,
    _drop_edges_to_negated,
    _entity_matches,
    _filter_event_edges,
    _gate_replaces_requires_verb,
    _gate_replaces_selection,
    _remap_to_valid_entities,
    _snap_hardware_types,
    _suppress_temporal_edges,
    _validate_directions,
    _validate_hosting_direction,
    clean_extraction,
    normalize_relation_type,
    run_passes,
    validate_registry,
)
from app.services.extraction_pass_harness import (
    RegistryContractError,
    index_of,
    without,
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


# ── Direction validation (doc 06 §4 S4 box D4) ───────────────────────
#
# The Done-when has two halves and the second is the one that keeps a
# future "improvement" from guessing: an unambiguously wrong direction
# swaps, an ambiguous one is left exactly as extracted. A swap is a
# deterministic consequence of an explicit source-text pattern, never an
# inference. Both validators are invisible to the F1 bench.

_REPLACES_DIRECTION_CASES: dict[str, str] = {
    r"switched\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we switched from qdrant to pgvector",
    r"migrated?\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we migrated from qdrant to pgvector",
    r"replaced?\s+(.+?)\s+with\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we replaced qdrant with pgvector",
    r"replacing\s+(.+?)\s+with\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we are replacing qdrant with pgvector",
    r"chose\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we chose pgvector over qdrant",
    r"picked\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we picked pgvector over qdrant",
    r"went\s+with\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we went with pgvector instead of qdrant",
    r"decided\s+to\s+use\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)": "we decided to use pgvector over qdrant",
}

_IMPROVES_DIRECTION_CASES: dict[str, str] = {
    r"(.+?)\s+improves?\s+(?:on|upon|over)\s+(.+?)(?:\s+by\b|\s+because\b|[,;.]|$)": "pgvector improves on qdrant",
    r"(.+?)\s+is\s+better\s+than\s+(.+?)(?:\s+because\b|\s+since\b|[,;.]|$)": "pgvector is better than qdrant",
    r"(.+?)\s+builds?\s+on\s+(.+?)(?:\s+by\b|\s+because\b|[,;.]|$)": "pgvector builds on qdrant",
}


def _directional(source, target, rtype):
    return [{"source": source, "target": target, "type": rtype, "weight": 0.9}]


def test_every_direction_pattern_has_a_worked_example():
    assert {p.pattern for p, _, _ in _REPLACES_PATTERNS} == set(_REPLACES_DIRECTION_CASES)
    assert {p.pattern for p, _, _ in _IMPROVES_PATTERNS} == set(_IMPROVES_DIRECTION_CASES)


@pytest.mark.parametrize("content", sorted(_REPLACES_DIRECTION_CASES.values()))
def test_a_wrong_direction_replaces_is_swapped_onto_the_source_text(content):
    out = _validate_directions(_directional("qdrant", "pgvector", "REPLACES"), content)
    assert _triples(out) == {("pgvector", "REPLACES", "qdrant")}


@pytest.mark.parametrize("content", sorted(_REPLACES_DIRECTION_CASES.values()))
def test_a_right_direction_replaces_is_left_alone(content):
    out = _validate_directions(_directional("pgvector", "qdrant", "REPLACES"), content)
    assert _triples(out) == {("pgvector", "REPLACES", "qdrant")}


@pytest.mark.parametrize("content", sorted(_IMPROVES_DIRECTION_CASES.values()))
def test_a_wrong_direction_improves_on_is_swapped(content):
    out = _validate_directions(_directional("qdrant", "pgvector", "IMPROVES_ON"), content)
    assert _triples(out) == {("pgvector", "IMPROVES_ON", "qdrant")}


@pytest.mark.parametrize("content", sorted(_IMPROVES_DIRECTION_CASES.values()))
def test_a_right_direction_improves_on_is_left_alone(content):
    out = _validate_directions(_directional("pgvector", "qdrant", "IMPROVES_ON"), content)
    assert _triples(out) == {("pgvector", "IMPROVES_ON", "qdrant")}


def test_no_swap_when_only_one_endpoint_matches_its_swapped_role():
    content = "we switched from qdrant to pgvector"
    out = _validate_directions(_directional("qdrant", "redis", "REPLACES"), content)
    assert _triples(out) == {("qdrant", "REPLACES", "redis")}


def test_no_swap_when_an_endpoint_matches_both_its_expected_and_wrong_role():
    # Both sides of the migration share the 'pgvector' token, so the source
    # endpoint is grounded in each. The wrong-direction test alone would fire;
    # the ``and not src_matches_expected`` guard is what declines.
    content = "we replaced pgvector legacy with pgvector hnsw"
    out = _validate_directions(_directional("pgvector", "hnsw", "REPLACES"), content)
    assert _triples(out) == {("pgvector", "REPLACES", "hnsw")}


def test_no_swap_when_no_pattern_matches_the_content():
    content = "darkmem indexes memories with pgvector"
    out = _validate_directions(_directional("qdrant", "pgvector", "REPLACES"), content)
    assert _triples(out) == {("qdrant", "REPLACES", "pgvector")}


def test_endpoint_grounding_is_word_bounded_not_a_bare_substring():
    # Recorded regression. With a bare substring test both endpoints look
    # wrong-directioned -- 'postgres' inside 'postgresql' and 'vector'
    # inside 'pgvector' -- and the pass inverts a claim neither side
    # actually grounds. The \b anchors in _entity_matches decline instead.
    assert not _entity_matches("postgres", "postgresql")
    assert not _entity_matches("vector", "pgvector")
    content = "we switched from postgresql to pgvector"
    out = _validate_directions(_directional("postgres", "vector", "REPLACES"), content)
    assert _triples(out) == {("postgres", "REPLACES", "vector")}


@pytest.mark.parametrize("rtype", ["USES", "DEPLOYED_ON", "RELATED_TO", "MENTIONS"])
def test_relation_types_outside_the_two_families_pass_through(rtype):
    content = "we switched from qdrant to pgvector"
    out = _validate_directions(_directional("qdrant", "pgvector", rtype), content)
    assert _triples(out) == {("qdrant", rtype, "pgvector")}


def test_the_direction_pass_does_not_mutate_its_input():
    rels = _directional("qdrant", "pgvector", "REPLACES")
    before = copy.deepcopy(rels)
    _validate_directions(rels, "we switched from qdrant to pgvector")
    assert rels == before


def test_hardware_on_the_source_side_of_a_hosting_edge_swaps():
    out = _validate_hosting_direction(_directional("gpu", "darkmem", "DEPLOYED_ON"))
    assert _triples(out) == {("darkmem", "DEPLOYED_ON", "gpu")}


def test_hardware_on_the_target_side_of_a_hosting_edge_is_already_canonical():
    out = _validate_hosting_direction(_directional("darkmem", "gpu", "DEPLOYED_ON"))
    assert _triples(out) == {("darkmem", "DEPLOYED_ON", "gpu")}


def test_hardware_on_both_sides_is_ambiguous_and_does_not_swap():
    out = _validate_hosting_direction(_directional("gpu", "cpu", "DEPLOYED_ON"))
    assert _triples(out) == {("gpu", "DEPLOYED_ON", "cpu")}


def test_neither_endpoint_hardware_does_not_swap():
    out = _validate_hosting_direction(_directional("darkmem", "proxmox", "DEPLOYED_ON"))
    assert _triples(out) == {("darkmem", "DEPLOYED_ON", "proxmox")}


def test_only_deployed_on_is_a_hosting_candidate():
    # RUNS_ON never reaches this pass: normalize_relation_type rewrites it
    # to DEPLOYED_ON upstream. The coupling to LEGACY_RELATIONSHIP_TYPE_MAP
    # is invisible in the pass itself, so pin both halves.
    assert normalize_relation_type("RUNS_ON") == "DEPLOYED_ON"
    out = _validate_hosting_direction(_directional("gpu", "darkmem", "RUNS_ON"))
    assert _triples(out) == {("gpu", "RUNS_ON", "darkmem")}


@pytest.mark.parametrize("token", sorted(_HARDWARE_TOKENS))
def test_the_hardware_list_is_shared_with_the_type_snapper(token):
    # Both passes read one _HARDWARE_TOKENS frozenset on purpose. Asserting
    # the behaviour of each over the whole list fails if either grows a
    # private copy.
    (snapped,) = _snap_hardware_types([{"name": token.upper(), "type": "artifact"}])
    assert snapped["type"] == "tool"
    out = _validate_hosting_direction(_directional(token, "darkmem", "DEPLOYED_ON"))
    assert _triples(out) == {("darkmem", "DEPLOYED_ON", token)}


def test_the_hosting_pass_does_not_mutate_its_input():
    rels = _directional("gpu", "darkmem", "DEPLOYED_ON")
    before = copy.deepcopy(rels)
    _validate_hosting_direction(rels)
    assert rels == before


# ── Remap and negation stripping (doc 06 §4 S4 box D1) ───────────────


def test_an_endpoint_that_survived_shaping_under_another_name_is_rewritten():
    shaped = [{"name": "Postgres", "type": "database"}, {"name": "darkmem", "type": "project"}]
    raw = [{"name": "Postgres cluster", "type": "database"}, {"name": "darkmem", "type": "project"}]
    out = _remap_to_valid_entities(
        [{"source": "darkmem", "target": "Postgres cluster", "type": "USES"}], shaped, raw
    )
    assert _triples(out) == {("darkmem", "USES", "Postgres")}


def test_an_acronym_endpoint_is_rewritten_onto_its_expansion():
    shaped = [
        {"name": "Central Processing Unit", "type": "concept"},
        {"name": "darkmem", "type": "project"},
    ]
    raw = [{"name": "CPU", "type": "tool"}, *shaped]
    out = _remap_to_valid_entities(
        [{"source": "darkmem", "target": "CPU", "type": "USES"}], shaped, raw
    )
    assert _triples(out) == {("darkmem", "USES", "Central Processing Unit")}


def test_an_endpoint_that_did_not_survive_shaping_drops_its_edge():
    shaped = [{"name": "darkmem", "type": "project"}]
    out = _remap_to_valid_entities(
        [{"source": "darkmem", "target": "ghost", "type": "USES"}], shaped, shaped
    )
    assert out == []


def test_a_self_edge_after_the_remap_is_dropped():
    shaped = [{"name": "Postgres", "type": "database"}]
    raw = [{"name": "Postgres cluster", "type": "database"}, *shaped]
    out = _remap_to_valid_entities(
        [{"source": "Postgres cluster", "target": "Postgres", "type": "USES"}], shaped, raw
    )
    assert out == []


def test_the_remap_normalises_the_relation_type_through_the_closed_taxonomy():
    shaped = [{"name": "darkmem", "type": "project"}, {"name": "proxmox", "type": "tool"}]
    unknown = _remap_to_valid_entities(
        [{"source": "darkmem", "target": "proxmox", "type": "FROBNICATES"}], shaped, shaped
    )
    legacy = _remap_to_valid_entities(
        [{"source": "darkmem", "target": "proxmox", "type": "RUNS_ON"}], shaped, shaped
    )
    assert _triples(unknown) == {("darkmem", "RELATED_TO", "proxmox")}
    assert _triples(legacy) == {("darkmem", "DEPLOYED_ON", "proxmox")}


def test_the_remap_reads_the_raw_entity_list_not_the_shaped_one():
    # The binding T1.24a put in the registry declaration. Reading the shaped
    # list instead loses exactly the mappings the pass exists for, and the
    # loss is silent -- the edge is dropped, not flagged.
    step = PASS_REGISTRY[index_of(PASS_REGISTRY, "remap_to_valid_entities")]
    assert step.reads == ("relationships", "entities", "raw_entities")

    shaped = [{"name": "Postgres", "type": "database"}, {"name": "darkmem", "type": "project"}]
    raw = [{"name": "Postgres cluster", "type": "database"}, {"name": "darkmem", "type": "project"}]
    edge = [{"source": "darkmem", "target": "Postgres cluster", "type": "USES"}]
    assert _remap_to_valid_entities(edge, shaped, raw) != []
    assert _remap_to_valid_entities(edge, shaped, shaped) == []


def test_the_remap_does_not_mutate_its_input():
    shaped = [{"name": "darkmem", "type": "project"}, {"name": "proxmox", "type": "tool"}]
    rels = [{"source": "darkmem", "target": "proxmox", "type": "RUNS_ON"}]
    before = copy.deepcopy(rels)
    _remap_to_valid_entities(rels, shaped, shaped)
    assert rels == before


# The reachable input for ``drop_edges_to_negated``. It exists because two
# file-path vocabularies disagree: ``_filter_noise``'s ``_FILENAME_PATTERN``
# lists far fewer extensions than the rescue's ``_FILE_PATH_RE``, so a
# ``.css`` / ``.scss`` / ``.lua`` path is NOT dropped as noise and reaches
# ``_filter_negation_only``, which records it in ``negated_names``. A short
# leading directory keeps ``_filter_hallucinated_names`` under its two-token
# threshold. ``_rescue_file_path_entities`` -- the one rescue that is not
# negation-aware -- then re-adds it, so the endpoint is valid again by the
# time the remap runs and only this pass removes the edge.
_NEGATED_PATH_CONTENT = "The dashboard was rebuilt without ui/theme.css in the bundle."
_NEGATED_PATH_ENTITIES = [
    {"name": "ui/theme.css", "type": "artifact"},
    {"name": "dashboard", "type": "concept"},
]


def test_the_negated_entity_reaches_the_pass_with_a_live_edge():
    state = _state(
        content=_NEGATED_PATH_CONTENT,
        entities=_NEGATED_PATH_ENTITIES,
        relationships=[
            {"source": "dashboard", "target": "ui/theme.css", "type": "USES"},
        ],
    )
    spot = index_of(PASS_REGISTRY, "drop_edges_to_negated")
    at = run_passes(PASS_REGISTRY[:spot], state)
    assert "ui/theme.css" in at.negated_names
    assert "ui/theme.css" in _names(at.entities)
    assert _triples(at.relationships) == {("dashboard", "USES", "ui/theme.css")}


def test_an_edge_to_a_negated_entity_is_dropped():
    out = _drop_edges_to_negated(
        [
            {"source": "dashboard", "target": "ui/theme.css", "type": "USES"},
            {"source": "dashboard", "target": "ui/tokens.css", "type": "USES"},
        ],
        {"ui/theme.css"},
    )
    assert _triples(out) == {("dashboard", "USES", "ui/tokens.css")}


def test_an_empty_negated_set_is_a_no_op():
    rels = [{"source": "dashboard", "target": "ui/theme.css", "type": "USES"}]
    assert _drop_edges_to_negated(rels, set()) is rels


def test_only_this_pass_removes_the_edge_to_the_negated_path():
    raw = {
        "entities": _NEGATED_PATH_ENTITIES,
        "relationships": [
            {"source": "dashboard", "target": "ui/theme.css", "type": "USES"},
        ],
    }
    kept = clean_extraction(raw, _NEGATED_PATH_CONTENT)
    assert kept["relationships"] == []

    state = _state(
        content=_NEGATED_PATH_CONTENT,
        entities=raw["entities"],
        relationships=raw["relationships"],
    )
    reduced = run_passes(without(PASS_REGISTRY, "drop_edges_to_negated"), state)
    assert _triples(reduced.relationships) == {("dashboard", "USES", "ui/theme.css")}


def test_a_negation_does_not_mint_a_replaces_against_the_denied_entity():
    # The consequence that makes this pass invariant-bearing: without it the
    # REPLACES survives to detect_supersessions and flips a live memory out
    # of the default active view on the strength of a denial.
    content = (
        "We migrated the dashboard to ui/tokens.css "
        "without ui/theme.css in the bundle."
    )
    raw = {
        "entities": [
            {"name": "ui/theme.css", "type": "artifact"},
            {"name": "ui/tokens.css", "type": "artifact"},
        ],
        "relationships": [
            {"source": "ui/tokens.css", "target": "ui/theme.css", "type": "REPLACES"},
        ],
    }
    assert clean_extraction(raw, content)["relationships"] == []

    state = _state(
        content=content, entities=raw["entities"], relationships=raw["relationships"]
    )
    reduced = run_passes(without(PASS_REGISTRY, "drop_edges_to_negated"), state)
    assert _triples(reduced.relationships) == {
        ("ui/tokens.css", "REPLACES", "ui/theme.css")
    }


def test_the_negation_pass_does_not_mutate_its_input():
    rels = [{"source": "dashboard", "target": "ui/theme.css", "type": "USES"}]
    before = copy.deepcopy(rels)
    _drop_edges_to_negated(rels, {"ui/theme.css"})
    assert rels == before


# ── Event legality at its Stage-4 position (doc 06 §4 S4 box D5) ─────
#
# tests/test_extraction_clean_guards.py already covers the pass at unit
# level and tests/test_pass_registry.py owns the second, post-fan-out
# occurrence and its StraddlesPivot constraint (T1.24e's). Neither is
# repeated here.

_EVENT_ENTITIES = [
    {"name": "outage", "type": "event"},
    {"name": "darkmem", "type": "project"},
    {"name": "postgres", "type": "database"},
]


def test_the_event_allow_set_is_exactly_the_four_temporal_predicates():
    assert _EVENT_ALLOWED_RELS == frozenset(
        {"HAPPENED_ON", "CAUSES", "AUTHORED_BY", "MENTIONS"}
    )


@pytest.mark.parametrize("rtype", sorted(_EVENT_ALLOWED_RELS))
@pytest.mark.parametrize("side", ["source", "target"])
def test_every_allowed_type_survives_on_either_endpoint_side(rtype, side):
    edge = (
        {"source": "outage", "target": "darkmem", "type": rtype}
        if side == "source"
        else {"source": "darkmem", "target": "outage", "type": rtype}
    )
    assert _triples(_filter_event_edges([edge], _EVENT_ENTITIES)) == _triples([edge])


@pytest.mark.parametrize("rtype", ["USES", "DEPLOYED_ON", "REPLACES", "DEPENDS_ON"])
@pytest.mark.parametrize("side", ["source", "target"])
def test_a_disallowed_type_is_filtered_on_either_endpoint_side(rtype, side):
    edge = (
        {"source": "outage", "target": "darkmem", "type": rtype}
        if side == "source"
        else {"source": "darkmem", "target": "outage", "type": rtype}
    )
    assert _filter_event_edges([edge], _EVENT_ENTITIES) == []


def test_the_guard_is_keyed_on_the_entity_type_not_on_any_name():
    # The same name typed as something other than 'event' is not policed.
    not_an_event = [{**e, "type": "concept"} if e["name"] == "outage" else e
                    for e in _EVENT_ENTITIES]
    edge = [{"source": "outage", "target": "darkmem", "type": "USES"}]
    assert _filter_event_edges(edge, _EVENT_ENTITIES) == []
    assert _triples(_filter_event_edges(edge, not_an_event)) == _triples(edge)


def test_edges_between_non_event_entities_are_untouched():
    edge = [{"source": "darkmem", "target": "postgres", "type": "USES"}]
    assert _triples(_filter_event_edges(edge, _EVENT_ENTITIES)) == _triples(edge)


def test_the_event_guard_does_not_mutate_its_input():
    rels = [{"source": "outage", "target": "darkmem", "type": "USES"}]
    before = copy.deepcopy(rels)
    _filter_event_edges(rels, _EVENT_ENTITIES)
    assert rels == before


# ── The stage's contract through the composed chain ──────────────────
#
# Passes that are individually correct can still compose wrongly. These
# run through clean_extraction, which is what the task's Done-when
# actually asks for. The negation half lives with box D1 above, next to
# the reachability evidence that names the pass discharging it.


def test_a_selection_memory_yields_improves_on_and_never_replaces():
    out = clean_extraction(
        {
            "entities": [
                {"name": "pgvector", "type": "tool"},
                {"name": "qdrant", "type": "database"},
            ],
            "relationships": [
                {"source": "pgvector", "target": "qdrant", "type": "REPLACES"},
            ],
        },
        "we chose pgvector over qdrant for the vector index",
    )
    assert _triples(out["relationships"]) == {("pgvector", "IMPROVES_ON", "qdrant")}


def test_a_planned_memory_yields_mentions_and_never_uses():
    out = clean_extraction(
        {
            "entities": [
                {"name": "darkmem", "type": "project"},
                {"name": "redis", "type": "database"},
            ],
            "relationships": [
                {"source": "darkmem", "target": "redis", "type": "USES"},
            ],
        },
        "we plan to adopt redis for session state",
    )
    assert _triples(out["relationships"]) == {("darkmem", "MENTIONS", "redis")}


def test_an_unambiguous_migration_is_oriented_end_to_end():
    raw = {
        "entities": [
            {"name": "qdrant", "type": "database"},
            {"name": "pgvector", "type": "tool"},
        ],
        "relationships": [
            {"source": "qdrant", "target": "pgvector", "type": "REPLACES"},
        ],
    }
    out = clean_extraction(raw, "we migrated from qdrant to pgvector")
    assert _triples(out["relationships"]) == {("pgvector", "REPLACES", "qdrant")}


def test_an_ambiguous_replacement_is_left_exactly_as_extracted():
    raw = {
        "entities": [
            {"name": "qdrant", "type": "database"},
            {"name": "pgvector", "type": "tool"},
        ],
        "relationships": [
            {"source": "qdrant", "target": "pgvector", "type": "REPLACES"},
        ],
    }
    content = (
        "qdrant and pgvector are both vector stores; "
        "we replaced one of them last year"
    )
    out = clean_extraction(raw, content, relation_rescue=False)
    assert _triples(out["relationships"]) == {("qdrant", "REPLACES", "pgvector")}


@pytest.mark.parametrize(
    ("content", "raw"),
    [
        (
            "we chose pgvector over qdrant for the vector index",
            {
                "entities": [
                    {"name": "pgvector", "type": "tool"},
                    {"name": "qdrant", "type": "database"},
                ],
                "relationships": [
                    {"source": "pgvector", "target": "qdrant", "type": "FROBNICATES"},
                ],
            },
        ),
        (
            "darkmem runs on proxmox and the outage happened on 2026-05-12",
            {
                "entities": [
                    {"name": "darkmem", "type": "project"},
                    {"name": "proxmox", "type": "tool"},
                    {"name": "outage", "type": "event"},
                ],
                "relationships": [
                    {"source": "darkmem", "target": "proxmox", "type": "RUNS_ON"},
                ],
            },
        ),
    ],
)
def test_every_relation_type_the_stage_emits_is_in_the_closed_taxonomy(content, raw):
    out = clean_extraction(raw, content)
    assert out["relationships"]
    for r in out["relationships"]:
        assert r["type"] in RELATIONSHIP_TYPES


# ── Stage 4's internal orderings, declared as data ───────────────────
#
# T1.24a's premise: a load-bearing order is declared in
# ORDERING_CONSTRAINTS and validated at import, not left to the sequence
# happening to be right. Each constraint below is demonstrated with a
# concrete input before it is declared -- an ordering that cannot be
# broken into a wrong answer is a comment, not a contract.


def _reorder(registry, first, second):
    i, j = index_of(registry, first), index_of(registry, second)
    out = list(registry)
    out[i], out[j] = out[j], out[i]
    return tuple(out)


def _chain(registry, content, entities, relationships, relation_rescue=True):
    state = _state(
        content=content,
        entities=entities,
        relationships=relationships,
        relation_rescue=relation_rescue,
    )
    return _triples(run_passes(registry, state).relationships)


def test_the_remap_runs_before_the_negation_strip():
    assert index_of(PASS_REGISTRY, "remap_to_valid_entities") < index_of(
        PASS_REGISTRY, "drop_edges_to_negated"
    )


def test_stripping_negated_edges_before_the_remap_misses_a_shaped_name():
    # The entity is shaped from 'ui/theme.css store' to 'ui/theme.css', which
    # is the form negated_names carries. The edge endpoint keeps the raw form
    # until the remap, so a pre-remap check compares the two vocabularies and
    # finds nothing.
    content = "The dashboard was rebuilt without ui/theme.css in the bundle."
    entities = [
        {"name": "ui/theme.css store", "type": "artifact"},
        {"name": "dashboard", "type": "concept"},
    ]
    rels = [{"source": "dashboard", "target": "ui/theme.css store", "type": "USES"}]
    assert _chain(PASS_REGISTRY, content, entities, rels) == set()
    swapped = _reorder(PASS_REGISTRY, "remap_to_valid_entities", "drop_edges_to_negated")
    assert _chain(swapped, content, entities, rels) == {
        ("dashboard", "USES", "ui/theme.css")
    }


def test_swapping_the_remap_and_the_negation_strip_breaks_the_contract():
    swapped = _reorder(PASS_REGISTRY, "remap_to_valid_entities", "drop_edges_to_negated")
    with pytest.raises(RegistryContractError):
        validate_registry(swapped, ORDERING_CONSTRAINTS)


def test_the_remap_runs_before_the_first_name_keyed_gate():
    assert index_of(PASS_REGISTRY, "remap_to_valid_entities") < index_of(
        PASS_REGISTRY, "suppress_temporal_edges"
    )


def test_a_name_keyed_gate_before_the_remap_never_finds_its_endpoint():
    content = "postgres was patched after redis was upgraded"
    entities = [
        {"name": "Postgres cluster", "type": "database"},
        {"name": "redis", "type": "database"},
    ]
    rels = [{"source": "Postgres cluster", "target": "redis", "type": "RELATED_TO"}]
    assert _chain(PASS_REGISTRY, content, entities, rels, relation_rescue=False) == set()
    swapped = _reorder(
        PASS_REGISTRY, "remap_to_valid_entities", "suppress_temporal_edges"
    )
    assert _chain(swapped, content, entities, rels, relation_rescue=False) == {
        ("Postgres", "RELATED_TO", "redis")
    }


def test_swapping_the_remap_and_the_temporal_gate_breaks_the_contract():
    swapped = _reorder(
        PASS_REGISTRY, "remap_to_valid_entities", "suppress_temporal_edges"
    )
    with pytest.raises(RegistryContractError):
        validate_registry(swapped, ORDERING_CONSTRAINTS)


def test_the_selection_gate_runs_before_the_verb_gate():
    assert index_of(PASS_REGISTRY, "gate_replaces_selection") < index_of(
        PASS_REGISTRY, "gate_replaces_requires_verb"
    )


def test_the_verb_gate_first_collapses_a_selection_to_related_to():
    # 'chose X over Y' carries no replacement verb, so the verb gate reads the
    # REPLACES as unsupported and downgrades it to RELATED_TO. The selection
    # gate then has no REPLACES left to reclassify, and a genuine improvement
    # claim is lost to a generic edge.
    content = "we chose pgvector over qdrant for the vector index"
    entities = [
        {"name": "pgvector", "type": "tool"},
        {"name": "qdrant", "type": "database"},
    ]
    rels = [{"source": "pgvector", "target": "qdrant", "type": "REPLACES"}]
    assert _chain(PASS_REGISTRY, content, entities, rels, relation_rescue=False) == {
        ("pgvector", "IMPROVES_ON", "qdrant")
    }
    swapped = _reorder(
        PASS_REGISTRY, "gate_replaces_selection", "gate_replaces_requires_verb"
    )
    assert _chain(swapped, content, entities, rels, relation_rescue=False) == {
        ("pgvector", "RELATED_TO", "qdrant")
    }


def test_swapping_the_two_replaces_gates_breaks_the_contract():
    swapped = _reorder(
        PASS_REGISTRY, "gate_replaces_selection", "gate_replaces_requires_verb"
    )
    with pytest.raises(RegistryContractError):
        validate_registry(swapped, ORDERING_CONSTRAINTS)


def test_every_stage_four_constraint_carries_a_mechanism():
    stage4 = set(STAGE4_PASS_NAMES)
    mine = [
        c for c in ORDERING_CONSTRAINTS
        if isinstance(c, RunsBefore) and {c.earlier, c.later} <= stage4
    ]
    assert len(mine) == 3
    assert all(c.why for c in mine)
