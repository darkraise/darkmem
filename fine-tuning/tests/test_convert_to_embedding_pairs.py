# fine-tuning/tests/test_convert_to_embedding_pairs.py
import json
from pathlib import Path

from scripts.convert_to_embedding_pairs import convert_file


def test_convert_contrastive_and_triplet(tmp_path: Path):
    src = tmp_path / "in.jsonl"
    src.write_text(
        json.dumps({"id": "a", "source_id": "s-1", "query": "q", "positive": "p", "query_kind": "paraphrase"}) + "\n"
        + json.dumps({"id": "b", "source_id": "s-2", "query": "q2", "negative": "n", "query_kind": "hard-negative"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    convert_file(src, out)
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").strip().splitlines()]
    assert rows[0] == {"query": "q", "positive": "p"}
    assert rows[1] == {"query": "q2", "negative": "n"}
