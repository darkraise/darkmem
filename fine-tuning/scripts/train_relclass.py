"""Pair-wise relation classifier trainer.

Reads `data/splits/relclass_{train,val,test}.jsonl` where each row is
{text, e1_name, e1_type, e1_start, e1_end, e2_name, e2_type, e2_start, e2_end,
 label, source_id}. The `label` is one of the 10 relation types plus NONE.

Training input format: the text with `[E1]...[/E1]` and `[E2]...[/E2]` markers
wrapping the two entity spans. Both markers are added as special tokens so the
classifier sees them as anchor positions.

Loss: `CrossEntropyLoss(weight=inverse_class_freq)` computed on the train split.
Backbone: any HF sequence-classification model — ModernBERT-base, DeBERTa-v3-*,
DistilBERT-base, MiniLM.

Usage:
    python -m scripts.train_relclass \
        --base microsoft/deberta-v3-base \
        --output-dir models/relclass-deberta-v3-base \
        --epochs 5 --batch-size 16 --lr 3e-5
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"

LABELS = [
    "NONE",
    "USES", "DEPENDS_ON", "REPLACES", "IS_A", "HAS_PART",
    "DEPLOYED_ON", "CAUSES", "AUTHORED_BY", "HAPPENED_ON", "RELATED_TO",
]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for i, l in enumerate(LABELS)}


def set_seed(s: int) -> None:
    import numpy as np
    import torch
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def mark_text(row: dict[str, Any]) -> str:
    """Insert [E1]/[/E1] and [E2]/[/E2] markers around each entity span.

    Works by sorting the two entity spans by start offset and splicing markers
    in right-to-left order so earlier offsets stay valid.
    """
    text = row["text"]
    e1_start, e1_end = int(row["e1_start"]), int(row["e1_end"])
    e2_start, e2_end = int(row["e2_start"]), int(row["e2_end"])

    spans = [
        (e1_start, e1_end, "[E1]", "[/E1]"),
        (e2_start, e2_end, "[E2]", "[/E2]"),
    ]
    spans.sort(key=lambda x: x[0], reverse=True)  # splice from the right

    out = text
    for start, end, open_tag, close_tag in spans:
        out = out[:end] + close_tag + out[end:]
        out = out[:start] + open_tag + out[start:]
    return out


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()]


def compute_metrics(eval_pred):
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, preds)
    macro_p, macro_r, macro_f, _ = precision_recall_fscore_support(labels, preds, average="macro", zero_division=0)
    micro_p, micro_r, micro_f, _ = precision_recall_fscore_support(labels, preds, average="micro", zero_division=0)
    # Exclude NONE for the "real-rel" micro
    none_id = LABEL2ID["NONE"]
    mask = labels != none_id
    if mask.sum() > 0:
        pos_p, pos_r, pos_f, _ = precision_recall_fscore_support(
            labels[mask], preds[mask], average="micro", zero_division=0, labels=[i for i in range(len(LABELS)) if i != none_id]
        )
    else:
        pos_p = pos_r = pos_f = 0.0
    return {
        "accuracy": acc,
        "macro_f1": macro_f,
        "micro_f1": micro_f,
        "pos_micro_f1": pos_f,
        "pos_micro_precision": pos_p,
        "pos_micro_recall": pos_r,
    }


def main() -> int:
    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForSequenceClassification, AutoTokenizer,
        Trainer, TrainingArguments, DataCollatorWithPadding,
    )

    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True, help="HF model id or local path")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--train-path", default=str(SPLITS / "relclass_train.jsonl"))
    p.add_argument("--val-path", default=str(SPLITS / "relclass_val.jsonl"))
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--lr", type=float, default=3e-5)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fp16", action="store_true", help="force fp16 (for Turing GPUs)")
    p.add_argument("--no-special-tokens", action="store_true",
                   help="Do not add [E1]/[/E1]/[E2]/[/E2] as special tokens; let the tokenizer split them. Recommended for SentencePiece-based models (DeBERTa-v3).")
    p.add_argument("--class-weight-scheme", choices=["inverse", "sqrt", "none"], default="inverse",
                   help="Class-weight scheme for CrossEntropyLoss: inverse=1/freq, sqrt=sqrt(1/freq), none=uniform.")
    args = p.parse_args()

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Device: {device}", flush=True)
    if device == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}", flush=True)
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB", flush=True)

    train_rows = load_rows(Path(args.train_path))
    val_rows = load_rows(Path(args.val_path))
    print(f"train: {len(train_rows)} rows, val: {len(val_rows)}", flush=True)

    train_texts = [mark_text(r) for r in train_rows]
    train_labels = np.array([LABEL2ID[r["label"]] for r in train_rows])
    val_texts = [mark_text(r) for r in val_rows]
    val_labels = np.array([LABEL2ID[r["label"]] for r in val_rows])

    # Class weights from train split only.
    cls_counts = Counter(train_labels.tolist())
    total = sum(cls_counts.values())
    weights = np.zeros(len(LABELS), dtype=np.float32)
    for i in range(len(LABELS)):
        n = cls_counts.get(i, 0)
        if n <= 0:
            weights[i] = 0.0
            continue
        inv = total / (len(LABELS) * n)
        if args.class_weight_scheme == "inverse":
            weights[i] = inv
        elif args.class_weight_scheme == "sqrt":
            weights[i] = float(np.sqrt(inv))
        else:
            weights[i] = 1.0
    print(f"class_weight_scheme={args.class_weight_scheme}", flush=True)
    print(f"class weights: {dict(zip(LABELS, [round(float(w), 3) for w in weights]))}", flush=True)
    class_weights = torch.tensor(weights, device=device)

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    added = 0
    if not args.no_special_tokens:
        added = tokenizer.add_special_tokens(
            {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
        )
    else:
        print("Skipping special-token addition; markers will be split by the base tokenizer.", flush=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base, num_labels=len(LABELS),
        id2label=ID2LABEL, label2id=LABEL2ID,
        trust_remote_code=True,
    )
    if added:
        model.resize_token_embeddings(len(tokenizer))
    if device == "cuda":
        model = model.to("cuda")

    class RCDataset(Dataset):
        def __init__(self, texts, labels):
            self.texts = texts
            self.labels = labels
        def __len__(self):
            return len(self.texts)
        def __getitem__(self, i):
            enc = tokenizer(self.texts[i], truncation=True, max_length=args.max_length)
            enc["labels"] = int(self.labels[i])
            return enc

    train_ds = RCDataset(train_texts, train_labels)
    val_ds = RCDataset(val_texts, val_labels)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported() and not args.fp16
    use_fp16 = args.fp16 or (device == "cuda" and not use_bf16)

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.get("logits")
            loss_fct = nn.CrossEntropyLoss(weight=class_weights)
            loss = loss_fct(logits.view(-1, logits.size(-1)), labels.view(-1))
            return (loss, outputs) if return_outputs else loss

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="pos_micro_f1",
        greater_is_better=True,
        logging_steps=50,
        bf16=use_bf16,
        fp16=use_fp16,
        seed=args.seed,
        report_to="none",
        dataloader_num_workers=0,
    )

    trainer_kwargs = dict(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )
    try:
        trainer = WeightedTrainer(processing_class=tokenizer, **trainer_kwargs)
    except TypeError:
        trainer = WeightedTrainer(tokenizer=tokenizer, **trainer_kwargs)

    trainer.train()

    best_dir = Path(args.output_dir) / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))

    metrics = trainer.evaluate()
    metrics_path = Path(args.output_dir) / "metrics_val.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
