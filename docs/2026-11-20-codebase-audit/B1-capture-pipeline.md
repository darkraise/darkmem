# B1 — memory capture and the ingestion pipeline

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**Counts:** 2 high, 6 medium, 7 low, plus dead-code items. I found no path that loses a buffered row or processes it twice.

**Three most important findings:**
1. **High: any extraction failure wipes the memory's graph.** `extract()` turns every error (outage, 429, timeout, bad JSON) into an `_error` result (`services/extraction.py:131-151`). The pipeline calls that "partial" and enters savepoint B anyway (`services/pipeline.py:515, 671`). On re-extraction this deletes the prior graph, empties `technologies` and withdraws all fact sources (`pipeline.py:695, 799`). The buffer then marks the row done and never retries it (`buffer_flush.py:156`). The test that should catch this stubs `extract` to raise, which production never does (`tests/test_pipeline_savepoints.py:135-137`).
2. **High: merge can fail or delete data.** `merge_memories` deletes the source without demoting memories it superseded, so the CHECK fails and the request returns 500. Merging a memory into itself deletes it (`services/memory.py:918-965`).
3. **Medium: concurrent writes conflict.** Phase 5 writers lock shared entity rows in arbitrary order, so deadlocks are plausible (`pipeline.py:708-745`). `detect_supersessions` also re-points memories that are already superseded, so the last writer wins (`services/supersession.py:198-202`).

**Other medium findings:**
- Per-memory `= ANY(memory_ids)` predicates cannot use the GIN index, so every write does several full table scans (`repositories/graph.py:582, 593, 907`).
- `wait_process` cancels the flush at its 10s deadline, which strands the row for about 5 minutes and wastes the model spend.
- The reprocess and failure-retry routes are not refused in read-only mode, so the backup worker can spend on DeepSeek.

**Dead code:** `entity_registry.py` and `entity_detector.py` (731 lines) and `ml_seed.py` (28 lines) have no importers. The `classifier_kind=local` path, built on `classification_ml.py` and `ml_runtime.py`, cannot run because torch is not in `requirements.lock`.

---

- **B1-1** (high, bug, confirmed). Every extraction failure (outage, 429, timeout, bad JSON) comes back as an `_error` result the pipeline labels "partial", which enters savepoint B, strips the prior graph, empties `technologies`, withdraws all fact sources, and makes the buffer mark the row done and never retry it; the test that should catch this stubs `extract` to raise, which production never does. Remedy: Map `_error` to `extract="error"` so savepoint B is skipped, split transient from deterministic failures and make transient ones a hard step the buffer retries, and rewrite the test to drive the real `ExtractionService` against a failing LLM. Where: backend/app/services/extraction.py:131-151; backend/app/services/pipeline.py:511-517, 671, 695, 757-759, 799; backend/app/services/fact_provenance.py:289-307; backend/app/services/buffer_flush.py:156-158; backend/tests/test_pipeline_savepoints.py:135-137, 373-394

- **B1-2** (high, bug, confirmed). `merge_memories` deletes the source without `demote_dependents`, so merging any source that superseded another memory fails the CHECK with a 500, and a merge whose target is the source itself deletes the memory and then returns 500. Remedy: Refuse `target_id == memory_id` with a 422, and before the delete either demote the dependents or point their `superseded_by` at the target. Where: backend/app/services/memory.py:918-965; backend/app/api/routes/memories.py:364-376; backend/app/schemas/memory.py:254-255; backend/app/repositories/relational.py:97-103

- **B1-3** (medium, bug, plausible). Up to `pipeline_concurrency` Phase 5 sessions upsert shared entity and relation rows in extraction order and hold the locks until commit, which is the same deadlock class `bulk_delete_memories` already documents; each deadlock becomes a `graph_write` failure that forces a full LLM re-run. Remedy: Sort entities by (name, type) and relations by (source, target, type) before writing in savepoint B. Where: backend/app/services/pipeline.py:708-745, 1197-1212; backend/app/repositories/graph.py:157-185, 228-248; backend/app/services/memory.py:461-466

- **B1-4** (medium, bug, confirmed). The supersession UPDATE has no `status='active'` predicate, so two concurrent writers re-point an already-superseded memory, the last commit wins `superseded_by`, and a second `superseded` event is journalled with a false `before: active`. Remedy: Add `status == 'active'` plus `RETURNING id` to the UPDATE and journal only the returned ids. Where: backend/app/services/supersession.py:193-218; backend/app/services/pipeline.py:1197-1212

- **B1-5** (medium, performance, confirmed). Predicates written as `:mid = ANY(memory_ids)` cannot use the GIN index, so every memory write does at least four full scans of `entities` / `entity_relations`. Remedy: Rewrite them as `memory_ids @> ARRAY[CAST(:mid AS uuid)]` and pin the plan with an EXPLAIN test. Where: backend/app/repositories/graph.py:582, 593, 907, 920; backend/app/services/fact_provenance.py:175; backend/migrations/versions/0001_baseline.py:265, 288

- **B1-6** (medium, weak-assumption, confirmed). At its 10-second deadline `wait_process` cancels the in-flight flush, leaving the row claimed for at least 300 s, charging an attempt, and discarding the LLM spend. Remedy: On the deadline return the ack and let the flush finish as a tracked background task on its own session. Where: backend/app/services/wait_process.py:78-91; backend/app/services/memory.py:313; backend/app/services/buffer_flush.py:124

- **B1-7** (medium, security, confirmed). The reprocess and pipeline-failure retry routes are not refused in read-only mode, so on the backup worker they send the corpus to the embedder and DeepSeek before the writes fail. Remedy: Add `Depends(refuse_when_read_only)` to all four routes and update the read-only list in CLAUDE.md. Where: backend/app/api/routes/analytics.py:29-55; backend/app/api/routes/pipeline_failures.py:97-252; backend/app/main.py:175

- **B1-8** (low, bug, confirmed). If the same-batch reconciliation SELECT or commit raises, the `_process_batch` backstop overwrites every already-committed status with vector and graph errors, which causes false failure rows and a full re-run. Remedy: Give the reconciliation block its own try/except that logs and keeps `normalized`. Where: backend/app/services/pipeline.py:899-917, 1230-1271

- **B1-9** (low, bug, confirmed). `wait_process` returns 201 with an unprocessed memory for a capture whose replay hard-failed and was released back to pending. Remedy: Base the 201 decision on `ClaimedFlushResult.done` and return the ack otherwise. Where: backend/app/services/buffer_flush.py:967-969; backend/app/services/memory.py:251-274; backend/app/api/routes/memories.py:152-154

- **B1-10** (low, ui-ux, confirmed). Discarding an `error` buffer row leaves its already-materialized memory live with no vector or graph and nothing left to retry it. Remedy: Delete the memory through `MemoryService.delete_memory` when it exists, or tell the operator in the response that it survives. Where: backend/app/services/buffer_monitor.py:256-291; backend/app/services/buffer_flush.py:826-835

- **B1-11** (low, redundancy, confirmed). The retry/reprocess entry dict is built in three places, and two of them omit `project`, so retried ingests are billed with project NULL. Remedy: Build entries in one shared helper used by all three sites. Where: backend/app/api/routes/pipeline_failures.py:35-55; backend/app/main.py:210-229; backend/app/services/analytics.py:62-73

- **B1-12** (low, redundancy, confirmed). `pipeline._get_feature_flags` duplicates `feature_flags.get_feature_flags_dict`. Remedy: Delegate to `get_feature_flags_dict` and repoint both callers. Where: backend/app/services/pipeline.py:35-45; backend/app/api/routes/reembed.py:47; backend/app/services/analytics.py:103

- **B1-13** (low, bug, confirmed). A caller-supplied `importance` is always overwritten by the extractor's value (0.5 on any failure), while `memory_type` lets the caller win. Remedy: Fill importance only when the caller left the default. Where: backend/app/services/pipeline.py:638-642; backend/app/services/buffer_flush.py:136-143; backend/app/schemas/memory.py:62

- **B1-14** (low, doc-drift, confirmed). `ProcessingPipeline._apply_rank_fusion_factor` is a wrapper only tests call, yet CLAUDE.md names it as the consumer of `confidence`. Remedy: Delete the wrapper, point the tests at `HybridSearchService.apply_rank_fusion_factor`, and fix the sentence in CLAUDE.md. Where: backend/app/services/pipeline.py:1391-1417; backend/tests/test_rrf_fusion.py:352-447; CLAUDE.md Domain model `confidence`

- **B1-15** (low, design-critique, confirmed). torch and transformers are not in `requirements.lock`, so `classifier_kind=local` silently falls back to the LLM classifier in every shipped image, and the pyproject comment still refers to a regex classifier and an ML Profiles tab that no longer exist. Remedy: Remove the local path (about 300 lines plus 3 test files, an owner decision because `classifier_kind` is in the contract), or ship the extra and refuse `local` at config save when it is absent. Where: backend/app/services/pipeline.py:97-121, 234-275; backend/app/services/classification_ml.py; backend/app/services/ml_runtime.py; backend/app/main.py:673-679; backend/pyproject.toml:95-102; backend/requirements.lock

- **B1-16** (low, dead-code, confirmed). These 731 lines have no importer outside each other (only eval scripts and markdown mention them). Remedy: Remove both files. Where: backend/app/services/entity_registry.py; backend/app/services/entity_detector.py

- **B1-17** (low, dead-code, confirmed). Nothing imports this 28-line module, and it seeds the `ml_profiles` table, which has been dropped. Remedy: Remove it. Where: backend/app/services/ml_seed.py

- **B1-18** (low, dead-code, confirmed). The `isinstance(extraction, Exception)` branch and the `except` in `run_extract` cannot be reached, because `extract()` never raises. Remedy: Remove them, or make them reachable as part of finding 1. Where: backend/app/services/pipeline.py:507-510, 1022-1023

- **B1-19** (low, over-complexity, confirmed). A 116-name `__all__` plus a star re-export exist only so tests and scripts can import private pass helpers from `app.services.extraction`; every pass itself is live through `PASS_REGISTRY`. Remedy: Drop the shim and repoint about 10 test modules and 3 scripts at `extraction_clean`. Where: backend/app/services/extraction_clean.py:2336-2452; backend/app/services/extraction.py:11-19

- **B1-20** (low, dead-code, confirmed). `EXTRACTION_SCHEMA` is used by one eval script only. Remedy: Have the script call `_build_extraction_schema()` and remove the constant. Where: backend/app/services/extraction_clean.py:138; backend/scripts/eval_round3/debug_clean.py:25

- **B1-21** (low, redundancy, confirmed). `_MAX_CONTENT_CHARS = 6000` is declared twice and is also reused as the reasoning context budget, which ties two unrelated limits together. Remedy: Declare it once and give reasoning its own named budget. Where: backend/app/services/extraction_clean.py:29; backend/app/services/classification_llm.py:13; backend/app/services/memory.py:893-895

- **B1-22** (low, over-complexity, confirmed). `buffer_wait_timeout_seconds` is a flag the API cannot set and nothing bounds, so it is a constant in practice. Remedy: Make it a module constant, or add it to `FeatureFlagsUpdate` with an upper bound below the claim-visibility window. Where: backend/app/services/memory.py:313; backend/app/api/routes/config.py:417-439; backend/app/config.py:287

Not opened: services/embedder_registry.py, services/reembed.py, api/routes/reembed.py, api/routes/pipeline.py, services/pipeline_aggregator.py (body), services/confidence.py, services/stated_expiry.py, services/relations.py, services/classification_areas.py, services/extraction_pass_harness.py, repositories/memory_relations.py, the bodies of classification_ml.py / ml_runtime.py / entity_registry.py / entity_detector.py (importers only), extraction_clean.py pass bodies (lines 140-2135), and repositories/relational.py apart from `delete` and `get_predecessors`.
