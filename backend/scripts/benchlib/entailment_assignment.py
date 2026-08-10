"""Deterministic premise assignment for the T2.54 authoring round (Rule A).

Composition is a function of pre-judge data only: the per-slice targets are
T2.25's slice proportions scaled to 200 by largest-remainder rounding
(frozen in LABELLING.md), and the premise-to-slot assignment below is a
pure function of the committed harvest manifest and the seed recorded in
its header -- no author, and no judge, chooses which fact meets which
slice. Re-running this module re-derives the exact assignment order, so a
reviewer can check that every authored ``l2-fact`` pair sits on its
assigned slot and every deviation is a logged skip, not silent curation.

``temporal`` takes no manifest premises: ``fact_lift`` renders no validity
window into fact text (measured fact M10), so the slice's premises are
hand-authored under doc 17 §11's exemption, whose sunset tripwire lives in
``entailment_gold.load_l2_harvest``.

Run from backend/:
  python scripts/benchlib/entailment_assignment.py [--batch N]
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib.entailment_gold import load_l2_harvest  # noqa: E402

# T2.25's 41-pair slice proportions scaled to 200 by largest-remainder
# rounding, ties broken alphabetically (LABELLING.md, "Frozen composition
# for the T2.54 authoring round"). The sum is exactly 200.
NEW_PAIR_SLICE_TARGETS: dict[str, int] = {
    "verbatim": 20,
    "paraphrase": 29,
    "weakening": 24,
    "temporal": 29,
    "direction": 25,
    "overreach": 29,
    "value-swap": 24,
    "unrelated": 20,
}

# Slot batches for the four authoring dispatches: contiguous ranges over the
# assignment order below, plus the hand-authored temporal block in batch 4.
BATCH_RANGES = ((0, 50), (50, 100), (100, 150), (150, 171))


# ── T2.110 growth round (round 2) ────────────────────────────────────────
#
# Census sizing, stated before any pair existed: `contradiction_recall_bar`
# is 0.95 = 19/20, and recall resolves in steps of 1/N over the
# gold-contradicted census N. At the prior N = 55 the achievable values
# bracket the bar at 52/55 ~= 0.9455 and 53/55 ~= 0.9636 -- 0.95 is not on
# the lattice, so the operative bar was 0.9636. The bar sits on the lattice
# only when N is a multiple of 20, and the resample protocol's full-census
# stratification caps N at RESAMPLE_N = 93. The one multiple of 20 in
# (55, 93] is 80, so the growth targets a contradicted census of exactly 80
# and scales every slice proportionally (241 -> 351 by largest-remainder
# rounding of the live slice counts).
#
# The seed is derived, never chosen: the first 8 hex digits of the
# pre-growth gold.json's SHA-256 (commit 53989628, 241 live pairs). An
# author cannot re-pick it without rewriting a committed file's history,
# which is what makes the premise-to-slot assignment unaimable.
ROUND2_BASE_GOLD_SHA256 = (
    "e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df"
)
ROUND2_SEED = int(ROUND2_BASE_GOLD_SHA256[:8], 16)

# Pairs whose premise usage predates round 2: everything up to the last
# T2.54 id. Counted regardless of a later `retired` flag, so the assignment
# re-derives identically forever (append-only makes the id range immutable).
ROUND2_MAX_EXISTING_ID = "eg-0241"

ROUND2_SLICE_TARGETS: dict[str, int] = {
    "verbatim": 11,
    "paraphrase": 16,
    "weakening": 13,
    "temporal": 16,
    "direction": 14,
    "overreach": 16,
    "value-swap": 13,
    "unrelated": 11,
}


def _round2_existing_usage(gold_doc: dict) -> dict[str, int]:
    usage: dict[str, int] = {}
    for pair in gold_doc["pairs"]:
        if pair["id"] <= ROUND2_MAX_EXISTING_ID:
            usage[pair["premise"]] = usage.get(pair["premise"], 0) + 1
    return usage


def build_round2_assignment(
    manifest: dict | None = None, gold_doc: dict | None = None,
) -> list[dict]:
    """The round-2 seeded (premise x slice) assignment.

    Unlike round 1, facts start with non-zero usage, so cycling alone would
    push a thrice-used premise past the cap. The cycle therefore skips
    exhausted facts: each slot takes the next fact in the seeded order with
    remaining capacity, decrementing as it goes. Deterministic in the
    manifest, the pre-growth usage and ROUND2_SEED alone.
    """
    manifest = manifest or load_l2_harvest()
    if gold_doc is None:
        import json

        gold_path = HERE / "entailment" / "gold.json"
        gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))

    facts = manifest["facts"]
    cap = manifest["header"]["pairs_per_premise_cap"]
    usage = _round2_existing_usage(gold_doc)
    remaining = {row["triple_key"]: cap - usage.get(row["fact"], 0) for row in facts}

    rng = random.Random(ROUND2_SEED)
    slots = [
        slice_name
        for slice_name in sorted(ROUND2_SLICE_TARGETS)
        if slice_name != "temporal"
        for _ in range(ROUND2_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    if sum(max(r, 0) for r in remaining.values()) < len(slots):
        raise RuntimeError(
            f"{len(slots)} slots exceed the harvest's remaining capacity "
            "under the pairs-per-premise cap -- the harvest is too small "
            "for this growth (do not widen the cap)"
        )

    assignment = []
    cursor = 0
    for slot, slice_name in enumerate(shuffled_slots):
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] > 0:
                break
        else:
            raise RuntimeError("no fact with remaining capacity")
        remaining[row["triple_key"]] -= 1
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
        })
    return assignment


# ── T2.115 lattice-resize round (round 3) ────────────────────────────────
#
# Not a growth round: the pooled contradicted census is held at 80 while
# Rule B's second population goes 25 -> 40, so 0.95 lands on its recall
# lattice (38/40) as it already does on the pooled one (76/80). Fifteen
# contacted contradicted pairs retire under LABELLING.md's lattice-retirement
# rule and fifteen are authored to replace them, with 51 companions keeping
# the second population's contradicted base rate at the gold's own ~23%.
#
# **Two decisions the plan review required be stated rather than inferred:**
#
# 1. **Usage counts LIVE pairs only.** LABELLING.md's cap is "<= 4 **live**
#    pairs per premise", and round 2's helper counted by id threshold
#    regardless of retirement -- correct there, because nothing had retired.
#    Here fifteen pairs have, and reading the cap literally is what lets
#    their premises take a replacement. Counting them would leave capacity
#    stranded behind pairs that no longer exist.
# 2. **The seed hashes the POST-retirement file.** Step 2 moves the sha, so
#    "the file's own hash" is ambiguous between the pre- and post-retirement
#    states; either is unchooseable, and two implementers reading the same
#    sentence would otherwise derive different assignments. The state that
#    *precedes the operation this seed drives* is the post-retirement one.
# Slices whose pairs are all contradicted, or whose verdict the
# reversal-exclusivity table may make contradicted. Named by slice, never by
# pair, so the priority cannot select for difficulty.
CONTRADICTED_FIRST_SLICES = ("value-swap", "direction")

ROUND3_SLICE_TARGETS: dict[str, int] = {
    # Contradicted replacements, mirroring the retirement draw's quota.
    # **This did NOT hold in execution and the comment used to claim it did**
    # ("unchanged end to end (rule clause 5)"): authoring returned one
    # `overreach`-contradicted pair and the temporal batch was sized at 2
    # rather than 3 to keep the census at 80, moving the pooled distribution
    # (temporal 15->14, overreach 0->1). Recorded in the gate ledger as C-1,
    # awaiting owner adjudication; do not re-assert preservation here.
    "value-swap": 8,
    "direction": 4 + 4,   # 4 contradicted + 4 unsupported companions
    # Companions, largest-remainder over the live non-contradicted
    # (slice, verdict) distribution.
    "overreach": 10,
    "paraphrase": 10,
    "unrelated": 7,
    "verbatim": 6,
    "weakening": 8,
    # Temporal is hand-authored (doc 17 section 11's premise exemption) and
    # takes no l2 slot. Planned 3C/3E/3U; **shipped 2C/3E/4U**, sized after
    # authoring to land the census at 80 (see C-1 in the gate ledger).
    "temporal": 9,
}


def _live_premise_usage(gold_doc: dict) -> dict[str, int]:
    """Premise usage over **live** pairs, per LABELLING.md's cap wording."""
    usage: dict[str, int] = {}
    for pair in gold_doc["pairs"]:
        if pair.get("retired"):
            continue
        usage[pair["premise"]] = usage.get(pair["premise"], 0) + 1
    return usage


def build_round3_assignment(
    manifest: dict | None = None, gold_doc: dict | None = None,
) -> list[dict]:
    """The round-3 seeded (premise x slice) assignment.

    Same capacity-aware cycle as round 2 -- each slot takes the next fact in
    the seeded order with remaining capacity -- over live usage and a seed
    derived from the post-retirement file.
    """
    import json

    manifest = manifest or load_l2_harvest()
    gold_path = HERE / "entailment" / "gold.json"
    if gold_doc is None:
        gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))

    seed = int(hashlib.sha256(gold_path.read_bytes()).hexdigest()[:8], 16)
    facts = manifest["facts"]
    cap = manifest["header"]["pairs_per_premise_cap"]
    usage = _live_premise_usage(gold_doc)
    remaining = {row["triple_key"]: cap - usage.get(row["fact"], 0) for row in facts}

    rng = random.Random(seed)
    slots = [
        slice_name
        for slice_name in sorted(ROUND3_SLICE_TARGETS)
        if slice_name != "temporal"
        for _ in range(ROUND3_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    # **The harvest is exhausted, and the shortfall is allocated by a rule
    # stated before the draw** (owner ruling 2026-08-10). Round 2 could anchor
    # every non-temporal slot; after it, 19 of this round's 57 slots have
    # capacity. LABELLING.md already has the mechanism -- a slot with no usable
    # premise takes a hand-authored one with a recorded skip, "so slice targets
    # stay exact and only the `l2-fact` count moves" -- and doc 17 section 11's
    # >= 50% l2-fact floor still holds with margin (238/402 = 59.2%). This read
    # 248/402 = 61.7% until 2026-08-10: that assumed all 19 anchored slots
    # landed, and ten of them skipped, which is the very mechanism the sentence
    # above describes. The floor holds either way; the number did not.
    #
    # Scarce capacity goes to CONTRADICTED_FIRST_SLICES before anything else:
    # those pairs are the census the gate's truth-critical bar is computed over,
    # so they are where a real minted premise is worth most. The rule is
    # content-blind -- it names slices, never pairs -- and companions then take
    # what is left in the seeded shuffled order, so which companions get anchors
    # is decided by the seed rather than by anyone.
    capacity = sum(max(r, 0) for r in remaining.values())
    priority = [
        index for index, name in enumerate(shuffled_slots)
        if name in CONTRADICTED_FIRST_SLICES
    ]
    rest = [
        index for index, name in enumerate(shuffled_slots)
        if name not in CONTRADICTED_FIRST_SLICES
    ]
    anchored = set((priority + rest)[:capacity])
    if len(priority) > capacity:
        raise RuntimeError(
            f"{len(priority)} contradicted slots exceed the harvest's remaining "
            f"capacity ({capacity}); the round cannot anchor the census it "
            "measures and the corpus must grow first (do not widen the cap)"
        )

    assignment = []
    cursor = 0
    for slot, slice_name in enumerate(shuffled_slots):
        if slot not in anchored:
            # Recorded as a capacity skip, not an infeasible-shape one.
            assignment.append({
                "slot": slot,
                "slice": slice_name,
                "triple_key": None,
                "rel_type": None,
                "fact": None,
                "premise_source": "hand-authored (harvest capacity exhausted)",
            })
            continue
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] > 0:
                break
        else:
            raise RuntimeError("no fact with remaining capacity")
        remaining[row["triple_key"]] -= 1
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
            "premise_source": "l2-fact",
        })
    return assignment


def l2_eligible_slices() -> list[str]:
    return sorted(s for s in NEW_PAIR_SLICE_TARGETS if s != "temporal")


def build_assignment(manifest: dict | None = None) -> list[dict]:
    """The seeded (premise x slice) assignment: one entry per non-temporal
    slot, in the shuffled order the seed derives. Facts cycle in a seeded
    order, so usage stays within the pairs-per-premise cap whenever
    ``ceil(slots / facts) <= cap`` -- asserted, not assumed."""
    manifest = manifest or load_l2_harvest()
    facts = manifest["facts"]
    header = manifest["header"]
    rng = random.Random(header["assignment_seed"])

    slots = [
        slice_name
        for slice_name in l2_eligible_slices()
        for _ in range(NEW_PAIR_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    max_usage = -(-len(slots) // len(facts))
    if max_usage > header["pairs_per_premise_cap"]:
        raise RuntimeError(
            f"{len(slots)} slots over {len(facts)} facts needs {max_usage} "
            f"pairs on some premise, above the cap "
            f"{header['pairs_per_premise_cap']} -- the harvest is too small "
            "for this composition (blocker B2 territory; do not widen the cap)"
        )

    assignment = []
    for slot, slice_name in enumerate(shuffled_slots):
        row = facts[fact_order[slot % len(facts)]]
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
        })
    return assignment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--batch", type=int, default=None,
        help=f"print only authoring batch 1..{len(BATCH_RANGES)} (round 1)",
    )
    parser.add_argument(
        "--round", type=int, default=1, choices=(1, 2),
        help="1 = the T2.54 authoring round, 2 = the T2.110 growth round",
    )
    args = parser.parse_args(argv)

    assignment = build_assignment() if args.round == 1 else build_round2_assignment()
    if args.batch is not None:
        start, end = BATCH_RANGES[args.batch - 1]
        assignment = assignment[start:end]
    for entry in assignment:
        print(
            f"{entry['slot']:3d}  {entry['slice']:<10}  "
            f"{entry['rel_type']:<12}  {entry['fact']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
