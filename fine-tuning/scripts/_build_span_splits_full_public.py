"""Build span-only training splits with darkmem + NuNER + WNUT-17.

Reads:
  data/splits/spanpub_train.jsonl — 60,770 rows (darkmem train + 50k NuNER)
  data/splits/spanpub_val.jsonl   — darkmem val (held-out, no public leak)
  data/splits/spanpub_test.jsonl  — darkmem test
  data/public_ner/wnut17_span.jsonl — 2,545 WNUT-17 rows

Writes:
  data/splits/spanpubwnut_train.jsonl — spanpub_train + WNUT (~63,315 rows)
  data/splits/spanpubwnut_val.jsonl   — same as spanpub_val (darkmem-only)
  data/splits/spanpubwnut_test.jsonl  — same as spanpub_test
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"
WNUT = ROOT / "data" / "public_ner" / "wnut17_span.jsonl"
SEED = 42


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open("r", encoding="utf-8") if l.strip()]


def main() -> int:
    spanpub_train = load(SPLITS / "spanpub_train.jsonl")
    spanpub_val = load(SPLITS / "spanpub_val.jsonl")
    spanpub_test = load(SPLITS / "spanpub_test.jsonl")
    wnut = load(WNUT)
    print(f"spanpub_train: {len(spanpub_train)}")
    print(f"wnut17_span: {len(wnut)}")

    train_combined = spanpub_train + wnut
    random.Random(SEED).shuffle(train_combined)
    print(f"combined train: {len(train_combined)}")

    with (SPLITS / "spanpubwnut_train.jsonl").open("w", encoding="utf-8") as f:
        for r in train_combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (SPLITS / "spanpubwnut_val.jsonl").open("w", encoding="utf-8") as f:
        for r in spanpub_val:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (SPLITS / "spanpubwnut_test.jsonl").open("w", encoding="utf-8") as f:
        for r in spanpub_test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote spanpubwnut_{{train,val,test}}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
