"""Parse a trainer log and write models/<model>/run_metadata.json.

Usage:
  python -m scripts._write_run_metadata \
      --model-dir models/gliner-small-v2corpus \
      --log runs/gliner-small-v2corpus/train.log \
      --base-model urchade/gliner_small-v2.1 \
      --kind gliner \
      --train-size 10000 --val-size 2000 \
      --epochs 5 --lr 1e-5 --batch-size 16
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LOSS_PAT = re.compile(r"'loss'\s*:\s*'?([0-9eE.+-]+)'?")
EVAL_LOSS_PAT = re.compile(r"'eval_loss'\s*:\s*'?([0-9eE.+-]+)'?")
EPOCH_PAT = re.compile(r"'epoch'\s*:\s*'?([0-9eE.+-]+)'?")
TRAIN_LOSS_PAT = re.compile(r"'train_loss'\s*:\s*'?([0-9eE.+-]+)'?")
ELAPSED_PAT = re.compile(r"Training complete in ([0-9]+)s\s*\(([0-9.]+)m\)")


def parse_log(log_path: Path) -> dict:
    losses: list[float] = []
    eval_losses: list[float] = []
    epochs: list[float] = []
    elapsed_s: float | None = None
    elapsed_m: float | None = None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for m in LOSS_PAT.finditer(text):
        try:
            losses.append(float(m.group(1)))
        except ValueError:
            pass
    for m in EVAL_LOSS_PAT.finditer(text):
        try:
            eval_losses.append(float(m.group(1)))
        except ValueError:
            pass
    for m in EPOCH_PAT.finditer(text):
        try:
            epochs.append(float(m.group(1)))
        except ValueError:
            pass
    m = ELAPSED_PAT.search(text)
    if m:
        elapsed_s = float(m.group(1))
        elapsed_m = float(m.group(2))
    train_losses = [float(m.group(1)) for m in TRAIN_LOSS_PAT.finditer(text)]
    return {
        "last_batch_loss": losses[-1] if losses else None,
        "final_train_loss_aggregate": train_losses[-1] if train_losses else None,
        "final_eval_loss": eval_losses[-1] if eval_losses else None,
        "loss_samples": len(losses),
        "eval_loss_samples": len(eval_losses),
        "final_epoch": epochs[-1] if epochs else None,
        "elapsed_seconds": elapsed_s,
        "elapsed_minutes": elapsed_m,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--base-model", required=True)
    p.add_argument("--kind", required=True, choices=["gliner", "rebel"])
    p.add_argument("--train-size", type=int, required=True)
    p.add_argument("--val-size", type=int, required=True)
    p.add_argument("--epochs", type=int, required=True)
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--batch-size", type=int, required=True)
    args = p.parse_args()

    parsed = parse_log(args.log)
    meta = {
        "base_model": args.base_model,
        "kind": args.kind,
        "epochs_requested": args.epochs,
        "train_size": args.train_size,
        "val_size": args.val_size,
        "training_args": {
            "lr": args.lr,
            "batch_size": args.batch_size,
        },
        "parsed": parsed,
    }
    args.model_dir.mkdir(parents=True, exist_ok=True)
    out = args.model_dir / "run_metadata.json"
    out.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
