"""Score a pair-wise relation classifier on a relclass JSONL table.

Computes micro precision/recall/F1 on positive classes only (excluding NONE),
plus per-class F1 and NONE precision. No Python eval() anywhere, purely JSON.

Usage:
    python -m scripts.eval_relclass \
        --model models/relclass/modernbert-base/best \
        --test data/splits/relclass_rebelgold_test.jsonl \
        --out runs/relclass/modernbert-base/rebelgold_metrics.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_relclass import LABELS, LABEL2ID, ID2LABEL, mark_text, load_rows  # noqa: E402


def main() -> int:
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--test", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-length", type=int, default=256)
    args = p.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_path = args.model.resolve().as_posix()
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path, trust_remote_code=True
    ).to(device)
    model.eval()

    rows = load_rows(args.test)
    texts = [mark_text(r) for r in rows]
    y_true = np.array([LABEL2ID.get(r["label"], LABEL2ID["NONE"]) for r in rows])
    print(f"rows: {len(rows)}, device: {device}", flush=True)

    y_pred = np.zeros(len(rows), dtype=np.int64)
    with torch.no_grad():
        for i in range(0, len(texts), args.batch_size):
            batch = texts[i:i + args.batch_size]
            enc = tokenizer(batch, truncation=True, max_length=args.max_length,
                            padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            y_pred[i:i + args.batch_size] = logits.argmax(-1).cpu().numpy()

    none_id = LABEL2ID["NONE"]
    pos_mask = y_true != none_id
    pred_pos_mask = y_pred != none_id

    correct_pos = int(((y_pred == y_true) & pos_mask).sum())
    total_gold_pos = int(pos_mask.sum())
    total_pred_pos = int(pred_pos_mask.sum())

    pos_p = correct_pos / total_pred_pos if total_pred_pos else 0.0
    pos_r = correct_pos / total_gold_pos if total_gold_pos else 0.0
    pos_f1 = (2 * pos_p * pos_r) / (pos_p + pos_r) if (pos_p + pos_r) else 0.0

    none_mask = y_true == none_id
    pred_none_mask = y_pred == none_id
    none_tp = int(((y_pred == y_true) & none_mask).sum())
    none_p = none_tp / int(pred_none_mask.sum()) if pred_none_mask.sum() else 0.0
    none_r = none_tp / int(none_mask.sum()) if none_mask.sum() else 0.0

    per_class = {}
    for label, lid in LABEL2ID.items():
        gold = int((y_true == lid).sum())
        pred = int((y_pred == lid).sum())
        tp = int(((y_pred == y_true) & (y_true == lid)).sum())
        pp = tp / pred if pred else 0.0
        rr = tp / gold if gold else 0.0
        f1 = (2 * pp * rr) / (pp + rr) if (pp + rr) else 0.0
        per_class[label] = {"precision": pp, "recall": rr, "f1": f1, "support": gold, "n_pred": pred}

    accuracy = float((y_pred == y_true).mean())

    result = {
        "accuracy": accuracy,
        "pos_micro_precision": pos_p,
        "pos_micro_recall": pos_r,
        "pos_micro_f1": pos_f1,
        "none_precision": none_p,
        "none_recall": none_r,
        "per_class": per_class,
        "n_rows": len(rows),
        "n_gold_pos": total_gold_pos,
        "n_pred_pos": total_pred_pos,
        "confusion_counter": {ID2LABEL[int(l)]: int(c) for l, c in Counter(y_pred.tolist()).most_common()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    summary = {k: v for k, v in result.items() if k not in ("per_class", "confusion_counter")}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
