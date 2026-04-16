"""Fine-tune an embedding model on darkmem (query, passage) pairs via contrastive loss."""
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
TRAIN_PATH = ROOT.parent / "docs" / "e2e" / "scripts" / "retrieval_eval" / "train_pairs_5k.jsonl"


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def apply_prefixes(pairs: list[dict], family: str) -> list[dict]:
    """Apply the correct query/passage prefix based on the model family."""
    out = []
    for p in pairs:
        q, a = p["query"], p["positive"]
        if family == "e5":
            q, a = f"query: {q}", f"passage: {a}"
        elif family == "bge":
            q = f"Represent this sentence for searching relevant passages: {q}"
            # bge doesn't use a passage prefix
        elif family == "embeddinggemma":
            q = f"task: search result | query: {q}"
            a = f"title: none | text: {a}"
        out.append({"query": q, "positive": a})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base model name")
    parser.add_argument("--family", required=True, choices=["e5", "bge", "embeddinggemma", "plain"])
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--hf-token", default=None)
    parser.add_argument("--trust-remote-code", action="store_true")
    args = parser.parse_args()

    set_seed(args.seed)
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available", file=sys.stderr)
        return 1
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Load pairs
    pairs = []
    with TRAIN_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                pairs.append(json.loads(line))
    print(f"Loaded {len(pairs)} training pairs")

    pairs = apply_prefixes(pairs, args.family)

    from sentence_transformers import SentenceTransformer, InputExample, losses

    kwargs = {"device": "cuda"}
    if args.hf_token:
        kwargs["token"] = args.hf_token
    if args.trust_remote_code:
        kwargs["trust_remote_code"] = True
    model = SentenceTransformer(args.base, **kwargs)

    examples = [InputExample(texts=[p["query"], p["positive"]]) for p in pairs]
    loader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    loss = losses.MultipleNegativesRankingLoss(model)

    warmup_steps = int(len(loader) * args.epochs * args.warmup_ratio)
    print(f"Training {args.epochs} epochs, {len(loader)} steps/epoch, warmup {warmup_steps}")

    t0 = time.perf_counter()
    model.fit(
        train_objectives=[(loader, loss)],
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
        "family": args.family,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "n_pairs": len(pairs),
        "train_seconds": elapsed,
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
