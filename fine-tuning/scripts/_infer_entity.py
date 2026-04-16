"""Phase 3a: run a fine-tuned GLiNER on a gold test set and write predictions.

Input gold schema: {id, text, entities: [{name, type, start, end}], ...}
Output pred schema: {id, text, entities: [{name, type, start, end}]}

Also emits per-row latency and peak VRAM into a sidecar metrics JSON so the
Phase 3 report can cite them.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.domains import ALL_ENTITY_TYPES

GLINER_THRESHOLD = 0.5


def run(model_path: Path, gold_path: Path, pred_path: Path, threshold: float) -> dict:
    import torch
    from gliner import GLiNER

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}", flush=True)
    print(f"Loading model: {model_path}", flush=True)
    model = GLiNER.from_pretrained(str(model_path))
    if device == "cuda":
        model = model.to("cuda")
        torch.cuda.reset_peak_memory_stats()

    print(f"Reading gold: {gold_path}", flush=True)
    gold: list[dict] = []
    with gold_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            gold.append(json.loads(line))
    print(f"  {len(gold)} rows", flush=True)

    pred_path.parent.mkdir(parents=True, exist_ok=True)
    latencies: list[float] = []
    with pred_path.open("w", encoding="utf-8") as out_f:
        for i, row in enumerate(gold):
            text = row["text"]
            t0 = time.perf_counter()
            raw = model.predict_entities(text, ALL_ENTITY_TYPES, threshold=threshold)
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            entities = []
            for e in raw:
                s, t = e["start"], e["end"]
                entities.append({
                    "name": text[s:t],
                    "type": e["label"],
                    "start": s,
                    "end": t,
                })
            out_f.write(json.dumps({
                "id": row["id"],
                "text": text,
                "entities": entities,
            }, ensure_ascii=False) + "\n")
            if (i + 1) % 200 == 0:
                print(f"  [{i+1}/{len(gold)}]", flush=True)

    peak_mb = 0.0
    if device == "cuda":
        peak_mb = torch.cuda.max_memory_allocated() / 1e6

    latencies.sort()
    n = len(latencies)
    p50 = latencies[n // 2] if n else 0.0
    p95 = latencies[int(n * 0.95)] if n else 0.0
    mean = sum(latencies) / n if n else 0.0

    side = {
        "model": str(model_path),
        "gold": str(gold_path),
        "rows": n,
        "latency_ms_per_row_mean": mean,
        "latency_ms_per_row_p50": p50,
        "latency_ms_per_row_p95": p95,
        "peak_vram_mb": peak_mb,
        "threshold": threshold,
    }
    side_path = pred_path.with_suffix(".runtime.json")
    side_path.write_text(json.dumps(side, indent=2), encoding="utf-8")
    print(f"\nWrote {n} preds to {pred_path}", flush=True)
    print(f"Runtime sidecar: {side_path}", flush=True)
    print(f"  mean {mean:.1f} ms, p50 {p50:.1f}, p95 {p95:.1f}, peak VRAM {peak_mb:.0f} MB", flush=True)
    return side


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--pred", type=Path, required=True)
    p.add_argument("--threshold", type=float, default=GLINER_THRESHOLD)
    a = p.parse_args()
    run(a.model, a.gold, a.pred, a.threshold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
