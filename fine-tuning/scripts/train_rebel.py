"""Fine-tune REBEL-large for relationship extraction.

Trains on linearized triplet format: text + entities -> triplet sequences.
Uses standard HuggingFace Seq2Seq training.

Usage:
    python -m scripts.train_rebel
    python -m scripts.train_rebel --epochs 5 --lr 3e-5
    python -m scripts.train_rebel --cpu
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SPLITS_DIR = ROOT / "data" / "splits"
MODELS_DIR = ROOT / "models"
DEFAULT_BASE = "Babelscape/rebel-large"


def load_rebel_dataset(path: Path) -> list[dict]:
    """Load JSONL in REBEL format: {input, output}."""
    examples = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def train(
    base_model: str,
    epochs: int,
    lr: float,
    batch_size: int,
    max_source_length: int,
    max_target_length: int,
    use_cpu: bool,
    output_dir: Path,
) -> None:
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        EarlyStoppingCallback,
    )

    device = "cpu" if use_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}", flush=True)
    if device == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}", flush=True)
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB", flush=True)

    print(f"\nLoading base model: {base_model}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(base_model)

    if device == "cuda":
        model = model.to("cuda")

    print("Loading training data...", flush=True)
    train_path = SPLITS_DIR / "rebel_train.jsonl"
    val_path = SPLITS_DIR / "rebel_val.jsonl"

    if not train_path.exists():
        print(f"ERROR: {train_path} not found. Run validate_data.py first.", file=sys.stderr)
        sys.exit(1)

    train_raw = load_rebel_dataset(train_path)
    val_raw = load_rebel_dataset(val_path) if val_path.exists() else []
    print(f"  Train: {len(train_raw)}, Val: {len(val_raw)}", flush=True)

    def tokenize_fn(batch: dict) -> dict:
        inputs = tokenizer(
            batch["input"],
            max_length=max_source_length,
            truncation=True,
            padding="max_length",
        )
        targets = tokenizer(
            batch["output"],
            max_length=max_target_length,
            truncation=True,
            padding="max_length",
        )
        pad_id = tokenizer.pad_token_id
        inputs["labels"] = [
            [(-100 if tok == pad_id else tok) for tok in seq]
            for seq in targets["input_ids"]
        ]
        return inputs

    train_dataset = Dataset.from_list(train_raw).map(tokenize_fn, batched=True, remove_columns=["input", "output"])
    val_dataset = Dataset.from_list(val_raw).map(tokenize_fn, batched=True, remove_columns=["input", "output"]) if val_raw else None

    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        warmup_steps=200,
        weight_decay=0.01,
        predict_with_generate=True,
        bf16=device == "cuda" and torch.cuda.is_bf16_supported(),
        save_strategy="epoch",
        eval_strategy="epoch" if val_dataset else "no",
        load_best_model_at_end=bool(val_dataset),
        metric_for_best_model="eval_loss" if val_dataset else None,
        greater_is_better=False if val_dataset else None,
        save_total_limit=3,
        logging_steps=50,
        dataloader_num_workers=0,
        report_to="none",
    )

    callbacks = []
    if val_dataset:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=3))

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        callbacks=callbacks,
    )

    print(f"\nTraining for {epochs} epochs, lr={lr}, batch_size={batch_size}", flush=True)
    print(f"  max_source_length={max_source_length}, max_target_length={max_target_length}", flush=True)
    t0 = time.perf_counter()
    trainer.train()
    elapsed = time.perf_counter() - t0
    print(f"\nTraining complete in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)

    best_dir = output_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"Model saved to: {best_dir}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune REBEL relationship extractor")
    parser.add_argument("--base-model", default=DEFAULT_BASE, help=f"Base model (default: {DEFAULT_BASE})")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs (default: 10)")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate (default: 5e-5)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--max-source-length", type=int, default=512, help="Max input length (default: 512)")
    parser.add_argument("--max-target-length", type=int, default=128, help="Max output length (default: 128)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU training")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else MODELS_DIR / "rebel-darkmem"

    train(
        base_model=args.base_model,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        max_source_length=args.max_source_length,
        max_target_length=args.max_target_length,
        use_cpu=args.cpu,
        output_dir=output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
