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
3. **Capacity under the per-premise cap.** `l2_harvest.json`'s header fixes
   `pairs_per_premise_cap` at 4 and `test_no_premise_supports_more_than_four_live_pairs`
   enforces it, so a premise already carrying four live pairs cannot take a
   fifth. **The first version of this module omitted this filter and the draw it
   produced was infeasible on both slots** — caught by a blind author who
   checked the cap before writing, which is the firewall working in the
   direction nobody designs it for.

4. **Seeded draw over the survivors, sorted by `triple_key`.** The seed is the
   gold file's own sha256, so the draw is a pure function of committed state and
   reproduces from the pre-round file alone.

Nothing here reads a verdict distribution, a slice failure rate, a judge result
or the quarantined per-pair census.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
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


PAIRS_PER_PREMISE_CAP = 4


def eligible_premises(
    gold: dict, harvest: list[dict], *, retiring: frozenset[str] = frozenset()
) -> list[dict]:
    """Harvest facts that can carry a *new* `direction`/`contradicted` pair.

    ``retiring`` names ids leaving in this same round, so capacity they free is
    counted. Here it frees none — both retiring pairs sit on premises that
    already carry a live `direction` pair, which filter 1 excludes anyway — but
    computing it the other way round would make the module wrong for the next
    repair rather than merely lucky for this one.
    """
    live = [
        p for p in gold["pairs"]
        if "retired" not in p and p["id"] not in retiring
    ]
    occupied = {
        p.get("fact_key", {}).get("triple_key")
        for p in live
        if "direction" in (p.get("slice_tags") or [])
    }
    pairs_on = Counter(p["premise"] for p in live)
    return sorted(
        (
            fact for fact in harvest
            if fact["triple_key"] not in occupied
            and fact["rel_type"] in EXCLUSIVE_REVERSAL_RELATIONS
            and pairs_on[fact["fact"]] < PAIRS_PER_PREMISE_CAP
        ),
        key=lambda f: f["triple_key"],
    )


def draw_premises(
    gold_path: Path,
    harvest_path: Path,
    count: int,
    *,
    retiring: frozenset[str] = frozenset(),
) -> dict:
    gold = json.loads(gold_path.read_text())
    harvest = json.loads(harvest_path.read_text())["facts"]
    pool = eligible_premises(gold, harvest, retiring=retiring)
    seed = derive_seed(gold_path)
    if len(pool) < count:
        # Exhaustion is an outcome, not an error: LABELLING.md's skip mechanism
        # already answers it — the slot takes a hand-authored premise and only
        # the `l2-fact` count moves. Returning a short draw silently would let a
        # caller author against a capped premise and redden the floor at commit.
        return {
            "seed": seed,
            "pool_size": len(pool),
            "exhausted": True,
            "drawn": [],
        }
    drawn = random.Random(seed).sample(pool, count)
    return {
        "seed": seed,
        "pool_size": len(pool),
        "exhausted": False,
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
