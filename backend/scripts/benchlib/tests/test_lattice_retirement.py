"""The committed draw's own guards (LABELLING.md's lattice-retirement rule).

The rule's clause 3 says the selection procedure must land in a commit before it
executes, "because pinning a seed alone does not close the aiming channel". A
module nobody tests is a procedure that can be edited between rounds, so these
pin the properties that make the draw unaimable rather than merely deterministic:
that it is a pure function of (file bytes, verdict, n), that the eligibility
clauses actually exclude what they name, and that no ordering incident of the
input can move the result.
"""

from __future__ import annotations

import json
import pathlib

from benchlib import entailment_gold, lattice_retirement as lr


GOLD = pathlib.Path(entailment_gold.ENTAILMENT_DIR) / "gold.json"


def _pairs() -> list[dict]:
    return json.loads(GOLD.read_text(encoding="utf-8"))["pairs"]


def test_the_draw_is_a_pure_function_of_the_file():
    """Same bytes, same verdict, same n, same ids — every time. This is what
    makes the one-command reproduction in the task report checkable by someone
    who does not trust the executor."""
    first = lr.draw(GOLD, "contradicted", 15)
    second = lr.draw(GOLD, "contradicted", 15)

    assert first.retired_ids == second.retired_ids
    assert first.seed == second.seed


def test_the_seed_comes_from_the_file_and_not_from_the_caller():
    """`derive_seed` over the gold's own bytes: a function of content nobody in
    the round chose. There is no seed parameter to pass, deliberately."""
    from benchlib import resample_draw

    assert lr.draw(GOLD, "contradicted", 15).seed == resample_draw.derive_seed(
        GOLD.read_bytes()
    )


def test_clause_1_only_the_contacted_population_is_eligible():
    """A round removes contaminated evidence and never fresh evidence."""
    pool = lr.eligible_pool(_pairs(), "contradicted")

    assert all(
        pair_id < lr.RULE_B_FIRST_ID for ids in pool.values() for pair_id in ids
    )


def test_clause_2_the_protected_core_is_never_eligible():
    """Rule B keeps the 41 T2.25 pairs live — the only fully human-scale
    cross-checked labels the set has."""
    pool = lr.eligible_pool(_pairs(), "contradicted")

    assert all(
        pair_id > lr.PROTECTED_CORE_LAST_ID
        for ids in pool.values()
        for pair_id in ids
    )
    # And the exclusion is doing work rather than being vacuous: the gold really
    # does hold protected pairs of this verdict.
    protected = [
        p for p in _pairs()
        if p["verdict"] == "contradicted" and p["id"] <= lr.PROTECTED_CORE_LAST_ID
    ]
    assert protected


def test_clause_5_the_quota_is_largest_remainder_over_the_pool():
    """Composition, not just size: the quota is a function of the eligible
    pool's own slice distribution, not of anything the executor picks.

    Asserted as the *property* rather than as one round's numbers. The first
    version pinned `{value-swap: 8, direction: 4, temporal: 3}` — T2.115's own
    draw — and then T2.115 retired those pairs, which moved the pool the pin
    was computed over and turned a correct procedure into a red test. A round's
    actual draw belongs in LABELLING.md's History, which is the protocol's
    memory; this file's job is that the next round's draw is derived the same
    way.
    """
    pool = lr.eligible_pool(_pairs(), "contradicted")
    sizes = {k: len(v) for k, v in pool.items()}
    quota = lr.largest_remainder(sizes, 15)

    assert sum(quota.values()) == 15
    population = sum(sizes.values())
    for slice_name, taken in quota.items():
        exact = 15 * sizes[slice_name] / population
        assert abs(taken - exact) < 1, (
            f"{slice_name}: {taken} is not within one of its proportional "
            f"share {exact:.2f} — the allocation is not largest-remainder"
        )


def test_input_order_cannot_move_the_result():
    """The pools are id-sorted and the strata processed in a fixed order, so a
    reordered file — a merge, a re-serialisation — draws the same set. Without
    this the 'reproduction' in the report would hold only for one file layout.
    """
    document = json.loads(GOLD.read_text(encoding="utf-8"))
    shuffled = dict(document)
    shuffled["pairs"] = list(reversed(document["pairs"]))

    straight = lr.eligible_pool(document["pairs"], "contradicted")
    reversed_pool = lr.eligible_pool(shuffled["pairs"], "contradicted")

    assert straight == reversed_pool


def test_a_multi_tag_pair_stops_the_draw_rather_than_being_guessed_at():
    """The stratification assumes one slice per pair. If that ever stops being
    true the draw must be revisited, not silently double-count a pair across
    strata — which would let one pair be retired twice or skew the quota."""
    import pytest

    document = json.loads(GOLD.read_text(encoding="utf-8"))
    victim = next(p for p in document["pairs"] if p["verdict"] == "contradicted")
    victim["slice_tags"] = [*victim["slice_tags"], "paraphrase"]
    path = pathlib.Path(__file__).parent / "_multi_tag_probe.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="slice tags"):
            lr.draw(path, "contradicted", 15)
    finally:
        path.unlink()
