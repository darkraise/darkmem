# fine-tuning/scripts/convert_to_classifier.py
"""Canonical → classifier {text, label} rows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def convert_file(src: Path, out: Path) -> int:
    count = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8") as fi, out.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            fo.write(json.dumps({"text": row["text"], "label": row["memory_type"]}) + "\n")
            count += 1
    return count


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    n = convert_file(a.src, a.out)
    print(f"wrote {n} rows to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
