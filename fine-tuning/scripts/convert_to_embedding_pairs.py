# fine-tuning/scripts/convert_to_embedding_pairs.py
"""Canonical → {query, positive} pairs for InfoNCE.
Hard-negative rows become {query, negative}; downstream loss code decides
whether to use triplet loss or drop them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def convert_file(src: Path, out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with src.open("r", encoding="utf-8") as fi, out.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("query_kind") == "hard-negative":
                fo.write(json.dumps({"query": row["query"], "negative": row["negative"]}) + "\n")
            else:
                fo.write(json.dumps({"query": row["query"], "positive": row["positive"]}) + "\n")
            count += 1
    return count


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    print(f"wrote {convert_file(a.src, a.out)} rows to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
