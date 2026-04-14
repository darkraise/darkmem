# fine-tuning/scripts/convert_to_gliner.py
"""Canonical → GLiNER training format.

Output rows: {"text": "...", "entities": [{"start": int, "end": int, "label": str}, ...]}

The base_model and failed_dir arguments are accepted for CLI compatibility but
character-span conversion requires no tokenizer — GLiNER's Trainer handles
tokenization internally from character offsets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def convert_file(src: Path, out: Path, *, failed_dir: Path, base_model: str = "urchade/gliner_small-v2.1") -> dict:
    failed_dir.mkdir(parents=True, exist_ok=True)
    failed_path = failed_dir / (src.stem + ".failures.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    converted = 0
    failed = 0
    with (
        src.open("r", encoding="utf-8") as fi,
        out.open("w", encoding="utf-8") as fo,
        failed_path.open("w", encoding="utf-8") as ff,
    ):
        for line_no, line in enumerate(fi, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = row["text"]
            entities = []
            ok = True
            for ent in row.get("entities", []):
                start, end = ent["start"], ent["end"]
                if start < 0 or end > len(text) or end <= start:
                    ok = False
                    ff.write(json.dumps({"line": line_no, "entity": ent, "reason": "invalid span"}) + "\n")
                    break
                entities.append({"start": start, "end": end, "label": ent["type"]})
            if not ok:
                failed += 1
                continue
            fo.write(json.dumps({"text": text, "entities": entities}) + "\n")
            converted += 1
    return {"converted": converted, "failed": failed}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--failed-dir", type=Path, required=True)
    p.add_argument("--base-model", default="urchade/gliner_small-v2.1")
    a = p.parse_args()
    stats = convert_file(a.src, a.out, failed_dir=a.failed_dir, base_model=a.base_model)
    print(f"converted={stats['converted']} failed={stats['failed']}")
    total = stats["converted"] + stats["failed"]
    if total and stats["failed"] / total > 0.01:
        print("ERROR: failure rate exceeds 1%; training should not proceed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
