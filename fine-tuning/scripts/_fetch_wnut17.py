"""Fetch WNUT-17 raw CoNLL files from the original GitHub mirror, parse BIO tags,
and collapse all entity types to a single 'entity' label.

WNUT-17 (Derczynski et al., "Results of the WNUT2017 Shared Task on Novel and
Emerging Entity Recognition") is noisy social-media text with unusual entity
mentions. Exactly the distribution we want span robustness on.

Output:
  data/public_ner/wnut17_span.jsonl  — GLiNER tokenized with single "entity" label

Usage:
  python -m scripts._fetch_wnut17
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "public_ner" / "wnut17_span.jsonl"

URLS = [
    "https://raw.githubusercontent.com/leondz/emerging_entities_17/master/wnut17train.conll",
    "https://raw.githubusercontent.com/leondz/emerging_entities_17/master/emerging.dev.conll",
    "https://raw.githubusercontent.com/leondz/emerging_entities_17/master/emerging.test.annotated",
]


def parse_conll(text: str) -> list[dict]:
    """Parse CoNLL-format text (token TAB tag per line, blank-line separated
    sentences) into a list of {tokenized_text, ner} rows with collapsed
    entity labels."""
    rows: list[dict] = []
    tokens: list[str] = []
    tags: list[str] = []

    def flush():
        if not tokens:
            return
        # Walk BIO tags to find contiguous entity runs
        ner: list[list] = []
        start = None
        for i in range(len(tags) + 1):
            tag = tags[i] if i < len(tags) else "O"
            if tag.startswith("B-") or (tag.startswith("I-") and start is None):
                if start is not None:
                    ner.append([start, i - 1, "entity"])
                start = i
            elif tag == "O":
                if start is not None:
                    ner.append([start, i - 1, "entity"])
                    start = None
        if ner:
            rows.append({"tokenized_text": list(tokens), "ner": ner})

    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            flush()
            tokens = []
            tags = []
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        tokens.append(parts[0])
        tags.append(parts[1])
    flush()  # final sentence
    return rows


def main() -> int:
    all_rows: list[dict] = []
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for url in URLS:
            print(f"fetch {url}", flush=True)
            r = client.get(url)
            r.raise_for_status()
            split_rows = parse_conll(r.text)
            print(f"  {len(split_rows)} rows parsed")
            all_rows.extend(split_rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nwrote {OUT} ({len(all_rows)} total rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
