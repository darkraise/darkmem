"""The round-5 sampling frame: the ratified rule, plus R5's row-level gate.

Rules 1 and 2 are **imported from** ``round4_frame``, not restated. They are the
same sitting-1-ratified derivation, and two copies of one ratified rule is the
drift this repo fails builds over — the diff between the rounds should be
exactly the amendment, so a reviewer can read the amendment by reading this
file.

**What R5 adds** (design and re-ratification requirements:
``docs/superpowers/plans/2026-08-14-t2.124-round5-frame-fix.md``; rule text and
the rule-3 amendment ratified by the owner 2026-08-14 through sitting 1's
channel):

Round 4's rule 3 gated feasibility on premise-*uses*
(``ceil(ceil(ceil(T/2)/cap) * 5/4)``), which is blind to distinctness. Step 9
then measured what that misses: 8 unanimous duplicate propositions, every one
on a premise the assignment had handed two entailed slots. So R5 adds a second,
**row-level** constraint:

    F >= ceil(E_manifest * 5/4)

where ``E_manifest`` is the derived matrix's entailed cells summed over the
slices that draw manifest premises — today every entailed-bearing slice except
``temporal``, whose premises are hand-authored because ``fact_lift`` renders no
validity window.

**Order matters and is the one structural difference.** Round 4 checks capacity
*before* deriving cells, because its gate depends only on T. ``E_manifest`` is a
property of the derived matrix, so this script must **derive first and gate
second**. Both gates can only *stop* a round: each is monotonically harder as T
grows, so neither can push T upward off the rule's minimum, which is what keeps
the plan's B3 argument (the rule emits its minimum T for every harvest the round
survives) true under the amendment.

**Inert until round 5 has inputs.** The harvest and exclusion list this reads
are round-5 chartering artifacts that do not exist yet, so ``main`` refuses
rather than inventing them, and the emitted matrix takes its own sitting-2-style
bounded ratification as a **new** file — never an edit of the ratified
``round4_frame.json``.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BENCHLIB_PARENT = str(Path(__file__).resolve().parent.parent)
if BENCHLIB_PARENT not in sys.path:
    sys.path.insert(0, BENCHLIB_PARENT)

from benchlib import round4_frame as r4  # noqa: E402
from benchlib.entailment_assignment import entailed_determined_slices  # noqa: E402
from benchlib.entailment_gold import ENTAILMENT_DIR, SLICE_VERDICTS  # noqa: E402

#: Round 5's own chartering artifacts. Neither exists until the round opens.
ROUND5_FRAME_PATH = ENTAILMENT_DIR / "round5_frame.json"
ROUND5_HARVEST_PATH = ENTAILMENT_DIR / "round5_l2_harvest.json"
ROUND5_EXCLUDED_KEYS_PATH = ENTAILMENT_DIR / "round5_excluded_triple_keys.json"

#: The archived round-4 gold supplies round 5's verdict splits, exactly as the
#: archived v1 file supplied round 4's. Set when the round-4 gold is archived.
ROUND4_ARCHIVE_PATH = ENTAILMENT_DIR / "retired" / "gold-round4.json"


def manifest_drawing_slices() -> frozenset[str]:
    """Slices whose premises come from the harvest manifest.

    Derived, never hand-listed: a slice draws from the manifest unless the
    assignment hand-authors it. ``temporal`` is that exception and the reason is
    in `entailment_assignment`'s own header — `fact_lift` renders no validity
    window, so no manifest fact can carry a temporal premise.
    """
    return frozenset(SLICE_VERDICTS) - frozenset({"temporal"})


def manifest_entailed(cells: dict[str, dict[str, int]]) -> int:
    """`E_manifest`: entailed cells over manifest-drawing slices.

    The quantity R5's constraint is stated in. Counted over the *derived*
    matrix rather than over T, which is why this script gates after deriving.
    """
    drawing = manifest_drawing_slices()
    return sum(
        counts.get("entailed", 0)
        for slice_name, counts in cells.items()
        if slice_name in drawing
    )


def entailed_row_floor(entailed_manifest: int) -> int:
    """R5's floor: one distinct premise per manifest entailed row, with the
    same 25% skip margin rule 3 already applies to uses."""
    return math.ceil(entailed_manifest * r4.SKIP_MARGIN)


def assert_amendment_is_expressible() -> None:
    """Fail loud if a manifest-drawing slice ever carries `entailed` in a mixed
    verdict set.

    R5 excludes a premise from funding two slots whose verdict is *determined*
    as entailed. A manifest slice offering `entailed` alongside other verdicts
    would make "this slot is entailed" a property of the authored pair rather
    than of the slice, and the exclusion could no longer be decided at
    assignment time. Today no such slice exists; `temporal` is mixed and is
    hand-authored, which is exactly why it is out of scope.
    """
    determined = entailed_determined_slices()
    offenders = sorted(
        s for s in manifest_drawing_slices()
        if "entailed" in SLICE_VERDICTS[s] and s not in determined
    )
    if offenders:
        raise ValueError(
            f"manifest-drawing slice(s) {offenders} carry 'entailed' in a mixed "
            "verdict set, so an entailed slot is no longer decidable from the "
            "slice at assignment time and R5's exclusion cannot be applied as "
            "ratified. The rule needs re-ratification before this round derives."
        )


def derive_frame(fresh_facts: int) -> dict:
    """Rules 1 + 2 as ratified, then rule 3's two gates: capacity, then rows."""
    assert_amendment_is_expressible()

    counted = r4.count_seed_splits(archive_path=ROUND4_ARCHIVE_PATH)
    splits = r4.T2_25_SPLITS_PINNED
    pinned_positive = {
        s: {v: n for v, n in cells.items() if n} for s, cells in splits.items()
    }
    if {s: dict(sorted(c.items())) for s, c in counted.items()} != {
        s: dict(sorted(c.items())) for s, c in pinned_positive.items()
    }:
        raise ValueError(
            "round-4 archive's counted verdict splits disagree with the "
            f"ratified pin: counted={counted!r}"
        )

    for total in r4._count(r4.T_MIN):
        slice_targets = r4.largest_remainder(r4.T2_25_PROPORTIONS, total)
        if any(slice_targets[s] < r4.T2_25_PROPORTIONS[s] for s in slice_targets):
            continue
        near_miss = sum(slice_targets[s] for s in r4.NEAR_MISS_SLICES)
        if near_miss * 2 <= total:
            continue

        capacity_floor = r4.fact_floor(total)
        if fresh_facts < capacity_floor:
            raise RuntimeError(
                f"STOP (capacity): fresh harvest yields {fresh_facts} facts "
                f"after the round-5 exclusion, below the use floor "
                f"{capacity_floor} at T={total}."
            )

        cells = {
            s: r4.largest_remainder(splits[s], slice_targets[s])
            for s in slice_targets
        }
        cells, moves = r4.minimal_adjustment(cells, splits)
        entailed, contradicted, unsupported = r4._totals(cells)

        # R5's gate, evaluated on the derived matrix.
        e_manifest = manifest_entailed(cells)
        row_floor = entailed_row_floor(e_manifest)
        if fresh_facts < row_floor:
            raise RuntimeError(
                f"STOP (R5 rows): the derived matrix needs {e_manifest} "
                f"manifest entailed rows, each on a distinct premise, so the "
                f"harvest must yield at least {row_floor} fresh facts with the "
                f"25% skip margin -- it yields {fresh_facts}. Round 4 would "
                "have passed this point and produced duplicate propositions "
                "instead; the owner hears it now, not at adjudication."
            )

        matrix = {
            s: {v: n for v, n in sorted(cells[s].items()) if n or v in splits[s]}
            for s in sorted(cells)
        }
        return {
            "_notes": (
                "Round-5 sampling frame. Rules 1-2 are round 4's, imported "
                "rather than restated; rule 3 gains R5's row-level floor "
                "(T2.124 step 9; rule ratified 2026-08-14 via sitting 1). "
                "Regenerate with scripts/benchlib/round5_frame.py --write; a "
                "hand edit fails the byte-comparison test. The emitted matrix "
                "awaits its own bounded ratification."
            ),
            "inputs": {
                "t2_25_proportions": dict(sorted(r4.T2_25_PROPORTIONS.items())),
                "t2_25_splits": {
                    s: dict(sorted(v.items())) for s, v in sorted(splits.items())
                },
                "verdict_split_seed": {
                    "path": str(ROUND4_ARCHIVE_PATH.relative_to(ENTAILMENT_DIR.parent)),
                    "retirement_flags": "ignored (post-judge information)",
                },
                "contradicted_target": r4.CONTRADICTED_TARGET,
                "entailed_lattice_modulus": r4.ENTAILED_LATTICE_MODULUS,
                "t_min": r4.T_MIN,
                "pairs_per_premise_cap": r4.PAIRS_PER_PREMISE_CAP,
            },
            "feasibility": {
                "fresh_facts_after_exclusion": fresh_facts,
                "fact_floor_at_t": capacity_floor,
                "manifest_entailed_rows": e_manifest,
                "entailed_row_floor": row_floor,
                "binding_gate": (
                    "rows" if row_floor >= capacity_floor else "capacity"
                ),
                "excluded_keys_path": "entailment/round5_excluded_triple_keys.json",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="emit round5_frame.json (refuses to overwrite)")
    args = parser.parse_args(argv)

    missing = [
        str(p) for p in (ROUND4_ARCHIVE_PATH, ROUND5_HARVEST_PATH,
                         ROUND5_EXCLUDED_KEYS_PATH)
        if not p.exists()
    ]
    if missing:
        print(
            "round 5 has not been chartered: missing "
            + ", ".join(missing)
            + "\nThe rule is ratified and this script is ready; its inputs are "
              "the round's own step 3 and step 4 artifacts.",
            file=sys.stderr,
        )
        return 2

    fresh = r4.fresh_fact_count(ROUND5_HARVEST_PATH, ROUND5_EXCLUDED_KEYS_PATH)
    frame = derive_frame(fresh)
    rendered = frame_json(frame)
    if args.write:
        if ROUND5_FRAME_PATH.exists():
            print(f"refusing to overwrite {ROUND5_FRAME_PATH}", file=sys.stderr)
            return 1
        ROUND5_FRAME_PATH.write_text(rendered, encoding="utf-8")
        print(f"wrote {ROUND5_FRAME_PATH}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
