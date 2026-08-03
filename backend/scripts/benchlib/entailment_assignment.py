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
        help=f"print only authoring batch 1..{len(BATCH_RANGES)}",
    )
    args = parser.parse_args(argv)

    assignment = build_assignment()
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
