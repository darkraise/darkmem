"""One-off emitter for shared-base batch-141 — 2-row closeout to hit the 7000 target.

Writes 2 rows to data/v2/shared/batch_141.tmp.jsonl with ids shared-07001..07002 (two fresh ids that fill the 2-row gap left by earlier dedup drops so the corpus lands at 7000 total rows).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_141.tmp.jsonl"
ID_OFFSET = 7000

ENTRIES: list[tuple] = [
    # --- 1 (personal — milestone recording the corpus closeout's real-world mirror)
    ("Finally hit my reading goal of 52 books this year, landing on the last page of Middlemarch in the armchair by the fireplace on 2026-04-15.", "milestone", "personal", False,
     [("Middlemarch", "publication"), ("2026-04-15", "date"), ("reading goal", "goal"), ("fireplace", "place")],
     [("reading goal", "Middlemarch", "RELATED_TO")],
     "which novel closed out this year's 52-book reading target and when did the final page happen",
     "annual book count goal middlemarch fireplace armchair april last page"),
    # --- 2 (ai_coding — milestone about finishing a long chunked corpus build)
    ("Closed the v2 shared base at 6998 rows across 140 parallel-agent batches, then emitted a final 2-row top-up to lock the corpus at exactly 7000 for downstream training.", "milestone", "ai_coding", False,
     [("shared base", "pattern"), ("6998 rows", "concept"), ("parallel-agent batches", "pattern"), ("7000", "config")],
     [("shared base", "parallel-agent batches", "USES")],
     "how did the pipeline close the v2 shared-base corpus down to an exact round-number row count",
     "fine tune corpus finalise closeout top up exact target downstream training"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
