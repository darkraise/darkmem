# fine-tuning/scripts/audit_existing.py
"""Sample and score existing corpora against the v2 schema.

Usage:
    python -m scripts.audit_existing \
        --source data/validated/all.jsonl --kind shared --out reports/audit_extraction.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_v2 import (
    load_taxonomy,
    validate_shared_row,
    validate_extraction_topup_row,
    validate_classification_topup_row,
    validate_retrieval_topup_row,
)


@dataclass
class SampleResult:
    total: int
    passed: int
    failures: list[tuple[int, list[str]]] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def sample_jsonl(path: Path, size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if size >= len(rows):
        return rows
    return rng.sample(rows, size)


def score_sample(sample: list[dict], kind: str) -> SampleResult:
    taxonomy = load_taxonomy()
    validators = {
        "shared": validate_shared_row,
        "extraction": validate_extraction_topup_row,
        "classification": validate_classification_topup_row,
        "retrieval": validate_retrieval_topup_row,
    }
    validator = validators[kind]
    total = len(sample)
    passed = 0
    failures: list[tuple[int, list[str]]] = []
    for i, row in enumerate(sample):
        result = validator(row, taxonomy)
        if result.ok:
            passed += 1
        else:
            failures.append((i, result.errors))
    return SampleResult(total=total, passed=passed, failures=failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--kind", required=True, choices=["shared", "extraction", "classification", "retrieval"])
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sample = sample_jsonl(args.source, size=args.size, seed=args.seed)
    result = score_sample(sample, kind=args.kind)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "source": str(args.source),
                "kind": args.kind,
                "total": result.total,
                "passed": result.passed,
                "pass_rate": result.pass_rate,
                "failures_head": result.failures[:20],
            },
            f,
            indent=2,
        )
    print(f"{args.source}: {result.passed}/{result.total} passed ({result.pass_rate:.2%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
