# Plan — GLiNER + REBEL training on expanded corpus

**Created**: 2026-04-16
**Branch**: `feat/architecture-overhaul`
**Execution model**: long-running, single continuous session. Do not stop for user input until the Final Report is written. All proceed/fail decisions are encoded in Acceptance criteria below.

## Goal

Train and benchmark the two remaining fine-tuned heads in the darkmem 4-head architecture (entity extraction via GLiNER, relationship extraction via REBEL). Produce head-level and end-to-end metrics, choose production GLiNER size, and write a comprehensive final report.

Cross-encoder reranker is **explicitly out of scope** (user rejected on latency + VRAM grounds).

## Context

Current production picks (from `fine-tuning/models/PRODUCTION.md`, commit 88219e0):
- Classifier: `classifier-v3aug2-modernbert-base/best` — acc 0.975 on gold_v3 (1000 rows)
- Retriever: `retriever-bge-base-7500clean-hn-ep5-b64` — MRR 0.884 on test_pairs (500 rows, corpus 7000)

Missing heads, data already exists at `fine-tuning/data/splits/`:
- GLiNER: 6400 train / 800 val / 800 test (derived from 7000-row `data/v2/shared/shared.jsonl`)
- REBEL: 6137 train / 767 val / 766 test (same source, filtered to rows with relationships)

Target sizes per user directive:
- **Train: at least 10,000 rows**
- **Val: at least 2,000 rows**
- **Test: at least 2,000 rows**

This requires expanding `shared.jsonl` from 7,000 → at least 14,000 rows. Each new shared row must carry entities (char-offset spans with type labels) and relationships (source, target, type triplets) annotated in the same schema as existing rows.

## Phase 0 — Preflight

1. Verify git status is clean on `feat/architecture-overhaul` (no uncommitted non-plan changes).
2. Verify `fine-tuning/data/v2/shared/shared.jsonl` has exactly 7000 rows.
3. Verify `fine-tuning/models/PRODUCTION.md` exists and lists classifier + retriever.
4. Verify VRAM baseline: `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` — should show < 2000 MB used on the RTX 5060 before starting. If higher, `docker restart ollama` to free it, then continue.
5. Verify disk free on D: is at least 50 GB.

If any check fails, document the failure at the top of the Final Report and continue if it is non-blocking (e.g., uncommitted diff on unrelated files is fine). If VRAM cannot be freed or disk is full, stop and write a partial Final Report.

## Phase 1 — Corpus expansion (shared rows 7001–14000)

### Goal
Add 7,000 new rows to `shared.jsonl`, each with `{id, domain, text, memory_type, noise, entities, relationships, queries}` fields matching the existing schema.

### Approach
Use the same parallel subagent fan-out pattern as batches 001–141 (emitter scripts with hand-curated 50-row lists), but larger batches (100 rows per emitter) to reduce agent count.

### Batch plan
70 new batches numbered 142–211, each emitting 100 rows:
- Batch 142–211 → rows shared-07001 … shared-14000

Dispatch in rounds of **15 parallel subagents**, so ~5 rounds to cover all 70 batches.

### Per-agent brief template
Each subagent receives:
- Batch number N (142 ≤ N ≤ 211)
- ID range: `shared-{(N-1)*100 + 1:05d}` .. `shared-{N*100:05d}`
- Output path: `data/v2/shared/batch_{N:03d}.tmp.jsonl`
- Reference: an existing clean emitter like `_emit_shared_batch_140.py` for schema and style
- Diversity mandate: rotate across the 7 memory types (fact, decision, preference, problem, reference, architecture, milestone) roughly balanced per batch; cover technical, personal, science, history, culture domains
- Annotation mandate: every row must carry at least 1 entity with correct char offsets; every non-noise row must carry at least 1 relationship; use the same entity types seen in `shared-00001..07000` (check `config/entity_pools.py`)

### Aggregation
After all rounds complete:
1. Run `python -m scripts.aggregate_shared_batches --source data/v2/shared --target data/v2/shared/shared.jsonl --from 142 --to 211` (extend aggregate script if the range arg is missing; alternatively concat manually using the Python 3.14 difflib workaround from `memory/debug_aggregator_difflib_python314.md`: append without SequenceMatcher and rely on id-exact-text collision detection).
2. Verify final shared.jsonl line count is 14,000.
3. Run `python -m scripts.validate_v2 --input data/v2/shared/shared.jsonl` — fix any schema errors flagged.

### Acceptance
- `shared.jsonl` has at least 14,000 rows (14,000 plus or minus 50 tolerance for per-batch undershoot).
- `validate_v2` passes.
- Each memory_type has at least 1,800 rows (stratification sanity, roughly even).
- New batches committed as `data(fine-tune): shared batches 142-211 (+7000 rows)`.

If aggregation produces fewer than 13,500 rows, fire additional rounds until it reaches 14,000. If the validator fails on more than 100 rows, drop the failing rows to `data/v2/failed/` and proceed (document the drop count in the report).

## Phase 2 — GLiNER and REBEL data conversion + splits

### Commands (deterministic seed 42)
```
python -m scripts.convert_to_gliner \
  --input data/v2/shared/shared.jsonl \
  --out data/v2/extraction/gliner.jsonl

python -m scripts.convert_to_rebel \
  --input data/v2/shared/shared.jsonl \
  --out data/v2/extraction/rebel.jsonl

python -m scripts.build_splits --shared data/v2/shared/shared.jsonl --seed 42 --out data/v2/splits
```

Then re-stratify splits to hit the exact targets. If `build_splits.py` does not support 10k/2k/2k ratios directly, write a one-off `_restratify_splits.py` that:
1. Loads `data/v2/splits/gliner_{train,val,test}.jsonl` combined.
2. Stratifies by `memory_type` (read from the matching shared row).
3. Writes 10000 train / 2000 val / 2000 test with seed 42.
4. Same for REBEL (may end up smaller after filtering rows without relationships — accept 8000+/1800+/1800+ if not quite 10k/2k/2k).

### Acceptance
- `data/splits/gliner_train.jsonl` has 10,000 rows; val and test each have 2,000.
- `data/splits/rebel_train.jsonl` has at least 8,000 rows; val and test each at least 1,800.
- Commit as `data(fine-tune): re-split GLiNER/REBEL to 10k/2k/2k`.

## Phase 3 — Training

All training runs sequential on the RTX 5060. Do not start the next training until the prior completes and the model directory has `model.safetensors` (or HF shards) written.

### 3a. GLiNER-small
Command:
```
python -m scripts.train_gliner \
  --base-model urchade/gliner_small-v2.1 \
  --train data/splits/gliner_train.jsonl \
  --val data/splits/gliner_val.jsonl \
  --output-dir models/gliner-small-v2corpus \
  --epochs 5 --batch-size 16 --lr 1e-5 \
  > runs/gliner-small-v2corpus/train.log 2>&1
```
Expected wall-clock: 1–2 hours. Expected inference VRAM: no more than 250 MB.

### 3b. GLiNER-large
```
python -m scripts.train_gliner \
  --base-model urchade/gliner_large-v2.1 \
  --train data/splits/gliner_train.jsonl \
  --val data/splits/gliner_val.jsonl \
  --output-dir models/gliner-large-v2corpus \
  --epochs 5 --batch-size 8 --lr 1e-5 \
  > runs/gliner-large-v2corpus/train.log 2>&1
```
Expected wall-clock: 3–5 hours. Expected inference VRAM: no more than 900 MB.
If CUDA OOM at batch 8, drop to 4 and add `--gradient-accumulation-steps 2`.

### 3c. REBEL-large
```
python -m scripts.train_rebel \
  --base-model Babelscape/rebel-large \
  --train data/splits/rebel_train.jsonl \
  --val data/splits/rebel_val.jsonl \
  --output-dir models/rebel-large-v2corpus \
  --epochs 3 --batch-size 4 --lr 3e-5 --max-source-length 256 --max-target-length 128 \
  > runs/rebel-large-v2corpus/train.log 2>&1
```
Expected wall-clock: 4–6 hours. Training VRAM around 6 GB.
If CUDA OOM, drop batch to 2 with `--gradient-accumulation-steps 4` and enable `--bf16 --gradient-checkpointing` (add flags to train_rebel.py if missing; follow the pattern in `train_classifier.py`).

### Failure handling
If any training run crashes with a recoverable error (OOM, dataloader hiccup), reduce batch and retry once. If it fails twice, skip that model, note the failure in the Final Report, and proceed to the next.

### Acceptance per model
- Checkpoint directory contains a loadable model (test via `AutoModel.from_pretrained` or `GLiNER.from_pretrained`).
- Train log shows the final epoch completed without NaN.
- Commit each as `feat(fine-tune): train <model-name> on expanded v2 corpus`.

## Phase 4 — Head-level benchmarking

### 4a. GLiNER scoring
Run `scripts.eval_entity` on both GLiNER checkpoints against `data/splits/gliner_test.jsonl`. Capture per-entity-type precision, recall, F1; overall micro and macro F1; inference latency (ms/row) and peak VRAM.

```
python -m scripts.eval_entity \
  --model models/gliner-small-v2corpus \
  --test data/splits/gliner_test.jsonl \
  --out runs/gliner-small-v2corpus/metrics.json

python -m scripts.eval_entity \
  --model models/gliner-large-v2corpus \
  --test data/splits/gliner_test.jsonl \
  --out runs/gliner-large-v2corpus/metrics.json
```

If `eval_entity` does not already emit per-type breakdowns, extend it (pattern: `fine-tuning/scripts/eval_retrieval_breakdown.py`).

### 4b. REBEL scoring
```
python -m scripts.eval_relation \
  --model models/rebel-large-v2corpus \
  --test data/splits/rebel_test.jsonl \
  --out runs/rebel-large-v2corpus/metrics.json
```

Capture triple F1 (exact match on source, target, type), per-relation-type F1, ms/row, VRAM.

### Acceptance
- Each metrics JSON written with at least: overall F1, per-type F1, N, ms/row, VRAM MB.
- Commit as `bench(fine-tune): head-level entity + relation metrics on 2k test split`.

## Phase 5 — End-to-end pipeline benchmark

Wire all 4 heads together and run against the existing extraction gold corpus at `docs/e2e/scripts/extraction_eval/`. Use the evaluation harness already there (`evaluate.py` in the fine-tuning repo orchestrates GLiNER + REBEL on a gold set).

### Commands
Two end-to-end runs — once with GLiNER-small, once with GLiNER-large — holding REBEL-large, classifier, retriever fixed.

```
python -m scripts.evaluate \
  --gliner-model models/gliner-small-v2corpus \
  --rebel-model models/rebel-large-v2corpus \
  --out runs/e2e-small/metrics.json

python -m scripts.evaluate \
  --gliner-model models/gliner-large-v2corpus \
  --rebel-model models/rebel-large-v2corpus \
  --out runs/e2e-large/metrics.json
```

Capture: overall extraction F1, per-entity F1, per-relation F1, end-to-end latency per document (single stream), total VRAM with all 4 heads plus qwen3.5:4b co-loaded (verify via `nvidia-smi` during the run).

### Acceptance
- Two end-to-end metric JSONs written.
- VRAM measurements documented.
- Commit as `bench(fine-tune): end-to-end pipeline with expanded corpus`.

## Phase 6 — Final report

Location: `docs/e2e/runs/2026-04-16-gliner-rebel-final.md`.

### Required sections
1. **Summary** — one paragraph stating the production picks and headline metrics.
2. **Corpus expansion** — new row count, memory-type distribution before/after, any dropped rows.
3. **Split sizes** — final train/val/test counts for GLiNER and REBEL.
4. **Head-level metrics table** — columns: model, base, params, train time, val F1, test F1, macro F1 per type, ms/row, VRAM MB.
5. **End-to-end metrics table** — two rows (small and large GLiNER paired with rebel-large), columns: entity F1, relation F1, combined F1, docs/sec, VRAM MB.
6. **Production recommendation** — choose GLiNER-small vs GLiNER-large based on: (a) F1 gap greater than 3 points favours large if VRAM allows, (b) co-load budget must fit under 6 GB total across all 4 heads plus qwen3.5:4b. Document the decision logic, not just the outcome.
7. **VRAM co-load table** — classifier + chosen retriever + chosen GLiNER + rebel-large + qwen3.5:4b summed, compared against 8.15 GB total on RTX 5060.
8. **What got cut** — cross-encoder reranker and any training runs that failed.
9. **Follow-ups** — backend wiring, any knobs worth tuning later.

### PRODUCTION.md updates
After writing the report, update `fine-tuning/models/PRODUCTION.md`:
- Add the chosen GLiNER entry (path, base, params, VRAM, recipe, metrics).
- Add the REBEL entry.
- Update the VRAM co-load table.

### Final commit
`feat(fine-tune): GLiNER + REBEL trained and benchmarked, pipeline complete`.
Include: the plan file, all Phase 1–5 commits already landed, the report, the updated PRODUCTION.md, memory updates.

### Memory updates
After the report is written, create `memory/project_gliner_rebel_training.md` summarising the winning picks and reasoning so future sessions can reference the decision without re-reading the full report.

## Execution contract

1. This plan is self-contained. The executing session must proceed through all six phases without pausing for user input, except in the two explicit stop conditions below.
2. **Stop conditions** — write a partial Final Report and halt if: (a) VRAM cannot be freed at Phase 0 and stays above 6 GB used, or (b) disk free drops below 10 GB mid-training.
3. **Checkpoint commits** — commit at the end of each phase so partial progress is never lost. If any phase fails and a retry is attempted, commit the partial work first.
4. **Time budget** — Phase 1 is the longest unknown; if after 4 hours of parallel agent minting the total is still below 12,000 rows, proceed with what is available and scale Phase 2's split targets accordingly (e.g., 8k/1.6k/1.6k) rather than blocking.
5. **Memory system writes** — follow the existing pattern: individual markdown in `memory/` with frontmatter, plus MEMORY.md index line.

## Out of scope (do not do these in this session)

- Cross-encoder reranker training or benchmarking.
- Switching the classifier or retriever bases.
- Touching the backend retrieval service wiring.
- Fine-tuning qwen3.5:4b.
- Re-running retrieval benchmarks from the previous session.

## Estimated total wall-clock

- Phase 1 (corpus expansion via subagents): 2–4 hours
- Phase 2 (conversion + splits): 10 minutes
- Phase 3a (GLiNER-small): 1–2 hours
- Phase 3b (GLiNER-large): 3–5 hours
- Phase 3c (REBEL-large): 4–6 hours
- Phase 4 (scoring): 30 minutes
- Phase 5 (end-to-end): 30 minutes
- Phase 6 (report + commits): 20 minutes

Total: roughly 12–18 hours of continuous wall-clock, most of it GPU-bound training.
