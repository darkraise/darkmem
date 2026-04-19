"""Schema validator for the 5-type coding-native relation corpus.

Same semantics as `_validate_relaug.py` but with the 5-type relation set.
Useful for:

  - Validating newly generated synth rows targeting a 5-type relation.
  - Sanity-checking coding5clean splits after rebuild.

Usage:
    python -m fine-tuning.scripts._validate_schema5 \
        --input data/splits/coding5clean_train_canon.jsonl \
        --survivors-dir runs/2026-04-19-schema-v2/survivors \
        --rejected-dir runs/2026-04-19-schema-v2/rejected

    # With a target-relation gate (e.g. to filter synth rows for IS_A):
    python -m fine-tuning.scripts._validate_schema5 \
        --input <generated.jsonl> \
        --target-relation IS_A \
        --survivors-dir <dir> \
        --rejected-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ENTITY_TYPES = {
    "tool", "service", "database", "language", "protocol",
    "project", "algorithm", "artifact", "concept", "entity",
}

RELATION_TYPES_5 = {"USES", "REPLACES", "IS_A", "DEPLOYED_ON", "CAUSES"}

MEMORY_TYPES = {
    "fact", "decision", "preference", "problem",
    "reference", "architecture", "milestone",
}

REQUIRED_FIELDS = {"text", "entities", "relationships", "memory_type", "domain"}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def validate_row(row: dict[str, Any], target_relation: str | None) -> tuple[bool, str]:
    missing = REQUIRED_FIELDS - row.keys()
    if missing:
        return False, f"missing_fields:{sorted(missing)}"

    text = row["text"]
    if not isinstance(text, str):
        return False, "text_not_string"

    if row["memory_type"] not in MEMORY_TYPES:
        return False, f"bad_memory_type:{row['memory_type']}"

    entities = row.get("entities") or []
    if not isinstance(entities, list) or not entities:
        return False, "no_entities"

    seen_slots: set[tuple[str, int]] = set()
    entity_names: set[str] = set()
    for i, e in enumerate(entities):
        name = e.get("name")
        etype = e.get("type")
        start = e.get("start")
        end = e.get("end")
        if not isinstance(name, str) or not name:
            return False, f"entity_{i}_bad_name"
        if etype not in ENTITY_TYPES:
            return False, f"entity_{i}_bad_type:{etype}"
        if not isinstance(start, int) or not isinstance(end, int):
            return False, f"entity_{i}_bad_offsets"
        if start < 0 or end > len(text) or start >= end:
            return False, f"entity_{i}_oob_offsets:{start}-{end}"
        if text[start:end] != name:
            return False, f"entity_{i}_offset_mismatch:text={text[start:end]!r}!=name={name!r}"
        norm = e.get("normalized_name") or _normalize(name)
        slot = (norm, start)
        if slot in seen_slots:
            return False, f"entity_{i}_duplicate_slot:{slot}"
        seen_slots.add(slot)
        entity_names.add(name)

    relationships = row.get("relationships") or []
    if not isinstance(relationships, list):
        return False, "relationships_not_list"
    has_target = target_relation is None
    for j, r in enumerate(relationships):
        rtype = r.get("type")
        if rtype not in RELATION_TYPES_5:
            return False, f"rel_{j}_bad_type:{rtype}"
        src = r.get("source")
        tgt = r.get("target")
        if src not in entity_names or tgt not in entity_names:
            return False, f"rel_{j}_names_not_in_entities:{src}->{tgt}"
        if src == tgt:
            return False, f"rel_{j}_self_loop:{src}"
        if target_relation and rtype == target_relation:
            has_target = True
    if not has_target:
        return False, f"no_target_relation:{target_relation}"

    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument(
        "--target-relation",
        default=None,
        choices=sorted(RELATION_TYPES_5),
        help="Require at least one relation of this type per row (optional).",
    )
    ap.add_argument("--survivors-dir", required=True, type=Path)
    ap.add_argument("--rejected-dir", required=True, type=Path)
    args = ap.parse_args()

    args.survivors_dir.mkdir(parents=True, exist_ok=True)
    args.rejected_dir.mkdir(parents=True, exist_ok=True)

    stem = args.input.stem
    surv_path = args.survivors_dir / f"{stem}.jsonl"
    rej_path = args.rejected_dir / f"{stem}.jsonl"

    n_total = 0
    n_survived = 0
    reason_counts: dict[str, int] = {}

    with (
        args.input.open("r", encoding="utf-8") as fin,
        surv_path.open("w", encoding="utf-8") as fsurv,
        rej_path.open("w", encoding="utf-8") as frej,
    ):
        for line in fin:
            if not line.strip():
                continue
            n_total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                reason = f"json_error:{e.msg}"
                frej.write(json.dumps({"_reject_reason": reason, "_raw": line.rstrip()}, ensure_ascii=False) + "\n")
                key = reason.split(":", 1)[0]
                reason_counts[key] = reason_counts.get(key, 0) + 1
                continue
            ok, reason = validate_row(row, args.target_relation)
            if ok:
                n_survived += 1
                fsurv.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                key = reason.split(":", 1)[0]
                reason_counts[key] = reason_counts.get(key, 0) + 1
                row["_reject_reason"] = reason
                frej.write(json.dumps(row, ensure_ascii=False) + "\n")

    survival = n_survived / n_total if n_total else 0.0
    print(f"{args.input.name}: {n_survived}/{n_total} survived ({survival*100:.1f}%)")
    for k, v in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"  rejected {k:30s} {v}")
    print(f"  survivors -> {surv_path}")
    print(f"  rejected  -> {rej_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
