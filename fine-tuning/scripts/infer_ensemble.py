"""Ensemble inference for memory-type classification.

Runs N classifier models on a gold JSONL and emits averaged-logit predictions.
Also emits a normalised gold file so `scripts/eval_classifier.py` can score it directly.

Usage:
    python -m scripts.infer_ensemble \
        --models models/classifier-v2-modernbert-base-seed42/best \
                 models/classifier-v2-modernbert-base-seed7/best \
                 models/classifier-v2-modernbert-base-seed1337/best \
        --gold ../docs/e2e/scripts/classification_eval/corpus/gold_v2.jsonl \
        --out runs/classification-v2-modernbert-base-ensemble/gold_v2_preds.jsonl \
        --norm-out runs/classification-v2-modernbert-base-ensemble/gold_v2_norm.jsonl \
        --max-length 512
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, nargs="+", required=True,
                        help="One or more model directories (each with tokenizer + model)")
    parser.add_argument("--gold", type=Path, required=True,
                        help="Gold JSONL with fields {id, type, text}")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output predictions JSONL with fields {id, memory_type}")
    parser.add_argument("--norm-out", type=Path, default=None,
                        help="Optional output: normalised gold JSONL with memory_type field")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    gold = [json.loads(l) for l in args.gold.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"gold rows: {len(gold)}")

    tokenizers = [AutoTokenizer.from_pretrained(m) for m in args.models]
    models = []
    for m in args.models:
        mdl = AutoModelForSequenceClassification.from_pretrained(m).to(args.device)
        mdl.train(False)  # inference mode (equivalent to .eval())
        models.append(mdl)
    id2label = models[0].config.id2label
    for m in models[1:]:
        if m.config.id2label != id2label:
            raise ValueError("Models disagree on id2label mapping; cannot ensemble")
    print(f"ensemble size: {len(models)} models, {len(id2label)} labels")

    preds = []
    with torch.inference_mode():
        for g in gold:
            probs_sum = None
            for tok, model in zip(tokenizers, models):
                t = tok(g["text"], truncation=True, max_length=args.max_length, return_tensors="pt").to(args.device)
                logits = model(**t).logits
                probs = torch.softmax(logits, dim=-1)
                probs_sum = probs if probs_sum is None else probs_sum + probs
            pred_id = int((probs_sum / len(models)).argmax(-1).item())
            preds.append({"id": g["id"], "memory_type": id2label[pred_id]})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(json.dumps(p) for p in preds) + "\n", encoding="utf-8")
    print(f"wrote {len(preds)} preds to {args.out}")

    if args.norm_out:
        args.norm_out.parent.mkdir(parents=True, exist_ok=True)
        norm = [{"id": g["id"], "memory_type": g["type"], "text": g["text"]} for g in gold]
        args.norm_out.write_text("\n".join(json.dumps(n) for n in norm) + "\n", encoding="utf-8")
        print(f"wrote normalised gold to {args.norm_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
