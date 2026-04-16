"""Per-slice retrieval breakdown: MRR and recall@k by query_kind and memory_type.

Usage:
    python -m scripts.eval_retrieval_breakdown \
        --model models/retriever-nomic-fresh-hn-ep5-b64 \
        --test runs/retrieval-contrastive/test_pairs.jsonl \
        --corpus data/v2/shared/shared.jsonl \
        --prefix search_query \
        --out runs/retrieval-contrastive/breakdown-nomic-fresh.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def apply_prefix(texts: list[str], prefix: str | None, role: str) -> list[str]:
    if not prefix:
        return texts
    if prefix == "nomic":
        tag = "search_query: " if role == "query" else "search_document: "
    elif prefix == "bge":
        tag = "Represent this sentence for searching relevant passages: " if role == "query" else ""
    else:
        tag = ""
    return [tag + t for t in texts]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=str, required=True)
    p.add_argument("--test", type=Path, required=True)
    p.add_argument("--corpus", type=Path, required=True,
                   help="shared.jsonl with id+memory_type+text")
    p.add_argument("--prefix", choices=["none", "nomic", "bge"], default="none")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--batch-size", type=int, default=64)
    a = p.parse_args()

    from sentence_transformers import SentenceTransformer

    corpus = load_jsonl(a.corpus)
    id_to_type = {r["id"]: r["memory_type"] for r in corpus}
    id_to_text = {r["id"]: r["text"] for r in corpus}
    corpus_ids = [r["id"] for r in corpus]
    corpus_texts = [r["text"] for r in corpus]
    print(f"corpus: {len(corpus_texts)} rows")

    pairs = load_jsonl(a.test)
    # keep only pairs whose source_id is in the corpus (should be all)
    valid = [p for p in pairs if p["source_id"] in id_to_text]
    print(f"test pairs: {len(valid)}/{len(pairs)} resolvable")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    prefix = None if a.prefix == "none" else a.prefix
    model = SentenceTransformer(a.model, device=device, trust_remote_code=True)

    pref = "nomic" if a.prefix == "nomic" else "bge" if a.prefix == "bge" else None
    q_texts = apply_prefix([p["query"] for p in valid], pref, "query")
    p_texts = apply_prefix(corpus_texts, pref, "passage")

    q_emb = model.encode(q_texts, batch_size=a.batch_size, convert_to_numpy=True,
                         normalize_embeddings=True, show_progress_bar=True)
    p_emb = model.encode(p_texts, batch_size=a.batch_size, convert_to_numpy=True,
                         normalize_embeddings=True, show_progress_bar=True)

    id_to_idx = {cid: i for i, cid in enumerate(corpus_ids)}
    gold_idx = np.array([id_to_idx[p["source_id"]] for p in valid])

    sims = q_emb @ p_emb.T
    # rank of gold: number of items with higher sim + 1
    ranks = []
    for i, gi in enumerate(gold_idx):
        rank = int((sims[i] > sims[i, gi]).sum()) + 1
        ranks.append(rank)
    ranks = np.array(ranks)

    def slice_metrics(ranks_sub: np.ndarray) -> dict:
        if len(ranks_sub) == 0:
            return {"n": 0}
        return {
            "n": int(len(ranks_sub)),
            "mrr_at_10": float(np.where(ranks_sub <= 10, 1.0 / ranks_sub, 0.0).mean()),
            "recall_at_1": float((ranks_sub == 1).mean()),
            "recall_at_5": float((ranks_sub <= 5).mean()),
            "recall_at_10": float((ranks_sub <= 10).mean()),
            "median_rank": float(np.median(ranks_sub)),
            "mean_rank": float(ranks_sub.mean()),
        }

    overall = slice_metrics(ranks)

    # By query_kind
    by_kind = defaultdict(list)
    for i, p in enumerate(valid):
        by_kind[p.get("query_kind", "unknown")].append(ranks[i])

    by_kind_metrics = {k: slice_metrics(np.array(v)) for k, v in sorted(by_kind.items())}

    # By memory_type
    by_type = defaultdict(list)
    for i, p in enumerate(valid):
        mt = id_to_type.get(p["source_id"], "unknown")
        by_type[mt].append(ranks[i])

    by_type_metrics = {k: slice_metrics(np.array(v)) for k, v in sorted(by_type.items())}

    # Crosstab kind x type (MRR only for brevity)
    cross = defaultdict(list)
    for i, p in enumerate(valid):
        kind = p.get("query_kind", "unknown")
        mt = id_to_type.get(p["source_id"], "unknown")
        cross[(kind, mt)].append(ranks[i])
    cross_metrics = {f"{k}|{m}": slice_metrics(np.array(v)) for (k, m), v in sorted(cross.items())}

    report = {
        "model": a.model,
        "prefix": a.prefix,
        "overall": overall,
        "by_query_kind": by_kind_metrics,
        "by_memory_type": by_type_metrics,
        "by_kind_x_type": cross_metrics,
    }

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print(f"=== {a.model} (prefix={a.prefix}) ===")
    print(f"overall: MRR={overall['mrr_at_10']:.4f}  R@1={overall['recall_at_1']:.3f}  R@5={overall['recall_at_5']:.3f}  R@10={overall['recall_at_10']:.3f}  n={overall['n']}")
    print()
    print(f"{'query_kind':<16} {'n':>4} {'MRR':>7} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'medR':>5}")
    for k, v in by_kind_metrics.items():
        print(f"{k:<16} {v['n']:>4} {v['mrr_at_10']:>7.4f} {v['recall_at_1']:>6.3f} {v['recall_at_5']:>6.3f} {v['recall_at_10']:>6.3f} {v['median_rank']:>5.0f}")
    print()
    print(f"{'memory_type':<16} {'n':>4} {'MRR':>7} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'medR':>5}")
    for k, v in by_type_metrics.items():
        print(f"{k:<16} {v['n']:>4} {v['mrr_at_10']:>7.4f} {v['recall_at_1']:>6.3f} {v['recall_at_5']:>6.3f} {v['recall_at_10']:>6.3f} {v['median_rank']:>5.0f}")
    print()
    print(f"saved breakdown -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
