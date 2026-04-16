"""Append batch_{N}.tmp.jsonl files (N = 142..237) into shared.jsonl.

Replaces scripts/aggregate_shared_batches.py for this session — the
difflib-based aggregator crashes mid-run on Python 3.14
(see memory/debug_aggregator_difflib_python314.md).

This appender is exact-match only: skip if id already exists in
shared.jsonl, skip if text exactly matches any existing text.
Any batch row that fails validate_v2 is dropped to
data/v2/failed/append_skips_2026-04-16.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_v2 import load_taxonomy, validate_shared_row

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
BATCH_DIR = ROOT / "data" / "v2" / "shared"
SKIPS = ROOT / "data" / "v2" / "failed" / "append_skips_2026-04-16.jsonl"
DROPS = ROOT / "data" / "v2" / "failed" / "invalid_offsets.jsonl"
START = 142
END = 281  # inclusive


def main() -> int:
    taxonomy = load_taxonomy()

    existing: dict[str, dict] = {}
    existing_texts: set[str] = set()
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            existing[row["id"]] = row
            existing_texts.add(row["text"])
    print(f"loaded shared.jsonl: {len(existing)} rows")

    SKIPS.parent.mkdir(parents=True, exist_ok=True)
    DROPS.parent.mkdir(parents=True, exist_ok=True)
    skip_f = SKIPS.open("w", encoding="utf-8")
    drop_f = DROPS.open("w", encoding="utf-8")

    appended = 0
    skipped_id = 0
    skipped_text = 0
    dropped = 0
    remap_entity = {
        "utility": "tool",
        "lib": "library",
        "product": "tool",
        "hardware": "infrastructure",
        "vendor": "organization",
        "application": "tool",
        "endpoint": "tool",
        "location": "place",
        "version": "config",
        "component": "infrastructure",
        "document": "publication",
        "driver": "tool",
        "software": "tool",
        "architecture": "algorithm",
        "crd": "concept",
        "resource": "concept",
        "standard": "publication",
        "module": "library",
        "plugin": "library",
        "format": "technology",
        "feature": "method",
        "model": "technology",
        "directory": "file",
        "brand": "organization",
        "material": "technology",
        "region": "place",
        "dataset": "tool",
        "number": "concept",
        "award": "concept",
        "org": "organization",
        "role": "concept",
        "problem": "concept",
        "milestone": "concept",
        "technique": "method",
        "plant": "concept",
        "organism": "concept",
        "exercise": "activity",
        "equipment": "tool",
        "program": "method",
    }
    remap_relation = {
        "INTEGRATES_WITH": "COMMUNICATES_WITH",
        "ENABLES": "SUPPORTS",
        "REPLICATES": "COMMUNICATES_WITH",
        "CREATED_BY": "AUTHORED_BY",
        "BLOCKS": "CONTRADICTS",
        "CREATED": "PRODUCES",
        "CREATES": "PRODUCES",
        "FEEDS": "PRODUCES",
        "DERIVES_FROM": "BUILDS_ON",
        "REFERENCES": "RELATED_TO",
        "BREAKS": "CAUSES",
        "AUTHORED": "AUTHORED_BY",
        "AUTHORS": "AUTHORED_BY",
        "ALIAS_OF": "RELATED_TO",
        "COUNTERFEITS": "RELATED_TO",
        "ORIGINATES_FROM": "LOCATED_IN",
        "RELATES_TO": "RELATED_TO",
        "OWNS": "WORKS_AT",
        "COUPLES_WITH": "DEPENDS_ON",
        "ALIAS": "RELATED_TO",
        "PART_OF": "HAS_PART",
        "DESCRIBES": "APPLIES_TO",
        "CONTRASTS_WITH": "CONTRADICTS",
        "ABBREVIATES": "RELATED_TO",
        "COMBINES_WITH": "RELATED_TO",
        "FEEDS_INTO": "PRODUCES",
        "INTRODUCES": "PRODUCES",
        "IMPLIES": "CAUSES",
        "DISCOVERED": "AUTHORED_BY",
        "PROPOSES": "AUTHORED_BY",
        "PROPOSED": "AUTHORED_BY",
        "FOUNDED": "WORKS_AT",
    }

    for n in range(START, END + 1):
        path = BATCH_DIR / f"batch_{n:03d}.tmp.jsonl"
        if not path.exists():
            print(f"missing batch_{n:03d}, skipping")
            continue
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as e:
                    skip_f.write(json.dumps({"batch": n, "line": line_no,
                                             "reason": f"bad json: {e}"}) + "\n")
                    dropped += 1
                    continue

                # id + text dedupe
                if row["id"] in existing:
                    skipped_id += 1
                    skip_f.write(json.dumps({"batch": n, "line": line_no,
                                             "id": row["id"],
                                             "reason": "duplicate id"}) + "\n")
                    continue
                if row["text"] in existing_texts:
                    skipped_text += 1
                    skip_f.write(json.dumps({"batch": n, "line": line_no,
                                             "id": row["id"],
                                             "reason": "duplicate text"}) + "\n")
                    continue

                # remap bad types before validation
                for ent in row.get("entities", []):
                    if ent.get("type") in remap_entity:
                        ent["type"] = remap_entity[ent["type"]]
                for rel in row.get("relationships", []):
                    if rel.get("type") in remap_relation:
                        rel["type"] = remap_relation[rel["type"]]

                result = validate_shared_row(row, taxonomy)
                if not result.ok:
                    drop_f.write(json.dumps({"batch": n, "line": line_no,
                                             "id": row["id"],
                                             "errors": result.errors}) + "\n")
                    dropped += 1
                    continue

                existing[row["id"]] = row
                existing_texts.add(row["text"])
                appended += 1

    # write combined shared.jsonl preserving insertion order of existing + appended
    tmp = SHARED.with_suffix(".jsonl.new")
    with tmp.open("w", encoding="utf-8") as f:
        for row in existing.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(SHARED)

    skip_f.close()
    drop_f.close()

    print(f"appended: {appended}")
    print(f"skipped (duplicate id): {skipped_id}")
    print(f"skipped (duplicate text): {skipped_text}")
    print(f"dropped (validation): {dropped}")
    print(f"final shared.jsonl size: {len(existing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
