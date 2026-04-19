"""Build span-only training splits augmented with public NER corpora.

Source 1: our 14k shared corpus — all entities collapse to "entity".
Source 2: NuNER-v2 (numind/NuNER-v2) — 1M+ rows, pick a stratified subsample.
Source 3: WNUT-17 (tner/wnut2017) — noisy social-media text, small and focused.

Final output:
  data/splits/spanpub_train.jsonl  — GLiNER tokenized
  data/splits/spanpub_val.jsonl    — held out from darkmem only (no public leak)
  data/splits/spanpub_test.jsonl   — held out from darkmem only

This keeps the eval distribution identical to the existing span evaluation
so we can read apples-to-apples deltas, while training gets a broad span
signal from ~50-60k additional rows.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_data import _char_spans_to_token_spans

SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
SPLITS_DIR = ROOT / "data" / "splits"
PUB_CACHE = ROOT / "data" / "public_ner"
SEED = 42

# How many NuNER-v2 rows to sample (1M+ available; taking 50k for balance)
NUNER_SAMPLE_N = 50_000
# WNUT-17: tiny (~5k train) — take all
WNUT_TAKE_ALL = True


def shared_to_tokenized(row: dict) -> dict | None:
    text = row["text"]
    char_ents = [
        {"start": e["start"], "end": e["end"], "label": "entity"}
        for e in row.get("entities") or []
    ]
    tokens, ner = _char_spans_to_token_spans(text, char_ents)
    if not ner:
        return None
    return {"tokenized_text": tokens, "ner": ner}


_NUNER_ITEM_RE = __import__("re").compile(r"'([^']*?)\s*<>\s*([^']*?)'")


def fetch_nuner(n: int) -> list[dict]:
    """Fetch n rows from numind/NuNER (split='entity') and convert to tokenized span format.

    NuNER schema: {input: text, output: "['span <> label', 'span <> label', ...]"}
    We parse the output string with a regex for the 'span <> label' items,
    locate each span's first occurrence in input, and emit (start, end, 'entity').
    """
    print(f"Fetching numind/NuNER (target {n} rows, split='entity') ...", flush=True)
    from datasets import load_dataset
    ds = load_dataset("numind/NuNER", split="entity", streaming=True)

    out: list[dict] = []
    pulled = 0
    for ex in ds:
        pulled += 1
        if len(out) >= n:
            break
        text = ex.get("input") or ""
        out_str = ex.get("output") or ""
        if not text or not out_str:
            continue
        matches = _NUNER_ITEM_RE.findall(out_str)
        if not matches:
            continue
        char_ents: list[dict] = []
        cursor = 0
        for span_text, _label in matches:
            span_text = span_text.strip()
            if not span_text:
                continue
            idx = text.find(span_text, cursor)
            if idx < 0:
                idx = text.find(span_text)
            if idx < 0:
                continue
            end = idx + len(span_text)
            char_ents.append({"start": idx, "end": end, "label": "entity"})
            cursor = end
        if not char_ents:
            continue
        tokens, ner = _char_spans_to_token_spans(text, char_ents)
        if not ner:
            continue
        out.append({"tokenized_text": tokens, "ner": ner})

    print(f"  pulled {pulled} raw, kept {len(out)} with valid spans", flush=True)
    return out


def fetch_wnut() -> list[dict]:
    """WNUT-17 dataset — pre-tokenized with BIO labels. Convert to GLiNER format."""
    print("Fetching tner/wnut2017 ...", flush=True)
    try:
        from datasets import load_dataset
        ds = load_dataset("tner/wnut2017", split="train")
    except Exception as exc:
        print(f"  wnut fetch failed: {exc}", flush=True)
        return []

    out: list[dict] = []
    # tner/wnut2017 schema: {tokens, tags (int ids)} — need to map
    # tag 0 = O, rest are B-*/I-*
    tag_names = ds.features["tags"].feature.names if hasattr(ds.features["tags"], "feature") else None
    for ex in ds:
        tokens = ex["tokens"]
        tags = ex["tags"]
        # Walk BIO tags to find contiguous entity spans; collapse all types
        ner: list[list] = []
        start = None
        for i, t_id in enumerate(tags + [0]):
            tag = tag_names[t_id] if tag_names else "O" if t_id == 0 else "B-X"
            if tag.startswith("B-") or (tag.startswith("I-") and start is None):
                if start is not None:
                    ner.append([start, i - 1, "entity"])
                start = i
            elif tag == "O":
                if start is not None:
                    ner.append([start, i - 1, "entity"])
                    start = None
        if ner:
            out.append({"tokenized_text": list(tokens), "ner": ner})
    print(f"  kept {len(out)} wnut rows with valid spans", flush=True)
    return out


def stratified_split_shared(rows: list[dict], seed: int) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get("memory_type", "?")].append(r)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    split = {"train": [], "val": [], "test": []}
    for k in sorted(groups):
        items = groups[k]
        n = len(items)
        n_val = max(1, int(round(n * 0.10))) if n >= 10 else 0
        n_test = max(1, int(round(n * 0.10))) if n >= 10 else 0
        split["test"].extend(items[:n_test])
        split["val"].extend(items[n_test:n_test + n_val])
        split["train"].extend(items[n_test + n_val:])
    return split


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    # 1. Load shared, split into canonical train/val/test
    shared_rows: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            shared_rows.append(json.loads(line))
    print(f"shared.jsonl: {len(shared_rows)} rows")

    shared_split = stratified_split_shared(shared_rows, SEED)

    # Convert each split to tokenized span rows
    shared_train_tok = [shared_to_tokenized(r) for r in shared_split["train"]]
    shared_train_tok = [r for r in shared_train_tok if r is not None]
    shared_val_tok = [shared_to_tokenized(r) for r in shared_split["val"]]
    shared_val_tok = [r for r in shared_val_tok if r is not None]
    shared_test_tok = [shared_to_tokenized(r) for r in shared_split["test"]]
    shared_test_tok = [r for r in shared_test_tok if r is not None]
    print(f"shared tokenized: train {len(shared_train_tok)}  val {len(shared_val_tok)}  test {len(shared_test_tok)}")

    # 2. Fetch public corpora — ONLY used for training, never val/test
    pub_rows: list[dict] = []
    pub_rows += fetch_nuner(NUNER_SAMPLE_N)
    pub_rows += fetch_wnut()
    rng = random.Random(SEED)
    rng.shuffle(pub_rows)
    print(f"public corpora: {len(pub_rows)} tokenized rows")

    # 3. Combine
    train_combined = shared_train_tok + pub_rows
    rng.shuffle(train_combined)

    write_jsonl(SPLITS_DIR / "spanpub_train.jsonl", train_combined)
    write_jsonl(SPLITS_DIR / "spanpub_val.jsonl", shared_val_tok)
    write_jsonl(SPLITS_DIR / "spanpub_test.jsonl", shared_test_tok)
    print(f"\nwrote spanpub_train ({len(train_combined)}), "
          f"spanpub_val ({len(shared_val_tok)}), "
          f"spanpub_test ({len(shared_test_tok)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
