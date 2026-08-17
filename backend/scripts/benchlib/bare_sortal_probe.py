"""Rule-discovery probe over the gold's bare-sortal existentials (T2.124).

**This is not a resample and certifies nothing.** The Layer-3 resample draws a
seeded stratified sample and its verdict gates the gold; this walks one
*construction* across the whole live gold to tell the owner where an
instrument's boundary actually falls, so a rule-then-pairs ruling rests on the
population rather than on whichever few pairs a draw happened to sample.

The gap it measures: LABELLING.md's Frame rule distinguishes a **universal
discourse frame** ("the estate" -- vacuous, entailed) from a **proper-subset
frame** (a named deployment -- asserted content). The gold's commonest
existential shape is neither: a **bare sortal** with no frame phrase at all
("at least one component"). Twenty-nine live pairs rest on a reading of that
shape which the rulebook never states, and the 2026-08-16 resample sat on
exactly three of them.

Deliberately identical to the resample where it can be, so the two are
comparable rather than merely adjacent: same ``SYSTEM``, same
``build_prompt``, same ``rulebook_excerpt``, same per-pair independence (one
request each, no shared conversation), same non-Claude refusal. What differs is
the population and that nothing here is scored against a bar or written into
``gold.json``.

Both models this probe is meant for have already sat this gold, so running it
adds **no** further resample-circularity cost -- which is the whole reason it is
cheap enough to prefer over ruling from three samples.

Run from ``backend/``:

    DEEPSEEK_API_KEY=... python scripts/benchlib/bare_sortal_probe.py \\
        --base-url https://api.deepseek.com/v1 --model deepseek-v4-pro \\
        --api-key-env DEEPSEEK_API_KEY
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

from benchlib import entailment_gold, resample_sheet  # noqa: E402
from benchlib.resample_llm import (  # noqa: E402
    assert_not_claude_family, label_one,
)

OUT_DIR = HERE / "entailment" / "probe_runs"

#: An existential generalisation, however phrased.
EXISTENTIAL = re.compile(r"at least one|one of the")

#: Phrases the Frame rule already rules on as universal discourse frames. A
#: hypothesis carrying one is NOT a bare sortal -- the rule covers it, so it is
#: outside this probe's question.
UNIVERSAL_FRAMES = (
    "of the estate", "in the estate", "in the stack",
    "in the environment", "of the environment", "somewhere in",
)

#: Sortals a relation's own semantics supply, per relation. `DEPLOYED_ON`
#: establishes host/guest roles and `DEPENDS_ON` establishes a dependency, so a
#: hypothesis reaching for those words is asking the premise for something the
#: premise's relation already asserts. This is the hypothesis the probe tests,
#: not a rule the gold states -- it is written here so the classification is
#: legible and falsifiable rather than implicit in the output.
RELATION_EARNED_SORTALS = {
    "DEPLOYED_ON": ("host", "deployed"),
    "DEPENDS_ON": ("dependency", "dependent"),
}


def classify(pair: dict) -> str | None:
    """``earned`` / ``unearned`` for a bare-sortal pair; ``None`` otherwise."""
    hypothesis = pair["hypothesis"].lower()
    if not EXISTENTIAL.search(hypothesis):
        return None
    if any(frame in hypothesis for frame in UNIVERSAL_FRAMES):
        return None
    rel = (pair.get("fact_key") or {}).get("rel_type", "")
    earned = RELATION_EARNED_SORTALS.get(rel, ())
    return "earned" if any(word in hypothesis for word in earned) else "unearned"


def population(gold_path: Path | str | None = None) -> list[dict]:
    doc = entailment_gold.load_entailment_gold(
        gold_path or entailment_gold.GOLD_PATH
    )
    rows = []
    for pair in doc["pairs"]:
        if pair.get("retired"):
            continue
        kind = classify(pair)
        if kind is None:
            continue
        rows.append({
            "id": pair["id"], "premise": pair["premise"],
            "hypothesis": pair["hypothesis"], "sortal": kind,
            # Recorded for the report, never sent to the model.
            "gold_verdict": pair["verdict"], "slice": pair["slice_tags"][0],
        })
    return rows


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key-env", required=True)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260808)
    ap.add_argument("--reasoning-effort", default="high")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    assert_not_claude_family(args.model)
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")

    rows = population()
    print(f"bare-sortal population: {len(rows)} "
          f"({sum(r['sortal'] == 'earned' for r in rows)} earned, "
          f"{sum(r['sortal'] == 'unearned' for r in rows)} unearned)")

    rulebook = resample_sheet.rulebook_excerpt(resample_sheet.LABELLING_PATH)
    params = {"seed": args.seed, "reasoning_effort": args.reasoning_effort}
    sem = asyncio.Semaphore(args.concurrency)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        tasks = [
            # The blind row only: the model never sees gold_verdict or slice.
            label_one(client, args.base_url, args.model, api_key, rulebook,
                      {"id": r["id"], "premise": r["premise"],
                       "hypothesis": r["hypothesis"]},
                      sem, params)
            for r in rows
        ]
        for n, coro in enumerate(asyncio.as_completed(tasks), start=1):
            pid, verdict = await coro
            out[pid] = verdict
            if n % 10 == 0 or n == len(tasks):
                print(f"  labelled {n}/{len(tasks)}")

    by_kind: dict[str, dict[str, int]] = {}
    for row in rows:
        got = out[row["id"]]["verdict"]
        bucket = by_kind.setdefault(row["sortal"], {})
        key = "agrees" if got == row["gold_verdict"] else f"reads {got}"
        bucket[key] = bucket.get(key, 0) + 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = args.model.replace(".", "-").replace("/", "-")
    path = OUT_DIR / f"{args.date}-bare-sortal-{slug}.json"
    path.write_text(json.dumps({
        "_notes": ("Rule-discovery probe, NOT a resample. Certifies nothing, "
                   "gated by nothing, written into no gold."),
        "model": args.model, "date": args.date, "params": params,
        "population": rows, "verdicts": out, "summary_by_sortal": by_kind,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nraw: {path}")
    for kind in sorted(by_kind):
        print(f"  {kind:9s} {by_kind[kind]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
