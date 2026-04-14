# fine-tuning/scripts/build_splits.py
"""Build deterministic train/val/test splits for v2 corpora.

Stratifies by `domain` for extraction/classification. For retrieval,
expands each shared row into 2 (query, positive) rows and appends the
retrieval top-up, splitting 90/10 train/val (test is the fixed 270-query set).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _stratified_split(rows: list[dict], key: str, seed: int, val_fraction: float, test_fraction: float) -> tuple[list[dict], list[dict], list[dict]]:
    rng = random.Random(seed)
    by_key: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_key[r.get(key, "_unknown")].append(r)
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for k, items in sorted(by_key.items()):
        items = items[:]
        rng.shuffle(items)
        n = len(items)
        n_val = max(1, int(n * val_fraction)) if n >= 10 else 0
        n_test = max(1, int(n * test_fraction)) if n >= 10 else 0
        test += items[:n_test]
        val += items[n_test : n_test + n_val]
        train += items[n_test + n_val :]
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def build_extraction_splits(shared_path: Path, topup_path: Path, out_dir: Path, seed: int = 42) -> None:
    shared = _read_jsonl(shared_path)
    topup = _read_jsonl(topup_path)
    # Project shared rows into extraction schema (drop queries)
    shared_ext = [
        {k: v for k, v in r.items() if k in {"id", "domain", "text", "memory_type", "entities", "relationships"}}
        for r in shared
    ]
    all_rows = shared_ext + topup
    train, val, test = _stratified_split(all_rows, key="domain", seed=seed, val_fraction=0.1, test_fraction=0.1)
    _write_jsonl(out_dir / "extraction_train.jsonl", train)
    _write_jsonl(out_dir / "extraction_val.jsonl", val)
    _write_jsonl(out_dir / "extraction_test.jsonl", test)


def build_classification_splits(shared_path: Path, topup_path: Path, out_dir: Path, seed: int = 42) -> None:
    shared = _read_jsonl(shared_path)
    topup = _read_jsonl(topup_path)
    shared_cls = [
        {k: v for k, v in r.items() if k in {"id", "domain", "text", "memory_type"}}
        for r in shared
    ]
    all_rows = shared_cls + topup
    train, val, test = _stratified_split(all_rows, key="memory_type", seed=seed, val_fraction=0.1, test_fraction=0.1)
    _write_jsonl(out_dir / "classification_train.jsonl", train)
    _write_jsonl(out_dir / "classification_val.jsonl", val)
    _write_jsonl(out_dir / "classification_test.jsonl", test)


def build_retrieval_splits(shared_path: Path, topup_path: Path, out_dir: Path, seed: int = 42, val_fraction: float = 0.1) -> None:
    shared = _read_jsonl(shared_path)
    topup = _read_jsonl(topup_path)
    pairs: list[dict] = []
    for row in shared:
        if row.get("noise"):
            continue
        for q in row.get("queries", []):
            pairs.append({
                "id": f"{row['id']}-{q['form']}",
                "source_id": row["id"],
                "query": q["text"],
                "positive": row["text"],
                "query_kind": q["form"],
            })
    pairs += topup
    rng = random.Random(seed)
    rng.shuffle(pairs)
    n_val = int(len(pairs) * val_fraction)
    val = pairs[:n_val]
    train = pairs[n_val:]
    _write_jsonl(out_dir / "retrieval_train.jsonl", train)
    _write_jsonl(out_dir / "retrieval_val.jsonl", val)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared", type=Path, default=ROOT / "data/v2/shared/shared.jsonl")
    parser.add_argument("--extraction-topup", type=Path, default=ROOT / "data/v2/extraction/topup.jsonl")
    parser.add_argument("--classification-topup", type=Path, default=ROOT / "data/v2/classification/topup.jsonl")
    parser.add_argument("--retrieval-topup", type=Path, default=ROOT / "data/v2/retrieval/topup.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "data/v2/splits")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    build_extraction_splits(args.shared, args.extraction_topup, args.out, seed=args.seed)
    build_classification_splits(args.shared, args.classification_topup, args.out, seed=args.seed)
    build_retrieval_splits(args.shared, args.retrieval_topup, args.out, seed=args.seed)
    print(f"splits written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
