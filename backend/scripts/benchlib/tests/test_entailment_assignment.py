"""The Rule A assignment is deterministic, complete, and cap-respecting."""
from collections import Counter

from benchlib.entailment_assignment import (
    BATCH_RANGES,
    NEW_PAIR_SLICE_TARGETS,
    build_assignment,
    l2_eligible_slices,
)
from benchlib.entailment_gold import SLICES, load_l2_harvest


def test_targets_cover_every_slice_and_sum_to_200():
    assert set(NEW_PAIR_SLICE_TARGETS) == SLICES
    assert sum(NEW_PAIR_SLICE_TARGETS.values()) == 200
    assert "temporal" not in l2_eligible_slices()


def test_assignment_is_deterministic_and_seeded_from_the_manifest():
    first = build_assignment()
    second = build_assignment()
    assert first == second
    assert len(first) == sum(
        NEW_PAIR_SLICE_TARGETS[s] for s in l2_eligible_slices()
    )


def test_assignment_meets_slice_targets_and_the_premise_cap():
    manifest = load_l2_harvest()
    assignment = build_assignment(manifest)

    by_slice = Counter(e["slice"] for e in assignment)
    for slice_name in l2_eligible_slices():
        assert by_slice[slice_name] == NEW_PAIR_SLICE_TARGETS[slice_name]

    cap = manifest["header"]["pairs_per_premise_cap"]
    usage = Counter(e["triple_key"] for e in assignment)
    assert max(usage.values()) <= cap


def test_batches_partition_the_assignment_exactly():
    total = sum(NEW_PAIR_SLICE_TARGETS[s] for s in l2_eligible_slices())
    covered = []
    for start, end in BATCH_RANGES:
        covered.extend(range(start, end))
    assert covered == list(range(total))


# ── the T2.110 round-2 growth assignment ─────────────────────────────────


def test_round2_targets_cover_every_slice_and_sum_to_110():
    from benchlib.entailment_assignment import ROUND2_SLICE_TARGETS

    assert set(ROUND2_SLICE_TARGETS) == SLICES
    assert sum(ROUND2_SLICE_TARGETS.values()) == 110


def test_round2_seed_is_derived_from_the_pregrowth_gold_hash():
    """A seed someone picks is a seed someone can re-pick. This one is the
    first 8 hex digits of the 241-pair gold's SHA-256 (commit 53989628);
    the committed constant and its derivation must keep agreeing."""
    from benchlib.entailment_assignment import (
        ROUND2_BASE_GOLD_SHA256, ROUND2_SEED,
    )

    assert len(ROUND2_BASE_GOLD_SHA256) == 64
    assert ROUND2_SEED == int(ROUND2_BASE_GOLD_SHA256[:8], 16)


def test_round2_assignment_is_deterministic_and_meets_targets():
    from benchlib.entailment_assignment import (
        ROUND2_SLICE_TARGETS, build_round2_assignment,
    )

    first = build_round2_assignment()
    second = build_round2_assignment()
    assert first == second
    by_slice = Counter(e["slice"] for e in first)
    for slice_name, target in ROUND2_SLICE_TARGETS.items():
        if slice_name == "temporal":
            assert slice_name not in by_slice
        else:
            assert by_slice[slice_name] == target


def test_round2_assignment_respects_the_cap_over_existing_usage():
    """Round 1 started from zero usage; round 2 does not, so cycling alone
    would breach the cap on a thrice-used premise. Existing (pre-growth)
    usage plus round-2 assignments must stay within the cap per premise."""
    import json

    from benchlib.entailment_assignment import (
        ROUND2_MAX_EXISTING_ID, build_round2_assignment,
    )
    from benchlib.entailment_gold import GOLD_PATH

    manifest = load_l2_harvest()
    gold_doc = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assignment = build_round2_assignment(manifest, gold_doc)

    existing = Counter(
        p["premise"] for p in gold_doc["pairs"]
        if p["id"] <= ROUND2_MAX_EXISTING_ID
    )
    cap = manifest["header"]["pairs_per_premise_cap"]
    total = Counter({row["fact"]: existing.get(row["fact"], 0)
                     for row in manifest["facts"]})
    for entry in assignment:
        total[entry["fact"]] += 1
    assert max(total.values()) <= cap


def test_committed_round2_l2_pairs_sit_on_assigned_slots():
    """The anti-curation property: every round-2 l2-fact pair's
    (slice, premise) is one the seeded assignment handed its author. Skips
    only remove assigned slots (logged in LABELLING.md); nothing may add a
    hand-picked premise under the l2 provenance."""
    import json

    from benchlib.entailment_assignment import (
        ROUND2_MAX_EXISTING_ID, build_round2_assignment,
    )
    from benchlib.entailment_gold import GOLD_PATH

    gold_doc = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assignment = build_round2_assignment(load_l2_harvest(), gold_doc)
    assigned = Counter((e["slice"], e["fact"]) for e in assignment)

    committed = Counter(
        (p["slice_tags"][0], p["premise"])
        for p in gold_doc["pairs"]
        if p["id"] > ROUND2_MAX_EXISTING_ID
        and not p.get("retired")
        and p["provenance"] == "l2-fact"
    )
    overdrawn = committed - assigned
    assert not overdrawn, f"l2 pairs off the seeded assignment: {overdrawn}"
