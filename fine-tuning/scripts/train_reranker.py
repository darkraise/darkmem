"""Fine-tune a cross-encoder reranker on darkmem (query, passage) data.

Uses in-batch negatives (sampled randomly from other pairs) as hard negatives.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT.parent / "docs" / "e2e" / "scripts" / "retrieval_eval" / "train_pairs.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--negatives-per-query", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    pairs = []
    with TRAIN_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                pairs.append(json.loads(line))
    print(f"Loaded {len(pairs)} training pairs")

    # Build training examples: positive (label=1) + sampled negatives (label=0)
    from sentence_transformers import InputExample
    from sentence_transformers.cross_encoder import CrossEncoder

    all_passages = [p["positive"] for p in pairs]
    examples = []
    for i, p in enumerate(pairs):
        # Positive pair
        examples.append(InputExample(texts=[p["query"], p["positive"]], label=1.0))
        # Sampled negatives (other pairs' passages, avoid same index)
        neg_indices = rng.sample([j for j in range(len(pairs)) if j != i],
                                 min(args.negatives_per_query, len(pairs) - 1))
        for j in neg_indices:
            examples.append(InputExample(texts=[p["query"], all_passages[j]], label=0.0))

    rng.shuffle(examples)
    print(f"Built {len(examples)} training examples (pos+neg)")

    model = CrossEncoder(args.base, num_labels=1, device="cuda")
    loader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    warmup_steps = int(len(loader) * args.epochs * 0.1)

    t0 = time.perf_counter()
    model.fit(
        train_dataloader=loader,
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        optimizer_params={"lr": args.lr},
        show_progress_bar=False,
    )
    elapsed = time.perf_counter() - t0
    print(f"Training finished in {elapsed:.1f}s")

    out = Path(args.output_dir) / "best"
    out.mkdir(parents=True, exist_ok=True)
    model.save(str(out))
    print(f"Saved to {out}")

    (Path(args.output_dir) / "run_metadata.json").write_text(json.dumps({
        "base_model": args.base,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "n_examples": len(examples),
        "negatives_per_query": args.negatives_per_query,
        "train_seconds": elapsed,
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
