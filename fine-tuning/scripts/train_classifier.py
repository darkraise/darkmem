"""Fine-tune a small text classifier for memory type classification.

Usage:
    python -m scripts.train_classifier                       # default: DeBERTa-v3-small
    python -m scripts.train_classifier --base microsoft/MiniLM-L12-H384-uncased
    python -m scripts.train_classifier --epochs 20 --lr 2e-5
    python -m scripts.train_classifier --cpu                 # force CPU (debug only)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "classification" / "train_v2.jsonl"
OUTPUT_DIR = ROOT / "models" / "classifier-darkmem-v2"

LABELS = [
    "fact", "decision", "preference", "problem", "reference", "architecture", "milestone",
]
LABEL_TO_ID = {l: i for i, l in enumerate(LABELS)}
ID_TO_LABEL = {i: l for i, l in enumerate(LABELS)}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_data(path: Path) -> tuple[list[str], list[int]]:
    texts: list[str] = []
    labels: list[int] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj["label"] not in LABEL_TO_ID:
                raise ValueError(f"Unknown label: {obj['label']}")
            texts.append(obj["text"])
            labels.append(LABEL_TO_ID[obj["label"]])
    return texts, labels


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="macro", zero_division=0)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1,
        "macro_precision": precision,
        "macro_recall": recall,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune a text classifier")
    parser.add_argument("--base", default="microsoft/deberta-v3-small",
                        help="Base model (default: microsoft/deberta-v3-small)")
    parser.add_argument("--epochs", type=int, default=15,
                        help="Training epochs (default: 15)")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Training batch size (default: 16)")
    parser.add_argument("--lr", type=float, default=2e-5,
                        help="Learning rate (default: 2e-5)")
    parser.add_argument("--weight-decay", type=float, default=0.01,
                        help="Weight decay (default: 0.01)")
    parser.add_argument("--warmup-ratio", type=float, default=0.1,
                        help="LR warmup ratio (default: 0.1)")
    parser.add_argument("--max-length", type=int, default=256,
                        help="Max sequence length (default: 256)")
    parser.add_argument("--val-split", type=float, default=0.15,
                        help="Validation split fraction (default: 0.15)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data", type=Path, default=DATA_PATH,
                        help=f"Training data JSONL (default: {DATA_PATH})")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU training (for debugging)")
    parser.add_argument("--hf-token", type=str, default=None,
                        help="HuggingFace token for gated models")
    parser.add_argument("--trust-remote-code", action="store_true",
                        help="Enable trust_remote_code for custom model architectures")
    parser.add_argument("--bf16", action="store_true",
                        help="Enable bf16 mixed-precision training")
    parser.add_argument("--gradient-checkpointing", action="store_true",
                        help="Enable gradient checkpointing to save VRAM at ~20%% training cost")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1,
                        help="Gradient accumulation steps (effective batch = batch_size * this)")
    parser.add_argument("--class-weights", action="store_true",
                        help="Weight cross-entropy loss by inverse class frequency")
    parser.add_argument("--lr-scheduler-type", default="linear",
                        choices=["linear", "cosine", "cosine_with_restarts", "polynomial", "constant", "constant_with_warmup"],
                        help="LR schedule for the HF Trainer (default: linear)")
    parser.add_argument("--label-smoothing", type=float, default=0.0,
                        help="Label smoothing factor (0.0-0.3, default 0.0)")
    from scripts._hf_dataset_loader import add_hf_args, resolve_dataset_path
    add_hf_args(parser, purpose="train")
    args = parser.parse_args()

    # Allow either the local --data path or an HF dataset repo pull.
    if args.hf_train_repo:
        args.data = resolve_dataset_path(
            local=args.data if args.data and args.data != DATA_PATH else None,
            repo=args.hf_train_repo,
            filename=args.hf_train_file,
            token=args.hf_token,
        )

    set_seed(args.seed)

    if not torch.cuda.is_available() and not args.cpu:
        print("ERROR: CUDA not available. Use --cpu to force CPU, or check your install.", file=sys.stderr)
        return 1
    device = "cpu" if args.cpu else "cuda"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Load data
    print(f"\nLoading data from {args.data}...")
    texts, labels = load_data(args.data)
    print(f"  Total examples: {len(texts)}")
    label_counts = {l: labels.count(LABEL_TO_ID[l]) for l in LABELS}
    print(f"  Distribution: {label_counts}")

    # Stratified train/val split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels,
        test_size=args.val_split,
        stratify=labels,
        random_state=args.seed,
    )
    print(f"  Train: {len(train_texts)}, Val: {len(val_texts)}")

    # Import transformers after sanity checks
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        DataCollatorWithPadding,
        EarlyStoppingCallback,
    )
    from datasets import Dataset

    print(f"\nLoading tokenizer and model: {args.base}")
    tokenizer_kwargs = {}
    if args.hf_token:
        tokenizer_kwargs["token"] = args.hf_token
    if args.trust_remote_code:
        tokenizer_kwargs["trust_remote_code"] = True
    tokenizer = AutoTokenizer.from_pretrained(args.base, **tokenizer_kwargs)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base,
        num_labels=len(LABELS),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
        **tokenizer_kwargs,
    )

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_length,
        )

    train_ds = Dataset.from_dict({"text": train_texts, "label": train_labels}).map(tokenize, batched=True)
    val_ds = Dataset.from_dict({"text": val_texts, "label": val_labels}).map(tokenize, batched=True)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        save_total_limit=2,
        logging_steps=10,
        report_to="none",
        seed=args.seed,
        bf16=args.bf16,
        fp16=False,
        max_grad_norm=1.0,
        dataloader_num_workers=0,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        gradient_checkpointing=args.gradient_checkpointing,
        lr_scheduler_type=args.lr_scheduler_type,
        label_smoothing_factor=args.label_smoothing,
    )
    if args.gradient_checkpointing:
        model.config.use_cache = False

    # Optional inverse-frequency class weights for cross-entropy loss
    class_weights_tensor = None
    if args.class_weights:
        counts = np.bincount(np.array(train_labels), minlength=len(LABELS))
        weights = counts.sum() / (len(LABELS) * np.maximum(counts, 1))
        class_weights_tensor = torch.tensor(weights, dtype=torch.float32)
        print(f"  Class weights (inverse-frequency): {dict(zip(LABELS, [round(float(w), 3) for w in weights]))}")

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            loss_fct = torch.nn.CrossEntropyLoss(
                weight=class_weights_tensor.to(logits.device) if class_weights_tensor is not None else None
            )
            loss = loss_fct(logits.view(-1, len(LABELS)), labels.view(-1))
            return (loss, outputs) if return_outputs else loss

    TrainerCls = WeightedTrainer if class_weights_tensor is not None else Trainer
    trainer = TrainerCls(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    print(f"\nTraining for up to {args.epochs} epochs (early stopping patience=3)")
    t_start = time.perf_counter()
    trainer.train()
    elapsed = time.perf_counter() - t_start
    print(f"\nTraining finished in {elapsed:.1f}s")

    # Final evaluation on val set
    print("\nFinal validation metrics:")
    eval_metrics = trainer.evaluate()
    for k, v in eval_metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")

    # Save best model
    best_dir = output_dir / "best"
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"\nBest model saved to: {best_dir}")

    # Save run metadata
    metadata = {
        "base_model": args.base,
        "epochs_run": trainer.state.epoch,
        "best_metric": trainer.state.best_metric,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "train_size": len(train_texts),
        "val_size": len(val_texts),
        "labels": LABELS,
        "training_args": {
            "lr": args.lr,
            "batch_size": args.batch_size,
            "weight_decay": args.weight_decay,
            "warmup_ratio": args.warmup_ratio,
            "max_length": args.max_length,
        },
        "final_metrics": {k: float(v) for k, v in eval_metrics.items() if isinstance(v, (int, float))},
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Metadata saved to: {output_dir / 'run_metadata.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
