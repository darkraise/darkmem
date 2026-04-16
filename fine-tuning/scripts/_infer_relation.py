"""Phase 3b: run a fine-tuned REBEL on a gold test set and write predictions.

Input gold schema: {id, text, entities: [{name, type, ...}], relationships: [{source, target, type}]}
Output pred schema: {id, relationships: [{source, target, type}]}

The model consumes the text plus an "Entities:" hint string built from the
gold entity list (same format used during training by convert_to_rebel).
Seq2seq decode uses num_beams=4, max_target_length=128.

Also emits per-row latency and peak VRAM into a sidecar JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def parse_triplets(decoded: str) -> list[dict]:
    rels: list[dict] = []
    for chunk in decoded.split("<triplet>"):
        chunk = chunk.strip()
        if not chunk or chunk == "NONE":
            continue
        a = chunk.split("<subj>")
        if len(a) != 2:
            continue
        source = a[0].strip()
        b = a[1].split("<obj>")
        if len(b) != 2:
            continue
        target = b[0].strip()
        rtype = b[1].strip().split("<")[0].strip()
        if source and target and rtype:
            rels.append({"source": source, "target": target, "type": rtype})
    return rels


def run(
    model_path: Path,
    gold_path: Path,
    pred_path: Path,
    num_beams: int,
    max_source_length: int,
    max_target_length: int,
) -> dict:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}", flush=True)
    print(f"Loading model: {model_path}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path))
    if device == "cuda":
        model = model.to("cuda")
        torch.cuda.reset_peak_memory_stats()
    model.train(False)

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
            ents = row.get("entities") or []
            ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in ents)
            inp = f"{text} | Entities: {ent_str}"
            t0 = time.perf_counter()
            tokens = tokenizer(
                inp,
                return_tensors="pt",
                max_length=max_source_length,
                truncation=True,
            )
            if device == "cuda":
                tokens = {k: v.to("cuda") for k, v in tokens.items()}
            with torch.no_grad():
                out = model.generate(
                    **tokens,
                    max_length=max_target_length,
                    num_beams=num_beams,
                )
            decoded = tokenizer.decode(out[0], skip_special_tokens=False)
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            rels = parse_triplets(decoded)
            out_f.write(json.dumps({
                "id": row["id"],
                "relationships": rels,
            }, ensure_ascii=False) + "\n")
            if (i + 1) % 100 == 0:
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
        "num_beams": num_beams,
        "max_source_length": max_source_length,
        "max_target_length": max_target_length,
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
    p.add_argument("--num-beams", type=int, default=4)
    p.add_argument("--max-source-length", type=int, default=512)
    p.add_argument("--max-target-length", type=int, default=128)
    a = p.parse_args()
    run(
        a.model, a.gold, a.pred,
        num_beams=a.num_beams,
        max_source_length=a.max_source_length,
        max_target_length=a.max_target_length,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
