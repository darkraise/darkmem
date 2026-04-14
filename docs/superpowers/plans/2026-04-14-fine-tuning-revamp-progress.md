# Fine-Tuning Revamp — Progress Tracker

**Plan:** `docs/superpowers/plans/2026-04-14-fine-tuning-revamp.md`
**Spec:** `docs/superpowers/specs/2026-04-14-fine-tuning-revamp-design.md`
**Branch:** `feat/architecture-overhaul`
**Started:** 2026-04-14

## Current scope

Subagent-driven execution of the 19 pure-code preparation tasks. Corpus generation (Tasks 15–19, 20), training (22–25), evaluation execution (31), and deployment (32–33) are deferred pending user decision after this phase lands.

## Phase A — Configuration and validation infrastructure

| Task | Status | Commit | Notes |
|---|---|---|---|
| 1 — Taxonomy config | pending | — | |
| 2 — Training hyperparameter config | pending | — | |
| 3 — qwen3.5:4b prompt config | pending | — | |
| 4 — Validator tests (red) | pending | — | |
| 5 — Validator implementation | pending | — | |

## Phase B — Audit and absorb scripting

| Task | Status | Commit | Notes |
|---|---|---|---|
| 6 — Audit script tests (red) | pending | — | |
| 7 — Audit script implementation | pending | — | |

## Phase C — Split builder and converters

| Task | Status | Commit | Notes |
|---|---|---|---|
| 10 — build_splits tests (red) | pending | — | |
| 11 — build_splits implementation | pending | — | |
| 12 — Converter tests (red) | pending | — | |
| 13 — Converter implementations | pending | — | |

## Phase D — HANDOFF bootstrap

| Task | Status | Commit | Notes |
|---|---|---|---|
| 14 — HANDOFF.md with schema, rules, first-batch template | pending | — | |

## Phase F — Evaluation harnesses (code only)

| Task | Status | Commit | Notes |
|---|---|---|---|
| 26 — qwen baseline runner tests (red) | pending | — | |
| 27 — qwen baseline runner implementation | pending | — | |
| 28 — Entity eval harness | pending | — | |
| 29 — Relation eval harness | pending | — | |
| 30 — Classifier eval harness | pending | — | |

## Deferred — requires human-driven generation or GPU time

| Task | Status | Why deferred |
|---|---|---|
| 8 — Run audit, write report | deferred | Depends on Tasks 1–7 landing; runs once on real data |
| 9 — Absorb passing rows | deferred | Follows Task 8 outcome |
| 15 — Generate shared batch-001 | deferred | Multi-session hand-written corpus work |
| 16 — Continue shared-base generation | deferred | Multi-session |
| 17 — Generate extraction top-up | deferred | Multi-session |
| 18 — Generate classification top-up | deferred | Multi-session |
| 19 — Generate retrieval top-up | deferred | Multi-session |
| 20 — Generate document stub | deferred | Single-session hand-written (~200 items) |
| 21 — Run build_splits.py | deferred | Needs corpus generated first |
| 22 — Train GLiNER-large + small | deferred | Long GPU run |
| 23 — Train REBEL-large + mREBEL-base | deferred | Long GPU run |
| 24 — Train 3 classifiers | deferred | GPU time |
| 25 — Train 2 embedders | deferred | GPU time |
| 31 — Run all evals + compile reports | deferred | Needs trained models |
| 32 — Deploy winners to backend | deferred | Needs winners |
| 33 — Archive old data and close out | deferred | Final step |

## Status legend

- `pending` — not started
- `in_progress` — subagent dispatched or active
- `review` — implementation done, reviewers running
- `completed` — implementation + both reviews approved, commit landed
- `blocked` — subagent reported a blocker
- `deferred` — outside current scope

## Session log

| When | What |
|---|---|
| 2026-04-14 | Spec committed (e68bf30). Plan committed (e99323d). Progress tracker created. Subagent-driven execution scoped to 19 infrastructure tasks. |
