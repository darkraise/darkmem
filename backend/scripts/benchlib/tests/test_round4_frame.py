"""Pins for the round-4 frame, its assignment, and the cross-file near-screen.

Deliberately reads only the committed frame JSON, the archived retired gold,
the fresh harvest manifest and the exclusion list — never the canonical
``entailment/gold.json`` — so this file stays green through the sanctioned
mid-sequence window where no gold sits at the canonical path.
"""
import json

import pytest

from benchlib import duplicate_propositions, entailment_assignment, round4_frame
from benchlib.entailment_gold import RETIRED_GOLD_ARCHIVE_PATH, SLICE_VERDICTS
from benchlib.judge_qualification import MIN_GOLD_PAIRS, RESAMPLE_N, RULE_B_FIRST_ID

from app.taxonomy import RELATIONSHIP_TYPES


@pytest.fixture(scope="module")
def committed_frame():
    return json.loads(round4_frame.FRAME_PATH.read_text(encoding="utf-8"))


# ── the frame is the rule's output, not a hand-written table ─────────────


def test_committed_frame_regenerates_byte_identically():
    """D5's ordering guarantee with teeth: a hand edit of the committed JSON,
    or a drifted rule, fails here rather than relying on anyone's memory."""
    frame = round4_frame.derive_frame(round4_frame.fresh_fact_count())
    round4_frame.assert_frame_checks(frame)
    assert round4_frame.frame_json(frame) == round4_frame.FRAME_PATH.read_text(
        encoding="utf-8"
    )


def test_lattice_properties_hold_on_the_committed_matrix(committed_frame):
    """Sitting 2's mechanical checks, asserted from the committed file so a
    later hand edit that breaks one fails the floor."""
    census = committed_frame["census"]
    assert census["entailed"] % round4_frame.ENTAILED_LATTICE_MODULUS == 0
    assert census["contradicted"] == round4_frame.CONTRADICTED_TARGET
    assert census["contradicted"] % 20 == 0
    assert census["contradicted"] <= RESAMPLE_N
    assert committed_frame["total"] >= MIN_GOLD_PAIRS
    assert committed_frame["total"] == sum(census.values())
    assert committed_frame["total"] == sum(committed_frame["slice_targets"].values())
    for slice_name, cells in committed_frame["matrix"].items():
        assert sum(cells.values()) == committed_frame["slice_targets"][slice_name]
        for verdict, n in cells.items():
            assert n >= 0
            if n:
                assert verdict in SLICE_VERDICTS[slice_name]


def test_seed_splits_recount_from_the_archive_to_the_ratified_pin():
    counted = round4_frame.count_seed_splits()
    pinned_positive = {
        s: {v: n for v, n in cells.items() if n}
        for s, cells in round4_frame.T2_25_SPLITS_PINNED.items()
    }
    assert counted == pinned_positive


def test_every_slice_meets_its_t2_25_floor_and_near_miss_majority(committed_frame):
    targets = committed_frame["slice_targets"]
    for s, floor in round4_frame.T2_25_PROPORTIONS.items():
        assert targets[s] >= floor, s
    from benchlib.entailment_gold import NEAR_MISS_SLICES
    near = sum(targets[s] for s in NEAR_MISS_SLICES)
    assert near * 2 > committed_frame["total"]


def test_the_frame_census_is_rule_b_coincident():
    """D2: ids continue at eg-0418, so `id >= RULE_B_FIRST_ID` admits every
    fresh pair and the pooled and Rule B populations coincide until the
    first attempt spends. Lexical comparison is the runner's own predicate,
    so the pin uses exactly it."""
    assert entailment_assignment.ROUND4_FIRST_FRESH_ID >= RULE_B_FIRST_ID
    assert entailment_assignment.ROUND4_FIRST_FRESH_ID > "eg-0417"


# ── the absorbing rule is code, not a mid-round decision ─────────────────


def test_absorbing_rule_is_deterministic_and_preserves_the_reduced_total(
    committed_frame,
):
    absorbed = round4_frame.absorb_shortfall(committed_frame, 3)
    again = round4_frame.absorb_shortfall(committed_frame, 3)
    assert absorbed == again
    assert sum(sum(c.values()) for c in absorbed.values()) == (
        committed_frame["total"] - 3
    )
    for slice_name, cells in absorbed.items():
        for verdict, n in cells.items():
            if n:
                assert verdict in SLICE_VERDICTS[slice_name]


def test_absorbing_zero_shortfall_reproduces_the_frame(committed_frame):
    absorbed = round4_frame.absorb_shortfall(committed_frame, 0)
    expected = {
        s: {v: n for v, n in cells.items() if n}
        for s, cells in committed_frame["matrix"].items()
    }
    assert absorbed == {
        s: {v: n for v, n in cells.items() if n} for s, cells in absorbed.items()
    } == expected


# ── the cross-file near-screen is non-vacuous ────────────────────────────


def _archived_live_pairs():
    doc = json.loads(RETIRED_GOLD_ARCHIVE_PATH.read_text(encoding="utf-8"))
    return [
        p for p in doc["pairs"]
        if not ("retired" in p or p.get("retirement_kind"))
    ]


def test_near_screen_reports_a_reworded_archived_pair_the_duplicate_check_misses():
    """The non-vacuity pin the plan requires: a fresh pair reworded from an
    archived one shares no premise bytes, so `find_duplicate_propositions`
    groups it with nothing and reports nothing — while the cross-file screen
    flags it on both-sides token Jaccard. If either half of this stops being
    true, the screen has gone vacuous or the duplicate check's scope moved."""
    archived = _archived_live_pairs()[0]
    reworded = {
        "id": "eg-9999",
        "premise": "Indeed, " + archived["premise"],
        "hypothesis": "Indeed, " + archived["hypothesis"],
        "verdict": archived["verdict"],
    }
    assert reworded["premise"] != archived["premise"]

    assert duplicate_propositions.find_duplicate_propositions(
        [reworded] + [archived]
    ) == []

    findings = duplicate_propositions.cross_gold_near_overlap([reworded], [archived])
    assert [(f.fresh_id, f.archived_id) for f in findings] == [
        ("eg-9999", archived["id"])
    ]
    assert findings[0].premise_similarity >= 0.85
    assert findings[0].hypothesis_similarity >= 0.85


def test_near_screen_ignores_genuinely_fresh_premises():
    archived = _archived_live_pairs()[:5]
    fresh = [{
        "id": "eg-0418",
        "premise": "wholly new subject matter about a wholly new system",
        "hypothesis": "the wholly new system does a wholly new thing",
        "verdict": "entailed",
    }]
    assert duplicate_propositions.cross_gold_near_overlap(fresh, archived) == []


def test_near_screen_skips_retired_archived_rows():
    doc = json.loads(RETIRED_GOLD_ARCHIVE_PATH.read_text(encoding="utf-8"))
    retired = next(p for p in doc["pairs"] if p.get("retired"))
    clone = dict(retired)
    clone["id"] = "eg-9998"
    assert duplicate_propositions.cross_gold_near_overlap([clone], [retired]) == []


# ── the assignment is seeded, exclusion-honouring, and cap-bounded ───────


def test_reversal_classes_cover_the_taxonomy_exhaustively():
    union = (
        entailment_assignment.REVERSAL_EXCLUSIVE
        | entailment_assignment.REVERSAL_NON_EXCLUSIVE
        | entailment_assignment.REVERSAL_SYMMETRIC
    )
    assert union == set(RELATIONSHIP_TYPES)


@pytest.fixture(scope="module")
def round4_assignment():
    return entailment_assignment.build_round4_assignment()


def test_round4_assignment_is_deterministic(round4_assignment):
    assert entailment_assignment.build_round4_assignment() == round4_assignment


def test_round4_assignment_shape_matches_the_frame(committed_frame, round4_assignment):
    non_temporal = committed_frame["total"] - committed_frame["slice_targets"]["temporal"]
    assert len(round4_assignment) == non_temporal
    per_slice: dict[str, int] = {}
    for entry in round4_assignment:
        per_slice[entry["slice"]] = per_slice.get(entry["slice"], 0) + 1
    for slice_name, target in committed_frame["slice_targets"].items():
        if slice_name == "temporal":
            continue
        assert per_slice[slice_name] == target, slice_name


def test_round4_assignment_draws_no_excluded_premise(round4_assignment):
    excluded = set(json.loads(
        entailment_assignment.ROUND4_EXCLUDED_KEYS_PATH.read_text(encoding="utf-8")
    )["triple_keys"])
    assert not {e["triple_key"] for e in round4_assignment} & excluded


def test_round4_assignment_respects_the_cap_and_determined_slices(round4_assignment):
    usage: dict[str, int] = {}
    per_slice_premises: dict[str, list[str]] = {}
    for entry in round4_assignment:
        usage[entry["triple_key"]] = usage.get(entry["triple_key"], 0) + 1
        per_slice_premises.setdefault(entry["slice"], []).append(entry["triple_key"])
    assert max(usage.values()) <= 4
    for slice_name in entailment_assignment.ROUND4_DETERMINED_SLICES:
        premises = per_slice_premises[slice_name]
        assert len(premises) == len(set(premises)), (
            f"{slice_name} reused a premise; its hypothesis is determined by "
            "the premise, so a reuse is a near-duplicate by construction"
        )


def test_round4_direction_slots_realise_the_frame_quota_by_relation_class(
    committed_frame, round4_assignment,
):
    cells = committed_frame["matrix"]["direction"]
    exclusive = [
        e for e in round4_assignment
        if e["slice"] == "direction" and e["reversal_class"] == "exclusive"
    ]
    non_exclusive = [
        e for e in round4_assignment
        if e["slice"] == "direction" and e["reversal_class"] == "non-exclusive"
    ]
    assert len(exclusive) == cells["contradicted"]
    assert len(non_exclusive) == cells["unsupported"]
    for entry in exclusive:
        assert entry["rel_type"] in entailment_assignment.REVERSAL_EXCLUSIVE
    for entry in non_exclusive:
        assert entry["rel_type"] in entailment_assignment.REVERSAL_NON_EXCLUSIVE
    for entry in round4_assignment:
        if entry["slice"] != "direction":
            assert entry["reversal_class"] is None


def test_round4_seed_derives_from_the_committed_frame_bytes():
    import hashlib
    expected = int(
        hashlib.sha256(round4_frame.FRAME_PATH.read_bytes()).hexdigest()[:8], 16
    )
    assert entailment_assignment.round4_seed() == expected
