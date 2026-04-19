# Production model manifest

Last updated: 2026-04-19

Five fine-tuned checkpoints for the darkmem extraction pipeline, one per head. All non-production experiments are archived under `_experiments/` for reference but are NOT shipped.

All checkpoints are gitignored (see `fine-tuning/.gitignore`). Reproduce by running the training recipe listed per model.

## Chosen models (shipping)

### 1. darkmem-classifier-v1 — memory type classification (7 classes)

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-classifier-v1/best` |
| base | `answerdotai/ModernBERT-base` |
| params | 150 M |
| inference VRAM idle | ~619 MB |
| training data | `fine-tuning/data/classification/train_v2_aug2.jsonl` (11,300 rows) |
| eval set | `docs/e2e/scripts/classification_eval/corpus/gold_v3.jsonl` (1,000 rows) |
| metric | accuracy 0.975, macro F1 0.975 |
| labels | fact, decision, preference, problem, reference, architecture, milestone |
| max_length | 256 |
| recipe | `python -m scripts.train_classifier --base answerdotai/ModernBERT-base --epochs 10 --batch-size 16 --lr 3e-5 --max-length 256 --bf16 --lr-scheduler-type cosine --label-smoothing 0.05 --trust-remote-code --data data/classification/train_v2_aug2.jsonl --output-dir models/darkmem-classifier-v1` |

### 2. darkmem-retriever-v1 — dense embedder for semantic search

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-retriever-v1` |
| base | `BAAI/bge-base-en-v1.5` |
| params | 109.5 M |
| inference VRAM idle | ~439 MB |
| training data | `fine-tuning/runs/retrieval-contrastive/train_pairs_7k_clean.jsonl` (7,500 pairs) + `train_triplets.jsonl` (400 hard-neg triplets) |
| eval set | `fine-tuning/runs/retrieval-contrastive/test_pairs.jsonl` (500 pairs, corpus 7,000) |
| metric | MRR@10 0.884, R@1 0.872, R@5 0.904, R@10 0.910 |
| max_length | 256 |
| query prefix | `"Represent this sentence for searching relevant passages: "` |
| passage prefix | none |
| recipe | `python -m scripts.contrastive_finetune --base BAAI/bge-base-en-v1.5 --train runs/retrieval-contrastive/train_pairs_7k_clean.jsonl --triplets runs/retrieval-contrastive/train_triplets.jsonl --out models/darkmem-retriever-v1 --epochs 5 --batch-size 64 --lr 2e-5 --max-length 256` |

### 3. darkmem-span-v1 — entity span detector (stage 1 of two-stage NER)

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-span-v1/best` |
| base | `urchade/gliner_small-v2.1` |
| params | ~50 M |
| inference VRAM idle | ~613 MB |
| training data | `fine-tuning/data/splits/span_train.jsonl` (6,319 rows, coding10 with every entity collapsed to single `entity` label) |
| eval set | `fine-tuning/data/splits/span_test.jsonl` + 90-example historical gold |
| metric (name recall) | 0.972 on 90-gold, 0.793 on 2k v2 remap, 0.800 on coding10_test |
| labels | single label: `entity` (span-only detector; types assigned by darkmem-typer-v1) |
| threshold | 0.5 recommended; see `_infer_entity_twostage.py` for the two-stage pipeline |
| recipe | `python -m scripts.train_gliner --base-model urchade/gliner_small-v2.1 --output-dir models/darkmem-span-v1 --epochs 5 --batch-size 16 --lr 1e-5` |

### 4. darkmem-typer-v1 — entity type classifier (stage 2 of two-stage NER)

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-typer-v1/best` |
| base | `answerdotai/ModernBERT-base` |
| params | 150 M |
| inference VRAM idle | ~618 MB |
| training data | `fine-tuning/data/splits/typer_train.jsonl` (21,949 rows: one row per gold entity with `[ENT]…[/ENT]` markers in context, 10-type label) |
| eval set | `fine-tuning/data/splits/typer_test.jsonl` (2,752 rows) |
| metric | eval accuracy 0.692, macro F1 0.678; on two-stage pipeline: type accuracy given name 0.83 on 90-gold, 0.77 on 2k v2 |
| labels | `tool, service, database, language, protocol, project, algorithm, artifact, concept, entity` (10-type coding taxonomy) |
| input format | text with `[ENT]span[/ENT]` markers around the entity; max_length 256 |
| recipe | `python -m scripts.train_typer --base answerdotai/ModernBERT-base --output-dir models/darkmem-typer-v1 --epochs 5 --batch-size 16 --lr 3e-5 --max-length 256 --fp16` |

### 5. darkmem-relation-base-v1 — relation extractor (seq2seq REBEL, base size)

**Shipping decision 2026-04-19:** promoted rebel-base (139 M) over rebel-large (407 M) for
the VRAM-constrained 12 GB RTX 2060 LXC. F1 drops 0.660 → 0.618 on 5-type rescored
(Δ −0.042) in exchange for ~1 GB less VRAM and ~14% faster inference. Pair-wise accuracy
on 5-type stays at 0.934 (NONE dominates). See
`fine-tuning/runs/2026-04-19-schema-v2/progress.md` for the full trade-off record and
why `darkmem-relation-v2` failed the promotion gate.

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-relation-base-v1/best` |
| base | `Babelscape/rebel-base` (139 M; the large variant 407 M is archived as darkmem-relation-v1) |
| params | ~139 M |
| inference VRAM idle (measured) | ~606 MB peak during inference |
| latency (measured, beams=4, max_src=512) | mean 426 ms/row, p50 357 ms, p95 831 ms |
| training data | `fine-tuning/data/splits/rebel_train.jsonl` (8,052 rows, 30-type taxonomy) |
| epochs | 6 (3-epoch variant was 0.496 F1; 6 epochs was the plateau) |
| eval set (10-type) | `rebel_coding10_test_gold.jsonl` (567 rows) — pair-wise F1 0.602 |
| eval set (5-type rescored, schema-v2) | `rebel_coding5_test_gold.jsonl` (495 rows) — pair-wise F1 0.618, P 0.718, R 0.542 |
| per-class 5-type F1 | USES 0.51, REPLACES 0.78, DEPLOYED_ON 0.45, CAUSES 0.32, IS_A 0.0 |
| output labels | 30 relation types native; collapsed 30→10 via `REL_MAP`, then 10→5 via `REL_MAP_5` in `backend/app/services/extraction.clean_extraction` |
| inference | seq2seq `<triplet> source <subj> target <obj> type` format; decode with `num_beams=4, max_target=128` |
| recipe | `python -m scripts.train_rebel --base-model Babelscape/rebel-base --output-dir models/darkmem-relation-base-v1 --epochs 6 --batch-size 2 --lr 3e-5 --max-source-length 512 --max-target-length 128` |

### 5b. darkmem-relation-v1 — large variant (archived, not shipping)

Retained on disk as a Pareto reference and for emergency fallback. Kept out of
`PRODUCTION.md` shipping list so operators do not accidentally wire it; use `.env`
override (`ML_PIPELINE_HUB_RELATION_REPO=...` or a local-path tweak) if you need the
higher-F1 option on a fatter GPU.

| field | value |
|---|---|
| path | `fine-tuning/models/darkmem-relation-v1/best` |
| base | `Babelscape/rebel-large` |
| params | ~407 M |
| inference VRAM idle | ~1,625 MB |
| metric (10-type) | F1 0.638 |
| metric (5-type rescored) | F1 0.660, P 0.688, R 0.634 |

## Consolidated 10-type taxonomy (for entity typer and relation post-hoc map)

**Entity types (10)**: `tool, service, database, language, protocol, project, algorithm, artifact, concept, entity`. See `fine-tuning/scripts/_build_coding10_splits.py` for the 35→10 mapping used for every downstream head that consumes entity types.

**Relation types (10)**: `USES, DEPENDS_ON, REPLACES, IS_A, HAS_PART, DEPLOYED_ON, CAUSES, AUTHORED_BY, HAPPENED_ON, RELATED_TO`. See `fine-tuning/scripts/_build_rebel_coding10_splits.py` for the 30→10 map (`REL_MAP` dict).

## Co-load budget (RTX 5060, 8.15 GB) — measured 2026-04-17

| component | VRAM (MB) | notes |
|---|---:|---|
| darkmem-classifier-v1 | 619 | measured |
| darkmem-retriever-v1 | 439 | measured |
| **darkmem-span-v1 + darkmem-typer-v1** (two-stage) | **1,231** | 613 + 618, measured as a pair |
| darkmem-relation-base-v1 | 606 | measured (swapped from 1,625 MB rebel-large on 2026-04-19) |
| qwen3.5:4b (Ollama, reasoning) | ~3,000 | estimate; add to this table after first production warm-load |
| CUDA / activations overhead | ~600 | nvidia-smi minus torch allocated |
| **Total** | **~6,495** | **~1,656 MB headroom** on the 8,151 MB card (was 640 MB under rebel-large) |

## Final pipeline metrics summary

| task | test | score |
|---|---|---:|
| memory-type classification | `classification_eval/corpus/gold_v3.jsonl`, 7 classes | 0.975 accuracy |
| retrieval | `retrieval-contrastive/test_pairs.jsonl`, MRR@10 | 0.884 |
| entity extraction (pair F1, strict, 90-gold) | coding memories | 0.733 |
| entity extraction (lenient F1, 90-gold) | coding memories | 0.940 |
| entity extraction (pair F1, 2k v2 remapped) | broader mix | 0.603 |
| relation extraction (F1, coding10 10-type) | via darkmem-relation-base-v1 + `REL_MAP` | **0.602** |
| relation extraction (F1, 5-type rescored) | via darkmem-relation-base-v1 + `REL_MAP_5` | **0.618** |
| relation extraction (F1, 5-type, archived rebel-large reference) | darkmem-relation-v1 + `REL_MAP_5` | 0.660 |
