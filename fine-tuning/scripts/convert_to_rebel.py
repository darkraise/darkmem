# fine-tuning/scripts/convert_to_rebel.py
"""Canonical → REBEL linearized triplet format."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _format_input(text: str, entities: list[dict]) -> str:
    entity_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
    return f"{text} | Entities: {entity_str}"


def _format_output(relationships: list[dict]) -> str:
    if not relationships:
        return "<triplet> NONE"
    parts = [f"<triplet> {r['source']} <subj> {r['target']} <obj> {r['type']}" for r in relationships]
    return " ".join(parts)


def convert_file(src: Path, out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with src.open("r", encoding="utf-8") as fi, out.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            fo.write(json.dumps({
                "input": _format_input(row["text"], row.get("entities", [])),
                "output": _format_output(row.get("relationships", [])),
            }) + "\n")
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
