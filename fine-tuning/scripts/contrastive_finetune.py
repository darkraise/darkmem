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
    p.add_argument("--base", type=str, required=True,
                   help="Local path or HF repo id for a Transformers encoder")
    p.add_argument("--train", type=Path, default=None,
                   help="JSONL with {query, positive} per line (local path)")
    p.add_argument("--triplets", type=Path, default=None,
                   help="Optional JSONL with {query, positive, negative} triplets (local path)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--warmup-steps", type=int, default=100)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--hf-token", default=None, help="HuggingFace token for private dataset repos.")
    from scripts._hf_dataset_loader import add_hf_args, resolve_dataset_path
    # The retriever dataset has `train_pairs.jsonl` + `train_triplets.jsonl`;
    # expose both as HF-pullable with their specific defaults.
    p.add_argument("--hf-dataset-repo", default=None,
                   help="HF dataset repo (e.g. darkraise/darkmem-retriever-dataset). "
                        "When set, pulls train_pairs.jsonl and (optionally) train_triplets.jsonl.")
    p.add_argument("--hf-pairs-file", default="train_pairs.jsonl",
                   help="Pairs filename inside the HF repo (default: train_pairs.jsonl).")
    p.add_argument("--hf-triplets-file", default="train_triplets.jsonl",
                   help="Triplets filename inside the HF repo (default: train_triplets.jsonl).")
    a = p.parse_args()

    # Resolve --train and --triplets from either local path or the HF repo.
    if a.hf_dataset_repo:
        a.train = resolve_dataset_path(
            local=a.train,
            repo=a.hf_dataset_repo,
            filename=a.hf_pairs_file,
            token=a.hf_token,
        )
        if a.hf_triplets_file:
            try:
                a.triplets = resolve_dataset_path(
                    local=a.triplets,
                    repo=a.hf_dataset_repo,
                    filename=a.hf_triplets_file,
                    token=a.hf_token,
                )
            except Exception as exc:
                print(f"warning: triplets file not found in repo, continuing pairs-only: {exc}")
                a.triplets = None
    elif not a.train:
        p.error("--train (local path) or --hf-dataset-repo is required.")

    # Wrap a raw HF encoder with SentenceTransformer: word-embedding + mean-pool
    word = st_models.Transformer(a.base, max_seq_length=a.max_length, model_args={"trust_remote_code": True})
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

    if a.triplets:
        n_tri = 0
        for line in a.triplets.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            pairs.append(InputExample(texts=[r["query"], r["positive"], r["negative"]]))
            n_tri += 1
        print(f"loaded {n_tri} hard-negative triplets")

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
