"""Audit gold entity labels across the shared corpus for type-assignment
consistency.

Every time the same surface form appears (case-folded) in shared.jsonl, it
should be tagged with the same type. In practice the synthetic corpus has
drift — asyncio as `library` in some rows and `tool` in others, TTL as
`config` in some rows and `concept` in others. This is the hard ceiling on
type accuracy the fine-tuned model can ever reach.

Output:
  - JSON report at runs/2026-04-17-push-to-95/label_consistency_audit.json
  - Human-readable markdown at label_consistency_audit.md listing the top
    contested surface forms by count × number-of-types.

Run:
  python -m scripts._label_consistency_audit
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT_DIR = ROOT / "runs" / "2026-04-17-push-to-95"

_WS = re.compile(r"\s+")


def normalize(name: str) -> str:
    return _WS.sub(" ", name.strip().lower())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--min-count", type=int, default=2, help="Minimum occurrences to report (default 2)")
    p.add_argument("--top-conflicts", type=int, default=50, help="How many contested forms to list in markdown (default 50)")
    args = p.parse_args()

    by_form: dict[str, Counter[str]] = defaultdict(Counter)
    total_mentions = 0

    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for ent in row.get("entities") or []:
                name = ent.get("name") or ""
                etype = ent.get("type") or ""
                if not name or not etype:
                    continue
                nform = normalize(name)
                if not nform:
                    continue
                by_form[nform][etype] += 1
                total_mentions += 1

    # Build report
    per_form: list[dict] = []
    for form, counter in by_form.items():
        count = sum(counter.values())
        if count < args.min_count:
            continue
        types = dict(counter.most_common())
        winner, winner_n = counter.most_common(1)[0]
        inconsistent = len(counter) > 1
        per_form.append({
            "surface": form,
            "total": count,
            "types": types,
            "winner": winner,
            "winner_share": winner_n / count,
            "num_types": len(counter),
            "inconsistent": inconsistent,
            "conflict_weight": count * (len(counter) - 1),  # total × types-beyond-winner
        })

    per_form.sort(key=lambda r: -r["conflict_weight"])

    # Aggregate stats
    n_forms = len(per_form)
    n_inconsistent = sum(1 for r in per_form if r["inconsistent"])
    mentions_in_inconsistent = sum(r["total"] for r in per_form if r["inconsistent"])
    conflict_rate = mentions_in_inconsistent / total_mentions if total_mentions else 0.0

    report = {
        "total_entity_mentions": total_mentions,
        "distinct_surface_forms_with_ge_min_count": n_forms,
        "min_count": args.min_count,
        "inconsistent_surface_forms": n_inconsistent,
        "mentions_in_inconsistent_forms": mentions_in_inconsistent,
        "mention_level_conflict_rate": conflict_rate,
        "top_contested": per_form[: args.top_conflicts],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "label_consistency_audit.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# Gold-label consistency audit — 2026-04-17",
        "",
        f"Source: `{SHARED.relative_to(ROOT)}`",
        f"Total entity mentions: **{total_mentions:,}**",
        f"Distinct surface forms (≥ {args.min_count} occurrences): **{n_forms:,}**",
        f"Inconsistent surface forms (>1 type): **{n_inconsistent:,}** ({n_inconsistent/n_forms*100:.1f}%)",
        f"Entity mentions in inconsistent forms: **{mentions_in_inconsistent:,}** ({conflict_rate*100:.1f}% of all mentions)",
        "",
        "## Top contested surface forms",
        "",
        "| surface | total | num types | winner (share) | full distribution |",
        "|---|---:|---:|---|---|",
    ]
    for r in per_form[: args.top_conflicts]:
        types_str = ", ".join(f"{t}={n}" for t, n in r["types"].items())
        md_lines.append(
            f"| `{r['surface']}` | {r['total']} | {r['num_types']} | "
            f"`{r['winner']}` ({r['winner_share']:.0%}) | {types_str} |"
        )
    md_lines.append("")
    md_lines.append("## Interpretation")
    md_lines.append("")
    md_lines.append(
        f"Mention-level conflict rate is **{conflict_rate*100:.1f}%** — that's the mathematical "
        f"ceiling the type classifier cannot exceed unless the gold itself is cleaned. "
        f"Resolving boundary disagreements via a decision tree and relabelling these rows "
        f"is the single highest-ROI lever before any more training."
    )

    md_path = OUT_DIR / "label_consistency_audit.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"total mentions: {total_mentions:,}")
    print(f"distinct forms (>= {args.min_count}): {n_forms:,}")
    print(f"inconsistent forms: {n_inconsistent:,} ({n_inconsistent/n_forms*100:.1f}%)")
    print(f"mention-level conflict rate: {conflict_rate*100:.2f}%")
    print(f"wrote {json_path} + {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
