"""The committed draw for a lattice retirement (LABELLING.md, ratified 2026-08-10).

**This module exists to have no free parameters, and that is its whole
contract.** A lattice retirement removes *correctly labelled* pairs to hold a
census constant while a bar's lattice is fixed. The rule's clause 3 requires the
selection procedure to land in a commit *before* it executes, because pinning a
seed alone does not close the aiming channel: the same seed under a different
algorithm — a different sort order, strata in a different order, ``rng.sample``
versus shuffle-and-slice — yields a different retired set, and the executor of
a lattice round is by construction someone who has read the gate's failure
attribution. Choosing among defensible algorithms *after* seeing the seed is
what this file makes unavailable.

Every decision that could otherwise be made at execution time is therefore made
here, in the open:

- the **seed** is ``resample_draw.derive_seed`` over the pre-retirement file, so
  it is a function of content nobody in the round chose;
- the **eligible pool** excludes retired pairs, the protected T2.25 core, and
  every verdict class but the one being reshaped;
- each **stratum's pool is sorted by ``id``** before sampling, so dict or file
  ordering cannot move the result;
- **strata are processed in a stated fixed order** (alphabetical by slice name),
  not in the order a Counter happened to yield;
- the quota is **largest-remainder over the eligible pool's own slice
  distribution**, ties broken by slice name;
- selection is ``rng.sample`` from a single ``random.Random(seed)`` advanced
  once per stratum in that order.

Nothing here reads a label, a rationale, a premise, a hypothesis or any judge
output. The only pair property that enters is ``slice_tags``, and only as the
stratification the rule's clause 4 permits by name.

Reproduction is one command, and the report must carry it::

    cd backend && PYTHONPATH=.:scripts python -m benchlib.lattice_retirement \
        --verdict contradicted --n 15
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

from benchlib import entailment_gold, resample_draw

# Rule B keeps the 41 T2.25 pairs live; clause 2 forbids retiring them.
PROTECTED_CORE_LAST_ID = "eg-0041"

# Clause 1: only the contacted population may be retired. The boundary is Rule
# B's own, imported rather than restated so the two cannot drift.
from benchlib.judge_qualification import RULE_B_FIRST_ID  # noqa: E402


@dataclass(frozen=True)
class Draw:
    """A retirement draw, fully determined by (gold file, verdict, n)."""

    seed: int
    quota: dict[str, int]
    eligible: dict[str, list[str]]
    retired_ids: list[str]

    def as_report(self) -> dict:
        return {
            "seed": self.seed,
            "quota": self.quota,
            "eligible_counts": {k: len(v) for k, v in sorted(self.eligible.items())},
            "retired_ids": self.retired_ids,
        }


def eligible_pool(pairs: list[dict], verdict: str) -> dict[str, list[str]]:
    """Ids eligible for retirement, keyed by slice, each list ``id``-sorted.

    A pair qualifies when it is live, carries the verdict being reshaped, sits
    in the contacted population (clause 1) and is outside the protected core
    (clause 2). A pair carrying several slice tags would appear under each; the
    gold's contradicted pairs carry exactly one, and ``draw`` asserts that
    rather than assuming it.
    """
    pool: dict[str, list[str]] = {}
    for pair in pairs:
        if pair.get("retired") or pair["verdict"] != verdict:
            continue
        if pair["id"] >= RULE_B_FIRST_ID or pair["id"] <= PROTECTED_CORE_LAST_ID:
            continue
        for tag in pair["slice_tags"]:
            pool.setdefault(tag, []).append(pair["id"])
    return {slice_name: sorted(ids) for slice_name, ids in pool.items()}


def largest_remainder(counts: dict[str, int], total: int) -> dict[str, int]:
    """Clause 5's allocation, ties broken by slice name so it is total.

    Shared with the authoring quota, because the round's whole composition
    guarantee is that what leaves and what arrives are allocated the same way.
    """
    population = sum(counts.values())
    if population == 0:
        raise ValueError("empty pool")
    exact = {k: total * v / population for k, v in counts.items()}
    allocation = {k: int(v) for k, v in exact.items()}
    order = sorted(counts, key=lambda k: (-(exact[k] - allocation[k]), k))
    index = 0
    while sum(allocation.values()) < total:
        allocation[order[index % len(order)]] += 1
        index += 1
    return allocation


def draw(gold_path: Path, verdict: str, n: int) -> Draw:
    """The whole procedure. Deterministic in (file bytes, verdict, n)."""
    document = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    pairs = document["pairs"]
    for pair in pairs:
        if pair["verdict"] == verdict and len(pair["slice_tags"]) != 1:
            raise ValueError(
                f"{pair['id']} carries {len(pair['slice_tags'])} slice tags; the "
                "stratification assumes exactly one and must be revisited before "
                "a multi-tag pair can be drawn"
            )

    seed = resample_draw.derive_seed(Path(gold_path).read_bytes())
    pool = eligible_pool(pairs, verdict)
    quota = largest_remainder({k: len(v) for k, v in pool.items()}, n)

    rng = random.Random(seed)
    retired: list[str] = []
    for slice_name in sorted(quota):  # fixed order, not Counter order
        take = quota[slice_name]
        if take:
            retired.extend(rng.sample(pool[slice_name], take))
    return Draw(seed=seed, quota=quota, eligible=pool, retired_ids=sorted(retired))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdict", required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument(
        "--gold", default=str(entailment_gold.ENTAILMENT_DIR / "gold.json")
    )
    args = parser.parse_args()
    print(json.dumps(draw(Path(args.gold), args.verdict, args.n).as_report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
