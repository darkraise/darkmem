"""Remove near-duplicates from the training corpus (cosine similarity >= 0.80)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "classification" / "train.jsonl"
BACKUP_PATH = TRAIN_PATH.with_suffix(".jsonl.pre_cleanup")
THRESHOLD = 0.80


def main() -> int:
    # Backup original
    if not BACKUP_PATH.exists():
        shutil.copy(TRAIN_PATH, BACKUP_PATH)
        print(f"Backup saved to {BACKUP_PATH}")

    # Load
    data = []
    with TRAIN_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    print(f"Loaded {len(data)} examples")

    # Compute similarity matrix
    texts = [d["text"] for d in data]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2).fit_transform(texts)
    n = len(texts)
    to_remove = set()

    chunk = 500
    for i in range(0, n, chunk):
        sims = cosine_similarity(vec[i:i+chunk], vec)
        for local_i, row in enumerate(sims):
            global_i = i + local_i
            if global_i in to_remove:
                continue
            for j, s in enumerate(row):
                if j > global_i and s >= THRESHOLD and j not in to_remove:
                    # Remove the second occurrence
                    to_remove.add(j)
                    print(f"  [sim={s:.2f}] remove idx {j} (keep {global_i}): {data[j]['label']}")
                    print(f"    kept:    {data[global_i]['text'][:80]}")
                    print(f"    removed: {data[j]['text'][:80]}")

    cleaned = [d for i, d in enumerate(data) if i not in to_remove]
    print(f"\nRemoved {len(to_remove)} duplicates. New total: {len(cleaned)}")

    with TRAIN_PATH.open("w", encoding="utf-8") as fh:
        for d in cleaned:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"Wrote cleaned corpus to {TRAIN_PATH}")
    return 0


if __name__ == "__main__":
    main()
