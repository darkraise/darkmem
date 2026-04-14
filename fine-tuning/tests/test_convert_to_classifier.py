# fine-tuning/tests/test_convert_to_classifier.py
import json
from pathlib import Path

from scripts.convert_to_classifier import convert_file


def test_convert_produces_text_label_rows(tmp_path: Path):
    src = tmp_path / "in.jsonl"
    src.write_text(
        json.dumps({"id": "a", "domain": "technical", "text": "Hello.", "memory_type": "fact"}) + "\n"
        + json.dumps({"id": "b", "domain": "personal", "text": "Goodbye.", "memory_type": "preference"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    convert_file(src, out)
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").strip().splitlines()]
    assert rows == [
        {"text": "Hello.", "label": "fact"},
        {"text": "Goodbye.", "label": "preference"},
    ]
