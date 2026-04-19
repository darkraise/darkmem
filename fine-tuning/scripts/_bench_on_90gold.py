"""Benchmark gliner-large-coding10 on the 90-example historical gold under
both the lenient historical scorer (extraction_eval/metrics.py — name match
only, types diagnostic) and the strict entity-pair scorer.

Gold types are remapped to the 10-type coding taxonomy; entities whose
original types drop out (food/emotion/hobby/activity/goal) are removed so
we don't get false negatives against a taxonomy the model doesn't cover.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "docs" / "e2e" / "scripts"))

from extraction_eval.metrics import AggregatedMetrics, score_example
from scripts._build_coding10_splits import TYPE_MAP
from scripts.eval_entity_pair import score as pair_score

GOLD_PATH = REPO / "docs" / "e2e" / "scripts" / "extraction_eval" / "corpus" / "gold.jsonl"

CODING10_LABELS = ["tool", "service", "database", "language", "protocol",
                   "project", "algorithm", "artifact", "concept", "entity"]


def remap_expected(row: dict) -> dict:
    """Convert 90-gold schema into our canonical schema with 10-type labels."""
    ents = []
    for e in row.get("expected_entities") or []:
        nt = TYPE_MAP.get(e.get("type"))
        if not nt:
            continue
        ents.append({"name": e.get("name") or "", "type": nt})
    ent_names = {e["name"] for e in ents}
    rels = []
    for r in row.get("expected_relationships") or []:
        if r.get("source") in ent_names and r.get("target") in ent_names:
            rels.append({
                "source": r["source"],
                "target": r["target"],
                "type": r["type"],
            })
    return {
        "id": row["id"],
        "tier": row.get("tier", ""),
        "topic": row.get("topic", ""),
        "text": row["text"],
        "entities": ents,
        "relationships": rels,
        "memory_type": row.get("expected_memory_type", "fact"),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--out", type=Path,
                   default=ROOT / "runs" / "2026-04-17-push-to-95" / "bench_on_90gold.json")
    args = p.parse_args()

    import torch
    from gliner import GLiNER

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} | model: {args.model}", flush=True)
    model = GLiNER.from_pretrained(str(args.model))
    if device == "cuda":
        model = model.to("cuda")

    # Load and remap gold
    gold_rows = []
    with GOLD_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            gold_rows.append(remap_expected(json.loads(line)))
    print(f"Loaded {len(gold_rows)} gold rows (10-type remapped)", flush=True)

    # Run inference
    preds: list[dict] = []
    agg_lenient = AggregatedMetrics()
    latencies: list[float] = []

    for i, g in enumerate(gold_rows):
        t0 = time.perf_counter()
        raw = model.predict_entities(g["text"], CODING10_LABELS, threshold=args.threshold)
        dt = (time.perf_counter() - t0) * 1000
        latencies.append(dt)

        pred_ents = [{"name": g["text"][e["start"]:e["end"]],
                      "type": e["label"]} for e in raw]
        predicted = {
            "entities": pred_ents,
            "relationships": [],
            "memory_type": "fact",
        }
        preds.append({"id": g["id"], "entities": pred_ents})

        m = score_example(
            example_id=g["id"], tier=g["tier"], topic=g["topic"],
            gold_entities=g["entities"],
            gold_relationships=g["relationships"],
            gold_memory_type=g["memory_type"],
            predicted=predicted,
        )
        agg_lenient.add(m)

    # Lenient (historical) summary
    lenient = {
        "entity_precision": statistics.mean(agg_lenient.entity_precision),
        "entity_recall": statistics.mean(agg_lenient.entity_recall),
        "entity_f1": agg_lenient.entity_f1(),
        "type_accuracy": statistics.mean(agg_lenient.type_accuracy) if agg_lenient.type_accuracy else 0.0,
        "memtype_accuracy": statistics.mean(agg_lenient.memtype_accuracy),
        "n_examples": agg_lenient.n_examples,
    }

    # Strict entity-pair
    pred_index = {p["id"]: p for p in preds}
    strict = pair_score(gold_rows, pred_index)

    report = {
        "model": str(args.model),
        "threshold": args.threshold,
        "labels": CODING10_LABELS,
        "gold": str(GOLD_PATH),
        "n_rows": len(gold_rows),
        "latency_ms_per_row_mean": statistics.mean(latencies),
        "lenient_historical_scorer": lenient,
        "strict_entity_pair_scorer": {
            "micro_f1": strict["micro_f1"],
            "micro_precision": strict["micro_precision"],
            "micro_recall": strict["micro_recall"],
            "name_recall": strict["components"]["name_recall"],
            "type_accuracy_given_name": strict["components"]["type_accuracy_given_name"],
            "n_gold_entities": strict["n_gold_entities"],
            "n_pred_entities": strict["n_pred_entities"],
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LENIENT (historical extraction_eval scorer, name match only) ===")
    print(f"  entity F1:       {lenient['entity_f1']:.3f}  (P {lenient['entity_precision']:.3f}, R {lenient['entity_recall']:.3f})")
    print(f"  type accuracy:   {lenient['type_accuracy']:.3f}  (on name-matched entities)")
    print(f"  memtype acc:     {lenient['memtype_accuracy']:.3f}")
    print("\n=== STRICT (entity-pair F1, name + type must both match) ===")
    print(f"  entity-pair F1:  {strict['micro_f1']:.3f}  (P {strict['micro_precision']:.3f}, R {strict['micro_recall']:.3f})")
    print(f"  name recall:     {strict['components']['name_recall']:.3f}")
    print(f"  type acc given:  {strict['components']['type_accuracy_given_name']:.3f}")
    print(f"\nmean latency: {report['latency_ms_per_row_mean']:.1f} ms/row")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
