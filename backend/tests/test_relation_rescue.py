"""Doc 06 §4 Stage 3 — the ``relation_rescue`` layer, pinned (T1.25).

The stage is three passes in a declared order: adjacency connectors,
subject-tracking, then the REPLACES pattern family. Each is gated on the
only surviving ingestion-side behavioural flag. What this file pins is
the *contract* the rest of the chain depends on, not the individual
regexes (``test_extraction_rescue.py`` owns those):

* the stage is exactly those three passes, in doc order, all gated;
* every triple any of them emits carries ``properties.rescue = True``,
  because that tag is what wins the Stage-5 tie-break;
* the REPLACES family collapses through ``family_key`` on the dedup key,
  for every member of ``REPLACES_FAMILY``;
* a *direction-grounded* rescue triple — one this stage's REPLACES
  pattern pass emitted, carrying its pattern label — beats a
  higher-weighted LLM triple in ``_dedup_by_target_predicate``, which is
  the recorded wrong-direction-REPLACES fix; weight decides otherwise.
  T1.24e narrowed that from "any rescue tag wins" after measuring that
  the adjacency pass's guessed subject was outranking the model's on the
  only case in either gold set where the rule fired.
"""
from __future__ import annotations

import pytest

from app.services.extraction_clean import (
    PASS_REGISTRY,
    STAGE_RELATION_SYNTHESIS,
    CleanState,
    _prefer_relation,
    _RESCUE_CONNECTORS,
    _SUBJECT_TRACKED_CONNECTORS,
    _rescue_relations,
    _rescue_relations_replaces,
    _rescue_relations_subject_tracking,
    clean_extraction,
    run_passes,
)
from app.services.extraction_pass_harness import index_of, without
from app.services.relations import REPLACES_FAMILY

STAGE3_PASS_NAMES = (
    "rescue_relations",
    "rescue_relations_subject_tracking",
    "rescue_relations_replaces",
)

STAGE3_FUNCTIONS = (
    _rescue_relations,
    _rescue_relations_subject_tracking,
    _rescue_relations_replaces,
)

# One sentence per emission path in the stage: every adjacency connector,
# every subject-tracked connector, and every REPLACES pattern label. The
# rescue-tag property test below runs the whole battery through every
# pass, so a pass that forgets the tag on any path fails here.
RESCUE_CORPUS: tuple[str, ...] = tuple(
    [f"alpha {conn} beta" for conn, _rel, _w, _legacy in _RESCUE_CONNECTORS]
    + [f"alpha ships {conn} beta" for conn, _rel, _w in _SUBJECT_TRACKED_CONNECTORS]
    + [
        "we migrated alpha from beta to gamma",
        "we replaced beta with gamma",
        "gamma supersedes beta",
        "the seed was moved out of beta into gamma",
    ]
)


def _entities(*names: str) -> list[dict]:
    return [{"name": n, "type": "tool", "properties": {}} for n in names]


CORPUS_ENTITIES = _entities("alpha", "beta", "gamma")


def _run_stage3(entities, relations, content, *, relation_rescue=True) -> list[dict]:
    return run_passes(
        tuple(p for p in PASS_REGISTRY if p.stage == STAGE_RELATION_SYNTHESIS),
        CleanState(
            content=content,
            entities=entities,
            relationships=relations,
            raw_entities=entities,
            relation_rescue=relation_rescue,
        ),
    ).relationships


def _triples(rels):
    return {
        (
            (r.get("source") or "").lower(),
            (r.get("type") or "").upper(),
            (r.get("target") or "").lower(),
        )
        for r in rels
    }


# ── The stage is three declared, gated passes ────────────────────────


def test_stage_three_is_the_three_doc_named_passes_in_order():
    synthesis = [p.name for p in PASS_REGISTRY if p.stage == STAGE_RELATION_SYNTHESIS]
    assert tuple(synthesis) == STAGE3_PASS_NAMES


def test_every_stage_three_pass_is_gated_on_the_flag():
    for name in STAGE3_PASS_NAMES:
        assert PASS_REGISTRY[index_of(PASS_REGISTRY, name)].gate == "relation_rescue"


@pytest.mark.parametrize("name", STAGE3_PASS_NAMES)
def test_each_stage_three_pass_is_individually_removable(name):
    """``without`` is what makes 'reorder or remove only against a measured
    delta' actionable: a pass the registry does not name cannot be dropped
    and re-measured on the F1 bench."""
    reduced = without(PASS_REGISTRY, name)
    assert len(reduced) == len(PASS_REGISTRY) - 1
    assert name not in {p.name for p in reduced}


def test_the_flag_off_skips_every_synthesis_pass():
    content = "darkmem runs on proxmox and we migrated from qdrant to pgvector"
    entities = _entities("darkmem", "proxmox", "qdrant", "pgvector")
    assert _run_stage3(entities, [], content, relation_rescue=False) == []
    assert _run_stage3(entities, [], content, relation_rescue=True) != []


def test_the_flag_off_leaves_llm_triples_untouched():
    seed = [{"source": "darkmem", "target": "proxmox", "type": "DEPLOYED_ON"}]
    out = _run_stage3(
        _entities("darkmem", "proxmox"),
        seed,
        "darkmem runs on proxmox",
        relation_rescue=False,
    )
    assert out == seed


# ── Ruling 4: properties.rescue on every emitted triple ──────────────


def _emitted(fn, content):
    before = []
    after = fn(CORPUS_ENTITIES, before, content)
    seen = {id(r) for r in before}
    return [r for r in after if id(r) not in seen]


@pytest.mark.parametrize("content", RESCUE_CORPUS)
@pytest.mark.parametrize(
    "fn", STAGE3_FUNCTIONS, ids=[f.__name__ for f in STAGE3_FUNCTIONS]
)
def test_every_emitted_triple_is_rescue_tagged(fn, content):
    for r in _emitted(fn, content):
        assert (r.get("properties") or {}).get("rescue") is True, r


def test_the_whole_stage_tags_every_triple_it_adds():
    for content in RESCUE_CORPUS:
        seed = [{"source": "alpha", "target": "beta", "type": "MENTIONS"}]
        out = _run_stage3(CORPUS_ENTITIES, seed, content)
        added = _triples(out) - _triples(seed)
        tagged = _triples(
            r for r in out if (r.get("properties") or {}).get("rescue") is True
        )
        assert added <= tagged, content


def test_the_battery_actually_exercises_every_emission_path():
    """Guards the tag test above: if a corpus sentence stops firing, the
    exhaustive claim silently weakens into a vacuous one."""
    connectors = len(_RESCUE_CONNECTORS) + len(_SUBJECT_TRACKED_CONNECTORS)
    firing = [c for c in RESCUE_CORPUS if _run_stage3(CORPUS_ENTITIES, [], c)]
    assert len(firing) == len(RESCUE_CORPUS)
    assert len(RESCUE_CORPUS) == connectors + 4


@pytest.mark.parametrize(
    ("content", "pattern"),
    [
        ("we migrated alpha from beta to gamma", "from-to"),
        ("we replaced beta with gamma", "verb-x-prep-y"),
        ("gamma supersedes beta", "supersedes"),
        ("the seed was moved out of beta into gamma", "out-of-into"),
    ],
)
def test_each_replaces_pattern_emits_a_tagged_triple(content, pattern):
    emitted = _emitted(_rescue_relations_replaces, content)
    assert emitted
    for r in emitted:
        assert r["properties"]["rescue"] is True
        assert r["properties"]["pattern"] == pattern


def test_subject_tracking_triples_are_tagged_as_both_rescue_and_tracked():
    emitted = _emitted(_rescue_relations_subject_tracking, "alpha ships via beta")
    assert emitted
    for r in emitted:
        assert r["properties"]["rescue"] is True
        assert r["properties"]["subject_tracked"] is True


# ── Ruling 5: the REPLACES family collapses through family_key ───────


def test_the_replaces_family_keeps_its_three_declared_members():
    """The suppression test below draws its cases from ``REPLACES_FAMILY``
    itself, so it cannot notice a member being deleted from the table.
    Adding a member is allowed; losing one of these three is not."""
    assert REPLACES_FAMILY >= {"REPLACES", "IMPROVES_ON", "BUILDS_ON"}


@pytest.mark.parametrize("existing_type", sorted(REPLACES_FAMILY))
def test_an_existing_family_member_suppresses_the_rescue(existing_type):
    """Every member of ``REPLACES_FAMILY`` shares one dedup bucket, so an
    LLM triple of any member blocks the rescue's REPLACES for that pair.
    Parametrized over the table so a new member cannot be added without
    this holding for it too."""
    seed = [{"source": "gamma", "target": "beta", "type": existing_type}]
    out = _rescue_relations_replaces(
        CORPUS_ENTITIES, seed, "we migrated alpha from beta to gamma"
    )
    assert out == seed


@pytest.mark.parametrize("unrelated_type", ["USES", "RELATED_TO", "DEPENDS_ON"])
def test_a_non_family_type_does_not_suppress_the_rescue(unrelated_type):
    seed = [{"source": "gamma", "target": "beta", "type": unrelated_type}]
    out = _rescue_relations_replaces(
        CORPUS_ENTITIES, seed, "we migrated alpha from beta to gamma"
    )
    assert ("gamma", "REPLACES", "beta") in _triples(out)


def test_the_family_collapse_holds_across_the_adjacency_pass_too():
    seed = [{"source": "alpha", "target": "beta", "type": "IMPROVES_ON"}]
    out = _rescue_relations(CORPUS_ENTITIES, seed, "alpha instead of beta")
    assert out == seed


# ── Ruling 3: rescue-tagged wins the tie-break, then weight ──────────


WRONG_DIRECTION_CONTENT = "We migrated darkmem from qdrant to pgvector last week."
WRONG_DIRECTION_RAW = {
    "entities": [
        {"name": "darkmem", "type": "project"},
        {"name": "qdrant", "type": "database"},
        {"name": "pgvector", "type": "tool"},
    ],
    # The mis-anchored LLM emission, at a weight no rescue triple can beat.
    "relationships": [
        {"source": "darkmem", "target": "qdrant", "type": "REPLACES", "weight": 0.99},
    ],
}


def test_rescue_beats_the_llm_on_the_wrong_direction_replaces():
    out = clean_extraction(dict(WRONG_DIRECTION_RAW), WRONG_DIRECTION_CONTENT)
    triples = _triples(out["relationships"])
    assert ("pgvector", "REPLACES", "qdrant") in triples
    assert ("darkmem", "REPLACES", "qdrant") not in triples

    survivor = next(
        r for r in out["relationships"]
        if (r["target"].lower(), r["type"]) == ("qdrant", "REPLACES")
    )
    assert survivor["properties"]["rescue"] is True
    assert survivor["weight"] < WRONG_DIRECTION_RAW["relationships"][0]["weight"]


def test_without_the_rescue_the_wrong_direction_edge_survives():
    """The other half of the same claim: the tie-break only rescues the
    direction because the rescue layer produced a competitor."""
    out = clean_extraction(
        dict(WRONG_DIRECTION_RAW), WRONG_DIRECTION_CONTENT, relation_rescue=False
    )
    assert ("darkmem", "REPLACES", "qdrant") in _triples(out["relationships"])


def test_a_direction_grounded_rescue_outranks_weight_in_the_tie_break():
    rescued = {"properties": {"rescue": True, "pattern": "from-to"}, "weight": 0.1}
    llm = {"properties": {}, "weight": 0.99}
    assert _prefer_relation(rescued, llm) is True
    assert _prefer_relation(llm, rescued) is False


@pytest.mark.parametrize("rescue", [True, False])
def test_weight_decides_when_both_sides_agree_on_rescue(rescue):
    props = {"rescue": True} if rescue else {}
    heavy = {"properties": dict(props), "weight": 0.9}
    light = {"properties": dict(props), "weight": 0.4}
    assert _prefer_relation(heavy, light) is True
    assert _prefer_relation(light, heavy) is False


# ── The declared order inside the stage ──────────────────────────────


def test_the_first_pass_to_claim_a_key_keeps_it():
    """Why the stage order is a contract and not a listing: the adjacency
    and subject-tracking passes can both reach ``alpha USES beta``, and
    whichever runs first fixes the weight and provenance the survivor
    carries into ``dedup_by_target_predicate``."""
    content = "alpha uses beta, and alpha ships to beta"
    entities = _entities("alpha", "beta")

    declared = _run_stage3(entities, [], content)
    assert [r["weight"] for r in declared] == [0.85]
    assert "subject_tracked" not in declared[0]["properties"]

    swapped = _rescue_relations(
        entities, _rescue_relations_subject_tracking(entities, [], content), content
    )
    assert [r["weight"] for r in swapped] == [0.55]
    assert swapped[0]["properties"]["subject_tracked"] is True


def test_the_synthesis_stage_runs_before_the_gating_stage():
    assert index_of(PASS_REGISTRY, "rescue_relations_replaces") < index_of(
        PASS_REGISTRY, "remap_to_valid_entities"
    )
