# fine-tuning/scripts/eval_entity.py
"""Entity eval harness. Reports per-type P/R/F1, type accuracy, span IoU, latency."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    s = max(a[0], b[0])
    e = min(a[1], b[1])
    inter = max(0, e - s)
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def score(gold_rows: list[dict], pred_rows: dict) -> dict:
    tp_by_type: dict[str, int] = defaultdict(int)
    fp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)
    ious: list[float] = []
    type_correct = 0
    type_total = 0
    for g in gold_rows:
        p = pred_rows.get(g["id"], {}).get("entities", [])
        gold_set = {(e["name"], e["type"], e["start"], e["end"]) for e in g["entities"]}
        pred_set = {(e["name"], e["type"], e["start"], e["end"]) for e in p}
        for e in gold_set:
            if e in pred_set:
                tp_by_type[e[1]] += 1
            else:
                fn_by_type[e[1]] += 1
        for e in pred_set:
            if e not in gold_set:
                fp_by_type[e[1]] += 1
        # span IoU + type accuracy on best-match pairs
        for ge in g["entities"]:
            best = max(
                (pe for pe in p if pe["name"] == ge["name"]),
                key=lambda pe: _iou((ge["start"], ge["end"]), (pe["start"], pe["end"])),
                default=None,
            )
            if best is not None:
                ious.append(_iou((ge["start"], ge["end"]), (best["start"], best["end"])))
                type_total += 1
                if best["type"] == ge["type"]:
                    type_correct += 1
    per_type: dict[str, dict] = {}
    for t in set(tp_by_type) | set(fp_by_type) | set(fn_by_type):
        tp, fp, fn = tp_by_type[t], fp_by_type[t], fn_by_type[t]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_type[t] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
    tp = sum(tp_by_type.values())
    fp = sum(fp_by_type.values())
    fn = sum(fn_by_type.values())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "micro_precision": prec,
        "micro_recall": rec,
        "micro_f1": f1,
        "type_accuracy": type_correct / type_total if type_total else 0.0,
        "mean_iou": sum(ious) / len(ious) if ious else 0.0,
        "per_type": per_type,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--pred", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    gold = [json.loads(l) for l in a.gold.read_text(encoding="utf-8").splitlines() if l.strip()]
    pred = {json.loads(l)["id"]: json.loads(l) for l in a.pred.read_text(encoding="utf-8").splitlines() if l.strip()}
    metrics = score(gold, pred)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "per_type"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
