# fine-tuning/tests/test_convert_to_rebel.py
import json
from pathlib import Path

from scripts.convert_to_rebel import convert_file


def test_convert_rebel_formats_triplet(tmp_path: Path):
    src = tmp_path / "in.jsonl"
    src.write_text(
        json.dumps({
            "id": "a",
            "domain": "technical",
            "text": "We switched from Celery to asyncio.",
            "memory_type": "decision",
            "entities": [
                {"name": "Celery", "type": "framework", "start": 17, "end": 23},
                {"name": "asyncio", "type": "library", "start": 27, "end": 34},
            ],
            "relationships": [{"source": "asyncio", "target": "Celery", "type": "REPLACES"}],
        }) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    convert_file(src, out)
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert "We switched from Celery to asyncio." in row["input"]
    assert "Celery (framework)" in row["input"]
    assert "asyncio (library)" in row["input"]
    assert "<triplet> asyncio <subj> Celery <obj> REPLACES" in row["output"]


def test_convert_rebel_empty_relationships_produces_none(tmp_path: Path):
    src = tmp_path / "in.jsonl"
    src.write_text(
        json.dumps({
            "id": "a",
            "domain": "technical",
            "text": "Solo.",
            "memory_type": "fact",
            "entities": [{"name": "Solo", "type": "project", "start": 0, "end": 4}],
            "relationships": [],
        }) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    convert_file(src, out)
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["output"] == "<triplet> NONE"
