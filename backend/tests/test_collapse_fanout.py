"""Doc 06 §4 Stage 5 — collapse, dedup and fan-out, pinned (T1.24e).

Six passes: the two redundancy collapses, the ``(target, predicate)``
dedup and its tie-break, the coordinated-subject fan-out, then the
second event-legality guard and the dangling-date sweep.

**Why this file exists at all.** A per-pass ablation over both gold sets
found that three of the six — ``drop_uses_when_deployed_on_exists``, the
Stage-5 ``filter_event_edges`` and ``drop_unlinked_dates`` — produce
bit-identical output on all 36 memories when deleted, and two more move
exactly one memory each. The F1 bench therefore cannot see half this
stage in either direction, so these behavioural tests, not the bench,
are its guard.

``tests/test_pass_registry.py`` owns the registry scaffold and one
isolated fixture per pass; ``tests/test_relation_rescue.py`` owns the
rescue side of the tie-break contract and its unit-level ordering pins;
``tests/test_extraction_rescue.py`` and ``tests/test_replaces_family.py``
carry the pre-existing unit coverage of the two collapse passes;
``tests/test_relation_gating.py`` pins the same stage-4-before-stage-5
property from the gating side. Overlap is deliberate — this file states
Stage 5's contract from inside the stage.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys

import pytest

from app.services.extraction_clean import (
    ORDERING_CONSTRAINTS,
    PASS_REGISTRY,
    REPLACES_FAMILY,
    RunsBefore,
    STAGE_COLLAPSE_AND_FANOUT,
    STAGE_RELATION_GATING,
    CleanState,
    Pass,
    _dedup_by_target_predicate,
    _drop_unlinked_dates,
    _drop_uses_when_deployed_on_exists,
    _drop_uses_when_replaces_exists,
    _fan_out_coordinated,
    _filter_event_edges,
    _is_direction_grounded,
    _prefer_relation,
    _rescue_relations_replaces,
    clean_extraction,
    run_passes,
    validate_registry,
)
from app.services.extraction_pass_harness import (
    RegistryContractError,
    index_of,
)

STAGE5_PASS_NAMES = (
    "drop_uses_when_replaces_exists",
    "drop_uses_when_deployed_on_exists",
    "dedup_by_target_predicate",
    "fan_out_coordinated",
    "filter_event_edges",
    "drop_unlinked_dates",
)


def _state(**kw) -> CleanState:
    kw.setdefault("raw_entities", kw.get("entities", []))
    return CleanState(**kw)


def _names(entities):
    return [e["name"] for e in entities]


def _triples(relationships):
    return {(r["source"], r["type"], r["target"]) for r in relationships}


def _ordered_triples(relationships):
    return [(r["source"], r["type"], r["target"]) for r in relationships]


def _stage_indices(stage: str) -> list[int]:
    return [i for i, p in enumerate(PASS_REGISTRY) if p.stage == stage]


def _entities(*names, etype="tool"):
    return [{"name": n, "type": etype, "properties": {}} for n in names]


def _drop_occurrence(name: str, stage: str) -> tuple[Pass, ...]:
    """The registry minus one named pass's occurrence in one stage."""
    spot = next(
        i for i, p in enumerate(PASS_REGISTRY)
        if p.name == name and p.stage == stage
    )
    return tuple(p for i, p in enumerate(PASS_REGISTRY) if i != spot)


def _run(registry, entities, relationships, content, *, relation_rescue=True):
    payload = copy.deepcopy({"entities": entities, "relationships": relationships})
    state = run_passes(registry, CleanState(
        content=content,
        entities=payload["entities"],
        relationships=payload["relationships"],
        raw_entities=payload["entities"],
        relation_rescue=relation_rescue,
    ))
    return state


# ── Stage shape ──────────────────────────────────────────────────────


def test_stage_five_runs_the_six_collapse_steps_in_doc_06_s5_order():
    names = tuple(p.name for p in PASS_REGISTRY if p.stage == STAGE_COLLAPSE_AND_FANOUT)
    assert names == STAGE5_PASS_NAMES


def test_stage_five_follows_the_gating_stage():
    """The mirror of ``test_stage_four_precedes_the_collapse_stage``; both
    sides assert it so neither stage can be moved from its own file."""
    assert max(_stage_indices(STAGE_RELATION_GATING)) < min(
        _stage_indices(STAGE_COLLAPSE_AND_FANOUT)
    )


def test_stage_five_is_the_last_stage():
    assert max(_stage_indices(STAGE_COLLAPSE_AND_FANOUT)) == len(PASS_REGISTRY) - 1


# ── Collapse: USES under REPLACES ────────────────────────────────────


@pytest.mark.parametrize("family_type", sorted(REPLACES_FAMILY))
def test_every_replaces_family_member_collapses_the_parallel_uses(family_type):
    rels = [
        {"source": "pgvector", "target": "qdrant", "type": family_type},
        {"source": "pgvector", "target": "qdrant", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert _triples(out) == {("pgvector", family_type, "qdrant")}


def test_the_uses_collapse_is_direction_agnostic():
    """Deliberately pair-based: a REPLACES on the unordered pair already
    conveys the relationship, so the USES goes in either direction."""
    rels = [
        {"source": "pgvector", "target": "qdrant", "type": "REPLACES"},
        {"source": "qdrant", "target": "pgvector", "type": "USES"},
    ]
    assert _triples(_drop_uses_when_replaces_exists(rels)) == {
        ("pgvector", "REPLACES", "qdrant")
    }


def test_the_uses_collapse_ignores_an_unrelated_pair():
    rels = [
        {"source": "pgvector", "target": "qdrant", "type": "REPLACES"},
        {"source": "darkmem", "target": "redis", "type": "USES"},
    ]
    assert len(_drop_uses_when_replaces_exists(rels)) == 2


def test_the_uses_collapse_ignores_a_replaces_self_loop():
    rels = [
        {"source": "qdrant", "target": "qdrant", "type": "REPLACES"},
        {"source": "qdrant", "target": "qdrant", "type": "USES"},
    ]
    assert len(_drop_uses_when_replaces_exists(rels)) == 2


def test_the_uses_collapse_is_a_no_op_without_a_replaces():
    rels = [{"source": "darkmem", "target": "redis", "type": "USES"}]
    assert _drop_uses_when_replaces_exists(rels) is rels


# ── Collapse: USES under DEPLOYED_ON ─────────────────────────────────


def test_the_hosting_collapse_drops_the_parallel_uses():
    rels = [
        {"source": "darkmem", "target": "proxmox", "type": "DEPLOYED_ON"},
        {"source": "darkmem", "target": "proxmox", "type": "USES"},
    ]
    assert _triples(_drop_uses_when_deployed_on_exists(rels)) == {
        ("darkmem", "DEPLOYED_ON", "proxmox")
    }


def test_the_hosting_collapse_is_direction_sensitive():
    """The deliberate asymmetry with the REPLACES collapse above: a host
    using its own deployed service is a legitimate distinct edge, so a
    reversed pair is left alone."""
    rels = [
        {"source": "darkmem", "target": "proxmox", "type": "DEPLOYED_ON"},
        {"source": "proxmox", "target": "darkmem", "type": "USES"},
    ]
    assert len(_drop_uses_when_deployed_on_exists(rels)) == 2


def test_the_hosting_collapse_is_a_no_op_without_a_deployed_on():
    rels = [{"source": "darkmem", "target": "proxmox", "type": "USES"}]
    assert _drop_uses_when_deployed_on_exists(rels) is rels


# ── Dedup by (target, predicate) ─────────────────────────────────────


def test_the_dedup_keys_on_target_and_predicate_only():
    rels = [
        {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.9},
        {"source": "qwen3-embedding", "target": "rrf", "type": "USES", "weight": 0.4},
    ]
    assert _triples(_dedup_by_target_predicate(rels)) == {("darkmem", "USES", "rrf")}


def test_the_dedup_separates_different_predicates_on_one_target():
    rels = [
        {"source": "darkmem", "target": "proxmox", "type": "DEPLOYED_ON", "weight": 0.9},
        {"source": "grafana", "target": "proxmox", "type": "USES", "weight": 0.4},
    ]
    assert len(_dedup_by_target_predicate(rels)) == 2


def test_the_dedup_passes_through_edges_missing_an_endpoint():
    rels = [
        {"source": "", "target": "rrf", "type": "USES", "weight": 0.9},
        {"source": "darkmem", "target": "", "type": "USES", "weight": 0.9},
    ]
    assert len(_dedup_by_target_predicate(rels)) == 2


# ── The tie-break, against the recorded wrong-direction case ─────────


WRONG_DIRECTION_CONTENT = (
    "We migrated from qdrant to pgvector last month for the darkmem store."
)
WRONG_DIRECTION_RAW = {
    "entities": [
        {"name": "qdrant", "type": "tool", "properties": {}},
        {"name": "pgvector", "type": "tool", "properties": {}},
        {"name": "darkmem", "type": "project", "properties": {}},
    ],
    # The LLM reads the sentence's grammatical subject as the replacer and
    # emits the edge backwards, at a HIGHER weight than the rescue layer's.
    "relationships": [
        {"source": "darkmem", "target": "qdrant", "type": "REPLACES",
         "properties": {}, "weight": 0.9},
    ],
}


def _weight_only_registry() -> tuple[Pass, ...]:
    def _dedup_on_weight(relationships):
        by_key: dict[tuple[str, str], dict] = {}
        untouchable: list[dict] = []
        for r in relationships:
            target = (r.get("target") or "").strip().lower()
            rtype = (r.get("type") or "").strip().upper()
            if not target or not rtype or not r.get("source"):
                untouchable.append(r)
                continue
            prev = by_key.get((target, rtype))
            if prev is None or float(r.get("weight") or 0) > float(prev.get("weight") or 0):
                by_key[(target, rtype)] = r
        return list(by_key.values()) + untouchable

    spot = index_of(PASS_REGISTRY, "dedup_by_target_predicate")
    p = PASS_REGISTRY[spot]
    swapped = Pass(p.name, p.stage, _dedup_on_weight, p.reads, p.writes, p.gate)
    return tuple(swapped if i == spot else q for i, q in enumerate(PASS_REGISTRY))


def test_the_rescue_wins_the_real_wrong_direction_replaces():
    """Ruling 4's case, driven end to end rather than as two bare dicts.

    ``_rescue_relations_replaces`` reads "from qdrant to pgvector" as a
    directional pattern and emits the correct edge; the tie-break keeps
    it over the LLM's backwards one."""
    out = clean_extraction(copy.deepcopy(WRONG_DIRECTION_RAW), WRONG_DIRECTION_CONTENT)
    assert ("pgvector", "REPLACES", "qdrant") in _triples(out["relationships"])
    assert ("darkmem", "REPLACES", "qdrant") not in _triples(out["relationships"])


def test_weight_alone_would_have_kept_the_backwards_edge():
    """What makes the test above non-vacuous: the rescue triple carries the
    LOWER weight (0.85 against 0.9), so a weight-only tie-break keeps the
    edge pointing the wrong way — and a wrong-direction surviving REPLACES
    is what ``detect_supersessions`` reads to flip a live memory out of the
    default ``active`` view."""
    state = _run(
        _weight_only_registry(),
        WRONG_DIRECTION_RAW["entities"],
        WRONG_DIRECTION_RAW["relationships"],
        WRONG_DIRECTION_CONTENT,
    )
    assert ("darkmem", "REPLACES", "qdrant") in _triples(state.relationships)


def test_the_rescue_triple_that_wins_is_direction_grounded():
    rescued = _rescue_relations_replaces(
        WRONG_DIRECTION_RAW["entities"], [], WRONG_DIRECTION_CONTENT,
    )
    winner = [r for r in rescued if (r["source"], r["target"]) == ("pgvector", "qdrant")]
    assert winner and _is_direction_grounded(winner[0])


def test_every_pattern_rescued_replaces_is_direction_grounded():
    """The tie-break reads the pattern label, so an emission that forgets to
    stamp it silently loses the wrong-direction fix instead of failing."""
    cases = [
        (["qdrant", "pgvector"], "We migrated from qdrant to pgvector last month."),
        (["qdrant", "pgvector"], "pgvector supersedes qdrant for this workload."),
        (["qdrant", "pgvector"], "We moved out of qdrant and into pgvector."),
        (["qdrant", "pgvector"], "The team swapped qdrant for pgvector."),
    ]
    seen = 0
    for names, content in cases:
        for r in _rescue_relations_replaces(_entities(*names), [], content):
            assert _is_direction_grounded(r), r
            seen += 1
    assert seen >= len(cases)


# ── The tie-break's scope ────────────────────────────────────────────


def test_a_direction_grounded_rescue_outranks_a_heavier_llm_triple():
    grounded = {"properties": {"rescue": True, "pattern": "from-to"}, "weight": 0.1}
    llm = {"properties": {}, "weight": 0.99}
    assert _prefer_relation(grounded, llm) is True
    assert _prefer_relation(llm, grounded) is False


def test_an_adjacency_rescue_does_not_outrank_a_heavier_llm_triple():
    """The adjacency and subject-tracking passes ground ADJACENCY and infer
    the subject from position, so their direction is a guess. Letting that
    guess beat the model's on weight re-introduces the subject anchoring
    this pass exists to correct — measured on gold e14 ("The gateway's JWT
    auth ... signs tokens with RS256"), where the subject-tracking rescue
    took the possessive modifier ``gateway`` for the subject head ``JWT
    auth`` and displaced the correct ``JWT USES RS256``."""
    adjacency = {"properties": {"rescue": True}, "weight": 0.6}
    tracked = {"properties": {"rescue": True, "subject_tracked": True}, "weight": 0.6}
    llm = {"properties": {}, "weight": 0.8}
    for rescued in (adjacency, tracked):
        assert _prefer_relation(rescued, llm) is False
        assert _prefer_relation(llm, rescued) is True


@pytest.mark.parametrize("grounded", [True, False])
def test_weight_decides_when_both_sides_agree_on_grounding(grounded):
    props = {"rescue": True, "pattern": "from-to"} if grounded else {}
    heavy = {"properties": dict(props), "weight": 0.9}
    light = {"properties": dict(props), "weight": 0.4}
    assert _prefer_relation(heavy, light) is True
    assert _prefer_relation(light, heavy) is False


def test_the_subject_anchored_llm_pair_still_resolves_on_weight():
    """Failure mode 1 in the pass's docstring, unchanged by the narrowing:
    neither competitor is rescue-tagged, so weight picks the survivor."""
    rels = [
        {"source": "qwen3-embedding", "target": "rrf", "type": "USES", "weight": 0.4},
        {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.9},
    ]
    assert _triples(_dedup_by_target_predicate(rels)) == {("darkmem", "USES", "rrf")}


# ── Fan-out ──────────────────────────────────────────────────────────


FANOUT_CONTENT = "The dashboard, admin console and billing portal all use tRPC."
FANOUT_ENTITIES = [
    {"name": "dashboard", "type": "tool", "properties": {}},
    {"name": "admin console", "type": "tool", "properties": {}},
    {"name": "billing portal", "type": "tool", "properties": {}},
    {"name": "tRPC", "type": "tool", "properties": {}},
]
FANOUT_RELS = [
    {"source": "dashboard", "target": "tRPC", "type": "USES",
     "properties": {}, "weight": 0.9},
]


def test_fan_out_mints_a_multi_source_set_for_one_target_predicate():
    state = _run(PASS_REGISTRY, FANOUT_ENTITIES, FANOUT_RELS, FANOUT_CONTENT)
    sources = {s for s, t, _ in _triples(state.relationships) if t == "USES"}
    assert {"dashboard", "admin console", "billing portal"} <= sources


def test_dedup_after_fan_out_would_collapse_the_set():
    """Why ``RunsBefore(dedup, fan_out)`` exists, as an executable fact
    rather than as the constraint's ``why=`` string."""
    dedup = index_of(PASS_REGISTRY, "dedup_by_target_predicate")
    fan = index_of(PASS_REGISTRY, "fan_out_coordinated")
    swapped = list(PASS_REGISTRY)
    swapped[dedup], swapped[fan] = swapped[fan], swapped[dedup]

    state = _run(tuple(swapped), FANOUT_ENTITIES, FANOUT_RELS, FANOUT_CONTENT)
    sources = {s for s, t, _ in _triples(state.relationships) if t == "USES"}
    assert len(sources) == 1


def test_the_fan_out_ordering_constraint_is_enforced_at_import():
    dedup = index_of(PASS_REGISTRY, "dedup_by_target_predicate")
    fan = index_of(PASS_REGISTRY, "fan_out_coordinated")
    swapped = list(PASS_REGISTRY)
    swapped[dedup], swapped[fan] = swapped[fan], swapped[dedup]
    with pytest.raises(RegistryContractError):
        validate_registry(tuple(swapped), ORDERING_CONSTRAINTS)


def test_fan_out_leaves_a_date_out_of_the_coordinated_set():
    content = "postgres, redis and 2026-05-12 all appear in the note; postgres uses disk."
    entities = _entities("postgres", "redis") + [
        {"name": "2026-05-12", "type": "concept", "properties": {}},
        {"name": "disk", "type": "hardware", "properties": {}},
    ]
    rels = [{"source": "postgres", "target": "disk", "type": "USES",
             "properties": {}, "weight": 0.9}]
    out = _fan_out_coordinated(rels, entities, content)
    assert all(r["source"] != "2026-05-12" for r in out)


def test_fan_out_does_not_mint_an_edge_that_already_exists():
    rels = FANOUT_RELS + [
        {"source": "admin console", "target": "tRPC", "type": "USES",
         "properties": {}, "weight": 0.5},
    ]
    out = _fan_out_coordinated(copy.deepcopy(rels), FANOUT_ENTITIES, FANOUT_CONTENT)
    minted = [r for r in out if (r["source"], r["target"]) == ("admin console", "tRPC")]
    assert len(minted) == 1


# ── Fan-out determinism ──────────────────────────────────────────────


# Five conjuncts, not the three above, and six fixed hash seeds. A
# three-member group has only six possible orderings, and seeds 1 and 2
# happen to agree on one of them even with the defect present — a guard
# that green under the bug it exists to catch. Five members give 120, and
# these six seeds were confirmed to disagree with the defect restored.
WIDE_FANOUT_CONTENT = (
    "The dashboard, admin console, billing portal, mobile app and worker all use tRPC."
)
WIDE_FANOUT_ENTITIES = [
    {"name": n, "type": "tool", "properties": {}}
    for n in ("dashboard", "admin console", "billing portal",
              "mobile app", "worker", "tRPC")
]
WIDE_FANOUT_RELS = [
    {"source": "dashboard", "target": "tRPC", "type": "USES",
     "properties": {}, "weight": 0.9},
]
_HASH_SEEDS = ("0", "1", "2", "3", "5", "7")


def test_fan_out_emits_coordinated_members_in_a_stable_order():
    out = _fan_out_coordinated(
        copy.deepcopy(WIDE_FANOUT_RELS), WIDE_FANOUT_ENTITIES, WIDE_FANOUT_CONTENT,
    )
    minted = [r["source"] for r in out[len(WIDE_FANOUT_RELS):]]
    assert len(minted) == 4
    assert minted == sorted(minted, key=str.lower)


_CROSS_SEED_SCRIPT = """
import json, sys
from app.services.extraction_clean import clean_extraction
raw = json.loads(sys.argv[1])
out = clean_extraction(raw, sys.argv[2])
print(json.dumps([(r.get("source"), r.get("type"), r.get("target"))
                  for r in out["relationships"]]))
"""


def _chain_output_under_hash_seed(seed: str, raw: dict, content: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    proc = subprocess.run(
        [sys.executable, "-c", _CROSS_SEED_SCRIPT, json.dumps(raw), content],
        capture_output=True, text=True, env=env, timeout=180,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()[-1]


def test_the_whole_chain_output_order_is_stable_across_hash_seeds():
    """Doc 17 §7 and ``CLAUDE.md``'s reproducibility contract claim identical
    input yields identical output. Seeding the LLM call protects the model
    side; a pass iterating a ``set`` of strings breaks the same property from
    the other end, and only a cross-process comparison of the output LIST —
    not its set — can see it."""
    raw = {"entities": WIDE_FANOUT_ENTITIES, "relationships": WIDE_FANOUT_RELS}
    outputs = {
        seed: _chain_output_under_hash_seed(seed, raw, WIDE_FANOUT_CONTENT)
        for seed in _HASH_SEEDS
    }
    assert len(set(outputs.values())) == 1, outputs


# ── The second event filter, and the straddle it needs ───────────────


EVENT_CONTENT = "The migration and postgres both depend on pgbouncer."
EVENT_ENTITIES = [
    {"name": "migration", "type": "event", "properties": {}},
    {"name": "postgres", "type": "tool", "properties": {}},
    {"name": "pgbouncer", "type": "tool", "properties": {}},
]
EVENT_RELS = [
    {"source": "postgres", "target": "pgbouncer", "type": "DEPENDS_ON",
     "properties": {}, "weight": 0.9},
]
ILLEGAL_EVENT_EDGE = ("migration", "DEPENDS_ON", "pgbouncer")


def test_the_second_event_filter_catches_an_edge_fan_out_minted():
    state = _run(PASS_REGISTRY, EVENT_ENTITIES, EVENT_RELS, EVENT_CONTENT)
    assert ILLEGAL_EVENT_EDGE not in _triples(state.relationships)


def test_the_first_event_filter_could_not_have_seen_it():
    """The asymmetry is the proof, not the fact that the pass appears twice.

    Dropping the Stage-4 occurrence changes nothing, because the edge does
    not exist yet when it runs. Dropping the Stage-5 occurrence lets an
    illegal event edge reach the output. A single occurrence at either
    position alone is therefore insufficient — which is what
    ``StraddlesPivot`` encodes."""
    without_first = _run(
        _drop_occurrence("filter_event_edges", STAGE_RELATION_GATING),
        EVENT_ENTITIES, EVENT_RELS, EVENT_CONTENT,
    )
    without_second = _run(
        _drop_occurrence("filter_event_edges", STAGE_COLLAPSE_AND_FANOUT),
        EVENT_ENTITIES, EVENT_RELS, EVENT_CONTENT,
    )
    full = _run(PASS_REGISTRY, EVENT_ENTITIES, EVENT_RELS, EVENT_CONTENT)

    assert _triples(without_first.relationships) == _triples(full.relationships)
    assert ILLEGAL_EVENT_EDGE in _triples(without_second.relationships)


def test_the_illegal_edge_is_absent_before_fan_out_runs():
    """Rules out the alternative reading — that the second filter is merely
    idempotent cleanup of something the first already had a chance at."""
    fan = index_of(PASS_REGISTRY, "fan_out_coordinated")
    state = _run(PASS_REGISTRY[:fan], EVENT_ENTITIES, EVENT_RELS, EVENT_CONTENT)
    assert ILLEGAL_EVENT_EDGE not in _triples(state.relationships)


@pytest.mark.parametrize("stage", [STAGE_RELATION_GATING, STAGE_COLLAPSE_AND_FANOUT])
def test_removing_either_occurrence_breaks_the_straddle_constraint(stage):
    with pytest.raises(RegistryContractError):
        validate_registry(
            _drop_occurrence("filter_event_edges", stage), ORDERING_CONSTRAINTS,
        )


def test_a_legal_event_edge_survives_the_second_filter():
    rels = [{"source": "migration", "target": "2026-05-12", "type": "HAPPENED_ON"}]
    assert _filter_event_edges(rels, EVENT_ENTITIES) == rels


# ── Dangling dates ───────────────────────────────────────────────────


def test_a_date_with_no_happened_on_is_dropped():
    entities = [
        {"name": "2026-05-12", "type": "concept"},
        {"name": "postgres", "type": "tool"},
    ]
    assert _names(_drop_unlinked_dates(entities, [])) == ["postgres"]


def test_a_date_with_a_happened_on_survives():
    entities = [{"name": "2026-05-12", "type": "concept"}]
    rels = [{"source": "outage", "target": "2026-05-12", "type": "HAPPENED_ON"}]
    assert _names(_drop_unlinked_dates(entities, rels)) == ["2026-05-12"]


def test_the_happened_on_match_is_case_and_whitespace_insensitive():
    entities = [{"name": " 2026-05-12 ", "type": "concept"}]
    rels = [{"source": "outage", "target": "2026-05-12", "type": "happened_on"}]
    assert len(_drop_unlinked_dates(entities, rels)) == 1


def test_a_name_that_merely_contains_a_date_is_never_dropped():
    """``fullmatch``, not ``search``. The difference between dropping a
    dangling value node and deleting every dated event entity — and the
    ablation rates this pass at exactly 0.000 on both gold sets, so no
    bench run would catch the swap."""
    entities = [
        {"name": "2026-05-12 outage", "type": "event"},
        {"name": "release 2026-05-12", "type": "event"},
    ]
    assert len(_drop_unlinked_dates(entities, [])) == 2


def test_a_non_date_entity_is_never_dropped():
    entities = [{"name": "postgres", "type": "tool"}]
    assert _drop_unlinked_dates(entities, []) == entities


# ── Purity ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", STAGE5_PASS_NAMES)
def test_stage_five_passes_do_not_mutate_their_inputs(name):
    p = next(q for q in PASS_REGISTRY
             if q.name == name and q.stage == STAGE_COLLAPSE_AND_FANOUT)
    args = {
        "content": FANOUT_CONTENT,
        "entities": copy.deepcopy(FANOUT_ENTITIES),
        "relationships": copy.deepcopy(FANOUT_RELS),
    }
    before = copy.deepcopy(args)
    p.fn(*(args[r] for r in p.reads))
    assert args == before
