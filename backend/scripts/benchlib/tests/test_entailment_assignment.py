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
