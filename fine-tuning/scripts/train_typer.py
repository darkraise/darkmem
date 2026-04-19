"""Stage 2 of two-stage entity extraction: fine-tune a ModernBERT-base
sequence classifier to assign one of 10 coding-taxonomy types to an entity
span marked inside its context with [ENT]...[/ENT].

Training data: data/splits/typer_train.jsonl / _val / _test
  Each row: {"text": "...[ENT]span[/ENT]...", "span": str, "label": str}

Usage:
    python -m scripts.train_typer
    python -m scripts.train_typer --base answerdotai/ModernBERT-base --epochs 5
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SPLITS = ROOT / "data" / "splits"
LABELS = ["tool", "service", "database", "language", "protocol",
          "project", "algorithm", "artifact", "concept", "entity"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for i, l in enumerate(LABELS)}


def load(path: Path) -> tuple[list[str], list[int]]:
    texts, labs = [], []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            texts.append(r["text"])
            labs.append(LABEL2ID[r["label"]])
    return texts, labs


def set_seed(s: int) -> None:
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
        "weighted_f1": f1_score(labels, preds, average="weighted"),
    }


def main() -> int:
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForSequenceClassification, AutoTokenizer,
        Trainer, TrainingArguments, DataCollatorWithPadding,
    )

    p = argparse.ArgumentParser()
    p.add_argument("--base", default="answerdotai/ModernBERT-base")
    p.add_argument("--output-dir", default=str(ROOT / "models" / "typer-modernbert-coding10"))
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--lr", type=float, default=3e-5)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fp16", action="store_true", help="force fp16 (for Turing GPUs)")
    p.add_argument("--train-path", default=None, help="Typer train JSONL (defaults to data/splits/typer_train.jsonl)")
    p.add_argument("--val-path", default=None, help="Typer val JSONL (defaults to data/splits/typer_val.jsonl)")
    p.add_argument("--hf-token", default=None, help="HuggingFace API token (env HF_TOKEN otherwise).")
    from scripts._hf_dataset_loader import add_hf_args, resolve_dataset_path
    add_hf_args(p, purpose="train")
    add_hf_args(p, purpose="val")
    args = p.parse_args()

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    train_path = resolve_dataset_path(
        local=Path(args.train_path) if args.train_path else None,
        repo=args.hf_train_repo,
        filename=args.hf_train_file,
        token=args.hf_token,
    ) if (args.train_path or args.hf_train_repo) else (SPLITS / "typer_train.jsonl")
    val_path = resolve_dataset_path(
        local=Path(args.val_path) if args.val_path else None,
        repo=args.hf_val_repo,
        filename=args.hf_val_file,
        token=args.hf_token,
    ) if (args.val_path or args.hf_val_repo) else (SPLITS / "typer_val.jsonl")
    train_texts, train_y = load(train_path)
    val_texts, val_y = load(val_path)
    print(f"train: {len(train_texts)} typer rows, val: {len(val_texts)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    # Add [ENT] / [/ENT] as special tokens so they tokenize cleanly as anchors.
    added = tokenizer.add_special_tokens(
        {"additional_special_tokens": ["[ENT]", "[/ENT]"]}
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base, num_labels=len(LABELS),
        id2label=ID2LABEL, label2id=LABEL2ID,
        trust_remote_code=True,
    )
    if added:
        model.resize_token_embeddings(len(tokenizer))
    if device == "cuda":
        model = model.to("cuda")

    class JD(Dataset):
        def __init__(self, texts, labels):
            self.texts, self.labels = texts, labels
        def __len__(self): return len(self.texts)
        def __getitem__(self, i):
            enc = tokenizer(self.texts[i], truncation=True,
                            max_length=args.max_length, padding=False)
            enc["labels"] = int(self.labels[i])
            return enc

    train_ds = JD(train_texts, train_y)
    val_ds = JD(val_texts, val_y)

    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported() and not args.fp16
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        warmup_ratio=0.1,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=50,
        bf16=use_bf16,
        fp16=args.fp16 or (device == "cuda" and not use_bf16),
        report_to="none",
        dataloader_num_workers=0,
    )

    # transformers 5.x: tokenizer is passed via processing_class
    trainer_kwargs = dict(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )
    try:
        trainer = Trainer(**trainer_kwargs, processing_class=tokenizer)
    except TypeError:
        trainer = Trainer(**trainer_kwargs, tokenizer=tokenizer)

    print(f"\nTraining {args.base} -> {args.output_dir}", flush=True)
    trainer.train()
    trainer.save_model(str(Path(args.output_dir) / "best"))
    tokenizer.save_pretrained(str(Path(args.output_dir) / "best"))
    print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
