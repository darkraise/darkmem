import pytest

from app.services.extraction_ml import (
    ExtractionMLService,
    _build_marked_text,
    _extract_sync,
    _nms_spans,
    _parse_rebel_triplets,
)


def test_nms_empty():
    assert _nms_spans([], 0.3) == []


def test_nms_drops_high_overlap_low_score():
    spans = [
        {"start": 0, "end": 10, "score": 0.9},
        {"start": 2, "end": 9, "score": 0.7},
        {"start": 20, "end": 30, "score": 0.8},
    ]
    kept = _nms_spans(spans, iou_threshold=0.3)
    assert len(kept) == 2
    starts = sorted(k["start"] for k in kept)
    assert starts == [0, 20]


def test_nms_keeps_non_overlapping_regardless_of_score():
    spans = [
        {"start": 0, "end": 5, "score": 0.2},
        {"start": 10, "end": 15, "score": 0.95},
    ]
    kept = _nms_spans(spans, iou_threshold=0.3)
    assert len(kept) == 2


def test_parse_rebel_none_token():
    assert _parse_rebel_triplets("<triplet> NONE") == []


def test_parse_rebel_single_triplet():
    decoded = "<triplet> FastAPI <subj> darkmem <obj> USES"
    rels = _parse_rebel_triplets(decoded)
    assert rels == [{"source": "FastAPI", "target": "darkmem", "type": "USES"}]


def test_parse_rebel_strips_trailing_special_tokens():
    decoded = "<triplet> A <subj> B <obj> USES</s>"
    rels = _parse_rebel_triplets(decoded)
    assert rels == [{"source": "A", "target": "B", "type": "USES"}]


def test_parse_rebel_multiple_triplets():
    decoded = (
        "<triplet> PostgreSQL <subj> darkmem <obj> USES "
        "<triplet> darkmem <subj> pgvector <obj> DEPENDS_ON"
    )
    rels = _parse_rebel_triplets(decoded)
    assert len(rels) == 2
    assert rels[0]["type"] == "USES"
    assert rels[1]["type"] == "DEPENDS_ON"


def test_build_marked_text_wraps_span():
    text = "darkmem uses PostgreSQL"
    marked = _build_marked_text(text, 13, 23)
    assert marked == "darkmem uses [ENT]PostgreSQL[/ENT]"


async def test_extract_empty_content():
    svc = ExtractionMLService()
    result = await svc.extract("")
    assert result["entities"] == []
    assert result["relationships"] == []
    assert result["memory_type"] == "fact"
    assert result["importance"] == 0.5


async def test_extract_whitespace_only():
    svc = ExtractionMLService()
    result = await svc.extract("   \n  ")
    assert result["entities"] == []
    assert result["relationships"] == []


async def test_extract_falls_back_when_models_missing(monkeypatch):
    """If MLModels aren't loaded, the service should return an error-tagged empty result."""
    svc = ExtractionMLService()
    result = await svc.extract("darkmem uses PostgreSQL 17")
    assert result["entities"] == []
    assert result["relationships"] == []
    assert result["memory_type"] == "fact"
    assert "_error" in result


async def test_extract_passes_through_clean_extraction(monkeypatch):
    """A successful ML pass goes through clean_extraction — bogus short names are dropped."""

    def fake_extract_sync(content: str) -> dict:
        return {
            "memory_type": "fact",
            "importance": 0.5,
            "entities": [
                {"name": "PostgreSQL", "type": "database", "properties": {}},
                {"name": "it", "type": "concept", "properties": {}},
            ],
            "relationships": [
                {
                    "source": "darkmem",
                    "target": "PostgreSQL",
                    "type": "USES",
                    "properties": {},
                    "weight": 0.6,
                },
            ],
        }

    monkeypatch.setattr("app.services.extraction_ml._extract_sync", fake_extract_sync)

    svc = ExtractionMLService()
    result = await svc.extract("darkmem uses PostgreSQL")
    names = {e["name"] for e in result["entities"]}
    assert "PostgreSQL" in names
    assert "it" not in names  # filtered by length in clean_extraction
    assert result["relationships"] == []  # target stays but source not in valid_names


async def test_extract_normalizes_legacy_relation_types(monkeypatch):
    def fake_extract_sync(content: str) -> dict:
        return {
            "memory_type": "fact",
            "importance": 0.5,
            "entities": [
                {"name": "Alloy", "type": "tool", "properties": {}},
                {"name": "Promtail", "type": "tool", "properties": {}},
            ],
            "relationships": [
                {
                    "source": "Alloy",
                    "target": "Promtail",
                    "type": "IMPROVES_ON",
                    "properties": {},
                    "weight": 0.8,
                },
            ],
        }

    monkeypatch.setattr("app.services.extraction_ml._extract_sync", fake_extract_sync)

    svc = ExtractionMLService()
    result = await svc.extract("Alloy improves on Promtail")
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["type"] == "REPLACES"
