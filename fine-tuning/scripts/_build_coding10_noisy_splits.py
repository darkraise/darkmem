"""Merge coding-10 corpus with the new 500 noisy batches (_emit_noisy_batch_01..10)
and rebuild span + typer splits.

Subagents produced a mix of v2 taxonomy types (35-type: library/framework/tool/
platform/infrastructure/…) and the new coding-10 labels (artifact, entity).
We run TYPE_MAP over every entity to collapse both into the 10-type space.
Entities whose type doesn't map are dropped; the row is kept if at least one
entity survives.

Output (augmented vs base coding10clean):
  data/splits/coding10noisy_train.jsonl         — GLiNER span-only (all labels -> "entity")
  data/splits/coding10noisy_val.jsonl           — held out from darkmem only
  data/splits/coding10noisy_test.jsonl          — same
  data/splits/coding10noisy_train_canon.jsonl   — canonical w/ 10-type labels

Note: the noisy batches go into TRAIN only. VAL/TEST come from the existing
coding10clean held-outs so our benchmarks stay comparable.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._build_coding10_splits import TYPE_MAP
from scripts.validate_data import _char_spans_to_token_spans

SPLITS_DIR = ROOT / "data" / "splits"
NOISY_DIR = ROOT / "data" / "v2" / "noisy"
SEED = 42


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open("r", encoding="utf-8") if l.strip()]


def remap_entities(ents: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in ents or []:
        raw = e.get("type")
        # 'artifact' and 'entity' from sub-agents map to themselves directly in
        # TYPE_MAP; the 35-type names (library/framework/service/etc) also map.
        # Special-case 'command', 'file', 'config', 'error' which map to 'artifact'.
        # Special-case 'person', 'organization', 'place', 'date', 'event' which
        # map to 'entity'. TYPE_MAP handles both cases already.
        if raw in ("artifact", "entity"):
            mapped = raw  # subagent used 10-type name directly
        else:
            mapped = TYPE_MAP.get(raw)
        if not mapped:
            continue
        out.append({
            "name": e.get("name") or "",
            "type": mapped,
            "start": e["start"],
            "end": e["end"],
        })
    return out


def load_noisy() -> list[dict]:
    rows: list[dict] = []
    for i in range(1, 11):
        batch = NOISY_DIR / f"noisy_batch_{i:02d}.jsonl"
        if not batch.exists():
            continue
        for r in load(batch):
            ents = remap_entities(r.get("entities"))
            if not ents:
                continue
            ent_names = {e["name"] for e in ents}
            rels = [
                {"source": x["source"], "target": x["target"], "type": x["type"]}
                for x in (r.get("relationships") or [])
                if x.get("source") in ent_names and x.get("target") in ent_names
            ]
            rows.append({
                "id": r.get("id"),
                "domain": r.get("domain") or "ai_coding",
                "text": r["text"],
                "memory_type": r.get("memory_type") or "fact",
                "entities": ents,
                "relationships": rels,
            })
    return rows


def to_gliner_span_only(row: dict) -> dict | None:
    text = row["text"]
    char_ents = [{"start": e["start"], "end": e["end"], "label": "entity"}
                 for e in row.get("entities") or []]
    tokens, ner = _char_spans_to_token_spans(text, char_ents)
    if not ner:
        return None
    return {"tokenized_text": tokens, "ner": ner}


def main() -> int:
    # Existing coding10clean canonical train + val + test (val/test stay darkmem-only)
    canon_train = load(SPLITS_DIR / "coding10clean_train_canon.jsonl")
    canon_val = load(SPLITS_DIR / "coding10clean_val_canon.jsonl")
    canon_test = load(SPLITS_DIR / "coding10clean_test_canon.jsonl")
    print(f"coding10clean: train {len(canon_train)}, val {len(canon_val)}, test {len(canon_test)}")

    noisy = load_noisy()
    print(f"noisy batches (after type-remap): {len(noisy)} rows")
    tc = Counter()
    ent_count = 0
    for r in noisy:
        for e in r["entities"]:
            tc[e["type"]] += 1
            ent_count += 1
    print(f"noisy entity mentions: {ent_count}")
    print("noisy type distribution:")
    for t, n in tc.most_common():
        print(f"  {t:10s} {n:5d}")

    # Combine train: coding10clean_train + noisy
    combined_canon_train = canon_train + noisy
    rng = random.Random(SEED)
    rng.shuffle(combined_canon_train)
    print(f"\ncombined train (canonical): {len(combined_canon_train)}")

    # Write GLiNER span-only splits (single "entity" label for stage 1)
    train_tok = [to_gliner_span_only(r) for r in combined_canon_train]
    train_tok = [r for r in train_tok if r is not None]
    val_tok = [to_gliner_span_only(r) for r in canon_val]
    val_tok = [r for r in val_tok if r is not None]
    test_tok = [to_gliner_span_only(r) for r in canon_test]
    test_tok = [r for r in test_tok if r is not None]
    print(f"span splits (tokenized): train {len(train_tok)}, val {len(val_tok)}, test {len(test_tok)}")

    with (SPLITS_DIR / "coding10noisy_train.jsonl").open("w", encoding="utf-8") as f:
        for r in train_tok:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (SPLITS_DIR / "coding10noisy_val.jsonl").open("w", encoding="utf-8") as f:
        for r in val_tok:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (SPLITS_DIR / "coding10noisy_test.jsonl").open("w", encoding="utf-8") as f:
        for r in test_tok:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (SPLITS_DIR / "coding10noisy_train_canon.jsonl").open("w", encoding="utf-8") as f:
        for r in combined_canon_train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote coding10noisy_{train,val,test}.jsonl + coding10noisy_train_canon.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
