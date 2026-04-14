# fine-tuning/scripts/eval_classifier.py
"""Memory classifier eval. Reports per-type accuracy, macro-F1, confusion matrix, reference recall."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def score(gold_rows: list[dict], pred_rows: dict) -> dict:
    classes = sorted({g["memory_type"] for g in gold_rows})
    conf: dict[str, dict[str, int]] = {c: {c2: 0 for c2 in classes} for c in classes}
    correct = 0
    total = 0
    tp_by_type: dict[str, int] = defaultdict(int)
    fp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)
    for g in gold_rows:
        gt = g["memory_type"]
        pt = pred_rows.get(g["id"], {}).get("memory_type") or pred_rows.get(g["id"], {}).get("label", "")
        conf.setdefault(gt, {}).setdefault(pt, 0)
        conf[gt][pt] = conf[gt].get(pt, 0) + 1
        total += 1
        if pt == gt:
            correct += 1
            tp_by_type[gt] += 1
        else:
            fn_by_type[gt] += 1
            fp_by_type[pt] += 1
    per_type: dict[str, dict] = {}
    for t in classes:
        tp, fp, fn = tp_by_type[t], fp_by_type[t], fn_by_type[t]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_type[t] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
    macro_f1 = sum(v["f1"] for v in per_type.values()) / len(per_type) if per_type else 0.0
    return {
        "accuracy": correct / total if total else 0.0,
        "macro_f1": macro_f1,
        "reference_recall": per_type.get("reference", {}).get("recall", 0.0),
        "confusion_matrix": conf,
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
    print(json.dumps({k: v for k, v in metrics.items() if k not in {"confusion_matrix", "per_type"}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
