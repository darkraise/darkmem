"""The round-4 sampling frame, derived — never chosen (T2.124, D5).

This module is the committed form of the derivation rule the owner ratified
at sitting 1 (gate-ledger.md, "T2.124 frame — owner ratification, sitting
1", 2026-08-13): every number in the emitted ``entailment/round4_frame.json``
is a function of pre-judge inputs alone, with all tie-breaks alphabetical,
so no party who has read any judge's failure profile holds a free parameter
anywhere in the sizing. The emitted matrix takes its own bounded
ratification at the plan's step 6 (sitting 2); if this script and the plan's
worked table ever disagree, the script wins and the disagreement is a defect
to locate before authoring.

Pinned inputs, all pre-judge:

- T2.25's frozen slice proportions (2026-07-30).
- T2.25's per-slice verdict splits, counted mechanically at run time from
  the archived v1 seed -- ``entailment/retired/gold-4975c5cc.json``, pairs
  ``eg-0001``..``eg-0041``, retirement flags ignored (retirement is
  post-judge information) -- and cross-checked against the counts recorded
  in the ratified rule, so archive corruption fails loudly instead of
  silently moving the frame.
- ``SLICE_VERDICTS`` (the closed slice/verdict lawfulness table).
- The fresh harvest yield, which enters rule 3 **only as a feasibility
  gate**: it can stop the round, never move T.

The rule (ratified, implemented verbatim):

1. Slice targets: T2.25 proportions scaled to total T by largest remainder,
   ties alphabetical.
2. Verdict splits inside each mixed slice: T2.25's own split scaled by
   largest remainder (ties alphabetical by verdict name), then the minimal
   adjustment -- fewest moved slots subject to slice totals fixed, every
   cell lawful under ``SLICE_VERDICTS``, total entailed on the 0.90 lattice
   (E ≡ 0 mod 10) and total contradicted = 80 -- with ties among
   equal-cost solutions resolved by the lexicographically smallest sorted
   move list (slice name, then verdict names), which is the alphabetical
   tie-break stated in the rule.
3. T is the smallest total >= 280 satisfying: every slice >= its T2.25
   count, near-miss slices a majority, and l2-fact capacity >= 50% of T
   from the fresh harvest at the pairs-per-premise cap with a 25% skip
   margin, drawing only facts outside the round-4 premise exclusion.

Run from backend/:
  python scripts/benchlib/round4_frame.py          # verify against committed
  python scripts/benchlib/round4_frame.py --write  # (re)emit the JSON
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from itertools import count as _count
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib.entailment_gold import (  # noqa: E402
    ENTAILMENT_DIR,
    HARVEST_PATH,
    RETIRED_GOLD_ARCHIVE_PATH,
    SLICE_VERDICTS,
    NEAR_MISS_SLICES,
)

FRAME_PATH = ENTAILMENT_DIR / "round4_frame.json"
EXCLUDED_KEYS_PATH = ENTAILMENT_DIR / "round4_excluded_triple_keys.json"

# T2.25's frozen slice proportions (LABELLING.md, frozen 2026-07-30).
T2_25_PROPORTIONS: dict[str, int] = {
    "verbatim": 4, "paraphrase": 6, "weakening": 5, "temporal": 6,
    "direction": 5, "overreach": 6, "value-swap": 5, "unrelated": 4,
}

# The verdict splits the archived seed must count to. Recorded in the
# ratified rule (sitting 1, item 1) and re-counted from the archive at every
# derivation; a disagreement is archive corruption or a mis-pin, and either
# stops the frame rather than moving it.
T2_25_SPLITS_PINNED: dict[str, dict[str, int]] = {
    "verbatim": {"entailed": 4},
    "paraphrase": {"entailed": 6},
    "weakening": {"entailed": 5},
    "temporal": {"contradicted": 2, "entailed": 2, "unsupported": 2},
    "direction": {"contradicted": 3, "unsupported": 2},
    "overreach": {"contradicted": 0, "unsupported": 6},
    "value-swap": {"contradicted": 5},
    "unrelated": {"unsupported": 4},
}
T2_25_SEED_LAST_ID = "eg-0041"

CONTRADICTED_TARGET = 80          # T2.110's ratified census size
ENTAILED_LATTICE_MODULUS = 10     # the 0.90 lattice: E ≡ 0 (mod 10)
T_MIN = 280                       # rule 3's minimum-total form
PAIRS_PER_PREMISE_CAP = 4
L2_FACT_FLOOR_SHARE = Fraction(1, 2)   # doc 17 §11's 50% floor
SKIP_MARGIN = Fraction(5, 4)           # rule 3's 25% skip margin

VERDICTS_ORDER = ("contradicted", "entailed", "unsupported")


def count_seed_splits(
    archive_path: str | Path = RETIRED_GOLD_ARCHIVE_PATH,
) -> dict[str, dict[str, int]]:
    """Count the T2.25 seed's per-slice verdict splits from the archive.

    Raw ``json.loads`` on purpose: the archive is an audit copy that
    predates the live harvest manifest, so the validating loader does not
    apply. Retirement flags are ignored -- retirement is post-judge
    information and the seed is read as it was authored.
    """
    doc = json.loads(Path(archive_path).read_text(encoding="utf-8"))
    splits: dict[str, dict[str, int]] = {s: {} for s in T2_25_PROPORTIONS}
    n = 0
    for pair in doc["pairs"]:
        if pair["id"] > T2_25_SEED_LAST_ID:
            continue
        n += 1
        cell = splits[pair["slice_tags"][0]]
        cell[pair["verdict"]] = cell.get(pair["verdict"], 0) + 1
    if n != sum(T2_25_PROPORTIONS.values()):
        raise ValueError(
            f"archived seed counts {n} pairs at ids <= {T2_25_SEED_LAST_ID}; "
            f"expected {sum(T2_25_PROPORTIONS.values())}"
        )
    return splits


def largest_remainder(weights: dict[str, int], total: int) -> dict[str, int]:
    """Largest-remainder apportionment, remainder ties broken alphabetically."""
    denom = sum(weights.values())
    quotas = {k: Fraction(v * total, denom) for k, v in weights.items()}
    floors = {k: int(q) for k, q in quotas.items()}
    short = total - sum(floors.values())
    order = sorted(quotas, key=lambda k: (-(quotas[k] - floors[k]), k))
    for k in order[:short]:
        floors[k] += 1
    return floors


def _totals(cells: dict[str, dict[str, int]]) -> tuple[int, int, int]:
    e = sum(c.get("entailed", 0) for c in cells.values())
    c_ = sum(c.get("contradicted", 0) for c in cells.values())
    u = sum(c.get("unsupported", 0) for c in cells.values())
    return e, c_, u


def minimal_adjustment(
    cells: dict[str, dict[str, int]], splits: dict[str, dict[str, int]],
) -> tuple[dict[str, dict[str, int]], list[tuple[str, str, str]]]:
    """Fewest single-slot moves inside the mixed slices reaching E ≡ 0
    (mod 10) and C = 80, cells lawful, slice totals fixed.

    Exhaustive breadth-first search over move counts, so "minimal" is a
    computed property rather than a derivation someone believed; among
    equal-cost solutions the lexicographically smallest sorted move list
    wins -- the rule's alphabetical tie-break, which carries zero content.
    """
    mixed = sorted(s for s, split in splits.items() if len(split) > 1)

    def freeze(state):
        return json.dumps(state, sort_keys=True)

    start = {s: dict(cells[s]) for s in cells}
    best: int | None = None
    solutions: list[tuple[list[tuple[str, str, str]], dict]] = []
    frontier: list[tuple[int, list, dict]] = [(0, [], start)]
    seen = {freeze(start): 0}
    while frontier:
        nxt: list[tuple[int, list, dict]] = []
        for cost, moves, state in frontier:
            if best is not None and cost > best:
                continue
            e, c_, _u = _totals(state)
            if c_ == CONTRADICTED_TARGET and e % ENTAILED_LATTICE_MODULUS == 0:
                if best is None or cost < best:
                    best, solutions = cost, []
                if cost == best:
                    solutions.append((sorted(moves), state))
                continue
            for s in mixed:
                lawful = SLICE_VERDICTS[s]
                for a in VERDICTS_ORDER:
                    if a not in lawful or state[s].get(a, 0) <= 0:
                        continue
                    for b in sorted(lawful):
                        if b == a:
                            continue
                        new = {k: dict(v) for k, v in state.items()}
                        new[s][a] -= 1
                        new[s][b] = new[s].get(b, 0) + 1
                        key = freeze(new)
                        if key in seen and seen[key] <= cost + 1:
                            continue
                        seen[key] = cost + 1
                        nxt.append((cost + 1, moves + [(s, a, b)], new))
        frontier = nxt
        if best is not None and (not frontier or min(f[0] for f in frontier) > best):
            break
    if not solutions:
        raise RuntimeError("no adjustment reaches the ratified constraints")
    solutions.sort(key=lambda pair: pair[0])
    moves, state = solutions[0]
    return state, moves


def fresh_fact_count(
    harvest_path: str | Path = HARVEST_PATH,
    excluded_path: str | Path = EXCLUDED_KEYS_PATH,
) -> int:
    manifest = json.loads(Path(harvest_path).read_text(encoding="utf-8"))
    excluded = set(
        json.loads(Path(excluded_path).read_text(encoding="utf-8"))["triple_keys"]
    )
    return len({r["triple_key"] for r in manifest["facts"]} - excluded)


def fact_floor(total: int) -> int:
    """Rule 3's capacity gate: 50% of T anchored, at the cap, with the 25%
    skip margin. ``ceil(ceil(ceil(T/2) / cap) * 5/4)``."""
    anchored = math.ceil(total * L2_FACT_FLOOR_SHARE)
    base = math.ceil(anchored / PAIRS_PER_PREMISE_CAP)
    return math.ceil(base * SKIP_MARGIN)


def derive_frame(fresh_facts: int) -> dict:
    """The whole derivation: rule 3's minimum-total loop over rules 1 + 2."""
    # A count cannot produce a zero cell, so the pin's explicit zeros
    # (overreach's contradicted, T2.25's own 0/6 split) are compared away
    # here and kept in the pin as scaling weights.
    counted = count_seed_splits()
    pinned_positive = {
        s: {v: n for v, n in cells.items() if n}
        for s, cells in T2_25_SPLITS_PINNED.items()
    }
    if {s: dict(sorted(c.items())) for s, c in counted.items()} != {
        s: dict(sorted(c.items())) for s, c in pinned_positive.items()
    }:
        raise ValueError(
            "archived seed's counted verdict splits disagree with the "
            f"ratified pin: counted={counted!r}"
        )
    splits = T2_25_SPLITS_PINNED

    for total in _count(T_MIN):
        slice_targets = largest_remainder(T2_25_PROPORTIONS, total)
        if any(slice_targets[s] < T2_25_PROPORTIONS[s] for s in slice_targets):
            continue
        near_miss = sum(slice_targets[s] for s in NEAR_MISS_SLICES)
        if near_miss * 2 <= total:
            continue
        floor = fact_floor(total)
        if fresh_facts < floor:
            raise RuntimeError(
                f"STOP: fresh harvest yields {fresh_facts} facts after the "
                f"round-4 exclusion, below the floor {floor} at T={total} -- "
                "the frame's l2 capacity constraint is infeasible at the "
                "rule's minimum T; the owner hears this now, not at "
                "eligibility time"
            )
        cells = {
            s: largest_remainder(splits[s], slice_targets[s])
            for s in slice_targets
        }
        cells, moves = minimal_adjustment(cells, splits)
        entailed, contradicted, unsupported = _totals(cells)
        matrix = {
            s: {v: n for v, n in sorted(cells[s].items()) if n or v in splits[s]}
            for s in sorted(cells)
        }
        return {
            "_notes": (
                "Round-4 sampling frame, derived by the committed rule from "
                "pre-judge inputs alone (T2.124 D5; ratified at sitting 1, "
                "emitted matrix ratified at sitting 2). Regenerate with "
                "scripts/benchlib/round4_frame.py --write; a hand edit "
                "fails the byte-comparison test."
            ),
            "inputs": {
                "t2_25_proportions": dict(sorted(T2_25_PROPORTIONS.items())),
                "t2_25_splits": {
                    s: dict(sorted(v.items()))
                    for s, v in sorted(T2_25_SPLITS_PINNED.items())
                },
                "t2_25_seed": {
                    "path": "entailment/retired/gold-4975c5cc.json",
                    "id_range": ["eg-0001", T2_25_SEED_LAST_ID],
                    "retirement_flags": "ignored (post-judge information)",
                },
                "contradicted_target": CONTRADICTED_TARGET,
                "entailed_lattice_modulus": ENTAILED_LATTICE_MODULUS,
                "t_min": T_MIN,
                "pairs_per_premise_cap": PAIRS_PER_PREMISE_CAP,
            },
            "feasibility": {
                "fresh_facts_after_exclusion": fresh_facts,
                "fact_floor_at_t": fact_floor(total),
                "excluded_keys_path": "entailment/round4_excluded_triple_keys.json",
            },
            "total": total,
            "slice_targets": dict(sorted(slice_targets.items())),
            "matrix": matrix,
            "census": {
                "contradicted": contradicted,
                "entailed": entailed,
                "unsupported": unsupported,
            },
            "adjustment_moves": [list(m) for m in moves],
        }
    raise AssertionError("unreachable")


def frame_json(frame: dict) -> str:
    return json.dumps(frame, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def assert_frame_checks(frame: dict) -> None:
    """The lattice and shape properties sitting 2 verifies mechanically.

    Asserted here at emit time and re-asserted by test from the committed
    file, so a later hand edit that breaks one fails the floor. The
    direction slice's contradicted/unsupported split is realised at
    authoring time by drawing relations from LABELLING.md's
    reversal-exclusivity classes per quota -- a property of the finished
    gold that step 8 reconciles, not of this file.
    """
    census = frame["census"]
    from benchlib.judge_qualification import MIN_GOLD_PAIRS, RESAMPLE_N

    assert census["entailed"] % ENTAILED_LATTICE_MODULUS == 0
    assert census["contradicted"] == CONTRADICTED_TARGET
    assert census["contradicted"] % 20 == 0
    assert census["contradicted"] <= RESAMPLE_N
    assert frame["total"] >= MIN_GOLD_PAIRS
    assert frame["total"] == sum(frame["slice_targets"].values())
    assert frame["total"] == sum(census.values())
    for slice_name, cells in frame["matrix"].items():
        assert sum(cells.values()) == frame["slice_targets"][slice_name]
        for verdict, n in cells.items():
            assert n >= 0
            if n:
                assert verdict in SLICE_VERDICTS[slice_name], (slice_name, verdict)


def absorb_shortfall(frame: dict, shortfall: int) -> dict[str, dict[str, int]]:
    """Clause 5b's absorbing rule, as code: where an authoring shortfall
    lands.

    Reference distribution: the ratified frame matrix's own cells.
    Population: the fresh gold's live pairs. A shortfall of ``n`` slots
    re-derives every cell by largest remainder over the frame's cell
    weights at total ``T - n``, ties alphabetical by (slice, verdict) --
    fewest assumptions, zero discretion, and the deviation is the diff
    against the frame. Whether the absorbed census still satisfies the
    lattice constraints is step 8's check: if it does not, the round stops
    for owner adjudication (clause 5a/5c) rather than absorbing silently.
    """
    if shortfall < 0:
        raise ValueError("shortfall must be non-negative")
    weights = {
        f"{slice_name}|{verdict}": n
        for slice_name, cells in frame["matrix"].items()
        for verdict, n in cells.items()
        if n
    }
    scaled = largest_remainder(weights, frame["total"] - shortfall)
    absorbed: dict[str, dict[str, int]] = {}
    for key, n in scaled.items():
        slice_name, verdict = key.split("|")
        absorbed.setdefault(slice_name, {})[verdict] = n
    return {s: dict(sorted(v.items())) for s, v in sorted(absorbed.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write", action="store_true",
        help="write entailment/round4_frame.json (default: verify only)",
    )
    args = parser.parse_args(argv)

    frame = derive_frame(fresh_fact_count())
    assert_frame_checks(frame)
    rendered = frame_json(frame)
    if args.write:
        FRAME_PATH.write_text(rendered, encoding="utf-8")
        print(f"frame written: {FRAME_PATH}")
    else:
        committed = FRAME_PATH.read_text(encoding="utf-8")
        if committed != rendered:
            print("committed frame does NOT regenerate from the rule", file=sys.stderr)
            return 1
        print("committed frame regenerates byte-identically")
    print(f"T={frame['total']} census={frame['census']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
