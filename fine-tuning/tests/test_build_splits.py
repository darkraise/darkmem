from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_splits import build_extraction_splits, build_classification_splits, build_retrieval_splits


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_extraction_splits_deterministic_and_stratified(tmp_path: Path):
    shared_path = tmp_path / "shared.jsonl"
    topup_path = tmp_path / "extraction_topup.jsonl"
    shared = [
        {"id": f"s-{i}", "domain": "technical", "text": "a", "memory_type": "fact", "noise": False, "entities": [], "relationships": []}
        for i in range(400)
    ] + [
        {"id": f"s-{i}", "domain": "personal", "text": "a", "memory_type": "fact", "noise": False, "entities": [], "relationships": []}
        for i in range(400, 800)
    ]
    topup = [
        {"id": f"t-{i}", "domain": "technical", "text": "a", "memory_type": "fact", "entities": [], "relationships": []}
        for i in range(200)
    ]
    _write(shared_path, shared)
    _write(topup_path, topup)

    out = tmp_path / "splits"
    build_extraction_splits(shared_path, topup_path, out, seed=42)
    build_extraction_splits(shared_path, topup_path, out / "rerun", seed=42)

    a = (out / "extraction_train.jsonl").read_text()
    b = (out / "rerun" / "extraction_train.jsonl").read_text()
    assert a == b   # determinism

    train_lines = a.strip().splitlines()
    val_lines = (out / "extraction_val.jsonl").read_text().strip().splitlines()
    test_lines = (out / "extraction_test.jsonl").read_text().strip().splitlines()
    total = len(train_lines) + len(val_lines) + len(test_lines)
    assert total == 1000
    # Approximate 80/10/10 split
    assert 780 <= len(train_lines) <= 820
    assert 80 <= len(val_lines) <= 120
    assert 80 <= len(test_lines) <= 120


def test_retrieval_train_includes_two_queries_per_shared_plus_topup(tmp_path: Path):
    shared_path = tmp_path / "shared.jsonl"
    topup_path = tmp_path / "retrieval_topup.jsonl"
    shared = [
        {
            "id": f"s-{i}",
            "domain": "technical",
            "text": f"text-{i}",
            "memory_type": "fact",
            "noise": False,
            "entities": [{"name": "E", "type": "project", "start": 0, "end": 1}],
            "relationships": [],
            "queries": [
                {"form": "question", "text": f"q-{i}-a"},
                {"form": "keyword", "text": f"q-{i}-b"},
            ],
        }
        for i in range(100)
    ]
    topup = [
        {
            "id": f"rt-{i}",
            "source_id": f"s-{i}",
            "query": f"typo-{i}",
            "positive": f"text-{i}",
            "query_kind": "typo",
        }
        for i in range(30)
    ]
    _write(shared_path, shared)
    _write(topup_path, topup)

    out = tmp_path / "splits"
    build_retrieval_splits(shared_path, topup_path, out, seed=42, val_fraction=0.1)
    train = (out / "retrieval_train.jsonl").read_text().strip().splitlines()
    val = (out / "retrieval_val.jsonl").read_text().strip().splitlines()
    total = len(train) + len(val)
    assert total == 100 * 2 + 30   # 230
    assert abs(len(val) / total - 0.1) < 0.05
