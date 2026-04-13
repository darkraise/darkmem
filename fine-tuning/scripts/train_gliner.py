"""Fine-tune GLiNER on the validated training data.

Loads the base gliner_multitask-large-v0.5 model and fine-tunes it on
domain-specific entity spans using the gliner Trainer API directly.
The data_collator_class on the loaded model handles tokenization and
label preparation from raw {tokenized_text, ner} dicts.

Usage:
    python -m scripts.train_gliner
    python -m scripts.train_gliner --epochs 3 --lr 2e-5
    python -m scripts.train_gliner --base-model urchade/gliner_multi_pii-v1
    python -m scripts.train_gliner --cpu  # force CPU training
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.domains import ALL_ENTITY_TYPES

SPLITS_DIR = ROOT / "data" / "splits"
MODELS_DIR = ROOT / "models"
DEFAULT_BASE = "urchade/gliner_multitask-large-v0.5"


def load_gliner_dataset(path: Path) -> list[dict]:
    """Load JSONL in GLiNER format: {tokenized_text, ner: [[start, end, label]]}."""
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
    use_cpu: bool,
    output_dir: Path,
) -> None:
    import torch
    from gliner import GLiNER
    from gliner.training import Trainer, TrainingArguments

    device = "cpu" if use_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}", flush=True)
    if device == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}", flush=True)
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB", flush=True)

    print(f"\nLoading base model: {base_model}", flush=True)
    model = GLiNER.from_pretrained(base_model)

    print("Loading training data...", flush=True)
    train_path = SPLITS_DIR / "gliner_train.jsonl"
    val_path = SPLITS_DIR / "gliner_val.jsonl"

    if not train_path.exists():
        print(f"ERROR: {train_path} not found. Run validate_data.py first.", file=sys.stderr)
        sys.exit(1)

    train_data = load_gliner_dataset(train_path)
    val_data = load_gliner_dataset(val_path) if val_path.exists() else []
    print(f"  Train: {len(train_data)}, Val: {len(val_data)}", flush=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()

    # Build collator using the class registered on the concrete model subclass.
    # prepare_labels=True ensures training labels are included in each batch.
    collator = model.data_collator_class(
        model.config,
        data_processor=model.data_processor,
        prepare_labels=True,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=lr,
        weight_decay=0.01,
        others_lr=lr,
        others_weight_decay=0.01,
        lr_scheduler_type="linear",
        warmup_ratio=0.1,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        dataloader_num_workers=0,
        save_steps=500,
        save_total_limit=3,
        logging_steps=50,
        bf16=use_bf16,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=collator,
        train_dataset=train_data,
        eval_dataset=val_data if val_data else None,
    )

    print(f"\nTraining for {epochs} epochs, lr={lr}, batch_size={batch_size}", flush=True)
    t0 = time.perf_counter()
    trainer.train()
    elapsed = time.perf_counter() - t0
    print(f"\nTraining complete in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)

    best_dir = output_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(best_dir))
    print(f"Model saved to: {best_dir}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune GLiNER entity extractor")
    parser.add_argument("--base-model", default=DEFAULT_BASE, help=f"Base model (default: {DEFAULT_BASE})")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs (default: 5)")
    parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate (default: 1e-5)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU training")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else MODELS_DIR / "gliner-darkmem"

    train(
        base_model=args.base_model,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        use_cpu=args.cpu,
        output_dir=output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
