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


def test_committed_l2_pairs_sit_on_assigned_slots():
    """The anti-curation property: every live l2-fact pair's (slice, premise)
    is one a seeded assignment handed its author. Skips only remove assigned
    slots (logged in LABELLING.md); nothing may add a hand-picked premise
    under the l2 provenance.

    **Checked per round against that round's own assignment, not against the
    union of every assignment ever built.** The union form was right while one
    file accumulated rounds 2 and 3: each round has its own seed, so checking
    T2.115's nine appended pairs against round 2's slots reported them as
    curated when they were nothing of the kind. Round 4 replaced the file
    rather than appending to it, and under a replacement the union inverts —
    rounds 2 and 3 assigned premises for pairs that no longer exist, so every
    slot they contribute is a slot a round-4 pair could match without its own
    assignment ever having handed it out. The archive holds the earlier
    rounds' pairs and the property is asserted there by its own round's
    artifacts; here the population is round 4's and so is the assignment.

    Scoped to the **authored** census, because the assignment only ever
    covered that: the seeded draw ran once, before authoring, and a pair
    minted afterwards to replace a retired one has no slot in it by
    construction. Those are checked by the test below instead.
    """
    import json

    from benchlib.entailment_assignment import build_round4_assignment
    from benchlib.entailment_gold import GOLD_PATH

    gold_doc = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assigned = Counter(
        (e["slice"], e["fact"]) for e in build_round4_assignment()
    )

    committed = Counter(
        (p["slice_tags"][0], p["premise"])
        for p in gold_doc["pairs"]
        if p["id"] <= _last_authored_id()
        and not p.get("retired")
        and p["provenance"] == "l2-fact"
    )
    assert committed, "the round's l2 population must not be empty"
    overdrawn = committed - assigned
    assert not overdrawn, f"l2 pairs off the seeded assignment: {overdrawn}"


def _last_authored_id() -> str:
    """The last id the seeded authoring minted, derived from the ratified
    frame rather than read off the file it bounds.

    Ids are consecutive from the round's first fresh id, and the frame's total
    is how many the round authored, so the boundary between "assigned" and
    "minted as a replacement" is a property of two committed artifacts and not
    of anyone's memory of which commit ended the authoring batch.
    """
    import json

    from benchlib import round4_frame
    from benchlib.entailment_assignment import ROUND4_FIRST_FRESH_ID

    frame = json.loads(round4_frame.FRAME_PATH.read_text(encoding="utf-8"))
    first = int(ROUND4_FIRST_FRESH_ID.split("-")[1])
    return f"eg-{first + frame['total'] - 1:04d}"


def test_every_pair_past_the_authored_census_answers_a_retirement():
    """The replacement population, bounded so the exemption above cannot grow.

    Adjudication retires a pair whose recorded label a later rule condemns,
    and file discipline forbids flipping it in place — the slice contract and
    the ratified matrix both depend on the cell counts — so the retirement is
    answered by a freshly minted pair. Those pairs sit past the authored
    range and their premises are chosen under the rule each minting commit
    records (a manifest fact funding no other slot of the same verdict, or a
    hand-authored premise where the slice has no manifest source), never by
    the seeded assignment, which ran once before authoring and was consumed.

    What keeps that from being an open door: minting a replacement is only
    lawful as the answer to a retirement, so the two populations are the same
    size. A curated pair added under no retirement lands here as a count
    mismatch.
    """
    import json

    from benchlib.entailment_gold import GOLD_PATH

    gold_doc = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    last_authored = _last_authored_id()
    minted = [p for p in gold_doc["pairs"] if p["id"] > last_authored]
    retired = [p for p in gold_doc["pairs"] if p.get("retired")]

    assert len(minted) == len(retired), (
        f"{len(minted)} pairs minted past {last_authored} against "
        f"{len(retired)} retirements — a replacement is lawful only as the "
        "answer to a retirement, and the counts are what say so"
    )
    # A replacement never reaches outside the round's two premise sources.
    assert {p["provenance"] for p in minted} <= {
        "l2-fact", "hand-authored-synthetic-fact"
    }


def test_no_live_pair_predates_the_round_4_population():
    """The checks above are scoped to round 4's ids, so they are exhaustive
    only while the file holds nothing older. A later round that appends rather
    than replaces must extend the scoping, not inherit it silently."""
    import json

    from benchlib.entailment_assignment import ROUND4_FIRST_FRESH_ID
    from benchlib.entailment_gold import GOLD_PATH

    gold_doc = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    older = [
        p["id"] for p in gold_doc["pairs"]
        if not p.get("retired") and p["id"] < ROUND4_FIRST_FRESH_ID
    ]
    assert not older, (
        f"live pairs predate {ROUND4_FIRST_FRESH_ID}: {older}. The assignment "
        "checks above cover round 4's ids only; widen them to the rounds whose "
        "pairs are now live before this pin is relaxed."
    )
