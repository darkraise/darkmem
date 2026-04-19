"""Produce a version of data/splits/test.jsonl (2k v2) with its entity types
remapped into the 10-type coding taxonomy.

Output:
  data/splits/test_coding10.jsonl — same row ids and text as test.jsonl,
  but entity types collapsed to {tool, service, database, language, protocol,
  project, algorithm, artifact, concept, entity}. Entities whose original type
  drops out (food, emotion, hobby, activity, goal) are removed.

This lets us score *existing* predictions (from any model that wrote preds
against test.jsonl) under the new 10-type gold without re-running inference.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._build_coding10_splits import TYPE_MAP

IN_PATH = ROOT / "data" / "splits" / "test.jsonl"
OUT_PATH = ROOT / "data" / "splits" / "test_coding10.jsonl"


def main() -> int:
    kept = 0
    total_in = 0
    with IN_PATH.open("r", encoding="utf-8") as fi, OUT_PATH.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            total_in += 1
            row = json.loads(line)
            ents = []
            for e in row.get("entities") or []:
                nt = TYPE_MAP.get(e.get("type"))
                if not nt:
                    continue
                ents.append({
                    "name": e.get("name") or "",
                    "type": nt,
                    **({"start": e["start"], "end": e["end"]} if "start" in e else {}),
                })
            ent_names = {e["name"] for e in ents}
            rels = [r for r in row.get("relationships") or []
                    if r.get("source") in ent_names and r.get("target") in ent_names]
            out = {
                "id": row["id"],
                "domain": row.get("domain"),
                "text": row["text"],
                "memory_type": row.get("memory_type"),
                "entities": ents,
                "relationships": rels,
            }
            fo.write(json.dumps(out, ensure_ascii=False) + "\n")
            kept += 1
    print(f"wrote {OUT_PATH} ({kept}/{total_in} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
