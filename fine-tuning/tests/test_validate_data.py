"""Tests for validate_data output formats."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_data import write_gliner_jsonl


def test_gliner_format_has_tokenized_text_and_ner():
    """GLiNER JSONL must use tokenized_text (list[str]) and ner (list of [start, end, label])."""
    examples = [
        {
            "text": "We switched from Flask to FastAPI for better performance.",
            "entities": [
                {"name": "Flask", "type": "framework", "start": 17, "end": 22},
                {"name": "FastAPI", "type": "framework", "start": 26, "end": 33},
            ],
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = Path(f.name)

    try:
        write_gliner_jsonl(examples, path)
        with path.open() as fh:
            record = json.loads(fh.readline())

        assert "tokenized_text" in record, f"Missing 'tokenized_text', got keys: {list(record.keys())}"
        assert isinstance(record["tokenized_text"], list)
        assert all(isinstance(tok, str) for tok in record["tokenized_text"])

        assert "ner" in record, f"Missing 'ner', got keys: {list(record.keys())}"
        assert isinstance(record["ner"], list)
        for span in record["ner"]:
            assert len(span) == 3, f"Expected [start, end, label], got {span}"
            assert isinstance(span[0], int) and isinstance(span[1], int)
            assert isinstance(span[2], str)

        tokens = record["tokenized_text"]
        for span in record["ner"]:
            start_tok, end_tok, label = span
            entity_tokens = tokens[start_tok:end_tok]
            entity_text = " ".join(entity_tokens)
            assert entity_text in ("Flask", "FastAPI"), f"Bad span: tokens[{start_tok}:{end_tok}] = '{entity_text}'"
    finally:
        path.unlink(missing_ok=True)


def test_gliner_format_multiword_entity():
    """Multi-word entities like 'Apache Spark' must span the correct token range."""
    examples = [
        {
            "text": "We deployed Apache Spark on Kubernetes.",
            "entities": [
                {"name": "Apache Spark", "type": "technology", "start": 12, "end": 24},
                {"name": "Kubernetes", "type": "technology", "start": 28, "end": 38},
            ],
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = Path(f.name)

    try:
        write_gliner_jsonl(examples, path)
        with path.open() as fh:
            record = json.loads(fh.readline())

        tokens = record["tokenized_text"]
        ner = record["ner"]

        spark_spans = [s for s in ner if s[2] == "technology" and " ".join(tokens[s[0]:s[1]]) == "Apache Spark"]
        assert len(spark_spans) == 1, f"Expected 1 'Apache Spark' span, got {spark_spans}"

        s = spark_spans[0]
        assert s[1] - s[0] == 2, f"Expected 2-token span, got {s[1] - s[0]}"
    finally:
        path.unlink(missing_ok=True)


from scripts.validate_data import split_data


def test_split_single_example_domain():
    """A domain with 1 example should place it in train, not leak to test."""
    examples = [{"id": "solo-1", "domain": "tiny", "text": "hello"}]
    train, val, test = split_data(examples, seed=42)

    total = len(train) + len(val) + len(test)
    assert total == 1, f"Expected 1 total, got {total}"
    assert len(train) == 1
    assert len(val) == 0
    assert len(test) == 0


def test_split_two_example_domain():
    """A domain with 2 examples should not leak the same example into multiple splits."""
    examples = [
        {"id": "pair-1", "domain": "tiny", "text": "hello"},
        {"id": "pair-2", "domain": "tiny", "text": "world"},
    ]
    train, val, test = split_data(examples, seed=42)

    total = len(train) + len(val) + len(test)
    assert total == 2, f"Expected 2 total, got {total}"

    all_ids = [ex["id"] for ex in train + val + test]
    assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs across splits: {all_ids}"
