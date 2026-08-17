"""T2.124 step 9 — the independence and freshness pass.

Runs the plan's step-9 checks over the authored round-4 census and prints
them, machine-readable, for a party outside the authoring lineage to
adjudicate. **It reports; it does not judge.** Nothing here decides whether a
finding loops back to step 7 — that verdict is the reviewer's, and this script
exists so the reviewer argues with numbers they can regenerate rather than
with numbers the controller typed.

Every check reads pair *text* and the gold's own labels only. No judge output,
no rationale, no slice difficulty, so no number below can be a function of how
any model performed on anything.

The five checks, in the plan's order:

1. ``retired_pair_overlap`` — byte-identical reproduction of a retired pair,
   against the digest pin. The authoring gate is **zero**.
2. ``find_duplicate_propositions`` per verdict class at the committed
   threshold. The authoring gate is **zero within-class findings**.
3. ``census_independence`` for the contradicted and entailed classes, both
   readings (rows and independent propositions), against their own bars.
   Disclosure, not a gate.

**A clean result on check 2 is not a duplicate-free census, and this script
says so on every run.** Both checks 2 and 3 score hypothesis pairs by content-
token Jaccard, which sees lexical overlap and not entailment. Measured on this
census 2026-08-14: the three duplicate propositions the authoring lineage
recorded by reading score 0.8333, 0.3333 and 0.2857, so **none** of them is
caught at the committed 0.85 — and one ruled-lawful pair scores 0.2857, exactly
equal to a recorded duplicate. No threshold separates the two populations,
which means check 2 cannot be repaired by moving its number and check 3's
independent-proposition count inherits the same blindness: it will report a
class fully independent while known duplicates sit inside it.

So the script also reports the **candidate population** — every set of live
pairs sharing a byte-identical premise and verdict, the only place a same-
proposition duplicate can occur. That population is the honest denominator for
an exhaustive human adjudication, and it is small enough for one. Read the
gate's zero as "no *lexical* duplicate", never as "no duplicate".
4. ``cross_gold_near_overlap`` against the archived gold — the near-screen the
   digest pin cannot see, and which ``find_duplicate_propositions`` is vacuous
   for across files.
5. The cross-verdict diligence check: one premise, near-identical hypotheses,
   *different* verdicts. These are the reversal hard negatives the gold exists
   to contain, so a hit here is expected and is dismissed with a reason — it
   is listed for a human to read, never counted against the gate.

Usage::

    python -m benchlib.run_step9_independence [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCHLIB_PARENT = str(Path(__file__).resolve().parent.parent)
if BENCHLIB_PARENT not in sys.path:
    sys.path.insert(0, BENCHLIB_PARENT)

from benchlib import entailment_gold as eg  # noqa: E402
from benchlib import judge_qualification as jq  # noqa: E402
from benchlib.duplicate_propositions import (  # noqa: E402
    JACCARD_THRESHOLD,
    cross_gold_near_overlap,
    find_duplicate_propositions,
    similarity,
)

ARCHIVED_GOLD = eg.ENTAILMENT_DIR / "retired" / "gold-4975c5cc.json"

#: The bars each class's recall is stated against. Contradicted carries
#: `contradiction_recall_bar`; entailed carries the entailment role's 0.90.
#: Read here only to compute what the census can *express* — this script
#: scores nothing, so neither value can be moved by anything it prints.
CLASS_BARS = {"contradicted": 0.95, "entailed": 0.90}


def _live(pairs: list[dict]) -> list[dict]:
    return [p for p in pairs if not ("retired" in p or p.get("retirement_kind"))]


def duplicate_candidate_population(pairs: list[dict]) -> list[dict]:
    """Every live pair sharing a byte-identical premise **and** verdict.

    The population inside which a same-proposition duplicate can occur at all,
    reported because the Jaccard checks cannot see a paraphrase and their zero
    would otherwise read as an all-clear. Two pairs that assert one proposition
    must agree on the premise and on the verdict; they need not share a token
    of hypothesis wording. This is therefore the denominator an exhaustive
    human pass works through, and its rows are ordered by hypothesis Jaccard
    only to give a reader somewhere to start — **not** as a ranking of
    likelihood, since the measured scores of known duplicates and of ruled-
    lawful pairs interleave completely.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for pair in pairs:
        groups.setdefault(
            (pair.get("premise", ""), pair.get("verdict", "")), []
        ).append(pair)

    rows: list[dict] = []
    for (_, verdict), group in groups.items():
        if len(group) < 2:
            continue
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                rows.append({
                    "verdict": verdict,
                    "left": left["id"],
                    "right": right["id"],
                    "hypothesis_similarity": round(
                        similarity(
                            left.get("hypothesis", ""), right.get("hypothesis", "")
                        ), 4
                    ),
                })
    return sorted(rows, key=lambda r: -r["hypothesis_similarity"])


def cross_verdict_diligence(
    pairs: list[dict], *, threshold: float = JACCARD_THRESHOLD
) -> list[dict]:
    """One premise, near-identical hypotheses, different verdicts.

    The mirror of ``find_duplicate_propositions``, which requires a *shared*
    verdict because a duplicate asserts the same proposition. This asks the
    opposite question: where does the gold say two nearly identical claims
    about one premise have different truth values? That is the reversal
    hard-negative shape on purpose, so this is a diligence list for a human,
    not a gate.
    """
    by_premise: dict[str, list[dict]] = {}
    for pair in pairs:
        by_premise.setdefault(pair.get("premise", ""), []).append(pair)

    rows: list[dict] = []
    for group in by_premise.values():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                if left.get("verdict") == right.get("verdict"):
                    continue
                score = similarity(
                    left.get("hypothesis", ""), right.get("hypothesis", "")
                )
                if score >= threshold:
                    rows.append({
                        "left": left["id"],
                        "left_verdict": left.get("verdict"),
                        "right": right["id"],
                        "right_verdict": right.get("verdict"),
                        "hypothesis_similarity": round(score, 4),
                    })
    return sorted(rows, key=lambda r: (r["left"], r["right"]))


def run() -> dict:
    gold = eg.load_entailment_gold()
    fresh = _live(gold["pairs"])

    with open(ARCHIVED_GOLD, encoding="utf-8") as fh:
        archived_doc = json.load(fh)
    archived = archived_doc["pairs"]

    # 1. byte-identical reproduction of a retired pair
    retired_overlap = sorted(eg.retired_pair_overlap(fresh))

    # 2. within-class duplicates, partitioned by the class the finding sits in
    all_findings = find_duplicate_propositions(fresh)
    verdict_of = {p["id"]: p.get("verdict") for p in fresh}
    within_class: dict[str, list[dict]] = {}
    for finding in all_findings:
        left_verdict = verdict_of[finding.left]
        # find_duplicate_propositions groups on premise AND verdict, so both
        # sides of any finding already share a class; asserted, not assumed.
        assert left_verdict == verdict_of[finding.right], finding
        within_class.setdefault(left_verdict, []).append({
            "left": finding.left,
            "right": finding.right,
            "hypothesis_similarity": finding.score,
        })

    # 3. what each census can express against its own bar
    independence = {
        verdict: jq.census_independence(fresh, verdict, bar)
        for verdict, bar in CLASS_BARS.items()
    }

    # 4. near-reproduction of an archived live pair
    cross_gold = [
        {
            "fresh_id": f.fresh_id,
            "archived_id": f.archived_id,
            "premise_similarity": f.premise_similarity,
            "hypothesis_similarity": f.hypothesis_similarity,
        }
        for f in cross_gold_near_overlap(fresh, archived)
    ]

    # 5. diligence, not a gate
    cross_verdict = cross_verdict_diligence(fresh)

    return {
        "threshold": JACCARD_THRESHOLD,
        "class_bars": CLASS_BARS,
        "gold_path": str(eg.GOLD_PATH),
        "gold_pairs_sha256": eg.pairs_content_hash(gold["pairs"]),
        "archived_gold_path": str(ARCHIVED_GOLD),
        "fresh_live_pairs": len(fresh),
        "archived_live_pairs": len(_live(archived)),
        "census": {
            verdict: sum(1 for p in fresh if p.get("verdict") == verdict)
            for verdict in ("contradicted", "entailed", "unsupported")
        },
        "gates": {
            "retired_pair_overlap": retired_overlap,
            "within_class_duplicates": within_class,
        },
        "disclosure": {
            "census_independence": independence,
            "duplicate_candidate_population": duplicate_candidate_population(fresh),
        },
        "screens": {
            "cross_gold_near_overlap": cross_gold,
            "cross_verdict_diligence": cross_verdict,
        },
    }


def render(result: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("T2.124 step 9 — independence and freshness pass")
    add("")
    add(f"gold                 {result['gold_path']}")
    add(f"gold_pairs_sha256    {result['gold_pairs_sha256']}")
    add(f"archived gold        {result['archived_gold_path']}")
    add(f"threshold            {result['threshold']}")
    add(
        f"census               {result['fresh_live_pairs']} live — "
        + ", ".join(f"{k} {v}" for k, v in result["census"].items())
    )
    add("")
    add("== authoring gates (both must be empty) ==")
    overlap = result["gates"]["retired_pair_overlap"]
    add(f"retired-pair byte overlap    {len(overlap)} {overlap if overlap else ''}")
    dupes = result["gates"]["within_class_duplicates"]
    total = sum(len(v) for v in dupes.values())
    add(f"within-class duplicates      {total}   (LEXICAL ONLY — see below)")
    for verdict, findings in sorted(dupes.items()):
        for f in findings:
            add(
                f"    {verdict:14s} {f['left']} ~ {f['right']}  "
                f"jaccard={f['hypothesis_similarity']}"
            )
    add("")
    add("== what the duplicate gate cannot see ==")
    add(
        "Both the gate above and the independence count below score hypotheses by"
    )
    add(
        "content-token Jaccard. It does not see paraphrase. The three duplicates"
    )
    add(
        "recorded by reading score 0.8333 / 0.3333 / 0.2857 — none caught at 0.85 —"
    )
    add(
        "and a ruled-lawful pair scores 0.2857, equal to one of them. No threshold"
    )
    add("separates them, so the zero above means 'no lexical duplicate' only.")
    add("")
    pop = result["disclosure"]["duplicate_candidate_population"]
    by_class: dict[str, int] = {}
    for row in pop:
        by_class[row["verdict"]] = by_class.get(row["verdict"], 0) + 1
    add(
        f"candidate pairs for exhaustive human adjudication: {len(pop)}  "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_class.items()))
    )
    for row in pop:
        add(
            f"    {row['verdict']:14s} {row['left']} ~ {row['right']}  "
            f"jaccard={row['hypothesis_similarity']}"
        )
    add("")
    add("== disclosure: what each census can express ==")
    for verdict, ci in result["disclosure"]["census_independence"].items():
        add(
            f"{verdict:14s} bar {ci['bar']}  rows {ci['rows']}  "
            f"independent {ci['independent_propositions']}"
        )
        add(
            f"{'':14s} min-pass on rows {ci['min_passing_rows']}"
            f" (effective {ci['effective_bar_on_rows']}),"
            f" on independent {ci['min_passing_independent']}"
            f" (effective {ci['effective_bar_on_independent']})"
        )
        add(f"{'':14s} bar expressible on rows: {ci['bar_expressible_on_rows']}")
    add("")
    add("== freshness screen vs the archived gold ==")
    cross = result["screens"]["cross_gold_near_overlap"]
    add(f"cross-gold near overlap      {len(cross)}")
    for row in cross:
        add(
            f"    {row['fresh_id']} ~ {row['archived_id']}  "
            f"premise={row['premise_similarity']} "
            f"hypothesis={row['hypothesis_similarity']}"
        )
    add("")
    add("== cross-verdict diligence (expected; dismissed with reasons) ==")
    cv = result["screens"]["cross_verdict_diligence"]
    add(f"cross-verdict near pairs     {len(cv)}")
    for row in cv:
        add(
            f"    {row['left']} ({row['left_verdict']}) ~ "
            f"{row['right']} ({row['right_verdict']})  "
            f"jaccard={row['hypothesis_similarity']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="also write the raw result here")
    args = parser.parse_args()

    result = run()
    print(render(result))
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
