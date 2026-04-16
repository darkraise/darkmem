"""Fine-tune a SetFit classifier using contrastive learning.

Usage:
    python -m scripts.train_setfit
    python -m scripts.train_setfit --base sentence-transformers/all-MiniLM-L6-v2 --epochs 2
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
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "classification" / "train.jsonl"
OUTPUT_DIR = ROOT / "models" / "classifier-setfit"

LABELS = [
    "fact", "decision", "preference", "problem", "reference", "architecture",
    "milestone", "workaround", "goal", "question", "observation", "comparison",
]
LABEL_TO_ID = {l: i for i, l in enumerate(LABELS)}


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
            texts.append(obj["text"])
            labels.append(LABEL_TO_ID[obj["label"]])
    return texts, labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a SetFit classifier")
    parser.add_argument("--base", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--epochs", type=int, default=2, help="Contrastive training epochs")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--body-lr", type=float, default=2e-5)
    parser.add_argument("--head-lr", type=float, default=1e-2)
    parser.add_argument("--num-iterations", type=int, default=20,
                        help="Contrastive pairs sampled per training example")
    parser.add_argument("--val-split", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    set_seed(args.seed)

    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 1
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    print(f"\nLoading data from {DATA_PATH}...")
    texts, labels = load_data(DATA_PATH)
    print(f"  Total examples: {len(texts)}")

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels,
        test_size=args.val_split,
        stratify=labels,
        random_state=args.seed,
    )
    print(f"  Train: {len(train_texts)}, Val: {len(val_texts)}")

    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments

    train_ds = Dataset.from_dict({"text": train_texts, "label": train_labels})
    val_ds = Dataset.from_dict({"text": val_texts, "label": val_labels})

    print(f"\nLoading base model: {args.base}")
    model = SetFitModel.from_pretrained(
        args.base,
        labels=LABELS,
    )

    training_args = TrainingArguments(
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        num_iterations=args.num_iterations,
        body_learning_rate=args.body_lr,
        head_learning_rate=args.head_lr,
        seed=args.seed,
        output_dir=str(Path(args.output_dir) / "checkpoints"),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
    )

    print(f"\nTraining for {args.epochs} epoch(s) with {args.num_iterations} contrastive iterations per example")
    t_start = time.perf_counter()
    trainer.train()
    elapsed = time.perf_counter() - t_start
    print(f"\nTraining finished in {elapsed:.1f}s")

    # Evaluate on val set
    print("\nFinal validation metrics:")
    metrics = trainer.evaluate()
    print(f"  {metrics}")

    # Save best model
    best_dir = Path(args.output_dir) / "best"
    model.save_pretrained(str(best_dir))
    print(f"\nBest model saved to: {best_dir}")

    # Save run metadata
    metadata = {
        "base_model": args.base,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "num_iterations": args.num_iterations,
        "train_size": len(train_texts),
        "val_size": len(val_texts),
        "labels": LABELS,
        "final_metrics": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
    }
    (Path(args.output_dir) / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
