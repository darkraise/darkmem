"""Build the 5-type coding-native canonical splits from the 10-type clean corpus.

Entity taxonomy is unchanged (same 10 entity types). Only relations are remapped
via REL_MAP_5. Rows whose original relations all collapse to None are dropped;
rows that had no relations to begin with are preserved as entity-only rows,
matching the coding10 canonical behaviour.

Reads:
  data/splits/coding10clean_train_canon.jsonl         (post-relaug training source)
  data/splits/coding10clean_{val,test}_canon.jsonl    (byte-identical to pre-relaug backups)

Writes:
  data/splits/coding5clean_{train,val,test}_canon.jsonl
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._build_rebel_coding5_splits import REL_MAP_5  # noqa: E402

SPLITS = ROOT / "data" / "splits"


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def remap_relations(rels: list[dict]) -> list[dict]:
    out: list[dict] = []
    for rel in rels or []:
        rt = rel.get("type")
        new_type = REL_MAP_5.get(rt)
        if not new_type:
            continue
        out.append({
            "source": rel["source"],
            "target": rel["target"],
            "type": new_type,
        })
    return out


def process(rows: list[dict]) -> tuple[list[dict], dict[str, int], Counter[str]]:
    kept: list[dict] = []
    stats = {"total": 0, "kept": 0, "dropped_all_none": 0, "entity_only": 0}
    rel_counter: Counter[str] = Counter()
    for r in rows:
        stats["total"] += 1
        orig_rels = r.get("relationships") or []
        remapped = remap_relations(orig_rels)
        if orig_rels and not remapped:
            stats["dropped_all_none"] += 1
            continue
        if not remapped:
            stats["entity_only"] += 1
        for rel in remapped:
            rel_counter[rel["type"]] += 1
        kept.append({
            "id": r.get("id"),
            "domain": r.get("domain"),
            "text": r["text"],
            "memory_type": r.get("memory_type"),
            "entities": r.get("entities") or [],
            "relationships": remapped,
        })
        stats["kept"] += 1
    return kept, stats, rel_counter


def main() -> int:
    for split in ("train", "val", "test"):
        in_path = SPLITS / f"coding10clean_{split}_canon.jsonl"
        out_path = SPLITS / f"coding5clean_{split}_canon.jsonl"
        rows = load(in_path)
        kept, stats, rel_counter = process(rows)
        write_jsonl(out_path, kept)
        print(
            f"{split}: {stats['total']} in -> {stats['kept']} out  "
            f"(dropped_all_none={stats['dropped_all_none']}, "
            f"entity_only={stats['entity_only']})"
        )
        total = sum(rel_counter.values())
        for t, n in rel_counter.most_common():
            pct = (n / total * 100) if total else 0.0
            print(f"    {t:12s} {n:6d}  ({pct:.1f}%)")
        if total:
            print(f"    total relations: {total}")
        print(f"    wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
