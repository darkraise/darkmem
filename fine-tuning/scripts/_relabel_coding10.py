"""Relabel the 14k shared corpus using majority-wins in coding-10 space.

For every surface form where >=70% of mentions agree on one of the 10 types,
relabel the minority mentions to match the winner. Forms below 70% winner
share stay as-is (genuinely ambiguous; let the model learn from context).

Produces a new canonical-schema file:
  data/v2/shared/shared_coding10_clean.jsonl

Then re-generates the coding10 splits from it via a direct rebuild.
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
CLEAN = ROOT / "data" / "v2" / "shared" / "shared_coding10_clean.jsonl"
REPORT = ROOT / "runs" / "2026-04-17-push-to-95" / "relabel_coding10.json"

WINNER_SHARE_THRESHOLD = 0.70
MIN_MENTIONS_FOR_RELABEL = 3

_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s.strip().lower())


def build_winners() -> tuple[dict[str, str], dict]:
    by_form: dict[str, Counter[str]] = defaultdict(Counter)
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for ent in row.get("entities") or []:
                mapped = TYPE_MAP.get(ent.get("type"))
                if not mapped:
                    continue
                surface = norm(ent.get("name") or "")
                if not surface:
                    continue
                by_form[surface][mapped] += 1

    winners: dict[str, str] = {}
    stats = {
        "distinct_forms": len(by_form),
        "forms_with_winner": 0,
        "forms_below_threshold": 0,
        "forms_unanimous": 0,
    }
    for form, counter in by_form.items():
        total = sum(counter.values())
        if total < MIN_MENTIONS_FOR_RELABEL:
            continue
        winner, winner_n = counter.most_common(1)[0]
        share = winner_n / total
        if share >= WINNER_SHARE_THRESHOLD:
            winners[form] = winner
            if len(counter) == 1:
                stats["forms_unanimous"] += 1
            else:
                stats["forms_with_winner"] += 1
        else:
            stats["forms_below_threshold"] += 1
    return winners, stats


def main() -> int:
    winners, stats = build_winners()
    print(f"forms_unanimous: {stats['forms_unanimous']:,}")
    print(f"forms_with_winner (contested but >={WINNER_SHARE_THRESHOLD:.0%}): {stats['forms_with_winner']:,}")
    print(f"forms_below_threshold (leave alone): {stats['forms_below_threshold']:,}")
    print()

    rows_out = 0
    relabeled_mentions = 0
    kept_mentions = 0
    dropped_mentions = 0

    with SHARED.open("r", encoding="utf-8") as fi, CLEAN.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            new_ents = []
            for ent in row.get("entities") or []:
                raw_type = ent.get("type")
                mapped = TYPE_MAP.get(raw_type)
                if not mapped:
                    dropped_mentions += 1
                    continue
                surface = norm(ent.get("name") or "")
                winner = winners.get(surface)
                if winner and winner != mapped:
                    new_type = winner
                    relabeled_mentions += 1
                else:
                    new_type = mapped
                    kept_mentions += 1
                new_ents.append({
                    "name": ent.get("name"),
                    "type": new_type,
                    "start": ent["start"],
                    "end": ent["end"],
                })
            # Keep relationships only between surviving entities
            ent_names = {e["name"] for e in new_ents}
            new_rels = [
                {"source": r["source"], "target": r["target"], "type": r["type"]}
                for r in (row.get("relationships") or [])
                if r.get("source") in ent_names and r.get("target") in ent_names
            ]
            out = {
                "id": row["id"],
                "domain": row.get("domain"),
                "text": row["text"],
                "memory_type": row.get("memory_type"),
                "entities": new_ents,
                "relationships": new_rels,
                "noise": row.get("noise", False),
            }
            fo.write(json.dumps(out, ensure_ascii=False) + "\n")
            rows_out += 1

    report = {
        "winners_applied": len(winners),
        "relabeled_mentions": relabeled_mentions,
        "kept_mentions": kept_mentions,
        "dropped_mentions_outside_taxonomy": dropped_mentions,
        "rows_written": rows_out,
        "output_path": str(CLEAN.relative_to(ROOT)),
        "stats": stats,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    total_mentions = relabeled_mentions + kept_mentions
    print(f"rows: {rows_out:,}")
    print(f"entity mentions after remap: {total_mentions:,}")
    print(f"  relabeled to winner: {relabeled_mentions:,} ({relabeled_mentions/total_mentions*100:.2f}%)")
    print(f"  kept original map: {kept_mentions:,}")
    print(f"  dropped (outside 10-type): {dropped_mentions:,}")
    print(f"wrote {CLEAN.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
