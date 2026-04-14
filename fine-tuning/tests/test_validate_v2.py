# fine-tuning/tests/test_validate_v2.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v2 import (
    load_taxonomy,
    validate_shared_row,
    validate_extraction_topup_row,
    validate_classification_topup_row,
    validate_retrieval_topup_row,
    ValidationResult,
)


@pytest.fixture(scope="module")
def taxonomy():
    return load_taxonomy()


def _valid_shared_row() -> dict:
    return {
        "id": "shared-00001",
        "domain": "technical",
        "text": "We switched from Celery to asyncio.",
        "memory_type": "decision",
        "noise": False,
        "entities": [
            {"name": "Celery", "type": "framework", "start": 17, "end": 23},
            {"name": "asyncio", "type": "library", "start": 27, "end": 34},
        ],
        "relationships": [
            {"source": "asyncio", "target": "Celery", "type": "REPLACES"}
        ],
        "queries": [
            {"form": "question", "text": "why did we move off Celery"},
            {"form": "keyword", "text": "Celery to asyncio rationale"},
        ],
    }


def test_valid_shared_row_passes(taxonomy):
    result = validate_shared_row(_valid_shared_row(), taxonomy)
    assert result.ok, result.errors


def test_entity_offset_mismatch_fails(taxonomy):
    row = _valid_shared_row()
    row["entities"][0]["end"] = 20   # wrong end offset
    result = validate_shared_row(row, taxonomy)
    assert not result.ok
    assert any("offset" in e for e in result.errors)


def test_relationship_missing_endpoint_fails(taxonomy):
    row = _valid_shared_row()
    row["relationships"][0]["source"] = "Unknown"
    result = validate_shared_row(row, taxonomy)
    assert not result.ok
    assert any("endpoint" in e for e in result.errors)


def test_unknown_entity_type_fails(taxonomy):
    row = _valid_shared_row()
    row["entities"][0]["type"] = "not_a_real_type"
    result = validate_shared_row(row, taxonomy)
    assert not result.ok
    assert any("entity type" in e for e in result.errors)


def test_unknown_memory_type_fails(taxonomy):
    row = _valid_shared_row()
    row["memory_type"] = "not_a_type"
    result = validate_shared_row(row, taxonomy)
    assert not result.ok


def test_query_too_similar_to_source_fails(taxonomy):
    row = _valid_shared_row()
    row["queries"][0]["text"] = row["text"]   # identical
    result = validate_shared_row(row, taxonomy)
    assert not result.ok
    assert any("similarity" in e or "verbatim" in e for e in result.errors)


def test_noise_row_without_entities_passes(taxonomy):
    row = {
        "id": "noise-00001",
        "domain": "noise",
        "text": "Let me think about this for a moment.",
        "memory_type": "fact",
        "noise": True,
        "entities": [],
        "relationships": [],
    }
    result = validate_shared_row(row, taxonomy)
    assert result.ok, result.errors


def test_shared_row_without_entities_and_not_noise_fails(taxonomy):
    row = _valid_shared_row()
    row["entities"] = []
    row["relationships"] = []
    row["noise"] = False
    result = validate_shared_row(row, taxonomy)
    assert not result.ok


def test_extraction_topup_row_rejects_queries_field(taxonomy):
    row = {
        "id": "ext-topup-00001",
        "domain": "technical",
        "text": "Alpha uses Beta.",
        "memory_type": "fact",
        "entities": [
            {"name": "Alpha", "type": "project", "start": 0, "end": 5},
            {"name": "Beta", "type": "library", "start": 11, "end": 15},
        ],
        "relationships": [{"source": "Alpha", "target": "Beta", "type": "USES"}],
        "queries": [{"form": "question", "text": "stray"}],   # not allowed
    }
    result = validate_extraction_topup_row(row, taxonomy)
    assert not result.ok
    assert any("foreign field" in e or "queries" in e for e in result.errors)


def test_classification_topup_row_accepts_pair_id(taxonomy):
    row = {
        "id": "cls-topup-00001",
        "domain": "technical",
        "text": "See https://example.com for the full spec.",
        "memory_type": "reference",
        "pair_id": "ref-fact-0001",
    }
    result = validate_classification_topup_row(row, taxonomy)
    assert result.ok, result.errors


def test_retrieval_topup_row_with_hard_negative(taxonomy):
    row = {
        "id": "ret-topup-00001",
        "source_id": "shared-00042",
        "query": "why did we move off Celery",
        "negative": "Celery is a distributed task queue.",
        "query_kind": "hard-negative",
    }
    result = validate_retrieval_topup_row(row, taxonomy)
    assert result.ok, result.errors
