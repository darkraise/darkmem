"""Pre-pick source rows for each augmentation batch.

Writes one JSONL per batch under data/v2/retrieval/aug_sources/ so each
parallel subagent can mint queries for its specific rows.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT_DIR = ROOT / "data" / "v2" / "retrieval" / "aug_sources"

# (batch_id, query_kind, memory_type, n_rows, id_start)
BATCHES = [
    ("aug_001", "paraphrase",     "fact",         250, 3001),
    ("aug_002", "paraphrase",     "architecture", 150, 3251),
    ("aug_003", "paraphrase",     "problem",      150, 3401),
    ("aug_004", "paraphrase",     "reference",    100, 3551),
    ("aug_005", "typo",           "fact",         300, 3651),
    ("aug_006", "typo",           "reference",    200, 3951),
    ("aug_007", "typo",           "milestone",    150, 4151),
    ("aug_008", "typo",           "decision",     100, 4301),
    ("aug_009", "multi-sentence", "fact",         200, 4401),
    ("aug_010", "multi-sentence", "problem",      200, 4601),
    ("aug_011", "multi-sentence", "architecture", 100, 4801),
    ("aug_012", "multi-sentence", "milestone",    100, 4901),
]


def main() -> int:
    shared = [json.loads(l) for l in SHARED.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Group by memory_type, preserve natural order
    by_type: dict[str, list[dict]] = {}
    for r in shared:
        by_type.setdefault(r["memory_type"], []).append(r)

    # Shuffle each bucket deterministically so slice assignment is diverse
    rng = random.Random(42)
    for mt, rows in by_type.items():
        rng.shuffle(rows)

    # Track cursor per type so multiple batches over the same type get non-overlapping rows
    cursor: dict[str, int] = {mt: 0 for mt in by_type}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for batch_id, kind, mt, n, id_start in BATCHES:
        pool = by_type[mt]
        start = cursor[mt]
        end = start + n
        if end > len(pool):
            raise RuntimeError(f"batch {batch_id}: {mt} pool exhausted ({len(pool)} avail, need {end})")
        picks = pool[start:end]
        cursor[mt] = end
        out_path = OUT_DIR / f"{batch_id}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for i, src in enumerate(picks):
                f.write(json.dumps({
                    "index": i + 1,
                    "new_id": f"ret-{id_start + i:05d}",
                    "source_id": src["id"],
                    "memory_type": src["memory_type"],
                    "text": src["text"],
                }, ensure_ascii=False) + "\n")
        manifest.append({
            "batch_id": batch_id,
            "query_kind": kind,
            "memory_type": mt,
            "n": n,
            "id_start": id_start,
            "id_end": id_start + n - 1,
            "sources_path": str(out_path.relative_to(ROOT)),
        })
        print(f"{batch_id}: {kind} x {mt} x {n}  ids={id_start}..{id_start+n-1}  -> {out_path.relative_to(ROOT)}")

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nwrote manifest -> {(OUT_DIR / 'manifest.json').relative_to(ROOT)}")
    total = sum(b["n"] for b in manifest)
    print(f"total rows planned: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
