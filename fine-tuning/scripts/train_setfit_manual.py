"""Manual SetFit-style training: contrastive fine-tune sentence-transformer + logistic regression head.

Approach:
1. Generate positive pairs (same class) and negative pairs (different class) from training data
2. Fine-tune the sentence-transformer with contrastive loss (pairs with labels)
3. Encode all training texts with the fine-tuned model
4. Train a logistic regression classifier on the embeddings
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "classification" / "train.jsonl"
OUTPUT_DIR = ROOT / "models" / "classifier-setfit-manual"

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


def load_data(path: Path):
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


def generate_pairs(texts, labels, pairs_per_example, rng):
    from sentence_transformers import InputExample

    label_to_texts: dict[int, list[str]] = {}
    for t, l in zip(texts, labels):
        label_to_texts.setdefault(l, []).append(t)

    all_labels = list(label_to_texts.keys())
    pairs = []

    for t, l in zip(texts, labels):
        same_class = [x for x in label_to_texts[l] if x != t]
        if same_class:
            for _ in range(pairs_per_example):
                pos = rng.choice(same_class)
                pairs.append(InputExample(texts=[t, pos], label=1.0))
        other_labels = [ol for ol in all_labels if ol != l]
        for _ in range(pairs_per_example):
            neg_label = rng.choice(other_labels)
            neg = rng.choice(label_to_texts[neg_label])
            pairs.append(InputExample(texts=[t, neg], label=0.0))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--pairs-per-example", type=int, default=20)
    parser.add_argument("--val-split", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    set_seed(args.seed)
    rng = random.Random(args.seed)

    if not torch.cuda.is_available():
        print("ERROR: CUDA not available.", file=sys.stderr)
        return 1
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    texts, labels = load_data(DATA_PATH)
    print(f"Total: {len(texts)}")

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=args.val_split, stratify=labels, random_state=args.seed,
    )
    print(f"Train: {len(train_texts)}, Val: {len(val_texts)}")

    from sentence_transformers import SentenceTransformer, losses
    from torch.utils.data import DataLoader

    print(f"Loading base: {args.base}")
    model = SentenceTransformer(args.base, device="cuda")

    pairs = generate_pairs(train_texts, train_labels, args.pairs_per_example, rng)
    rng.shuffle(pairs)
    print(f"Pairs: {len(pairs)}")

    train_dl = DataLoader(pairs, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.CosineSimilarityLoss(model)

    t_start = time.perf_counter()
    model.fit(
        train_objectives=[(train_dl, train_loss)],
        epochs=args.epochs,
        warmup_steps=int(len(train_dl) * 0.1),
        show_progress_bar=False,
    )
    fit_elapsed = time.perf_counter() - t_start
    print(f"Contrastive training: {fit_elapsed:.1f}s")

    train_emb = model.encode(train_texts, convert_to_numpy=True, show_progress_bar=False, batch_size=64)
    val_emb = model.encode(val_texts, convert_to_numpy=True, show_progress_bar=False, batch_size=64)

    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(train_emb, train_labels)

    val_preds = clf.predict(val_emb)
    acc = accuracy_score(val_labels, val_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(val_labels, val_preds, average="macro", zero_division=0)
    total_elapsed = time.perf_counter() - t_start
    print(f"\nValidation:")
    print(f"  accuracy: {acc:.4f}")
    print(f"  macro_f1: {f1:.4f}")
    print(f"  total_time: {total_elapsed:.1f}s")

    best_dir = Path(args.output_dir) / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(best_dir / "encoder"))
    joblib.dump({"clf": clf, "labels": LABELS}, str(best_dir / "classifier.joblib"))
    print(f"Saved to {best_dir}")

    metadata = {
        "base_model": args.base,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "pairs_per_example": args.pairs_per_example,
        "train_size": len(train_texts),
        "val_size": len(val_texts),
        "labels": LABELS,
        "val_accuracy": float(acc),
        "val_macro_f1": float(f1),
    }
    (Path(args.output_dir) / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
