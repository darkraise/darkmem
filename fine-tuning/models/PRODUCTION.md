# Production model manifest

Last updated: 2026-04-16

Production fine-tuned checkpoints for the darkmem pipeline. Everything else in this directory that is not listed below was an experimental run and was archived/removed on 2026-04-16; see `project_retrieval_clean_7500_bge.md` and `project_classification_eval.md` in the auto-memory for the decision history.

All checkpoints are gitignored (see `fine-tuning/.gitignore`). Reproduce by running the training recipe listed per model.

## Chosen models

### Classifier — memory type (7 classes)

| field | value |
|---|---|
| path | `fine-tuning/models/classifier-v3aug2-modernbert-base/best` |
| base | `answerdotai/ModernBERT-base` |
| params | 150 M |
| on-disk | 575 MB |
| inference VRAM | ~300 MB |
| training data | `fine-tuning/data/classification/train_v2_aug2.jsonl` (11,300 rows) |
| eval set | `docs/e2e/scripts/classification_eval/corpus/gold_v3.jsonl` (1000 rows) |
| metric | accuracy 0.975, macro F1 0.975 |
| labels | fact, decision, preference, problem, reference, architecture, milestone |
| max_length | 256 |
| recipe | `python -m scripts.train_classifier --base answerdotai/ModernBERT-base --epochs 10 --batch-size 16 --lr 3e-5 --max-length 256 --bf16 --lr-scheduler-type cosine --label-smoothing 0.05 --trust-remote-code --data data/classification/train_v2_aug2.jsonl --output-dir models/classifier-v3aug2-modernbert-base` |

### Retriever — dense embedder for semantic search

| field | value |
|---|---|
| path | `fine-tuning/models/retriever-bge-base-7500clean-hn-ep5-b64` |
| base | `BAAI/bge-base-en-v1.5` |
| params | 109.5 M |
| on-disk | 419 MB |
| inference VRAM idle | 440 MB |
| inference VRAM peak (batch 64 encode) | 448 MB |
| training data | `fine-tuning/runs/retrieval-contrastive/train_pairs_7k_clean.jsonl` (7500 pairs) + `train_triplets.jsonl` (400 hard-neg triplets) |
| eval set | `fine-tuning/runs/retrieval-contrastive/test_pairs.jsonl` (500 pairs, corpus 7000) |
| metric | MRR@10 0.884, R@1 0.872, R@5 0.904, R@10 0.910 |
| max_length | 256 |
| query prefix | `"Represent this sentence for searching relevant passages: "` |
| passage prefix | none |
| recipe | `python -m scripts.contrastive_finetune --base BAAI/bge-base-en-v1.5 --train runs/retrieval-contrastive/train_pairs_7k_clean.jsonl --triplets runs/retrieval-contrastive/train_triplets.jsonl --out models/retriever-bge-base-7500clean-hn-ep5-b64 --epochs 5 --batch-size 64 --lr 2e-5 --max-length 256` |

## Reference checkpoints (kept for comparison, not production)

### bge-large ceiling

- path: `fine-tuning/models/retriever-bge-large-7500clean-hn-ep5-b16`
- base: `BAAI/bge-large-en-v1.5` (335 M params)
- MRR@10 0.895 (+1.1 over bge-base), 1342 MB inference VRAM
- Kept to document the achievable upper bound if co-loaded models are dropped or an additional GPU is added. Not shipped: the VRAM tradeoff does not leave room for GLiNER + REBEL + qwen3.5:4b on the RTX 5060.

### nomic baseline

- path: `fine-tuning/models/retriever-nomic-fresh-hn-ep5-b64`
- base: `nomic-ai/modernbert-embed-base`
- MRR@10 0.862 on the same test set
- Kept so future experiments can regenerate the "before-cleanup" baseline for regression checks.

### bge-base cross-encoder reranker

- path: `fine-tuning/models/reranker-bge-base`
- base: `BAAI/bge-reranker-base`
- Not yet wired to the retriever; kept for a future +3-5 MRR reranking experiment at ~10× latency.

## Not yet fine-tuned (gaps in the 4-head pipeline)

- **GLiNER** (entity extraction, target ~400 MB VRAM). Data: `fine-tuning/data/gliner/*.jsonl` (check presence before training).
- **REBEL** (relationship extraction, target ~800 MB VRAM). Data: `fine-tuning/data/rebel/*.jsonl`.
- **qwen3.5:4b** (reasoning, served via Ollama) — used as-is, no fine-tune planned.

## Co-load budget (RTX 5060, 8.15 GB)

| component | VRAM | notes |
|---|---:|---|
| Classifier (ModernBERT-base) | 300 MB | |
| Retriever (bge-base) | 440 MB | |
| GLiNER (fine-tuned target) | 400 MB | not yet trained |
| REBEL (fine-tuned target) | 800 MB | not yet trained |
| qwen3.5:4b (Ollama) | 3000 MB | reasoning |
| CUDA / activations overhead | ~800 MB | |
| **Total** | **~5740 MB** | headroom ~2.4 GB |

Swapping bge-base → bge-large consumes the headroom entirely and leaves no room for growth, which is why bge-base was chosen for shipping.
