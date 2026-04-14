# fine-tuning/tests/test_convert_to_gliner.py
import json
from pathlib import Path

from scripts.convert_to_gliner import convert_file


def test_convert_gliner_basic_entities(tmp_path: Path):
    src = tmp_path / "in.jsonl"
    src.write_text(
        json.dumps({
            "id": "a",
            "domain": "technical",
            "text": "Alpha uses Beta.",
            "memory_type": "fact",
            "entities": [
                {"name": "Alpha", "type": "project", "start": 0, "end": 5},
                {"name": "Beta", "type": "library", "start": 11, "end": 15},
            ],
            "relationships": [],
        }) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    failed_dir = tmp_path / "failed"
    stats = convert_file(src, out, failed_dir=failed_dir, base_model="urchade/gliner_small-v2.1")
    assert stats["converted"] == 1
    assert stats["failed"] == 0
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["text"] == "Alpha uses Beta."
    assert {"start": 0, "end": 5, "label": "project"} in row["entities"]
