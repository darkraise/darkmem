# Plan — GLiNER + REBEL training on expanded corpus (v2)

**Created**: 2026-04-16 (revised after self-review)
**Branch**: `feat/architecture-overhaul`
**Working directory**: `D:\Repositories\_local_projects\darkmem` — all `python -m scripts.*` commands run from `fine-tuning/` (cd there at Phase 0 and stay there).

**Execution model**: long-running, single continuous session. Do not stop for user input until the Final Report is written. All proceed/fail decisions are encoded in Acceptance criteria below.

## Goal

Train and benchmark the two remaining fine-tuned heads in the darkmem 4-head architecture (entity extraction via GLiNER, relationship extraction via REBEL). Produce head-level and extraction-pipeline metrics, choose production GLiNER size, write a comprehensive final report.

Cross-encoder reranker is **explicitly out of scope** (user rejected on latency + VRAM grounds).

## Context

Current production picks (from `fine-tuning/models/PRODUCTION.md`, commit 88219e0):
- Classifier: `classifier-v3aug2-modernbert-base/best` — acc 0.975 on gold_v3 (1000 rows)
- Retriever: `retriever-bge-base-7500clean-hn-ep5-b64` — MRR 0.884 on test_pairs (500 rows, corpus 7000)

Missing heads, data already exists at `fine-tuning/data/splits/`:
- GLiNER: 6400 train / 800 val / 800 test (derived from 7000-row `fine-tuning/data/v2/shared/shared.jsonl`)
- REBEL: 6137 train / 767 val / 766 test (same source, filtered to rows with relationships)

Target sizes per user directive:
- **Train: at least 10,000 rows**
- **Val: at least 2,000 rows**
- **Test: at least 2,000 rows**

This requires expanding `shared.jsonl` from 7,000 → at least 14,000 rows.

### Verified facts (from 2026-04-16 self-review)

- Existing emitter format: Python list of 8-tuples `(text, memory_type, domain, noise, entities, relationships, qq, qk)` per row. Reference: `scripts/_emit_shared_batch_140.py`.
- Existing batch cadence: 50 rows per emitter. Batches 001–141 together reached 7000 rows.
- Existing noise fraction: 3.9% (274/7000). Keep new data at 3–5%.
- Existing memory_type distribution is skewed: decision 22%, architecture 19%, milestone 14%, fact 14%, reference 13%, preference 9%, problem 8%. Matching is acceptable; do not enforce uniformity.
- Existing relationship coverage: only ~57% of rows carry a relationship. REBEL splits are produced by filtering to those rows, which is why REBEL totals lag GLiNER totals.
- Entity types are enumerated in `fine-tuning/config/entity_pools.py` (35 types): technology, service, library, database, framework, protocol, algorithm, project, language, platform, infrastructure, person, place, organization, event, date, food, activity, goal, emotion, hobby, concept, theory, publication, method, finding, claim, field, tool, file, command, error, config, pattern, api.
- `scripts/train_gliner.py` and `scripts/train_rebel.py` **hardcode** data paths to `data/splits/gliner_{train,val}.jsonl` and `data/splits/rebel_{train,val}.jsonl` — neither accepts `--train` or `--val` flags. Swap the split files in place before invoking training (no script patches needed).
- `scripts/eval_entity.py` and `scripts/eval_relation.py` take `--gold` and `--pred` (metrics-only). Inference must be run separately to produce a predictions JSONL before scoring.
- `scripts/evaluate.py` orchestrates GLiNER + REBEL **only**; it does not load the classifier or retriever. Phase 5 is therefore the **extraction pipeline** (2-head), not the full 4-head stack. Full-stack co-load is documented in Phase 6 via static VRAM measurement rather than a joint inference run.
- `scripts/aggregate_shared_batches.py` takes positional batch file paths (not `--from`/`--to`) and uses `difflib.SequenceMatcher`, which crashes on Python 3.14 mid-aggregate (see `memory/debug_aggregator_difflib_python314.md`). Use the append-only replacement bundled in Phase 1.5 instead.

## Phase 0 — Preflight

1. `cd fine-tuning` and remain there throughout the session.
2. `git status --short` — confirm no untracked blockers. Uncommitted diffs on unrelated files are fine; commit or stash them before Phase 1 if they touch `scripts/`, `data/v2/shared/`, `data/splits/`, or `models/`.
3. `wc -l data/v2/shared/shared.jsonl` — must print `7000`.
4. Confirm `models/PRODUCTION.md` lists the classifier and retriever.
5. `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` — should report under 2000 MB used. If higher, run `docker restart ollama` and re-check after 20 seconds.
6. `df -m` — ensure D: has ≥ 50 GB free.
7. Record the outputs of steps 3, 5, 6 into a running Phase 0 log at `runs/2026-04-16-training-session/preflight.log`.

Stop conditions: VRAM stays > 6 GB used after the restart attempt, or D: free drops below 10 GB. In either case write a partial Final Report citing the block and halt.

Note: Phase 5 needs ollama running with qwen3.5:4b warm-loaded for VRAM co-load measurement. Do not forget to `docker start ollama` (or equivalent) before Phase 5 even though Phase 0 stops it.

## Phase 1 — Corpus expansion (shared rows 7001–14000)

### Goal
Add 7,000 new rows to `shared.jsonl`, each with `{id, domain, text, memory_type, noise, entities, relationships, queries}` fields matching the existing schema.

### Batch plan
**140 new batches numbered 142–281, each emitting 50 rows.** This matches the proven 001–141 cadence.

- Batch 142 → ids shared-07051 … shared-07100 (set `ID_OFFSET = 7050` so first id lands at shared-07051 if the prior terminal id was shared-07000 — verify with the last existing ID and adjust)
- ... through batch 281 → shared-13951..14000
- Total: 140 × 50 = 7,000 rows → shared.jsonl grows to 14,000

Dispatch in **rounds of 15 parallel subagents**. ~10 rounds total. Do not exceed 15 concurrent subagents — it is the proven saturation point from the prior session.

### Per-agent brief template
Each subagent receives:
- Batch number N (142 ≤ N ≤ 281)
- Exact starting ID (computed from N: `ID_OFFSET = 7000 + (N - 142) * 50`)
- Target output path: `data/v2/shared/batch_{N:03d}.tmp.jsonl`
- Reference emitter: `scripts/_emit_shared_batch_140.py` — copy the ENTRIES 8-tuple schema exactly
- Emitter script target: `scripts/_emit_shared_batch_{N:03d}.py`
- Diversity mandate: domain theme for the batch (e.g., "web3/crypto", "cooking", "philosophy", "aviation", "tabletop games") so subagents don't collide on the same topic
- Memory-type mix per batch: 10–15 decision, 8–10 architecture, 6–8 milestone, 6–8 fact, 6–8 reference, 4–6 preference, 3–5 problem (sums to 50, matches historical skew)
- Noise fraction: exactly 2 of 50 rows flagged `noise=True` (4%)
- Entity annotations: every row must carry ≥ 1 entity; entity types must come from the 35-type set listed in `config/entity_pools.py`; char offsets must exactly match the text (`text[start:end] == name` must hold)
- Relationship annotations: ≥ 30 of 50 rows must carry ≥ 1 relationship with source, target both appearing in that row's entities
- Query stubs: each row gets one (qq, qk) tuple — a natural-language question and a keyword-form query of the same fact

### Subagent execution and run_in_background
Each subagent call runs in the background. Wait for all 15 completions per round via the notification system before starting the next round. Do not interleave rounds.

### Aggregation (replaces buggy aggregate_shared_batches.py)

Write a one-off `scripts/_append_shared_batches.py` that:
1. Loads existing `data/v2/shared/shared.jsonl` into a dict keyed by `id`.
2. Loads every `data/v2/shared/batch_{N:03d}.tmp.jsonl` for N in [142, 281] in order.
3. For each new row: skip if `id` collides with existing, skip if `text` exactly matches an existing `text`, else append.
4. Writes the combined dict back to `shared.jsonl` preserving insertion order.
5. Logs skips to `data/v2/failed/append_skips_2026-04-16.jsonl`.

This avoids `difflib.SequenceMatcher` entirely and sidesteps the Python 3.14 crash. Exact-match dedup is sufficient because subagent outputs are freshly generated text unlikely to byte-match existing rows.

After aggregation, run `python -m scripts.validate_v2 --input data/v2/shared/shared.jsonl`. For each validation failure:
- If the error is "char offset mismatch on entity", drop the row to `data/v2/failed/invalid_offsets.jsonl` and note it in the running log.
- If the error is "unknown entity type", rewrite the type to the nearest valid type (`utility` → `tool`, `lib` → `library`) via a small remap table.
- If > 200 rows fail, pause and escalate in the Final Report rather than dropping silently.

### Acceptance
- `shared.jsonl` has ≥ 13,800 rows after drops (target 14,000, tolerance 200).
- `validate_v2` passes on all remaining rows.
- Per-type counts: each memory_type has ≥ 1,400 rows.
- Commit: `data(fine-tune): shared batches 142-281 (+7000 rows)` — include all 140 emitter scripts, the 140 batch .tmp files, the new `_append_shared_batches.py`, and the updated `shared.jsonl`.

### Time-budget escape hatch
If after **4 hours of Phase 1 wall-clock** the corpus is still below 12,000 rows, stop minting and proceed with what is there. Phase 2's split targets scale accordingly: `train = floor(corpus * 10000/14000)`, `val = test = floor(corpus * 2000/14000)`. Document the undershoot at the top of the Final Report.

### Actual Phase 1 outcome (2026-04-16)
Stopped at **11,800 rows** (7,000 existing + 4,800 new across 96 batches: 142-237). Opus 4.6 token budget made the last 2,400 rows (batches 238-281) uneconomical to continue. Phase 1.1 below bridges the gap with open-corpus data instead.

## Phase 1.1 — Open-corpus top-up (NuNER + REBEL)

### Motivation
The 11,800 darkmem rows are in-distribution and irreplaceable but by themselves underserve the target 10k/2k/2k GLiNER split and 8k+/1.8k+/1.8k+ REBEL split. Open NER/RE corpora cover our taxonomy well enough to fill the gap at zero generation cost, and the GLiNER + REBEL papers both show domain-mix training helps generalization.

### Target
Expand the raw pool to **~50,000 rows** total by pulling and filtering from:
- `numind/NuNER-v2` — ~370k synthetic NER rows, ~200 entity types. Filter to rows whose labels are all in our 35-type set (or can be remapped via the table below). Expected keep-rate 15-25% ⇒ 50-90k eligible rows; cap at **30,000**.
- `Babelscape/rebel-dataset` — ~1M Wikipedia+DBpedia triplets with ~220 relation types. Filter to rows whose relations map onto our 30-set via the relation remap table. Expected keep-rate 30-40% ⇒ 300-400k eligible; cap at **10,000** to avoid drowning darkmem rows.

### Remap tables (open → darkmem taxonomy)
Entity type remap — only keep rows where every entity type maps cleanly:
```
PER / PERSON / PEOPLE       → person
LOC / LOCATION / GPE        → place
ORG / ORGANISATION          → organization
DATE / TIME                 → date
EVENT                       → event
PRODUCT                     → tool
LANGUAGE                    → language
TECH / TECHNOLOGY           → technology
LIBRARY / FRAMEWORK         → library
DATABASE                    → database
FRAMEWORK                   → framework
PROTOCOL                    → protocol
ALGORITHM                   → algorithm
PROJECT                     → project
PLATFORM                    → platform
INFRASTRUCTURE              → infrastructure
FILE / FILENAME / PATH      → file
COMMAND / CLI               → command
ERROR / EXCEPTION           → error
CONFIG / SETTING            → config
PATTERN / DESIGN_PATTERN    → pattern
API / ENDPOINT              → api
FOOD                        → food
ACTIVITY                    → activity
HOBBY                       → hobby
CONCEPT / IDEA              → concept
THEORY                      → theory
PUBLICATION / BOOK / PAPER  → publication
METHOD / TECHNIQUE          → method
FINDING / RESULT            → finding
CLAIM                       → claim
FIELD / DISCIPLINE          → field
TOOL / UTILITY              → tool
WORK_OF_ART / LAW / NORP    → (drop row — no clean map)
```

Relation type remap — REBEL's Wikidata property codes:
```
P31  (instance of)          → IS_A
P279 (subclass of)           → IS_A
P527 (has part)              → HAS_PART
P361 (part of)               → HAS_PART          (swap source/target)
P17  (country)               → LOCATED_IN
P131 (located in admin unit) → LOCATED_IN
P276 (location)              → LOCATED_IN
P50  / P57 / P170 (author/director/creator)
                             → AUTHORED_BY       (swap source/target)
P577 (publication date)      → HAPPENED_ON
P585 (point in time)         → HAPPENED_ON
P123 (publisher)             → PUBLISHED_IN      (swap)
P156 (followed by)           → REPLACES          (swap)
P155 (follows)               → REPLACES
P180 (depicts)               → APPLIES_TO
P176 (manufacturer)          → PRODUCES          (swap)
P249 (ticker symbol)         → RELATED_TO
P463 (member of)             → WORKS_AT          (swap)
P108 (employer)              → WORKS_AT
P800 (notable work)          → PRODUCES
P138 (named after)           → RELATED_TO
P710 (participant)           → RELATED_TO
P179 (part of series)        → HAS_PART          (swap)
P166 (award received)        → RELATED_TO
P737 (influenced by)         → BUILDS_ON
(all others)                 → drop row
```

### Steps
1. Write `scripts/_pull_open_corpora.py`:
   - Install/verify `datasets` library (Hugging Face `datasets`) is available. If not, `pip install datasets`.
   - Stream-download `numind/NuNER-v2`. For each row, remap types; drop if any unmappable; drop if text > 280 chars or < 30 chars. Write to `data/v2/open/nuner_filtered.jsonl` until 30,000 kept rows.
   - Stream-download `Babelscape/rebel-dataset` train split. For each row, parse the linearised triplet string into (source, target, wikidata_prop) tuples; remap props via the table; drop rows where any relation is unmappable or has <2 triplets. Recover entity spans from the source text (REBEL records character offsets in a separate field). Drop if text > 280 chars. Write to `data/v2/open/rebel_filtered.jsonl` until 10,000 kept rows.
   - Convert both streams to darkmem shared-row schema (`id`, `domain="open"`, `text`, `memory_type` set to `fact` by default, `noise=False`, `entities`, `relationships`). Use id prefix `nuner-` for NuNER and `rebel-` for REBEL to keep provenance obvious.
2. Run `python -m scripts.validate_v2 data/v2/open/nuner_filtered.jsonl --kind shared --failed-dir data/v2/open/_failures` and the same for REBEL. Drop any failing row.
3. Append the two filtered files into a new pool file `data/v2/shared/shared_expanded.jsonl` that combines `shared.jsonl` (11,800) + NuNER kept + REBEL kept. Target size: ≥ 40,000 rows, cap 50,000.
4. `shared.jsonl` stays at 11,800 untouched — Phase 1.5 draws from `shared_expanded.jsonl` instead. This keeps darkmem rows recoverable if we ever want a pure-darkmem retrain.

### Acceptance
- `data/v2/shared/shared_expanded.jsonl` has ≥ 40,000 rows, all passing `validate_v2 --kind shared`.
- NuNER contribution ≥ 20,000 rows, all entities within the 35-type set.
- REBEL contribution ≥ 6,000 rows, all relationships within the 30-type set.
- Every kept row has text in the 30–280 char window.
- Commit: `data(fine-tune): Phase 1.1 open-corpus top-up — NuNER + REBEL merged to 40k+ pool`. Include the two filtered files, the merged pool, and the puller script. The upstream raw downloads are NOT committed — they are multi-GB and easy to re-pull.

### Wait-gate
After Phase 1 commit, **pause for user confirmation** before executing Phase 1.1. Phase 1.1 changes the training-distribution mix, and the user wants to approve that shift explicitly before the splits are rebuilt.

## Phase 1.5 — Split re-stratification

The trainers hardcode split paths, so the new splits must land at `data/splits/gliner_{train,val,test}.jsonl` and `data/splits/rebel_{train,val,test}.jsonl`. Back up the current splits first.

### Steps
1. `cp data/splits/gliner_train.jsonl data/splits/gliner_train.v1.jsonl` and the same for val, test, and REBEL counterparts.
2. Write `scripts/_restratify_splits.py`:
   - Input: the expanded `data/v2/shared/shared.jsonl` (14k rows).
   - Build GLiNER rows via the same transform as `scripts.convert_to_gliner` (char-span entity list), stratified by `memory_type` where present (open-corpus rows don't carry memory_type — bucket them as `fact`).
   - Input: `data/v2/shared/shared_expanded.jsonl` from Phase 1.1 (40k+ rows).
   - Target GLiNER split: 10000 train / 2000 val / 2000 test; random seed 42; stratify so each memory_type contributes proportionally (no class gets less than 12% of its share in test/val). Test + val rows must both come from the darkmem portion (prefixes `shared-*`), not the open-corpus portion, so held-out evaluation is in-distribution for the production use case. Train may mix darkmem + open to hit 10k.
   - Build REBEL rows via `scripts.convert_to_rebel` (linearized triplets). Skip rows where `relationships` is empty. Target: train ≥ 8000, val ≥ 1800, test ≥ 1800. Test + val drawn from darkmem rows only; train may mix.
   - Write directly to `data/splits/gliner_{train,val,test}.jsonl` and `data/splits/rebel_{train,val,test}.jsonl`.

Do not invoke `scripts.build_splits` or `scripts.convert_to_gliner`/`convert_to_rebel` separately — the restratify script inlines the conversion so everything runs in one pass.

### Acceptance
- GLiNER train/val/test sizes: 10000, 2000, 2000.
- REBEL train ≥ 8000, val ≥ 1800, test ≥ 1800.
- Each split preserves memory_type distribution to within ±20% of its population share.
- Commit: `data(fine-tune): re-stratify GLiNER/REBEL to 10k/2k/2k target`.

## Phase 2 — Training (sequential)

All three trainings run back-to-back on the single RTX 5060. Do not start the next run until the prior's checkpoint is written.

### 2a. GLiNER-small
```
mkdir -p runs/gliner-small-v2corpus
python -m scripts.train_gliner \
  --base-model urchade/gliner_small-v2.1 \
  --output-dir models/gliner-small-v2corpus \
  --epochs 5 --batch-size 16 --lr 1e-5 \
  > runs/gliner-small-v2corpus/train.log 2>&1
```
Expected wall-clock: 1–2 hours. Inference VRAM about 250 MB.

### 2b. GLiNER-large
```
mkdir -p runs/gliner-large-v2corpus
python -m scripts.train_gliner \
  --base-model urchade/gliner_large-v2.1 \
  --output-dir models/gliner-large-v2corpus \
  --epochs 5 --batch-size 8 --lr 1e-5 \
  > runs/gliner-large-v2corpus/train.log 2>&1
```
Expected wall-clock: 3–5 hours. Inference VRAM about 900 MB. OOM fallback: drop `--batch-size` to 4.

### 2c. REBEL-large
`train_rebel.py` does not currently support `--bf16` or `--gradient-checkpointing` flags. **Start with batch 2 to stay inside 8 GB** (BART-large at batch 4 fp32 wants ~10–14 GB):
```
mkdir -p runs/rebel-large-v2corpus
python -m scripts.train_rebel \
  --base-model Babelscape/rebel-large \
  --output-dir models/rebel-large-v2corpus \
  --epochs 3 --batch-size 2 --lr 3e-5 \
  --max-source-length 256 --max-target-length 128 \
  > runs/rebel-large-v2corpus/train.log 2>&1
```
Expected wall-clock: 5–8 hours.

**If this OOMs at batch 2**, patch `train_rebel.py` in place by adding:
- `--bf16` flag that sets `bf16=True` and `fp16=False` in `Seq2SeqTrainingArguments`.
- `--gradient-checkpointing` flag that sets `gradient_checkpointing=True` and `model.config.use_cache=False`.

Use `train_classifier.py` as the reference for wiring those two flags. Retry with `--bf16 --gradient-checkpointing --batch-size 4 --gradient-accumulation-steps 2`.

### Failure handling
If a training run fails twice on recoverable errors (OOM, data collator crash), skip that model, record `FAILED_<MODEL>` in `runs/2026-04-16-training-session/failures.log`, and move to the next. If GLiNER-small fails, that is a blocker — halt. The other two failing individually is survivable.

### Acceptance per model
- Checkpoint directory loadable via `GLiNER.from_pretrained(path)` or `AutoModelForSeq2SeqLM.from_pretrained(path)`.
- Final-epoch loss is a finite number in the train log.
- Commit each trained model's artifacts (`runs/<run_dir>/train.log` and `models/<model>/run_metadata.json`) as: `feat(fine-tune): train <model-name> on 14k v2 corpus`. The model checkpoint itself is gitignored.

## Phase 3 — Head-level benchmarking

`eval_entity` and `eval_relation` only compute metrics between two JSONL files. Each model needs a separate inference step.

### 3a. Write a one-off `scripts/_infer_entity.py`
- Input: `--model <path>` and `--gold data/splits/gliner_test.jsonl`.
- Load the GLiNER model, iterate gold rows, run `model.predict_entities(text, labels=ALL_ENTITY_TYPES)`.
- Output: `--pred <path>` with rows `{id, text, entities: [{start, end, label}, ...]}` in the same schema as gold.
- Also emit latency per row and peak VRAM measured via `torch.cuda.max_memory_allocated`.

Run it twice:
```
python -m scripts._infer_entity --model models/gliner-small-v2corpus --gold data/splits/gliner_test.jsonl --pred runs/gliner-small-v2corpus/pred.jsonl
python -m scripts.eval_entity --gold data/splits/gliner_test.jsonl --pred runs/gliner-small-v2corpus/pred.jsonl --out runs/gliner-small-v2corpus/metrics.json

python -m scripts._infer_entity --model models/gliner-large-v2corpus --gold data/splits/gliner_test.jsonl --pred runs/gliner-large-v2corpus/pred.jsonl
python -m scripts.eval_entity --gold data/splits/gliner_test.jsonl --pred runs/gliner-large-v2corpus/pred.jsonl --out runs/gliner-large-v2corpus/metrics.json
```

### 3b. Write `scripts/_infer_relation.py` analogously for REBEL
- Seq2seq decoding with `max_target_length=128, num_beams=4`.
- Parse the `<triplet>` delimited output into `[{source, target, type}, ...]`.
- Run and score:
```
python -m scripts._infer_relation --model models/rebel-large-v2corpus --gold data/splits/rebel_test.jsonl --pred runs/rebel-large-v2corpus/pred.jsonl
python -m scripts.eval_relation --gold data/splits/rebel_test.jsonl --pred runs/rebel-large-v2corpus/pred.jsonl --out runs/rebel-large-v2corpus/metrics.json
```

### Metrics schema expected in the output JSON
```json
{
  "overall": {"precision": float, "recall": float, "f1": float, "n": int},
  "per_type": {"<type>": {"precision": float, "recall": float, "f1": float, "support": int}, ...},
  "latency_ms_per_row": float,
  "peak_vram_mb": float,
  "model": "<path>"
}
```
If `eval_entity`/`eval_relation` do not already emit `per_type` or latency/VRAM fields, extend them — follow the pattern in `scripts/eval_retrieval_breakdown.py`.

### Acceptance
- Three metric JSONs written, each with the schema above.
- Commit: `bench(fine-tune): head-level entity + relation metrics on 2k test split`.

## Phase 4 — Extraction pipeline benchmark

`scripts.evaluate` orchestrates GLiNER + REBEL only — the end-to-end 4-head integration has not been built yet. Phase 4 therefore measures the 2-head extraction pipeline; full 4-head co-load is documented statically in Phase 5 VRAM table.

### Commands
Re-start ollama if Phase 0 stopped it: `docker start ollama`. Wait 30 seconds and confirm `nvidia-smi` shows qwen3.5:4b loaded (~3 GB).

```
mkdir -p runs/e2e-small runs/e2e-large
python -m scripts.evaluate \
  --gliner-model models/gliner-small-v2corpus \
  --rebel-model models/rebel-large-v2corpus \
  --test-split \
  > runs/e2e-small/run.log 2>&1
# evaluate.py writes its metrics to a default path; move or capture to runs/e2e-small/metrics.json

python -m scripts.evaluate \
  --gliner-model models/gliner-large-v2corpus \
  --rebel-model models/rebel-large-v2corpus \
  --test-split \
  > runs/e2e-large/run.log 2>&1
```

During each run, capture `nvidia-smi` output every 10 seconds via a background `while` loop to `runs/e2e-<size>/vram.csv`. The peak value is the extraction-pipeline VRAM with qwen3.5:4b warm-loaded alongside — that is the number that matters for the production decision.

### Acceptance
- Two extraction-pipeline runs completed.
- Peak VRAM recorded per run.
- Commit: `bench(fine-tune): extraction pipeline with expanded corpus (small + large GLiNER)`.

## Phase 5 — Full 4-head VRAM audit (static)

Because `evaluate.py` does not load classifier + retriever, measure the full 4-head co-load as a separate VRAM audit rather than an end-to-end run.

### Steps
Write `scripts/_vram_coload_audit.py` that:
1. Loads the classifier model on CUDA.
2. Loads the retriever (bge-base-7500clean) on CUDA.
3. Loads the chosen GLiNER (initially both small and large variants, reported separately).
4. Loads REBEL-large on CUDA.
5. Also confirms qwen3.5:4b is up in ollama (via `docker ps` + HTTP ping to localhost:11434/api/tags).
6. Reports `torch.cuda.memory_allocated()` after each load plus the total free VRAM from `nvidia-smi`.

Write results to `runs/2026-04-16-training-session/vram_coload.json`.

### Acceptance
- JSON captures per-model idle VRAM and total sum for both GLiNER sizes.
- If sum with GLiNER-large > 7.2 GB, production pick must default to GLiNER-small.
- Commit: `bench(fine-tune): 4-head VRAM co-load audit`.

## Phase 6 — Final report

Location: `docs/e2e/runs/2026-04-16-gliner-rebel-final.md`.

### Required sections
1. **Summary** — one paragraph; production picks and headline metrics.
2. **Corpus expansion** — new row count, final memory_type distribution, dropped row count with reasons.
3. **Split sizes** — final GLiNER and REBEL train/val/test counts.
4. **Head-level metrics table** — columns: model, base, params, train time, val F1, test F1 (micro), macro F1, notable per-type outliers, ms/row, peak VRAM MB. Three rows (gliner-small, gliner-large, rebel-large).
5. **Extraction pipeline metrics table** — two rows (small, large GLiNER paired with rebel-large): entity F1, relation F1, combined F1, docs/sec, peak VRAM MB (from Phase 4 nvidia-smi).
6. **4-head VRAM audit table** — Phase 5 output rendered as a table.
7. **Production recommendation** — concrete decision criterion:
   - If head-level test F1 gap (large minus small) ≥ 5 points AND Phase-5 sum with GLiNER-large ≤ 7.2 GB → recommend GLiNER-large.
   - Else → recommend GLiNER-small.
   Explain the calculation, not just the outcome.
8. **What got cut** — cross-encoder reranker explicitly; any Phase failures.
9. **Follow-ups** — backend wiring, knobs worth tuning later.

### PRODUCTION.md updates
Append the chosen GLiNER and REBEL to `fine-tuning/models/PRODUCTION.md` with the same schema used for classifier and retriever (path, base, params, VRAM idle, VRAM peak, training data, test metrics, inference recipe). Update the VRAM co-load table at the bottom.

### Memory updates
Create `memory/project_gliner_rebel_training.md` with: production picks, test F1s, VRAM, reasoning. Add one line to `MEMORY.md` index.

### Final commit
`feat(fine-tune): GLiNER + REBEL trained and benchmarked, extraction pipeline complete`. Include the report, PRODUCTION.md updates, and memory updates.

## Commit checklist per phase

| phase | paths to stage |
|---|---|
| 0 | `runs/2026-04-16-training-session/preflight.log` |
| 1 | `scripts/_emit_shared_batch_{142..281}.py`, `scripts/_append_shared_batches.py`, `data/v2/shared/batch_{142..281}.tmp.jsonl`, `data/v2/shared/shared.jsonl`, `data/v2/failed/append_skips_2026-04-16.jsonl`, `data/v2/failed/invalid_offsets.jsonl` |
| 1.5 | `scripts/_restratify_splits.py`, `data/splits/{gliner,rebel}_{train,val,test}.jsonl`, `data/splits/{gliner,rebel}_{train,val,test}.v1.jsonl` |
| 2 | `runs/gliner-{small,large}-v2corpus/train.log`, `runs/rebel-large-v2corpus/train.log`, `models/*/run_metadata.json`, any train_rebel.py bf16/ckpt patches |
| 3 | `scripts/_infer_entity.py`, `scripts/_infer_relation.py`, `runs/*/pred.jsonl`, `runs/*/metrics.json`, `scripts/eval_entity.py` or `eval_relation.py` extensions |
| 4 | `runs/e2e-{small,large}/run.log`, `runs/e2e-{small,large}/vram.csv`, `runs/e2e-{small,large}/metrics.json` |
| 5 | `scripts/_vram_coload_audit.py`, `runs/2026-04-16-training-session/vram_coload.json` |
| 6 | `docs/e2e/runs/2026-04-16-gliner-rebel-final.md`, `fine-tuning/models/PRODUCTION.md`, `memory/project_gliner_rebel_training.md`, `memory/MEMORY.md` |

## Execution contract

1. This plan is self-contained. Proceed through all six phases without pausing for user input, except on the two stop conditions in Phase 0.
2. **Checkpoint commits** — commit at the end of each phase so partial progress is never lost. If any phase fails and a retry is attempted, commit the partial work first.
3. **Time-budget escape** — Phase 1 has a 4-hour cap with graceful scaledown. Training phases have no cap; overnight is fine.
4. **Memory system writes** — follow the existing pattern: individual markdown in `memory/` with frontmatter, plus MEMORY.md index line.

## Out of scope (do not do these in this session)

- Cross-encoder reranker training or benchmarking.
- Switching the classifier or retriever bases.
- Touching the backend retrieval service wiring.
- Fine-tuning qwen3.5:4b.
- Re-running retrieval benchmarks from the previous session.
- Rotating the Hugging Face token embedded in `train_gliner.py` / `train_rebel.py` — flag it in the Final Report's Follow-ups section as a separate security concern (pre-existing, out of scope here).

## Estimated total wall-clock

| phase | min | max |
|---:|---:|---:|
| 0 preflight | 5 min | 10 min |
| 1 corpus expansion | 2 h | 4 h |
| 1.5 re-stratify | 10 min | 15 min |
| 2a GLiNER-small | 1 h | 2 h |
| 2b GLiNER-large | 3 h | 5 h |
| 2c REBEL-large | 5 h | 8 h |
| 3 head scoring | 20 min | 30 min |
| 4 pipeline bench | 20 min | 30 min |
| 5 VRAM audit | 5 min | 10 min |
| 6 report + commits | 30 min | 45 min |
| **total** | **~12 h** | **~20 h** |

Roughly half of the wall-clock is REBEL training. Most of the rest is Phase 1 minting + GLiNER-large training.
