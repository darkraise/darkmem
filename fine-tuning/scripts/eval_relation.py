# fine-tuning/scripts/eval_relation.py
"""Relation eval harness. Reports per-type P/R/F1, direction rate, exact-match."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def score(gold_rows: list[dict], pred_rows: dict) -> dict:
    tp_by_type: dict[str, int] = defaultdict(int)
    fp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)
    direction_correct = 0
    direction_total = 0
    exact_match = 0
    for g in gold_rows:
        p = pred_rows.get(g["id"], {}).get("relationships", [])
        gold_set = {(r["source"], r["target"], r["type"]) for r in g["relationships"]}
        pred_set = {(r["source"], r["target"], r["type"]) for r in p}
        for r in gold_set:
            if r in pred_set:
                tp_by_type[r[2]] += 1
            else:
                fn_by_type[r[2]] += 1
        for r in pred_set:
            if r not in gold_set:
                fp_by_type[r[2]] += 1
        # direction: for each gold (s,t,T), is predicted (s,t,T) or (t,s,T)?
        for (s, t, T) in gold_set:
            direction_total += 1
            if (s, t, T) in pred_set:
                direction_correct += 1
        if gold_set == pred_set:
            exact_match += 1
    per_type: dict[str, dict] = {}
    for t in set(tp_by_type) | set(fp_by_type) | set(fn_by_type):
        tp, fp, fn = tp_by_type[t], fp_by_type[t], fn_by_type[t]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_type[t] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
    tp, fp, fn = sum(tp_by_type.values()), sum(fp_by_type.values()), sum(fn_by_type.values())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "micro_precision": prec,
        "micro_recall": rec,
        "micro_f1": f1,
        "direction_rate": direction_correct / direction_total if direction_total else 0.0,
        "exact_match_rate": exact_match / len(gold_rows) if gold_rows else 0.0,
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
