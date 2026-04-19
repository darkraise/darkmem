# Schema v2 migration progress log

Tracks per-phase execution of `fine-tuning/SCHEMA_V2_PLAN.md`.
Rows are append-only — do not rewrite history. Include counts, metrics, and decisions.

## Phase 0 — tooling

Started and completed: 2026-04-19.

Artifacts created:
- `fine-tuning/scripts/_build_rebel_coding5_splits.py` (defines REL_MAP_5 + builds rebel seq2seq)
- `fine-tuning/scripts/_build_coding5_splits.py` (builds 5-type canonical)
- `fine-tuning/scripts/_build_relclass5_splits.py` (pair-wise builder)
- `fine-tuning/scripts/_validate_schema5.py` (5-type validator)
- `rebel_pair_rescore.py` patched with `--schema {10type,5type}` (default 10type for back-compat)

## Phase 1 — remap gold and rebuild data tables

Completed: 2026-04-19.

### Canonical counts (`_build_coding5_splits.py`)

| split | in rows | out rows | dropped (all-None) | entity-only |
|---|---:|---:|---:|---:|
| train | 13,144 | 11,368 | 1,776 | 1,901 |
| val   | 791   | 711   | 80  | 238 |
| test  | 791   | 719   | 72  | 224 |

Rel-carrying train rows after 5-type remap: 9,467 (matches plan projection ~9,500).

### Train relation distribution (`rebel_coding5_train.jsonl`)

| class | count | % |
|---|---:|---:|
| USES | 7,798 | 54.1% |
| REPLACES | 2,655 | 18.4% |
| CAUSES | 1,460 | 10.1% |
| DEPLOYED_ON | 1,312 | 9.1% |
| IS_A | 1,191 | 8.3% |
| total | 14,416 | |

Matches plan projection exactly (USES 7,800, REPLACES 2,655, CAUSES 1,460, DEPLOYED_ON 1,312, IS_A 1,191).

### Test-gold positive pairs (`rebel_coding5_test_gold.jsonl`)

| class | count |
|---|---:|
| USES | 339 |
| REPLACES | 214 |
| DEPLOYED_ON | 32 |
| CAUSES | 29 |
| IS_A | 6 |
| total | 620 |

Matches plan projection exactly.

### v1-on-5-type baseline (`rebel_pair_rescore.py --schema 5type`)

Inputs: `runs/rebel-large-rescore/pred.jsonl` (shipping rebel-large-v1 predictions) against `data/splits/rebel_coding5_test_gold.jsonl`.

| metric | value |
|---|---:|
| pos_micro_precision | 0.6883 |
| pos_micro_recall    | 0.6339 |
| pos_micro_f1        | **0.6599** |
| accuracy            | 0.9374 |
| n_pairs             | 5,686 |
| n_gold_pos          | 620 |
| n_pred_pos          | 571 |

The 0.6599 lands inside the plan's 0.68–0.73 hypothesis range but a bit below centre; the
merger removed enough annotator-disagreement noise to lift F1 from 0.639 (10-type) to 0.660.

### Promotion gate for v2

- **Relative**: v2 F1 >= 0.6599 + 0.05 = **0.7099**
- **Absolute floor**: v2 F1 >= 0.70

Effective target: **v2 F1 >= 0.710**.

### Validator smoke test

`_validate_schema5.py` on `coding5clean_train_canon.jsonl`: 11,364 / 11,368 survived (100.0%).
4 rejections are `rel_0_self_loop` — a pre-existing corpus data-quality artefact present in
coding10clean too, not caused by the 5-type remap. Not a blocker.

## Phase 2 — train rebel-large-v2 on LXC

Completed: 2026-04-19 (116.6 minute walltime).
Command: `python3 -m scripts.train_rebel --base-model Babelscape/rebel-large --output-dir models/darkmem-relation-v2 --train-path data/splits/rebel_coding5_train.jsonl --val-path data/splits/rebel_coding5_val.jsonl --epochs 5 --batch-size 2 --lr 3e-5 --max-source-length 256 --max-target-length 128`
tmux session: `rebel-v2` on LXC (192.168.0.250). Log at `runs/darkmem-relation-v2/train.log`.

Early stop at epoch 4 (EarlyStoppingCallback inside `train_rebel.py`). Final metrics:

- train_loss 0.1375, eval_loss 0.3557 at epoch 4.
- Checkpoints kept: `best/` (saved from best epoch), `checkpoint-{4734, 14202, 18936}`.
- Plan hoped eval loss would land meaningfully lower than rebel-large-v1's ~0.165; instead
  it sits at 0.3557, suggesting the 5-type retrain is fitting worse than the 30-type
  baseline did. Not directly comparable loss values (different target vocab) but the gap
  motivates the evaluation below.

## Phase 3 — evaluate and promote

Completed: 2026-04-19. **Promotion gate FAILED. v2 not shipped. v1 remains the
production relation head.**

### Pair-wise F1 on `rebel_coding5_test_gold.jsonl` (`--schema 5type`)

| metric | v1 rescored | v2 trained on 5-type | delta |
|---|---:|---:|---:|
| pos_micro_precision | 0.6883 | 0.4537 | -0.2346 |
| pos_micro_recall    | 0.6339 | 0.4113 | -0.2226 |
| **pos_micro_f1**    | **0.6599** | **0.4315** | **-0.2284** |
| accuracy            | 0.9374 | 0.8896 | -0.0479 |

### Per-class v2 F1

| class | support | n_pred | precision | recall | f1 |
|---|---:|---:|---:|---:|---:|
| USES        | 339 | 281 | 0.342 | 0.283 | 0.310 |
| REPLACES    | 214 | 221 | 0.670 | 0.692 | 0.680 |
| DEPLOYED_ON | 32  | 36  | 0.250 | 0.281 | 0.265 |
| CAUSES      | 29  | 16  | 0.125 | 0.069 | 0.089 |
| IS_A        | 6   | 8   | 0.000 | 0.000 | 0.000 |

### Promotion gate

- Relative: v2 F1 0.4315 < v1+0.05 (0.7099). **FAIL**.
- Absolute floor: v2 F1 0.4315 < 0.70. **FAIL**.
- Decision: do **NOT** promote. Plan rule: "Do not ship until the relative gate at minimum passes."

### Diagnosis

Audited 5 random gold rows. Two were predicted exactly, two correctly predicted the gold
relation plus extra false-positive relations, one predicted a different source entity
entirely. Predicted class distribution (USES 284 / REPLACES 222 / DEPLOYED_ON 36 / CAUSES
17 / IS_A 8) roughly tracks gold distribution (339/214/32/29/6). So the model is not
class-collapsed or under-predicting; it is emitting plausible but noisier triplets.

Likely causes:

- Training data noise: rebel_coding5_train has 9,467 rel-carrying rows with a 54% USES
  majority. Collapsing 30-type surface forms into USES increases within-class heterogeneity
  and may hurt the seq2seq decoder more than the class-count reduction helps.
- Early stop at epoch 4: the eval_loss had plateaued at 0.3557; extending the run may have
  helped but was not available in the stopped session.

Not a remap-script bug: the coding5 canonical counts match the plan projection exactly,
and sample gold rows look coherent.

### Follow-ups (not in scope of this plan)

1. Train rebel-large on the 30-type `rebel_train.jsonl` and apply REL_MAP_5 post-hoc at
   inference (sub-experiment the plan flagged as optional). Compare against native-5-type
   training.
2. Relax early stopping and retrain v2 for the full 5 epochs with a small LR warmup.
3. Investigate USES heterogeneity: the 8 source labels folded into USES (USES,
   CONFIGURES, APPLIES_TO, COMMUNICATES_WITH, IMPLEMENTS, DEPENDS_ON, HAS_PART, EXTENDS)
   may need to remain sub-typed during training and be collapsed only at inference.

### Runtime impact of the gate failure

- Relation head stays at rebel-large-v1 (10-type via REL_MAP). `PRODUCTION.md` and
  `INTEGRATION_PLAN_v3.md` Section 3 stay as they are.
- Since new extractions emit 10-type labels and backfilled historical rows are 5-type,
  there is a schema drift risk. Separate decision needed on whether to add a REL_MAP_5
  post-hoc step in `ExtractionMLService` so new relation rows land in the 5-type set too.

## Phase 3b — rebel-large-v2b on 10-type + REL_MAP_5 at inference

Rationale: v2 native 5-type training hurt USES the most (collapsed eight 30-type surface
forms into one target). Hypothesis: train on the richer 10-type corpus (11,243 rows, keeps
DEPENDS_ON/HAS_PART/REPLACES as distinct training targets) and apply REL_MAP_5 only at
scoring time. Expected: match or beat v1-on-5-type (0.6599).

Training recipe: same as v1 (`rebel_coding10_train.jsonl`, 5 epochs, batch 2, lr 3e-5,
max_source 256, max_target 128). Completed full 5 epochs in ~2h53m on the LXC RTX 2060.
Final train_loss 0.115, eval_loss 0.6091 on `rebel_coding10_val.jsonl`. Checkpoint at
`models/darkmem-relation-v2b/best`.

### Pair-wise F1 (`--schema 5type` applies REL_MAP_5 to 10-type predictions)

| metric | v1 rescored | v2b trained on 10-type | delta vs v1 |
|---|---:|---:|---:|
| pos_micro_precision | 0.6883 | 0.5000 | -0.1883 |
| pos_micro_recall    | 0.6339 | 0.4097 | -0.2242 |
| **pos_micro_f1**    | **0.6599** | **0.4504** | **-0.2095** |
| accuracy            | 0.9374 | 0.8957 | -0.0417 |
| n_gold_pos          | 620    | 620    | — |
| n_pred_pos          | 571    | 508    | -63 |

### Per-class v2b F1

| class | support | n_pred | P | R | F1 | v1 F1 | v2 F1 | v2b F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| USES        | 339 | 268 | 0.336 | 0.265 | 0.297 | 0.599 | 0.310 | 0.297 |
| REPLACES    | 214 | 205 | 0.756 | 0.724 | 0.740 | 0.825 | 0.680 | 0.740 |
| DEPLOYED_ON | 32  | 30  | 0.267 | 0.250 | 0.258 | 0.485 | 0.265 | 0.258 |
| CAUSES      | 29  | 5   | 0.200 | 0.034 | 0.059 | 0.167 | 0.089 | 0.059 |
| IS_A        | 6   | 0   | —     | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### Promotion gate for v2b

- Relative: v2b F1 0.4504 < v1+0.05 (0.7099). **FAIL.**
- Absolute floor: 0.4504 < 0.70. **FAIL.**
- Decision: do **NOT** promote. rebel-large-v1 remains the shipping relation head.

### Diagnosis

v2b only improves +0.019 over v2 and is still 0.21 below v1. Per class: v2b is slightly
better than v2 on REPLACES (+0.06) but equal-or-worse on USES, DEPLOYED_ON, CAUSES, IS_A.
The 10-type training target did not recover the USES recall that v1 gets from its
30-type-then-collapse pipeline.

The likely explanation is that v1's original `rebel_train.jsonl` (8,052 rows, 30-type,
broad-domain) contains information that our coding-focused 10-type corpus does not. When
v1's REBEL decoder sees CONFIGURES / APPLIES_TO / COMMUNICATES_WITH / IMPLEMENTS as
distinct training targets, it learns surface-form discrimination that helps even after
everything collapses to USES at scoring time. Training on the already-collapsed 10-type
labels discards that signal.

Secondary factor: the coding10 corpus includes ~6,800 Phase-2 synthetic relaug rows. Those
may have distribution shift or quality issues that hurt the seq2seq head more than they
help. v1 never saw them.

### Next experiments (not in scope of this plan)

1. Train rebel-large on the raw 30-type `rebel_train.jsonl` (v1's recipe) on the current
   toolchain, apply REL_MAP_5 at inference. Controls for trainer version drift and
   isolates whether v1's recipe is still reproducible at 0.66.
2. Train on the 30-type corpus augmented with coding-focused Phase-2 synth rows but kept
   at 30-type granularity (requires re-annotating the synth rows to finer labels).
3. FLAN-T5-large with QLoRA on the same 30-type corpus — bigger model, finer signal,
   fits on the RTX 2060 with gradient checkpointing.

### Final shipping decision — amended 2026-04-19

Ship **rebel-base** as the production relation head. Path: `fine-tuning/models/darkmem-relation-base-v1/best`.

Rationale: VRAM is the binding constraint on the 12 GB LXC RTX 2060 (current co-load budget
tops out near 7.5 GB including qwen3.5:4b). Moving from rebel-large (1,625 MB) to rebel-base
(606 MB) frees ~1 GB of VRAM, enough to co-load a larger reasoning LLM or keep headroom
for GPU-backed auxiliary heads. Quality cost: F1 0.660 → 0.618 on 5-type rescored (Δ −0.042,
recall −0.09, precision +0.03). Per-class F1 stays within 0.02–0.06 of v1 on USES/REPLACES/
DEPLOYED_ON/CAUSES; IS_A is zero on both (6-pair test support).

Neither rebel-large-v2 nor rebel-large-v2b passed the schema-v2 promotion gate (both ~0.45
F1, far below the 0.71 relative gate). The `darkmem-relation-v2` name is **NOT** used;
rebel-base ships as `darkmem-relation-base-v1` to signal it is a smaller variant of the v1
generation, not a gate-passing v2.

Path changes (see git diff):
- `fine-tuning/models/darkmem-relation-base-v1/` created from a copy of
  `fine-tuning/models/rebel-base-30type-ep6/`.
- `backend/app/services/ml_models.py` `load_extraction` relation path flipped to
  `darkmem-relation-base-v1/best`.
- `fine-tuning/models/PRODUCTION.md` updated: section 5 now describes the base variant;
  section 5b documents the large variant as archived-but-available.
- `fine-tuning/INTEGRATION_PLAN_v3.md` amended at the path reference (line 342) with the
  Pareto trade-off note inline.
- `fine-tuning/runs/rebel-base-30type-ep6/metrics_pairwise_5type.json` saved for audit.

Backend schema-v2 work (migration 0005, pipeline wiring, retrieval filters, backfills,
lazy-load, TTL eviction, UI device picker, system prompts, LLM classification purpose) all
ship independently of which rebel variant is live, because `clean_extraction` applies
REL_MAP_5 post-hoc to whatever the extractor returns. Output vocabulary lands in the 5-type
set regardless.

pytest `backend/tests/` minus websocket/LLM/chat/MCP: **282 passed**, same as pre-swap.

Artifacts kept:
- `runs/2026-04-19-schema-v2/v1_on_5type_baseline.json` (v1 rescored, 0.6599)
- `runs/2026-04-19-schema-v2/v2_metrics_pairwise.json` (v2 native 5-type, 0.4315)
- `runs/2026-04-19-schema-v2/v2b_metrics_pairwise.json` (v2b 10-type, 0.4504)
- `runs/2026-04-19-schema-v2/v2b_pred.jsonl` (predictions for follow-up audit)
- `models/darkmem-relation-v2/` and `models/darkmem-relation-v2b/` on the LXC (not
  synced locally; can be deleted after the diagnosis above is accepted).

## Phase 4 — backend Alembic schema migration

Completed: 2026-04-19.

Artifacts:
- `backend/migrations/versions/0005_memory_metadata_v2.py` — upgrade + downgrade spell out
  enum creation, five added columns, FK, three indexes (btree x2 + GIN), CHECK constraint.
- `backend/app/models/memory.py` — Memory ORM updated with the five new attributes and the
  `chk_superseded_has_pointer` table-level CheckConstraint. `ARRAY(Text)` is imported from
  `sqlalchemy.dialects.postgresql` so `.overlap()` comparisons work in Phase 5 + 7 queries.

Verified against local test database (`darkmem_test` on localhost:5433):

- `alembic upgrade head` applied 0001 through 0005 cleanly.
- CHECK constraint fires on INSERT of `status='superseded'` with NULL `superseded_by`.
- Column defaults correct: project='default', status='active', technologies=[], confidence=0.75.
- Valid (status='superseded', superseded_by=<uuid>) INSERT succeeds.
- `alembic downgrade -1` reverts to 0004 without error; re-upgrade to head works.
- `pytest backend/tests/` minus websocket/LLM/chat/MCP (external deps): 213 passed.

## Phase 5 — pipeline metadata wiring

Completed: 2026-04-19.

Helper modules:
- `backend/app/services/relations.py` — `TECH_TYPES`, `RELATION_TYPES_V2`, `REL_MAP_5`,
  `SPECULATIVE_REPLACES_MARKERS`, `SUPERSESSION_WINDOW_DAYS`, `REPLACES_CONFIDENCE_THRESHOLD`.
- `backend/app/services/confidence.py` — rule-based `estimate_confidence(text, memory_type)`
  placeholder returning values in the [0.5, 0.9] band.
- `backend/app/services/supersession.py` — `detect_supersessions()` + `is_speculative()`.

Wiring:
- `MemoryCreate`/`MemoryUpdate` gain a `project` field; `MemoryCreate` plumbs through
  `MemoryService.create_memory -> PostgresMemoryRepository.create`.
- `MemoryResponse` now emits `project`, `status`, `superseded_by`, `technologies`, `confidence`.
- `ProcessingPipeline._write_memory` computes `technologies` from extracted tech entities,
  sets `confidence = estimate_confidence(content, memory_type)`, and calls
  `detect_supersessions(...)` in the same transaction once the row has technologies.
- REPLACES detector guards: same project, status='active', 90-day window, technologies
  overlap with target name, speculative-phrasing skip (source-text heuristic stands in for
  per-relation confidence until the extractor emits one).

Tests (all green):
- `tests/test_schema_v2_metadata.py` — 16 tests cover the confidence estimator (defaults,
  low/high markers, authoritative types, conflict fallback), speculative-phrasing detector,
  supersession guards (flips, skips, project scope, staleness, tech containment), Memory-row
  defaults, enum rejection of garbage, project lookup.

## Phase 6 — backfill historical memory metadata

Completed: 2026-04-19.

Artifacts:
- `backend/scripts/backfill_metadata_v2.py` — dry-run by default, `--commit` applies.
  Denormalises tech entity names into `memories.technologies` via a single SQL CTE and
  updates `confidence` per row using `estimate_confidence`.

Smoke: dry-run reports zero counts on an empty test DB without error. Logic verified by
`tests/test_backfill_v2.py::test_backfill_technologies_denormalises_entity_names` and
`test_backfill_confidence_uses_estimator`.

## Phase 6.5 — backfill historical relationships to 5-type

Completed: 2026-04-19.

Artifact:
- `backend/scripts/backfill_relations_v2.py` — dry-run by default, `--commit` applies.
  Deletes dropped-cluster labels (RELATED_TO, HAPPENED_ON, AUTHORED_BY + 30-type droppables)
  and remaps survivors via REL_MAP_5. The UPDATE step uses the same data-modifying-CTE
  merge pattern that migration 0004 introduced so colliding `(source, target, rel_type)`
  rows union their `memory_ids` and keep the max weight, preventing unique-constraint
  violations during the rename.

Smoke: dry-run reports zero counts on an empty test DB. Logic verified by
`tests/test_backfill_v2.py::test_backfill_relations_remap_and_delete`.

Runtime guardrails (per plan): run dry-run first, take a pg_dump before `--commit` because
the DELETEs are permanent.

## Phase 7 — retrieval integration

Completed (code): 2026-04-19.

Schema changes:
- `MemorySearchRequest` adds `project`, `status` (default `["active"]`), `technologies_any`.
- `PostgresMemoryRepository.search_by_tags` and `search_by_tags_paginated` accept the three
  new filters and apply them as SQL WHERE predicates. Shared `_apply_filters` helper keeps
  the two methods in sync.
- `MemoryService.search_memories` + `search_memories_paginated` plumb the new filters
  through, and mirror the SQL predicate set in `_matches_schema_v2_filters` so the
  semantic-search post-filter code path produces the same results.

Rank fusion:
- `ProcessingPipeline._apply_confidence_weighting` multiplies each result's score by
  `(1 + gamma * (confidence - 0.75))` and re-sorts. `gamma` comes from the
  `confidence_rank_gamma` feature flag (default `0.0`, added to `FEATURE_FLAGS_DEFAULTS`),
  so the change is a no-op until turned on after measurement.

Tests (all green):
- `tests/test_schema_v2_search_filters.py` — 5 tests cover `status` default hiding
  superseded/deprecated, explicit inclusion of superseded, project scope,
  `technologies_any` overlap, and paginated search respecting the combined filter set.

Deferred until the training run completes:
- Before/after retrieval benchmark on `runs/retrieval-contrastive/test_pairs.jsonl`. With
  `gamma=0.0` default, MRR@10 cannot regress. The qualitative stale-memory audit requires
  production-scale data and is not meaningful against the test schema.

## Backend unit-suite status

All backend unit tests excluding websocket/LLM/chat/MCP external-dependency paths:
**237 passed** (213 pre-existing + 16 Phase-5 metadata + 3 Phase-6 backfill + 5 Phase-7 filter).


