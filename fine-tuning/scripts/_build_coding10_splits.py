"""Build a coding-scoped, 10-type-consolidated split of the 14k shared corpus.

Produces:
  data/splits/coding10_train.jsonl      — GLiNER tokenized ({tokenized_text, ner})
  data/splits/coding10_val.jsonl
  data/splits/coding10_test.jsonl
  data/splits/coding10_train_canon.jsonl — canonical eval schema ({id, text, entities, ...})
  data/splits/coding10_val_canon.jsonl
  data/splits/coding10_test_canon.jsonl

Filters:
  - Include only rows with domain in {technical, ai_coding, cross}
  - Remap every entity to the 10-type taxonomy below
  - Drop entities whose original type maps to DROP
  - After remap, drop rows that end up with 0 entities (GLiNER crashes on empty-ner batches)

Stratified by memory_type. Uses the same inclusive-end token-span helper from
scripts.validate_data as the v2 restratify did (commit 7ccbf32 fix).
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

CODING_DOMAINS = {"technical", "ai_coding", "cross"}

TYPE_MAP = {
    # tool
    "library": "tool", "framework": "tool", "tool": "tool",
    "technology": "tool", "pattern": "tool",
    # service
    "service": "service", "platform": "service",
    "infrastructure": "service", "api": "service",
    # database (kept separate)
    "database": "database",
    # language
    "language": "language",
    # protocol
    "protocol": "protocol",
    # project
    "project": "project",
    # algorithm
    "algorithm": "algorithm", "method": "algorithm",
    # artifact (code-specific items)
    "file": "artifact", "command": "artifact",
    "config": "artifact", "error": "artifact",
    # concept (abstract fallback)
    "concept": "concept", "theory": "concept", "field": "concept",
    "publication": "concept", "finding": "concept", "claim": "concept",
    # entity (non-code named things)
    "person": "entity", "organization": "entity", "date": "entity",
    "place": "entity", "event": "entity",
    # drop — not useful for coding memory
    "food": None, "emotion": None, "hobby": None,
    "activity": None, "goal": None,
}

ALLOWED_TYPES = sorted(set(v for v in TYPE_MAP.values() if v))

SEED = 42
FRACS = {"train": 0.80, "val": 0.10, "test": 0.10}


def remap_entities(entities: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in entities or []:
        t = TYPE_MAP.get(e.get("type"))
        if not t:
            continue
        out.append({
            "name": e.get("name") or "",
            "type": t,
            "start": e["start"],
            "end": e["end"],
        })
    return out


def remap_relationships(rels: list[dict], entity_names: set[str]) -> list[dict]:
    # Keep relationships only if both endpoints survived the remap.
    out: list[dict] = []
    for r in rels or []:
        if r.get("source") in entity_names and r.get("target") in entity_names:
            out.append({
                "source": r["source"],
                "target": r["target"],
                "type": r["type"],
            })
    return out


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


def stratified_split(rows: list[dict], key: str, seed: int) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get(key, "?")].append(r)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    split = {"train": [], "val": [], "test": []}
    for grp_key in sorted(groups):
        items = groups[grp_key]
        n = len(items)
        n_val = max(1, int(round(n * FRACS["val"]))) if n >= 10 else 0
        n_test = max(1, int(round(n * FRACS["test"]))) if n >= 10 else 0
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
    rows_in: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows_in.append(json.loads(line))

    before = len(rows_in)
    rows = [r for r in rows_in if r.get("domain") in CODING_DOMAINS]
    print(f"domain filter: {before} -> {len(rows)} rows ({len(rows)/before*100:.1f}%)")

    # Remap entities + relationships + filter empty
    kept: list[dict] = []
    dropped_empty = 0
    for r in rows:
        ents = remap_entities(r.get("entities"))
        if not ents:
            dropped_empty += 1
            continue
        ent_names = {e["name"] for e in ents}
        rels = remap_relationships(r.get("relationships"), ent_names)
        kept.append({
            "id": r["id"],
            "domain": r["domain"],
            "text": r["text"],
            "memory_type": r["memory_type"],
            "entities": ents,
            "relationships": rels,
        })
    print(f"post-remap: {len(kept)} rows (dropped {dropped_empty} rows with zero entities after remap)")

    # Entity type distribution
    tc = Counter()
    for r in kept:
        for e in r["entities"]:
            tc[e["type"]] += 1
    print("\nType distribution after remap:")
    total = sum(tc.values())
    for t, n in tc.most_common():
        print(f"  {t:12s}  {n:6,}  ({n/total*100:.1f}%)")
    print(f"  total entities: {total:,}")

    # Stratified split
    split = stratified_split(kept, key="memory_type", seed=SEED)
    for s, rows in split.items():
        print(f"\n{s}: {len(rows)} rows")
        mt = Counter(r["memory_type"] for r in rows)
        for m, n in mt.most_common():
            print(f"  {m}: {n}")

    # Write: GLiNER tokenized + canonical
    for s in ("train", "val", "test"):
        rows_s = split[s]
        tok = [to_gliner(r) for r in rows_s]
        tok = [t for t in tok if t is not None]
        write_jsonl(SPLITS_DIR / f"coding10_{s}.jsonl", tok)
        write_jsonl(SPLITS_DIR / f"coding10_{s}_canon.jsonl",
                    [canonical(r) for r in rows_s])
        print(f"wrote coding10_{s}.jsonl ({len(tok)} tokenized rows) + "
              f"coding10_{s}_canon.jsonl ({len(rows_s)} canonical rows)")

    print(f"\nAllowed types ({len(ALLOWED_TYPES)}): {ALLOWED_TYPES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
