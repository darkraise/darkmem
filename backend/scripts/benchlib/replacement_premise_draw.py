"""Which premises the replacement pairs are authored against (ruling R-B).

A duplicate repair retires two pairs and must replace them, so somebody has to
decide which facts the replacements are written about. **That decision is the
aiming channel** — a contaminated party picking premises could pick easy ones —
so it is made here, mechanically, and this module lands in a commit *before* it
executes, exactly as clause 3 requires of the retirement draw.

Three filters, each from a ratified source and none from a judge:

1. **No live `direction` pair on the fact.** This is the condition round 3 of
   T2.115 broke three times: anchoring a `direction` slot on a fact that already
   carried one produces the reversal that is already in the set. Two collided
   byte-for-byte and were skipped; `eg-0367` did not collide and became the
   duplicate this repair exists to remove.
2. **A relation whose reversal is *exclusive*** by LABELLING.md's
   reversal-exclusivity table. A `direction` pair over a non-exclusive relation
   is `unsupported`, not `contradicted` — `USES`, `DEPENDS_ON` and `CAUSES`
   cannot fill a contradicted slot, and symmetric `RELATED_TO` was the recorded
   skip ground for three round-3 slots.
3. **Seeded draw over the survivors, sorted by `triple_key`.** The seed is the
   gold file's own sha256, so the draw is a pure function of committed state and
   reproduces from the pre-round file alone.

Nothing here reads a verdict distribution, a slice failure rate, a judge result
or the quarantined per-pair census.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

# LABELLING.md's reversal-exclusivity table, exclusive rows only. A reversal of
# one of these is contradicted *by the relation's meaning*; every other relation
# yields `unsupported` and cannot fill this slot.
EXCLUSIVE_REVERSAL_RELATIONS = frozenset({
    "HAS_PART", "IMPLEMENTS", "EXTENDS", "REPLACES", "IMPROVES_ON",
    "IS_A", "DEPLOYED_ON", "AUTHORED_BY", "HAPPENED_ON",
})


def derive_seed(gold_path: Path) -> int:
    """The gold file's own sha256, truncated — `lattice_retirement`'s convention.

    Deliberately the same derivation, so a reader who has checked one draw has
    checked the other's seeding too.
    """
    digest = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    return int(digest[:8], 16)


def eligible_premises(gold: dict, harvest: list[dict]) -> list[dict]:
    """Harvest facts that can carry a *new* `direction`/`contradicted` pair."""
    live = [p for p in gold["pairs"] if "retired" not in p]
    occupied = {
        p.get("fact_key", {}).get("triple_key")
        for p in live
        if "direction" in (p.get("slice_tags") or [])
    }
    return sorted(
        (
            fact for fact in harvest
            if fact["triple_key"] not in occupied
            and fact["rel_type"] in EXCLUSIVE_REVERSAL_RELATIONS
        ),
        key=lambda f: f["triple_key"],
    )


def draw_premises(gold_path: Path, harvest_path: Path, count: int) -> dict:
    gold = json.loads(gold_path.read_text())
    harvest = json.loads(harvest_path.read_text())["facts"]
    pool = eligible_premises(gold, harvest)
    seed = derive_seed(gold_path)
    drawn = random.Random(seed).sample(pool, count)
    return {
        "seed": seed,
        "pool_size": len(pool),
        "drawn": [
            {
                "triple_key": f["triple_key"],
                "fact": f["fact"],
                "subject_name": f["subject_name"],
                "rel_type": f["rel_type"],
                "object_name": f["object_name"],
                "project": f["project"],
            }
            for f in drawn
        ],
    }


if __name__ == "__main__":
    import argparse

    here = Path(__file__).resolve().parent / "entailment"
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default=str(here / "gold.json"))
    parser.add_argument("--harvest", default=str(here / "l2_harvest.json"))
    parser.add_argument("--n", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(
        draw_premises(Path(args.gold), Path(args.harvest), args.n), indent=2
    ))
