"""Audit surface-form label consistency under the 10-type coding taxonomy.

The 35-type audit (at runs/2026-04-17-push-to-95/label_consistency_audit.json)
showed 18.33% mention-level conflict, but most of those conflicts were
library/tool/framework boundary disputes that the 10-type collapse already
resolves. This script re-runs the audit in 10-type space to find the
residual conflicts we actually need to clean up before retraining.

Output:
  runs/2026-04-17-push-to-95/coding10_conflicts.json
  runs/2026-04-17-push-to-95/coding10_conflicts.md
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._build_coding10_splits import TYPE_MAP

SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT_DIR = ROOT / "runs" / "2026-04-17-push-to-95"

_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s.strip().lower())


def main() -> int:
    by_form: dict[str, Counter[str]] = defaultdict(Counter)
    total_mentions = 0
    dropped = 0

    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for ent in row.get("entities") or []:
                raw_type = ent.get("type")
                mapped = TYPE_MAP.get(raw_type)
                if not mapped:
                    dropped += 1
                    continue
                surface = norm(ent.get("name") or "")
                if not surface:
                    continue
                by_form[surface][mapped] += 1
                total_mentions += 1

    contested = []
    for form, counter in by_form.items():
        total = sum(counter.values())
        if total < 2:
            continue
        if len(counter) == 1:
            continue
        winner, winner_n = counter.most_common(1)[0]
        contested.append({
            "surface": form,
            "total": total,
            "types": dict(counter.most_common()),
            "winner": winner,
            "winner_share": winner_n / total,
            "num_types": len(counter),
        })

    contested.sort(key=lambda r: -r["total"] * (r["num_types"] - 1))

    distinct_forms = sum(1 for c in by_form.values() if sum(c.values()) >= 2)
    n_contested = len(contested)
    contested_mentions = sum(r["total"] for r in contested)

    report = {
        "taxonomy": "coding10",
        "total_mentions_after_remap": total_mentions,
        "dropped_mentions_outside_taxonomy": dropped,
        "distinct_forms_ge2": distinct_forms,
        "contested_forms": n_contested,
        "contested_share_of_forms": n_contested / distinct_forms if distinct_forms else 0,
        "mentions_in_contested_forms": contested_mentions,
        "mention_level_conflict_rate": contested_mentions / total_mentions if total_mentions else 0,
        "top_contested": contested[:60],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "coding10_conflicts.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"total entity mentions (in coding-10 taxonomy): {total_mentions:,}")
    print(f"dropped (outside coding-10): {dropped:,}")
    print(f"distinct surface forms >=2 occurrences: {distinct_forms:,}")
    print(f"contested forms: {n_contested:,} ({n_contested/distinct_forms*100:.1f}%)")
    print(f"mention-level conflict rate in coding-10 space: "
          f"{contested_mentions/total_mentions*100:.2f}%")
    print(f"wrote {json_path}")
    print("\nTop 20 contested under coding-10 taxonomy:")
    for r in contested[:20]:
        types_str = ", ".join(f"{t}={n}" for t, n in r["types"].items())
        print(f"  {r['surface']:25s} total={r['total']:4d} types={r['num_types']} "
              f"winner={r['winner']} ({r['winner_share']:.0%}) | {types_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
