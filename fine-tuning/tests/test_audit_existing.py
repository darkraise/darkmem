# fine-tuning/tests/test_audit_existing.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_existing import sample_jsonl, score_sample, SampleResult


def test_sample_jsonl_deterministic(tmp_path: Path):
    src = tmp_path / "src.jsonl"
    lines = [json.dumps({"id": i, "v": i * 2}) for i in range(500)]
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")

    a = sample_jsonl(src, size=50, seed=42)
    b = sample_jsonl(src, size=50, seed=42)
    assert a == b
    assert len(a) == 50


def test_sample_jsonl_size_capped_by_source(tmp_path: Path):
    src = tmp_path / "tiny.jsonl"
    src.write_text("\n".join([json.dumps({"i": i}) for i in range(10)]) + "\n", encoding="utf-8")
    result = sample_jsonl(src, size=50, seed=0)
    assert len(result) == 10


def test_score_sample_returns_pass_rate(tmp_path: Path):
    # Two rows: one will pass shared-row validator, one will not
    sample = [
        {
            "id": "a",
            "domain": "technical",
            "text": "Alpha uses Beta.",
            "memory_type": "fact",
            "noise": False,
            "entities": [
                {"name": "Alpha", "type": "project", "start": 0, "end": 5},
                {"name": "Beta", "type": "library", "start": 11, "end": 15},
            ],
            "relationships": [{"source": "Alpha", "target": "Beta", "type": "USES"}],
            "queries": [
                {"form": "question", "text": "what does Alpha depend on"},
                {"form": "keyword", "text": "Alpha Beta dependency"},
            ],
        },
        {
            "id": "b",
            # missing fields → will fail
        },
    ]
    result = score_sample(sample, kind="shared")
    assert isinstance(result, SampleResult)
    assert result.total == 2
    assert result.passed == 1
    assert 0.49 < result.pass_rate < 0.51
