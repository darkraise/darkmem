"""Build REBEL seq2seq splits on the 5-type coding-native relation schema.

RELATION MAP (30 or 10 -> 5):
  USES         = USES, CONFIGURES, APPLIES_TO, COMMUNICATES_WITH, IMPLEMENTS,
                 DEPENDS_ON, HAS_PART, EXTENDS
  REPLACES     = REPLACES, IMPROVES_ON, BUILDS_ON
  IS_A         = IS_A
  DEPLOYED_ON  = DEPLOYED_ON, LOCATED_IN
  CAUSES       = CAUSES, PRODUCES, FIXES

  Dropped (mapped to None, row skipped if nothing else survives):
    RELATED_TO, KNOWS, SUPPORTS, CONTRADICTS, PREFERS, FEELS_ABOUT, PLANS_TO,
    VISITED, LIVES_IN, HAPPENED_ON, AUTHORED_BY, PUBLISHED_IN, WORKS_AT

Single REL_MAP_5 dict handles both historical 30-type rows and post-REL_MAP
10-type rows because the keys collapse correctly in both cases.

Inputs:
  data/splits/coding5clean_{train,val,test}_canon.jsonl  (built first by
  _build_coding5_splits.py)

Outputs:
  data/splits/rebel_coding5_{train,val,test}.jsonl       — seq2seq {input, output}
  data/splits/rebel_coding5_{train,val,test}_gold.jsonl  — canonical for eval

Skips rows whose relationships all collapse to None.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"

REL_MAP_5: dict[str, str | None] = {
    # USES cluster — 30-type sources + the 10-type survivors DEPENDS_ON/HAS_PART/EXTENDS.
    "USES": "USES",
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "IMPLEMENTS": "USES",
    "DEPENDS_ON": "USES",
    "HAS_PART": "USES",
    "EXTENDS": "USES",
    # REPLACES cluster
    "REPLACES": "REPLACES",
    "IMPROVES_ON": "REPLACES",
    "BUILDS_ON": "REPLACES",
    # IS_A
    "IS_A": "IS_A",
    # DEPLOYED_ON cluster
    "DEPLOYED_ON": "DEPLOYED_ON",
    "LOCATED_IN": "DEPLOYED_ON",
    # CAUSES cluster
    "CAUSES": "CAUSES",
    "PRODUCES": "CAUSES",
    "FIXES": "CAUSES",
    # Dropped — explicit None so membership in REL_MAP_5 stays authoritative.
    "RELATED_TO": None,
    "KNOWS": None,
    "SUPPORTS": None,
    "CONTRADICTS": None,
    "PREFERS": None,
    "FEELS_ABOUT": None,
    "PLANS_TO": None,
    "VISITED": None,
    "LIVES_IN": None,
    "HAPPENED_ON": None,
    "AUTHORED_BY": None,
    "PUBLISHED_IN": None,
    "WORKS_AT": None,
}

RELATION_TYPES_5 = ("USES", "REPLACES", "IS_A", "DEPLOYED_ON", "CAUSES")


def format_input(text: str, entities: list[dict]) -> str:
    ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
    return f"{text} | Entities: {ent_str}"


def format_output(relationships: list[dict]) -> str:
    if not relationships:
        return "<triplet> NONE"
    parts = [f"<triplet> {r['source']} <subj> {r['target']} <obj> {r['type']}"
             for r in relationships]
    return " ".join(parts)


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open("r", encoding="utf-8") if l.strip()]


def process(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    rebel: list[dict] = []
    gold: list[dict] = []
    for r in rows:
        ents = r.get("entities") or []
        orig_rels = r.get("relationships") or []
        remapped = []
        for rel in orig_rels:
            rt = rel.get("type")
            new_type = REL_MAP_5.get(rt)
            if not new_type:
                continue
            remapped.append({
                "source": rel["source"],
                "target": rel["target"],
                "type": new_type,
            })
        if not remapped:
            continue
        rebel.append({
            "input": format_input(r["text"], ents),
            "output": format_output(remapped),
        })
        gold.append({
            "id": r["id"],
            "text": r["text"],
            "memory_type": r.get("memory_type"),
            "domain": r.get("domain"),
            "entities": ents,
            "relationships": remapped,
        })
    return rebel, gold


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    rel_counter: Counter[str] = Counter()
    for split in ("train", "val", "test"):
        canon_path = SPLITS / f"coding5clean_{split}_canon.jsonl"
        canon = load(canon_path)
        rebel, gold = process(canon)
        for g in gold:
            for rel in g["relationships"]:
                rel_counter[rel["type"]] += 1
        write_jsonl(SPLITS / f"rebel_coding5_{split}.jsonl", rebel)
        write_jsonl(SPLITS / f"rebel_coding5_{split}_gold.jsonl", gold)
        print(f"{split}: {len(canon)} canonical -> {len(rebel)} rel-carrying rows")
    print("\nRelation type distribution (across all splits):")
    total = sum(rel_counter.values())
    for t, n in rel_counter.most_common():
        print(f"  {t:15s} {n:5d}  ({n/total*100:.1f}%)")
    print(f"  total relations: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
