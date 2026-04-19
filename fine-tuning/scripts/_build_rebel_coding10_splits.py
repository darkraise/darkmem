"""Build REBEL seq2seq splits from the coding-10 canonical corpus with
relation types consolidated from 30 to 10 coding-relevant ones.

RELATION MAP (30 -> 10):
  USES           = USES, CONFIGURES, APPLIES_TO, COMMUNICATES_WITH, IMPLEMENTS
  DEPENDS_ON     = DEPENDS_ON
  REPLACES       = REPLACES, IMPROVES_ON, BUILDS_ON
  IS_A           = IS_A
  HAS_PART       = HAS_PART, EXTENDS
  DEPLOYED_ON    = DEPLOYED_ON, LOCATED_IN
  CAUSES         = CAUSES, PRODUCES, FIXES
  AUTHORED_BY    = AUTHORED_BY, PUBLISHED_IN, WORKS_AT
  HAPPENED_ON    = HAPPENED_ON, VISITED, LIVES_IN
  RELATED_TO     = RELATED_TO, KNOWS, SUPPORTS, CONTRADICTS, PREFERS,
                   FEELS_ABOUT, PLANS_TO

Inputs:
  data/splits/coding10clean_{train,val,test}_canon.jsonl

Outputs:
  data/splits/rebel_coding10_{train,val,test}.jsonl — REBEL {input, output}
  data/splits/rebel_coding10_{train,val,test}_gold.jsonl — canonical for eval

Skips rows with empty relationships after remap.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"

REL_MAP = {
    # USES cluster
    "USES": "USES",
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "IMPLEMENTS": "USES",
    # DEPENDS_ON
    "DEPENDS_ON": "DEPENDS_ON",
    # REPLACES cluster
    "REPLACES": "REPLACES",
    "IMPROVES_ON": "REPLACES",
    "BUILDS_ON": "REPLACES",
    # IS_A
    "IS_A": "IS_A",
    # HAS_PART cluster
    "HAS_PART": "HAS_PART",
    "EXTENDS": "HAS_PART",
    # DEPLOYED_ON
    "DEPLOYED_ON": "DEPLOYED_ON",
    "LOCATED_IN": "DEPLOYED_ON",
    # CAUSES cluster
    "CAUSES": "CAUSES",
    "PRODUCES": "CAUSES",
    "FIXES": "CAUSES",
    # AUTHORED_BY cluster
    "AUTHORED_BY": "AUTHORED_BY",
    "PUBLISHED_IN": "AUTHORED_BY",
    "WORKS_AT": "AUTHORED_BY",
    # HAPPENED_ON cluster
    "HAPPENED_ON": "HAPPENED_ON",
    "VISITED": "HAPPENED_ON",
    "LIVES_IN": "HAPPENED_ON",
    # RELATED_TO catch-all
    "RELATED_TO": "RELATED_TO",
    "KNOWS": "RELATED_TO",
    "SUPPORTS": "RELATED_TO",
    "CONTRADICTS": "RELATED_TO",
    "PREFERS": "RELATED_TO",
    "FEELS_ABOUT": "RELATED_TO",
    "PLANS_TO": "RELATED_TO",
}


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
            new_type = REL_MAP.get(rt)
            if not new_type:
                continue
            remapped.append({
                "source": rel["source"],
                "target": rel["target"],
                "type": new_type,
            })
        if not remapped:
            continue  # REBEL training skips empty-rel rows
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
    from collections import Counter
    rel_counter = Counter()
    for split in ("train", "val", "test"):
        canon = load(SPLITS / f"coding10clean_{split}_canon.jsonl")
        rebel, gold = process(canon)
        for g in gold:
            for rel in g["relationships"]:
                rel_counter[rel["type"]] += 1
        write_jsonl(SPLITS / f"rebel_coding10_{split}.jsonl", rebel)
        write_jsonl(SPLITS / f"rebel_coding10_{split}_gold.jsonl", gold)
        print(f"{split}: {len(canon)} canonical -> {len(rebel)} rel-carrying rows")
    print("\nRelation type distribution (across all splits):")
    total = sum(rel_counter.values())
    for t, n in rel_counter.most_common():
        print(f"  {t:15s} {n:5d}  ({n/total*100:.1f}%)")
    print(f"  total relations: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
