"""The seeded stratified resample draw and its blind export (T2.54 Layer 3).

`LABELLING.md`'s Layer 3 requires, after the set is stable, a **seeded blind
resample: n = 93, bar <= 1 disagreement**, stratified by gold verdict class —
"full census of `contradicted`, then `unsupported`, remainder `entailed`
proportionally". This module draws that sample and emits the blind export. It
**labels nothing** and it decides nothing: the resample's whole value is that
it is the first accuracy measurement made from outside the family that
labelled the set, so producing the labels here would defeat it.

**The seed is derived, never chosen.** It is the first 8 hex digits of the
gold file's own SHA-256. A seed someone picks is a seed someone can re-pick
until the sample looks kind, and this is the one measurement in the pipeline
that nothing downstream can second-guess. Deriving it means the draw is
reproducible by anyone holding the same gold, and unchooseable by everyone.

**The manifest deliberately records no ids.** Writing `{id: stratum}` would
publish each drawn pair's verdict class — `contradicted` most of all, which is
the stratum under review — and a labeller who read it would be neither blind
nor independent. Counts are enough to audit the draw, and the id set is
recoverable exactly by re-running against the same gold, which is the same
guarantee with none of the leak.

**The export is shuffled for the same reason.** Emitting strata in order would
hand a labeller the class boundaries even without ids: everything before the
first boundary is `contradicted`, and the six host-swap pairs the rulebook fork
turned on sit inside it.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from benchlib import entailment_gold
from benchlib.entailment_adjudication import BLIND_FIELDS

# Ratified 2026-07-31 (LABELLING.md Layer 3); certifies label error < 5% at
# ~95% confidence. Duplicated from judge_qualification deliberately: that
# module is the *lock* and this one is the *draw*, and a draw that silently
# tracked a loosened lock would produce a sample too small to certify what the
# lock claims. The test suite asserts they agree.
RESAMPLE_N = 93

# Order matters: the census stratum first, then the proportional remainder.
CENSUS_VERDICT = "contradicted"
PROPORTIONAL_VERDICTS = ("unsupported", "entailed")

ENTAILMENT_DIR = entailment_gold.ENTAILMENT_DIR
DEFAULT_EXPORT_PATH = ENTAILMENT_DIR / "resample_blind.json"
DEFAULT_MANIFEST_PATH = ENTAILMENT_DIR / "resample_manifest.json"


def derive_seed(gold_bytes: bytes) -> int:
    """The draw's seed, from the gold's own hash. See the module docstring."""
    return int(hashlib.sha256(gold_bytes).hexdigest()[:8], 16)


def _proportional_quota(remaining: int, sizes: dict[str, int]) -> dict[str, int]:
    """Split ``remaining`` across strata in proportion to their live sizes.

    Largest-remainder rather than naive rounding: rounding each share down
    loses up to one slot per stratum, which at n = 93 is the difference between
    the ratified sample size and a quietly smaller one.
    """
    total = sum(sizes.values())
    exact = {v: remaining * sizes[v] / total for v in sizes}
    floors = {v: int(exact[v]) for v in sizes}
    short = remaining - sum(floors.values())
    for verdict in sorted(sizes, key=lambda v: exact[v] - floors[v], reverse=True):
        if short <= 0:
            break
        floors[verdict] += 1
        short -= 1
    return floors


def draw(gold_doc: dict, gold_bytes: bytes, n: int = RESAMPLE_N) -> dict:
    """The drawn sample: shuffled blind rows plus a leak-free manifest."""
    live = [p for p in gold_doc["pairs"] if not p.get("retired")]
    by_verdict: dict[str, list[dict]] = {}
    for pair in live:
        by_verdict.setdefault(pair["verdict"], []).append(pair)

    census = sorted(by_verdict.get(CENSUS_VERDICT, []), key=lambda p: p["id"])
    if len(census) > n:
        raise ValueError(
            f"the {CENSUS_VERDICT!r} census alone is {len(census)} pairs, above "
            f"n = {n}: the stratification in LABELLING.md cannot be honoured "
            "and the protocol needs re-ratifying before this sample is drawn"
        )

    sizes = {
        v: len(by_verdict.get(v, []))
        for v in PROPORTIONAL_VERDICTS
        if by_verdict.get(v)
    }
    quota = _proportional_quota(n - len(census), sizes)

    rng = random.Random(derive_seed(gold_bytes))
    drawn = list(census)
    for verdict in PROPORTIONAL_VERDICTS:
        pool = sorted(by_verdict.get(verdict, []), key=lambda p: p["id"])
        take = quota.get(verdict, 0)
        if take > len(pool):
            raise ValueError(
                f"stratum {verdict!r} has {len(pool)} live pairs, short of its "
                f"quota {take}"
            )
        drawn.extend(rng.sample(pool, take))

    rng.shuffle(drawn)
    rows = [{field: pair[field] for field in BLIND_FIELDS} for pair in drawn]

    manifest = {
        "protocol": "LABELLING.md Layer 3 seeded blind resample",
        "n": len(drawn),
        "bar_max_disagreements": 1,
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "seed": derive_seed(gold_bytes),
        "seed_derivation": "int(sha256(gold.json)[:8], 16)",
        "strata": {
            CENSUS_VERDICT: {"mode": "full census", "drawn": len(census),
                             "live": len(by_verdict.get(CENSUS_VERDICT, []))},
            **{
                v: {"mode": "proportional", "drawn": quota.get(v, 0),
                    "live": sizes.get(v, 0)}
                for v in PROPORTIONAL_VERDICTS
            },
        },
        # No ids, and no id->stratum map: publishing either would tell a
        # labeller each pair's verdict class. Re-run this module against the
        # same gold to recover the exact set.
        "ids_recorded": False,
        "labels_recorded": False,
    }
    return {"rows": rows, "manifest": manifest}


def write(export_path: Path | str = DEFAULT_EXPORT_PATH,
          manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
          gold_path: Path | str = entailment_gold.GOLD_PATH) -> dict:
    gold_bytes = Path(gold_path).read_bytes()
    result = draw(entailment_gold.load_entailment_gold(gold_path), gold_bytes)
    Path(export_path).write_text(
        json.dumps(result["rows"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(manifest_path).write_text(
        json.dumps(result["manifest"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result["manifest"]


if __name__ == "__main__":  # pragma: no cover
    written = write()
    print(json.dumps(written, indent=2))
