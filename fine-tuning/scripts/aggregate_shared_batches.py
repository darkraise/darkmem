"""Aggregate parallel-agent shared-batch temp files into shared.jsonl with dedup.

Usage:
    cd fine-tuning
    python scripts/aggregate_shared_batches.py \
        data/v2/shared/batch_010.tmp.jsonl \
        data/v2/shared/batch_011.tmp.jsonl \
        data/v2/shared/batch_012.tmp.jsonl

Dedup policy:
- Any new row whose `text` matches an existing row's `text` with SequenceMatcher
  ratio >= DUPE_THRESHOLD is dropped.
- Dedup runs against both the existing shared.jsonl and earlier tmp files in the
  batch list, in order.
- Dropped rows get logged to data/v2/failed/aggregate_dropped.jsonl with the
  matching existing id so you can investigate.

The script does NOT touch HANDOFF.md, commit, or delete the tmp files — those
steps stay with the orchestrating session.
"""
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
FAILED = ROOT / "data" / "v2" / "failed"

DUPE_THRESHOLD = 0.85


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _is_dupe(text: str, existing_texts: list[tuple[str, str]], threshold: float) -> tuple[str, float] | None:
    """Return (matching_id, ratio) if text is a near-duplicate of any existing text."""
    best: tuple[str, float] | None = None
    for eid, etext in existing_texts:
        if text == etext:
            return (eid, 1.0)
        # SequenceMatcher is O(n*m); cheap here since corpus stays <10k rows
        ratio = SequenceMatcher(None, text, etext).ratio()
        if ratio >= threshold and (best is None or ratio > best[1]):
            best = (eid, ratio)
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tmp_files", nargs="+", type=Path,
                        help="Batch tmp files to aggregate, in order of batch id")
    parser.add_argument("--threshold", type=float, default=DUPE_THRESHOLD)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report stats without modifying shared.jsonl")
    args = parser.parse_args()

    existing_rows = _read_jsonl(SHARED)
    existing_texts: list[tuple[str, str]] = [(r["id"], r["text"]) for r in existing_rows]
    existing_ids: set[str] = {r["id"] for r in existing_rows}

    dropped: list[dict] = []
    kept_new: list[dict] = []

    for tmp in args.tmp_files:
        if not tmp.exists():
            print(f"WARN: {tmp} missing, skipping")
            continue
        rows = _read_jsonl(tmp)
        print(f"{tmp.name}: {len(rows)} rows")
        for row in rows:
            if row["id"] in existing_ids:
                dropped.append({"id": row["id"], "reason": "id collision",
                                "text": row["text"]})
                continue
            match = _is_dupe(row["text"], existing_texts, args.threshold)
            if match is not None:
                match_id, ratio = match
                dropped.append({
                    "id": row["id"],
                    "reason": f"text dupe of {match_id} (ratio={ratio:.3f})",
                    "text": row["text"],
                })
                continue
            kept_new.append(row)
            existing_texts.append((row["id"], row["text"]))
            existing_ids.add(row["id"])

    print(f"\nkept {len(kept_new)} new rows, dropped {len(dropped)}")
    if dropped:
        FAILED.mkdir(parents=True, exist_ok=True)
        out = FAILED / "aggregate_dropped.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for d in dropped:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"drop log: {out}")
        for d in dropped[:10]:
            print(f"  drop {d['id']}: {d['reason']}")

    if args.dry_run:
        print("\n[dry-run] shared.jsonl unchanged")
        return 0

    with SHARED.open("a", encoding="utf-8") as f:
        for row in kept_new:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"appended {len(kept_new)} rows to {SHARED}")
    total = len(existing_rows) + len(kept_new)
    print(f"shared.jsonl now at {total} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
