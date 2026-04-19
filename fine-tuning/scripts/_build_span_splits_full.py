"""Build span-only training splits from the FULL 14k shared corpus (all domains).

The span detector's job is binary: "is this text a named entity?" It doesn't
care about the 10-type taxonomy. Training on the whole 14k (including personal,
knowledge, cross, noise domains) gives it 2.3x more training signal than the
coding-only 6,319 rows we used previously.

Output:
  data/splits/spanfull_train.jsonl / _val / _test (GLiNER tokenized, single
  "entity" label).

Stratified by memory_type. Seed 42. Same 80/10/10 fractions.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_data import _char_spans_to_token_spans

SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
SPLITS_DIR = ROOT / "data" / "splits"
SEED = 42


def to_span_row(row: dict) -> dict | None:
    """All entity types collapse to 'entity'. Noise rows with empty entities
    are kept as negatives (empty ner list). GLiNER trainer crashes on empty
    ner; we filter those out at split-write time to be safe."""
    text = row["text"]
    char_ents = [
        {"start": e["start"], "end": e["end"], "label": "entity"}
        for e in row.get("entities") or []
    ]
    tokens, ner = _char_spans_to_token_spans(text, char_ents)
    if not ner:
        return None
    return {"tokenized_text": tokens, "ner": ner}


def stratified_split(rows: list[dict], seed: int) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get("memory_type", "?")].append(r)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    split = {"train": [], "val": [], "test": []}
    for k in sorted(groups):
        items = groups[k]
        n = len(items)
        n_val = max(1, int(round(n * 0.10))) if n >= 10 else 0
        n_test = max(1, int(round(n * 0.10))) if n >= 10 else 0
        split["test"].extend(items[:n_test])
        split["val"].extend(items[n_test:n_test + n_val])
        split["train"].extend(items[n_test + n_val:])
    for s in split:
        rng.shuffle(split[s])
    return split


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    rows: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    # Count domain distribution
    dom = Counter(r.get("domain") for r in rows)
    print(f"shared.jsonl: {len(rows)} total rows")
    for d, n in dom.most_common():
        print(f"  {d}: {n}")

    split = stratified_split(rows, seed=SEED)
    for s in ("train", "val", "test"):
        rs = split[s]
        tok = [to_span_row(r) for r in rs]
        tok = [t for t in tok if t is not None]
        write_jsonl(SPLITS_DIR / f"spanfull_{s}.jsonl", tok)
        dom_s = Counter(r.get("domain") for r in rs)
        print(f"\n{s}: {len(rs)} canonical rows -> {len(tok)} tokenized span rows")
        for d, n in dom_s.most_common():
            print(f"  {d}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
