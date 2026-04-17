# Production model manifest

Last updated: 2026-04-17

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

### GLiNER — entity extractor (35 entity types)

| field | value |
|---|---|
| path | `fine-tuning/models/gliner-small-v2corpus/best` |
| base | `urchade/gliner_small-v2.1` |
| params | ~50 M |
| inference VRAM idle | 613 MB (torch allocated), 647 MB peak nvidia-smi |
| training data | `fine-tuning/data/splits/gliner_train.jsonl` (10,000 rows, tokenized from v2 shared) |
| eval set | `fine-tuning/data/splits/test.jsonl` (2,000 rows, canonical schema) |
| metric (head-level) | micro F1 0.465, type accuracy 0.685, mean IoU 1.00 |
| metric (pipeline, paired with rebel-large) | entity F1 0.727, type acc 0.756, 13 ms/row |
| latency | 12 ms/row at threshold 0.5 |
| recipe | `python -m scripts.train_gliner --base-model urchade/gliner_small-v2.1 --output-dir models/gliner-small-v2corpus --epochs 5 --batch-size 16 --lr 1e-5` |

### REBEL — relationship extractor (30 relation types)

| field | value |
|---|---|
| path | `fine-tuning/models/rebel-large-v2corpus/best` |
| base | `Babelscape/rebel-large` |
| params | ~407 M |
| inference VRAM idle | 1,625 MB (torch allocated), 1,720 MB peak nvidia-smi |
| training data | `fine-tuning/data/splits/rebel_train.jsonl` (8,052 rows, relations-only subset) |
| eval set | `fine-tuning/data/splits/rebel_test_gold.jsonl` (1,007 rows) |
| metric (head-level) | micro F1 0.435, direction rate 0.416, exact-match 0.344 |
| metric (pipeline, paired with gliner-small) | rel F1 0.349, direction rate 0.995, 200 ms/row |
| latency | 229 ms/row at num_beams=4, max_target=128 |
| recipe | `python -m scripts.train_rebel --base-model Babelscape/rebel-large --output-dir models/rebel-large-v2corpus --epochs 3 --batch-size 2 --lr 3e-5 --max-source-length 256 --max-target-length 128` |

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

- **qwen3.5:4b** (reasoning, served via Ollama) — used as-is, no fine-tune planned.

## Co-load budget (RTX 5060, 8.15 GB)

Measured 2026-04-17 via `scripts/_vram_coload_audit.py` on the actual production checkpoints. Ollama was offline during the audit; qwen3.5:4b row is an estimate based on PRODUCTION.md's 3 GB figure.

| component | VRAM (MB, nvidia-smi delta) | notes |
|---|---:|---|
| Classifier (ModernBERT-base) | 619 | measured |
| Retriever (bge-base) | 439 | measured |
| GLiNER-small-v2corpus | 613 | measured |
| REBEL-large-v2corpus | 1,625 | measured |
| qwen3.5:4b (Ollama) | ~3,000 | estimate, not loaded at audit time |
| CUDA / activations overhead | ~600 | nvidia-smi minus torch allocated |
| **Total** | **~6,900 MB** | headroom ~1.2 GB |

Picking GLiNER-large instead of GLiNER-small pushes the total to ~8.5 GB, which exceeds the 8.15 GB card. Picking bge-large instead of bge-base consumes the remaining headroom.
