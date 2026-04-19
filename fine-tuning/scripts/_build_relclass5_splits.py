"""Build pair-wise relation-classification splits on the 5-type schema.

For each canonical row, enumerate every directional entity pair. The pair
label is `REL_MAP_5[rel_type]` if the pair appears in `relationships`, else
NONE. Dropped-cluster types collapse to NONE.

NONE cap applies to train only by default (auto-detected from output filename,
or forced via `--cap-none` / `--no-cap-none`). Mirrors the 10-type builder.

Default inputs:
    data/splits/coding5clean_{train,val,test}_canon.jsonl
Default outputs:
    data/splits/relclass5_{train,val,test}.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._build_rebel_coding5_splits import REL_MAP_5  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"

DEFAULT_PAIRS = [
    (SPLITS / "coding5clean_train_canon.jsonl", SPLITS / "relclass5_train.jsonl", True),
    (SPLITS / "coding5clean_val_canon.jsonl", SPLITS / "relclass5_val.jsonl", False),
    (SPLITS / "coding5clean_test_canon.jsonl", SPLITS / "relclass5_test.jsonl", False),
]


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()]


def build_pairs(row: dict[str, Any]) -> list[dict[str, Any]]:
    entities = row.get("entities") or []
    if len(entities) < 2:
        return []

    rel_index: dict[tuple[str, str], str] = {}
    for rel in (row.get("relationships") or []):
        mapped = REL_MAP_5.get(rel.get("type"))
        if not mapped:
            continue
        rel_index[(rel["source"], rel["target"])] = mapped

    text = row["text"]
    pairs: list[dict[str, Any]] = []
    for i, e1 in enumerate(entities):
        for j, e2 in enumerate(entities):
            if i == j:
                continue
            label = rel_index.get((e1["name"], e2["name"]), "NONE")
            pairs.append({
                "text": text,
                "e1_name": e1["name"],
                "e1_type": e1["type"],
                "e1_start": e1["start"],
                "e1_end": e1["end"],
                "e2_name": e2["name"],
                "e2_type": e2["type"],
                "e2_start": e2["start"],
                "e2_end": e2["end"],
                "label": label,
                "source_id": row.get("id"),
            })
    return pairs


def cap_none(pairs: list[dict[str, Any]], ratio: float, seed: int) -> list[dict[str, Any]]:
    positives = [p for p in pairs if p["label"] != "NONE"]
    nones = [p for p in pairs if p["label"] == "NONE"]
    if not positives:
        return pairs
    class_counts = Counter(p["label"] for p in positives)
    top_class_count = max(class_counts.values())
    cap = int(round(top_class_count * ratio))
    if len(nones) <= cap:
        return pairs
    rng = random.Random(seed)
    rng.shuffle(nones)
    return positives + nones[:cap]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def process(
    input_path: Path,
    output_path: Path,
    apply_none_cap: bool,
    ratio: float,
    seed: int,
) -> tuple[int, Counter, int, Counter]:
    rows = load(input_path)
    pairs: list[dict[str, Any]] = []
    for row in rows:
        pairs.extend(build_pairs(row))

    raw_total = len(pairs)
    raw_counts = Counter(p["label"] for p in pairs)

    if apply_none_cap:
        pairs = cap_none(pairs, ratio, seed)

    final_counts = Counter(p["label"] for p in pairs)
    write_jsonl(output_path, pairs)
    return raw_total, raw_counts, len(pairs), final_counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, help="single input canonical JSONL")
    ap.add_argument("--output", type=Path, help="single output pair-wise JSONL")
    ap.add_argument("--cap-none", dest="cap_none", action="store_true", default=None)
    ap.add_argument("--no-cap-none", dest="cap_none", action="store_false")
    ap.add_argument("--cap-none-ratio", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pairs: list[tuple[Path, Path, bool]]
    if args.input or args.output:
        if not (args.input and args.output):
            ap.error("--input and --output must be provided together")
        apply_cap = args.cap_none if args.cap_none is not None else "train" in args.output.name
        pairs = [(args.input, args.output, apply_cap)]
    else:
        pairs = DEFAULT_PAIRS
        if args.cap_none is not None:
            pairs = [(i, o, args.cap_none) for i, o, _ in pairs]

    for input_path, output_path, apply_cap in pairs:
        raw_total, raw_counts, final_total, final_counts = process(
            input_path, output_path, apply_cap, args.cap_none_ratio, args.seed,
        )
        print(f"{input_path.name} -> {output_path.name}")
        print(f"  rows pre-cap:  {raw_total:6d}  (NONE={raw_counts.get('NONE', 0)})")
        print(f"  rows post-cap: {final_total:6d}  (NONE={final_counts.get('NONE', 0)})  cap_applied={apply_cap}")
        for label, n in final_counts.most_common():
            print(f"    {label:12s} {n:6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
