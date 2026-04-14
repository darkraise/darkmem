# fine-tuning/scripts/validate_v2.py
"""Mechanical validator for v2 fine-tuning corpora.

Validates shared rows, extraction top-up rows, classification top-up rows,
and retrieval top-up rows against the schema defined in the design spec.
No model calls — pure schema + offset + taxonomy membership checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "taxonomy_v2.yaml"


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def load_taxonomy(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Flatten entity_types across domains into a single set for fast membership
    entity_types: set[str] = set()
    for types in data["entity_types"].values():
        entity_types.update(types)
    relation_types = set(data["relation_types"]["core"]) | set(data["relation_types"]["extended"])
    data["_entity_type_set"] = entity_types
    data["_relation_type_set"] = relation_types
    data["_memory_type_set"] = set(data["memory_types"])
    data["_allowed_domains"] = {"technical", "ai_coding", "personal", "knowledge", "cross", "noise"}
    return data


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _validate_entities(row: dict, taxonomy: dict) -> list[str]:
    errs: list[str] = []
    text = row["text"]
    for i, ent in enumerate(row.get("entities", [])):
        required = {"name", "type", "start", "end"}
        missing = required - ent.keys()
        if missing:
            errs.append(f"entity[{i}] missing fields: {sorted(missing)}")
            continue
        if ent["type"] not in taxonomy["_entity_type_set"]:
            errs.append(f"entity[{i}] unknown entity type: {ent['type']}")
        start, end = ent["start"], ent["end"]
        if not isinstance(start, int) or not isinstance(end, int):
            errs.append(f"entity[{i}] start/end must be int")
            continue
        if start < 0 or end > len(text) or start >= end:
            errs.append(f"entity[{i}] bad offset range [{start},{end}] for text length {len(text)}")
            continue
        if text[start:end] != ent["name"]:
            errs.append(
                f"entity[{i}] offset mismatch: text[{start}:{end}]={text[start:end]!r} != name={ent['name']!r}"
            )
    return errs


def _validate_relationships(row: dict, taxonomy: dict) -> list[str]:
    errs: list[str] = []
    entity_names = {e["name"] for e in row.get("entities", [])}
    for i, rel in enumerate(row.get("relationships", [])):
        required = {"source", "target", "type"}
        missing = required - rel.keys()
        if missing:
            errs.append(f"relationship[{i}] missing fields: {sorted(missing)}")
            continue
        if rel["source"] not in entity_names:
            errs.append(f"relationship[{i}] source endpoint not in entity list: {rel['source']}")
        if rel["target"] not in entity_names:
            errs.append(f"relationship[{i}] target endpoint not in entity list: {rel['target']}")
        if rel["type"] not in taxonomy["_relation_type_set"]:
            errs.append(f"relationship[{i}] unknown relation type: {rel['type']}")
    return errs


def _validate_queries(row: dict, taxonomy: dict) -> list[str]:
    errs: list[str] = []
    queries = row.get("queries")
    if queries is None:
        return errs   # queries are optional on shared rows only when omitted explicitly (noise)
    if len(queries) != 2:
        errs.append(f"queries must have exactly 2 items, got {len(queries)}")
        return errs
    forms = {q.get("form") for q in queries}
    if forms != {"question", "keyword"}:
        errs.append(f"queries must have forms {{question, keyword}}, got {forms}")
    text = row["text"]
    max_q_sim = taxonomy["validator"]["max_query_similarity_to_source"]
    max_pair_sim = taxonomy["validator"]["max_query_pair_similarity"]
    for i, q in enumerate(queries):
        if _ratio(q["text"], text) >= max_q_sim:
            errs.append(f"queries[{i}] too similar to source (verbatim quote) — normalized ratio >= {max_q_sim}")
    if len(queries) == 2 and _ratio(queries[0]["text"], queries[1]["text"]) >= max_pair_sim:
        errs.append(f"queries[0] and queries[1] too similar — normalized ratio >= {max_pair_sim}")
    return errs


def validate_shared_row(row: dict, taxonomy: dict) -> ValidationResult:
    errs: list[str] = []
    required = {"id", "domain", "text", "memory_type", "noise", "entities", "relationships"}
    missing = required - row.keys()
    if missing:
        return ValidationResult(ok=False, errors=[f"missing required fields: {sorted(missing)}"])
    if row["domain"] not in taxonomy["_allowed_domains"]:
        errs.append(f"unknown domain: {row['domain']}")
    if row["memory_type"] not in taxonomy["_memory_type_set"]:
        errs.append(f"unknown memory_type: {row['memory_type']}")
    errs += _validate_entities(row, taxonomy)
    errs += _validate_relationships(row, taxonomy)
    if not row["noise"] and not row["entities"]:
        errs.append("non-noise shared row has zero entities")
    if "queries" in row:
        errs += _validate_queries(row, taxonomy)
    return ValidationResult(ok=not errs, errors=errs)


_EXTRACTION_ALLOWED = {"id", "domain", "text", "memory_type", "entities", "relationships"}
_CLASSIFICATION_ALLOWED = {"id", "domain", "text", "memory_type", "pair_id"}
_RETRIEVAL_ALLOWED = {"id", "source_id", "query", "positive", "negative", "query_kind"}


def _foreign_fields(row: dict, allowed: set[str]) -> list[str]:
    foreign = set(row.keys()) - allowed
    return [f"foreign field on top-up row: {k}" for k in sorted(foreign)]


def validate_extraction_topup_row(row: dict, taxonomy: dict) -> ValidationResult:
    errs = _foreign_fields(row, _EXTRACTION_ALLOWED)
    required = {"id", "domain", "text", "memory_type", "entities", "relationships"}
    missing = required - row.keys()
    if missing:
        errs.append(f"missing required fields: {sorted(missing)}")
        return ValidationResult(ok=False, errors=errs)
    if row["memory_type"] not in taxonomy["_memory_type_set"]:
        errs.append(f"unknown memory_type: {row['memory_type']}")
    errs += _validate_entities(row, taxonomy)
    errs += _validate_relationships(row, taxonomy)
    return ValidationResult(ok=not errs, errors=errs)


def validate_classification_topup_row(row: dict, taxonomy: dict) -> ValidationResult:
    errs = _foreign_fields(row, _CLASSIFICATION_ALLOWED)
    required = {"id", "domain", "text", "memory_type"}
    missing = required - row.keys()
    if missing:
        errs.append(f"missing required fields: {sorted(missing)}")
        return ValidationResult(ok=False, errors=errs)
    if row["memory_type"] not in taxonomy["_memory_type_set"]:
        errs.append(f"unknown memory_type: {row['memory_type']}")
    return ValidationResult(ok=not errs, errors=errs)


def validate_retrieval_topup_row(row: dict, taxonomy: dict) -> ValidationResult:
    errs = _foreign_fields(row, _RETRIEVAL_ALLOWED)
    required = {"id", "source_id", "query", "query_kind"}
    missing = required - row.keys()
    if missing:
        errs.append(f"missing required fields: {sorted(missing)}")
        return ValidationResult(ok=False, errors=errs)
    allowed_kinds = {"paraphrase", "acronym", "typo", "code-switch", "multi-sentence", "hard-negative"}
    if row["query_kind"] not in allowed_kinds:
        errs.append(f"unknown query_kind: {row['query_kind']}")
    if row["query_kind"] == "hard-negative":
        if "negative" not in row:
            errs.append("hard-negative row requires 'negative' field")
    else:
        if "positive" not in row:
            errs.append("non-hard-negative row requires 'positive' field")
    return ValidationResult(ok=not errs, errors=errs)


def validate_file(path: Path, kind: str, taxonomy: dict) -> tuple[int, int, list[tuple[int, list[str]]]]:
    """Return (total, passed, failures). kind: shared|extraction|classification|retrieval."""
    validators = {
        "shared": validate_shared_row,
        "extraction": validate_extraction_topup_row,
        "classification": validate_classification_topup_row,
        "retrieval": validate_retrieval_topup_row,
    }
    validator = validators[kind]
    total = 0
    passed = 0
    failures: list[tuple[int, list[str]]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                failures.append((i, [f"invalid JSON: {e}"]))
                continue
            result = validator(row, taxonomy)
            if result.ok:
                passed += 1
            else:
                failures.append((i, result.errors))
    return total, passed, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--kind", required=True, choices=["shared", "extraction", "classification", "retrieval"])
    parser.add_argument("--failed-dir", type=Path, default=None)
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    total, passed, failures = validate_file(args.path, args.kind, taxonomy)
    print(f"{args.path}: {passed}/{total} passed, {len(failures)} failed")
    if failures and args.failed_dir:
        args.failed_dir.mkdir(parents=True, exist_ok=True)
        out = args.failed_dir / f"{args.path.stem}.failures.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for line_no, errs in failures:
                f.write(json.dumps({"line": line_no, "errors": errs}) + "\n")
        print(f"wrote failures to {out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
