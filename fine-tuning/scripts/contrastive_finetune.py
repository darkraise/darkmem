"""Contrastive fine-tune a SentenceTransformer-compatible encoder on retrieval (query, positive) pairs.

Usage:
    python -m scripts.contrastive_finetune \
        --base models/classifier-v3aug2-nomic-modernbert/best \
        --train runs/retrieval-contrastive/train_pairs.jsonl \
        --out models/unified-nomic-modernbert-contrastive \
        --epochs 2 --batch-size 32 --lr 2e-5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer, InputExample, losses, models as st_models
from torch.utils.data import DataLoader


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, required=True,
                   help="Path to a Transformers encoder (local dir)")
    p.add_argument("--train", type=Path, required=True,
                   help="JSONL with {query, positive} per line")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--warmup-steps", type=int, default=100)
    p.add_argument("--max-length", type=int, default=256)
    a = p.parse_args()

    # Wrap a raw HF encoder with SentenceTransformer: word-embedding + mean-pool
    word = st_models.Transformer(str(a.base), max_seq_length=a.max_length, model_args={"trust_remote_code": True})
    pool = st_models.Pooling(word.get_word_embedding_dimension(), pooling_mode="mean")
    model = SentenceTransformer(modules=[word, pool])

    pairs = []
    for line in a.train.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        pairs.append(InputExample(texts=[r["query"], r["positive"]]))
    print(f"loaded {len(pairs)} training pairs")

    loader = DataLoader(pairs, shuffle=True, batch_size=a.batch_size)
    loss = losses.MultipleNegativesRankingLoss(model)

    a.out.mkdir(parents=True, exist_ok=True)
    model.fit(
        train_objectives=[(loader, loss)],
        epochs=a.epochs,
        warmup_steps=a.warmup_steps,
        optimizer_params={"lr": a.lr},
        output_path=str(a.out),
        show_progress_bar=True,
    )
    print(f"saved contrastive-fine-tuned model to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
