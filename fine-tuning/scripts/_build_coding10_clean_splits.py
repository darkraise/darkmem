"""Rebuild coding-10 splits from the RELABELED corpus at
data/v2/shared/shared_coding10_clean.jsonl.

Produces:
  data/splits/coding10clean_train.jsonl / _val / _test       (GLiNER tokenized)
  data/splits/coding10clean_train_canon.jsonl / _val / _test (canonical eval)

Same stratification seed (42) and fractions (80/10/10) as the unclean version.
Entities in the clean file are already in 10-type form.
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

CLEAN = ROOT / "data" / "v2" / "shared" / "shared_coding10_clean.jsonl"
SPLITS_DIR = ROOT / "data" / "splits"
CODING_DOMAINS = {"technical", "ai_coding", "cross"}
SEED = 42


def to_gliner(row: dict) -> dict | None:
    text = row["text"]
    char_ents = [{"start": e["start"], "end": e["end"], "label": e["type"]}
                 for e in row["entities"]]
    tokens, ner = _char_spans_to_token_spans(text, char_ents)
    if not ner:
        return None
    return {"tokenized_text": tokens, "ner": ner}


def canonical(row: dict) -> dict:
    return {
        "id": row["id"],
        "domain": row["domain"],
        "text": row["text"],
        "memory_type": row["memory_type"],
        "entities": row["entities"],
        "relationships": row["relationships"],
    }


def stratified_split(rows: list[dict], seed: int) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get("memory_type", "?")].append(r)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    split = {"train": [], "val": [], "test": []}
    for grp_key in sorted(groups):
        items = groups[grp_key]
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
    rows_all: list[dict] = []
    with CLEAN.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows_all.append(json.loads(line))

    rows = [r for r in rows_all if r.get("domain") in CODING_DOMAINS]
    rows = [r for r in rows if r.get("entities")]
    print(f"loaded clean corpus: {len(rows_all)} total, "
          f"{len(rows)} coding + has-entities")

    tc = Counter()
    for r in rows:
        for e in r["entities"]:
            tc[e["type"]] += 1
    print("\nType distribution (pre-split):")
    total = sum(tc.values())
    for t, n in tc.most_common():
        print(f"  {t:10s}  {n:6,}  ({n/total*100:.1f}%)")

    split = stratified_split(rows, seed=SEED)
    for s, rs in split.items():
        print(f"\n{s}: {len(rs)} rows")

    for s in ("train", "val", "test"):
        rs = split[s]
        tok = [to_gliner(r) for r in rs]
        tok = [t for t in tok if t is not None]
        write_jsonl(SPLITS_DIR / f"coding10clean_{s}.jsonl", tok)
        write_jsonl(SPLITS_DIR / f"coding10clean_{s}_canon.jsonl",
                    [canonical(r) for r in rs])
        print(f"wrote coding10clean_{s}.jsonl ({len(tok)} tokenized) + "
              f"coding10clean_{s}_canon.jsonl ({len(rs)} canonical)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
