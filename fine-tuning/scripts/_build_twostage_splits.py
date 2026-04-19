"""Build the two-stage training data from the clean coding-10 corpus.

Stage 1 (span detector) input format — GLiNER tokenized with label "ENTITY":
  data/splits/span_train.jsonl / span_val.jsonl / span_test.jsonl
  Every entity, regardless of its 10-type label, becomes a single "ENTITY"
  span. The model only learns "is this a named entity?".

Stage 2 (type classifier) input format — sequence classification with
context markers:
  data/splits/typer_train.jsonl / typer_val.jsonl / typer_test.jsonl
  One row per entity mention: {
    "text": "darkmem uses [ENT]Tree-sitter[/ENT] for parsing...",
    "span": "Tree-sitter",
    "label": "tool"
  }
  Trainer: fine-tune ModernBERT-base as a 10-way sequence classifier.

Rows without entities are included in stage 1 (negative examples) but
dropped from stage 2 (no type to learn).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_data import _char_spans_to_token_spans

SPLITS_DIR = ROOT / "data" / "splits"

CANON = {
    "train": SPLITS_DIR / "coding10clean_train_canon.jsonl",
    "val": SPLITS_DIR / "coding10clean_val_canon.jsonl",
    "test": SPLITS_DIR / "coding10clean_test_canon.jsonl",
}


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open("r", encoding="utf-8") if l.strip()]


def stage1_row(row: dict) -> dict | None:
    """GLiNER tokenized row with single ENTITY label."""
    text = row["text"]
    char_ents = [{"start": e["start"], "end": e["end"], "label": "entity"}
                 for e in row.get("entities") or []]
    tokens, ner = _char_spans_to_token_spans(text, char_ents)
    if not ner:
        return None
    return {"tokenized_text": tokens, "ner": ner}


def stage2_rows(row: dict) -> list[dict]:
    """For each entity, build a classifier row with span markers around it.

    The marker scheme `[ENT]...[/ENT]` is simple and BERT-tokenizer safe.
    """
    text = row["text"]
    out: list[dict] = []
    ents = sorted(row.get("entities") or [], key=lambda e: e["start"])
    for e in ents:
        s, t = e["start"], e["end"]
        marked_text = text[:s] + "[ENT]" + text[s:t] + "[/ENT]" + text[t:]
        out.append({
            "text": marked_text,
            "span": text[s:t],
            "label": e["type"],
        })
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    for split_name, canon_path in CANON.items():
        rows = load(canon_path)

        # Stage 1 — span-only
        s1 = [stage1_row(r) for r in rows]
        s1 = [x for x in s1 if x is not None]
        write(SPLITS_DIR / f"span_{split_name}.jsonl", s1)

        # Stage 2 — per-entity classification
        s2: list[dict] = []
        for r in rows:
            s2.extend(stage2_rows(r))
        write(SPLITS_DIR / f"typer_{split_name}.jsonl", s2)

        print(f"{split_name}: {len(rows)} rows -> "
              f"stage1 {len(s1)} tokenized rows, stage2 {len(s2)} typer rows")

        if split_name == "train":
            c = Counter(r["label"] for r in s2)
            print(f"  typer_train label distribution:")
            total = sum(c.values())
            for lab, n in c.most_common():
                print(f"    {lab:10s}  {n:6d}  ({n/total*100:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
