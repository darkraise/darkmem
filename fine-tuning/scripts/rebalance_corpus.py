"""Rebalance the training corpus by capping each class at a target count.

Downsampling is deterministic via seeded shuffle to support reproducibility.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "classification" / "train.jsonl"
TARGET = 230  # cap per class
SEED = 42


def main() -> int:
    with TRAIN_PATH.open("r", encoding="utf-8") as fh:
        data = [json.loads(l) for l in fh if l.strip()]
    print(f"Loaded {len(data)} examples")

    by_label: dict[str, list[dict]] = defaultdict(list)
    for d in data:
        by_label[d["label"]].append(d)

    rng = random.Random(SEED)
    rebalanced: list[dict] = []
    for label in sorted(by_label):
        items = by_label[label]
        if len(items) > TARGET:
            rng.shuffle(items)
            kept = items[:TARGET]
            print(f"  {label:<14} {len(items)} -> {len(kept)} (removed {len(items) - len(kept)})")
        else:
            kept = items
            print(f"  {label:<14} {len(items)} (unchanged)")
        rebalanced.extend(kept)

    rng.shuffle(rebalanced)  # shuffle overall order
    with TRAIN_PATH.open("w", encoding="utf-8") as fh:
        for d in rebalanced:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(rebalanced)} examples (from {len(data)})")
    return 0


if __name__ == "__main__":
    main()
