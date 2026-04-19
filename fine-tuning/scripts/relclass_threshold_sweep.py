"""Threshold sweep for a pair-wise relation classifier.

Predict positive iff `max_pos_prob > threshold * none_prob`. Sweep threshold
values on val, pick best pos_micro_f1, report that threshold's metrics on test.

Usage:
    python -m scripts.relclass_threshold_sweep \
        --model models/relclass/modernbert-base/best \
        --val data/splits/relclass_val.jsonl \
        --test data/splits/relclass_test.jsonl \
        --out runs/relclass/modernbert-base/sweep.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_relclass import LABEL2ID, mark_text, load_rows  # noqa: E402


THRESHOLDS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0]


def infer_probs(model, tokenizer, rows, device, batch_size, max_length):
    import numpy as np
    import torch
    model.train(False)
    all_probs = []
    texts = [mark_text(r) for r in rows]
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = tokenizer(batch, truncation=True, max_length=max_length,
                            padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1)
            all_probs.append(probs.cpu().numpy())
    return np.concatenate(all_probs, axis=0)


def score_at_threshold(probs, y_true, threshold, none_id):
    import numpy as np
    none_prob = probs[:, none_id]
    pos_probs = probs.copy()
    pos_probs[:, none_id] = 0.0
    best_pos_prob = pos_probs.max(axis=-1)
    best_pos_label = pos_probs.argmax(axis=-1)
    predict_pos = best_pos_prob > threshold * none_prob
    y_pred = np.where(predict_pos, best_pos_label, none_id)

    pos_mask = y_true != none_id
    pred_pos_mask = y_pred != none_id
    correct_pos = int(((y_pred == y_true) & pos_mask).sum())
    total_gold_pos = int(pos_mask.sum())
    total_pred_pos = int(pred_pos_mask.sum())

    pos_p = correct_pos / total_pred_pos if total_pred_pos else 0.0
    pos_r = correct_pos / total_gold_pos if total_gold_pos else 0.0
    pos_f1 = (2 * pos_p * pos_r) / (pos_p + pos_r) if (pos_p + pos_r) else 0.0
    accuracy = float((y_pred == y_true).mean())
    return {
        "threshold": threshold,
        "pos_f1": pos_f1,
        "pos_precision": pos_p,
        "pos_recall": pos_r,
        "accuracy": accuracy,
        "n_pred_pos": total_pred_pos,
    }


def main() -> int:
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--val", required=True, type=Path)
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

    none_id = LABEL2ID["NONE"]

    val_rows = load_rows(args.val)
    test_rows = load_rows(args.test)
    print(f"val rows: {len(val_rows)}, test rows: {len(test_rows)}, device: {device}", flush=True)

    val_y = np.array([LABEL2ID.get(r["label"], none_id) for r in val_rows])
    test_y = np.array([LABEL2ID.get(r["label"], none_id) for r in test_rows])

    val_probs = infer_probs(model, tokenizer, val_rows, device, args.batch_size, args.max_length)
    test_probs = infer_probs(model, tokenizer, test_rows, device, args.batch_size, args.max_length)

    val_sweep = [score_at_threshold(val_probs, val_y, t, none_id) for t in THRESHOLDS]
    best_val = max(val_sweep, key=lambda x: x["pos_f1"])
    best_t = best_val["threshold"]

    test_at_best = score_at_threshold(test_probs, test_y, best_t, none_id)
    test_sweep = [score_at_threshold(test_probs, test_y, t, none_id) for t in THRESHOLDS]

    result = {
        "model": args.model.as_posix(),
        "val_sweep": val_sweep,
        "test_sweep": test_sweep,
        "best_val_threshold": best_t,
        "best_val_metrics": best_val,
        "test_at_best_threshold": test_at_best,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))

    print(f"\nval sweep ({len(val_rows)} rows):")
    for row in val_sweep:
        print(f"  t={row['threshold']:5.2f} F1={row['pos_f1']:.4f} P={row['pos_precision']:.3f} R={row['pos_recall']:.3f} acc={row['accuracy']:.3f} npp={row['n_pred_pos']:5d}")
    print(f"\nbest val threshold = {best_t}  (F1={best_val['pos_f1']:.4f})")
    print(f"\ntest at best threshold ({len(test_rows)} rows):")
    print(f"  F1={test_at_best['pos_f1']:.4f} P={test_at_best['pos_precision']:.3f} R={test_at_best['pos_recall']:.3f} acc={test_at_best['accuracy']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
