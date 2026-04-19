"""Merge relaug survivors into coding10clean_train_canon.jsonl only.

Val and test are never touched. First run copies them to `*.pre-relaug.jsonl`
as an idempotent backup so every downstream benchmark can reference the frozen
pre-aug gold.

Usage:
    python -m fine-tuning.scripts._merge_relaug \
        --survivors-dir data/v2/relaug/survivors \
        --train data/splits/coding10clean_train_canon.jsonl \
        --splits-dir data/splits

Prints row counts before and after the append.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _collect_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("id"):
                ids.add(r["id"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survivors-dir", required=True, type=Path)
    ap.add_argument("--train", required=True, type=Path)
    ap.add_argument("--splits-dir", required=True, type=Path)
    args = ap.parse_args()

    val_path = args.splits_dir / "coding10clean_val_canon.jsonl"
    test_path = args.splits_dir / "coding10clean_test_canon.jsonl"
    val_backup = args.splits_dir / "coding10clean_val_canon.pre-relaug.jsonl"
    test_backup = args.splits_dir / "coding10clean_test_canon.pre-relaug.jsonl"
    train_backup = args.splits_dir / "coding10clean_train_canon.pre-relaug.jsonl"

    for src, dst in (
        (val_path, val_backup),
        (test_path, test_backup),
        (args.train, train_backup),
    ):
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"backup: {src.name} -> {dst.name}")
        else:
            print(f"backup already present: {dst.name}")

    train_ids_before = _collect_ids(args.train)
    val_ids = _collect_ids(val_path)
    test_ids = _collect_ids(test_path)

    n_train_before = len(train_ids_before)
    n_val = len(val_ids)
    n_test = len(test_ids)

    appended = 0
    skipped_dup = 0
    skipped_leak = 0

    survivor_files = sorted(args.survivors_dir.glob("*.jsonl"))
    if not survivor_files:
        print(f"no survivor files found in {args.survivors_dir}")
        return 1

    with args.train.open("a", encoding="utf-8") as fout:
        for sf in survivor_files:
            per_file = 0
            with sf.open("r", encoding="utf-8") as fin:
                for line in fin:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    rid = r.get("id")
                    if rid in train_ids_before:
                        skipped_dup += 1
                        continue
                    if rid in val_ids or rid in test_ids:
                        skipped_leak += 1
                        continue
                    fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                    train_ids_before.add(rid)
                    appended += 1
                    per_file += 1
            print(f"{sf.name}: appended {per_file}")

    n_train_after = _count_rows(args.train)
    print()
    print(f"train rows before: {n_train_before}")
    print(f"train rows after:  {n_train_after} (+{appended})")
    print(f"val rows:          {n_val} (frozen)")
    print(f"test rows:         {n_test} (frozen)")
    print(f"skipped duplicates:        {skipped_dup}")
    print(f"skipped val/test leakage:  {skipped_leak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
