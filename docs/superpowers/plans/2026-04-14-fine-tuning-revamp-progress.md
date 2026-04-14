# Fine-Tuning Revamp — Progress Tracker

**Plan:** `docs/superpowers/plans/2026-04-14-fine-tuning-revamp.md`
**Spec:** `docs/superpowers/specs/2026-04-14-fine-tuning-revamp-design.md`
**Branch:** `feat/architecture-overhaul`
**Started:** 2026-04-14

## Current scope

Subagent-driven execution of the 17 pure-code preparation tasks completed. Corpus generation (Tasks 15–19, 20), training (22–25), evaluation execution (31), and deployment (32–33) are deferred pending user decision.

## Phase A — Configuration and validation infrastructure

| Task | Status | Commit | Notes |
|---|---|---|---|
| 1 — Taxonomy config | completed | `ebedcc0` | 11 technical entities, 12 core relations verified |
| 2 — Training hyperparameter config | completed | `157cc7a` | entity/relation/classifier/embedding blocks |
| 3 — qwen3.5:4b prompt config | completed | `657e4c9` | frozen, temp 0.0, seed 42, json format |
| 4 — Validator tests (red) | completed | `4cfb8b9` | 11 tests, ImportError confirmed |
| 5 — Validator implementation | completed | `8f045a6` | 11/11 pass |

## Phase B — Audit and absorb scripting

| Task | Status | Commit | Notes |
|---|---|---|---|
| 6 — Audit script tests (red) | completed | `83ef102` | 3 tests, ImportError confirmed |
| 7 — Audit script implementation | completed | `01184d6` | 14/14 pass |

## Phase C — Split builder and converters

| Task | Status | Commit | Notes |
|---|---|---|---|
| 10 — build_splits tests (red) | completed | `9b28fa4` | 2 tests, ImportError confirmed |
| 11 — build_splits implementation | completed | `6b83283` | 16/16 pass, stratified by domain/memory_type |
| 12 — Converter tests (red) | completed | `11b33da` | 4 tests across 4 files, all red |
| 13 — Converter implementations | completed | `0be1f58` | 34/34 total pass; GLiNER uses char-span native format |

## Phase D — HANDOFF bootstrap

| Task | Status | Commit | Notes |
|---|---|---|---|
| 14 — HANDOFF.md + v2 dir tree | completed | `e6988aa` | 7 subdirs with .gitkeep, schema + prompts documented |

## Phase F — Evaluation harnesses (code only)

| Task | Status | Commit | Notes |
|---|---|---|---|
| 26 — qwen baseline runner tests (red) | completed | `c338f6a` | 3 tests, ImportError confirmed |
| 27 — qwen baseline runner implementation | completed | `dd69e83` | 37/37 pass, Ollama JSON mode |
| 28 — Entity eval harness | completed | `3a9b0b7` | smoke test OK (micro_f1=1.0) |
| 29 — Relation eval harness | completed | `e324707` | direction rate + exact match |
| 30 — Classifier eval harness | completed | `dce6c78` | includes reference_recall gating metric |

## Deferred — requires human-driven generation or GPU time

| Task | Status | Why deferred |
|---|---|---|
| 8 — Run audit, write report | deferred | Needs user go-ahead; runs once on real data |
| 9 — Absorb passing rows | deferred | Follows Task 8 outcome |
| 15 — Generate shared batch-001 | deferred | Multi-session hand-written corpus work |
| 16 — Continue shared-base generation | deferred | Multi-session (~35 sessions) |
| 17 — Generate extraction top-up | deferred | Multi-session (~6 sessions) |
| 18 — Generate classification top-up | deferred | Multi-session (~6 sessions) |
| 19 — Generate retrieval top-up | deferred | Multi-session (~6 sessions) |
| 20 — Generate document stub | deferred | Single-session hand-written (~200 items) |
| 21 — Run build_splits.py | deferred | Needs corpus generated first |
| 22 — Train GLiNER-large + small | deferred | Long GPU run |
| 23 — Train REBEL-large + mREBEL-base | deferred | Long GPU run |
| 24 — Train 3 classifiers | deferred | GPU time |
| 25 — Train 2 embedders | deferred | GPU time |
| 31 — Run all evals + compile reports | deferred | Needs trained models |
| 32 — Deploy winners to backend | deferred | Needs winners |
| 33 — Archive old data and close out | deferred | Final step |

## Test suite status

| Test file | Tests | Status |
|---|---:|---|
| test_validate_v2.py | 11 | passing |
| test_audit_existing.py | 3 | passing |
| test_build_splits.py | 2 | passing |
| test_convert_to_classifier.py | 1 | passing |
| test_convert_to_gliner.py | 1 | passing |
| test_convert_to_rebel.py | 2 | passing |
| test_convert_to_embedding_pairs.py | 1 | passing |
| test_eval_baseline_qwen.py | 3 | passing |
| **Total** | **24** | **all passing** |

Note: count above tracks the *new* tests added in this preparation phase. `pytest tests/ -v` after Task 13 reported 34 total (including a few pre-existing tests from prior work); after Task 27 the count rose to 37.

## Artifacts created this phase

**Config (3 files):**
- `fine-tuning/config/taxonomy_v2.yaml`
- `fine-tuning/config/training_v2.yaml`
- `fine-tuning/config/prompts_v2.yaml`

**Scripts (10 files):**
- `fine-tuning/scripts/validate_v2.py`
- `fine-tuning/scripts/audit_existing.py`
- `fine-tuning/scripts/build_splits.py`
- `fine-tuning/scripts/convert_to_classifier.py`
- `fine-tuning/scripts/convert_to_gliner.py`
- `fine-tuning/scripts/convert_to_rebel.py`
- `fine-tuning/scripts/convert_to_embedding_pairs.py`
- `fine-tuning/scripts/eval_baseline_qwen.py`
- `fine-tuning/scripts/eval_entity.py`
- `fine-tuning/scripts/eval_relation.py`
- `fine-tuning/scripts/eval_classifier.py`

**Tests (8 files):** corresponding test_*.py under `fine-tuning/tests/`.

**Data layout:** `fine-tuning/data/v2/{shared,extraction,classification,retrieval,documents,failed,splits}/` with `.gitkeep` + `HANDOFF.md`.

## Known deviation from plan

**Task 13 (`convert_to_gliner.py`):** plan specified token-level BIO format via `AutoTokenizer`; implementation uses char-level `{"text", "entities": [{start, end, label}]}` to match Task 12 test assertions. This is the `gliner-finetune` package's native format. The `--failed-dir` and `--base-model` flags and the 1%-failure-rate gate are preserved. The implementation is strictly simpler and functionally correct for GLiNER training.

## Session log

| When | What |
|---|---|
| 2026-04-14 | Spec `e68bf30`, plan `e99323d`, progress tracker `93cc134` committed. 17 infra tasks dispatched via subagents on haiku/sonnet. 37 tests passing. Handing back to user for next-phase decision. |

## Next decision points for user

1. **Run audit on existing corpora (Task 8)?** This surfaces per-source pass rates against the v2 schema and tells us whether to absorb or regenerate. Runs in minutes on existing data.
2. **Start corpus generation (Tasks 15–19)?** Multi-session hand-written work driven from `HANDOFF.md`. Each session produces 3–5 batches (~150–250 items). Total budget ~35–58 sessions across weeks.
3. **Defer everything and review the infrastructure first?** Run `cd fine-tuning && python -m pytest tests/ -v` to confirm the 37 passing tests locally before committing to the generation phase.
