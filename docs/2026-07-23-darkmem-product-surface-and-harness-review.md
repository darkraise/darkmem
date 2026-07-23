# Adversarial Review — Product-Surface & Harness-First Requirements (2026-07-23)

**Reviewer:** Fable adversarial pass. **Target:** `docs/2026-07-23-darkmem-product-surface-and-harness-requirements.md`, verified against `backend/app` + `frontend/src`, the evolution plan v2, impl-notes §0.4, and the 2026-07-22 review ledger. Every load-bearing claim was checked at file:line rather than trusted.

---

## 1. Verdict

**Conditionally sound — the decomposition and sequencing are right, but the doc's central grounding claim ("most of the UI wave is frontend-only work") does not survive contact with the code.** Retrieval scores are computed and then dropped at every API boundary; the pipeline emits exactly one terminal websocket event per memory (no start/progress events, making the "live stepper" and the doc's own stalled-heartbeat rule unimplementable as specified); the calendar's data source is clamped to 90 days; and there is no date filter, no corpus-wide duplicate sweep, and no merge primitive. Sub-project A is therefore "frontend-led with a named backend contract package," not "UI over the existing engine." Harness-first is the correct call — it is Phase 0's standing directive and both C/D/E and the plan's Phase 0 gates require it — with one guard: the wave-A face of the harness is fixtures + contract tests, not eval science, and must not be inflated into a second LongMemEval.

## 2. Claim audit

| # | Doc claim | Status | Evidence |
|---|---|---|---|
| 1 | WS events carry per-phase status (`embed/extract/vector/graph`) + counts + error | **PARTIAL** | Shape confirmed (`frontend/src/lib/websocket-events.ts:1-10`; `backend/app/services/pipeline.py:497-508`) — but it is a **single terminal event per memory**; the only pipeline broadcast sites are pipeline.py:508 and :842 (`memory.deleted`). No `started`/per-phase/progress events exist. A "live 5-phase stepper" and "now processing" feed cannot be built from what's broadcast today. |
| 2 | Hybrid search "already computes `rrf_score`, per-modality `score`, and a 0–10 reranker score" | **PARTIAL → functionally REFUTED for the UI** | Computed: `hybrid_search.py:174-196`, `reranker.py:80-91`. But (a) `_rrf_fuse` **pops the `source` key** and discards per-modality ranks (`hybrid_search.py:180,193`); (b) `search_memories` rebuilds results from ORM rows, discarding all scores (`backend/app/services/memory.py:252-258`); (c) `MemoryResponse` carries no score field — only `confidence` (`backend/app/schemas/memory.py:36-58`); (d) MCP `memory_search` uses the same path (`backend/app/api/mcp/server.py:173-180`); (e) rerank score is normalized to 0–1 (`reranker.py:82-86`), pre-rerank rank isn't preserved, so "rerank delta" has no data. Only `reason()`'s `sources` and `code_search` expose any score. **"Why retrieved" is a backend feature.** |
| 3 | `pipeline_failures` + one-click retry | **CONFIRMED** | `backend/app/api/routes/pipeline_failures.py:99-260` — 202-async single + bulk retry, per-failure locks, `pipeline.retry_batch.progress` WS events; frontend consumer `frontend/src/features/pipeline/MaintenancePanel.tsx`. |
| 4 | JobRegistry run board data available | **PARTIAL** | `GET /api/v1/jobs` returns per-job `last_run_at/last_status/last_error` **snapshot only** (`backend/app/api/routes/jobs.py:29-33,150-152`); no run-history table (that's plan Phase 4). |
| 5 | Inline edit: "none exists today — only create + delete" | **PARTIAL — misleading in §2A, accurate in §5** | Backend `PUT /memories/{id}` exists with content-change re-extraction (`routes/memories.py:76-77`; `services/memory.py:103-127`) + MCP `memory_update` (mcp/server.py:199-221). Only the **UI** is missing. |
| 6 | `extraction_bench` cache-and-iterate shape | **CONFIRMED** | `backend/scripts/extraction_bench/run_bench.py:1-13,67-75` — LLM output cached per `sha256(content+system_prompt)`, `--algo-only` re-scores instantly. |
| 7 | Analytics per-day activity + 90-day clamp | **CONFIRMED — refutes calendar reuse** | Aggregation `backend/app/services/analytics.py:188-200`; clamp `max(1, min(days, 90))` `backend/app/api/routes/analytics.py:114`. |
| 8 | Sidebar 7 items / 3 groups; WS wired app-wide | **CONFIRMED** | `frontend/src/routes/_authenticated.tsx:27-48,72`. |
| 9 | `memory_find_duplicates`, `confidence`, lineage exist | **CONFIRMED — scope caveat** | `services/memory.py:304-307`; `schemas/memory.py:58`. `find_duplicates` is **per-memory**; a hygiene queue needs a corpus-wide sweep that doesn't exist. |
| 10 | Calendar "click-to-drill into that day's memories" | **REFUTED as frontend-only** | `MemorySearchRequest` has no `created_after/created_before` (`schemas/memory.py:68-81`). |

## 3. The harness

### 3.1 The three open decisions
**Decision 1 — order:** **Eval-foundation first, via a shared skeleton that serves both faces.** Both faces reduce to the same core: a pinned-seed corpus + DB reset + offline `process_batch` ingest driver. Build that shared layer (`benchlib`) first, stand the LongMemEval fixture tier on it (Phase 0 proper), and derive the UI activity-fixture generator from the same driver as the third deliverable. Wave-A *design* resumes as soon as the backend contract package (R1–R3) is specified — it does not wait for full-500 baselines.

**Decision 2 — how much §2B eval now:** **Define D's metrics now; define E's metric shape now and its dataset after C; defer B to contract tests.** Outdated-marking precision/recall runs against today's `detect_supersessions`. Consolidation dedup-rate operates on memory rows. Auto-research groundedness needs C — but if C adopts knowledge = derived memory rows + `DERIVED_FROM` edges, the metric shape (claim-level support vs linked evidence + citation coverage, pinned judge) is definable today; stub the dir, defer the dataset.

**Decision 3 — single family vs split:** **Split by toolchain, unify by convention.** Engine evals are `backend/scripts/*_bench/` siblings sharing `benchlib` + one results-ledger format. The UI harness stays vitest + `frontend/tests/` Playwright, consuming a backend fixture script. `benchlib` prevents three forked copies of ingest code.

### 3.2 What it measures, per sub-project

| Sub-project | Instrument | Metrics | Dataset |
|---|---|---|---|
| Engine (gates everything) | `longmemeval_bench` | recall@k / nDCG, per-qtype (knowledge-update, temporal, abstention), p95 latency, token cost, vs full-context | fixture-10 / `_oracle` / full-500 at gates (impl-notes §0.4) |
| **A** | contract tests + `ui_fixtures` + throughput probe | retrieval-trace schema pinned; event contract pinned; p95 ingest + per-phase timings (new instrumentation — status dict at pipeline.py:497 has outcomes, no timestamps) | deterministic seeded corpus + fault injection (failing LLM stub) to exercise `partial/failed` + retry |
| **D** | `curation_bench` | outdated-marking precision/recall of status flips; zero mutual-flips (regression from `debug_bidirectional_supersession`); `chk_superseded_has_pointer` never violated; dedup-rate without recall@k loss (ε-bounded) | ~30 curated correction pairs + negatives from CLAUDE.md gates (speculative markers, cross-project, >90-day, same-batch tie-break); seeded duplicate clusters |
| **C** | none — gate is a design doc + taxonomy diff + the metric definitions it unlocks | — | — |
| **E** | `research_bench` (stub now) | groundedness/faithfulness vs `DERIVED_FROM` evidence; citation coverage; pinned judge | after C |
| **B** | contract tests | every mutation emits an event; timeline reconstruction complete. A **memory-level** audit trail already exists (`audit_repo.log` at memory.py:113,126; read via `/analytics/pipeline-logs`) — B extends it to entity level | after C |

**Affordability (mandatory + one addition):** all of impl-notes §0.4 — pinned judge + seeds, three tiers, `process_batch` offline, granularity frozen once, `extraction_bench` co-gate. **R5 addition: port `extraction_bench`'s LLM cache to the pipeline boundary** — a caching orchestrator wrapper keyed `(content, prompt, gate-state)`. Even fixture-10 is ~10³ ingest LLM calls; without the cache the inner loop dies. `sha256(content)` seed forwarding makes cached replay sound.

### 3.3 Build sketch
```
backend/scripts/
  benchlib/            # shared: bench-DB reset (mirror conftest's darkmem_test discipline,
                       #   :5433, never the real DB), corpus loader, offline process_batch
                       #   runner, caching LLM wrapper, seed pinning, results ledger
  longmemeval_bench/
    fixtures/          # 10 checked-in instances
    ingest.py          # granularity decision recorded in FROZEN.md
    judge.py           # pinned judge purpose + seed
    run_bench.py       # --tier fixture|oracle|full
  curation_bench/
    corrections.json   # newer-correction pairs + negatives
    duplicates.json
    run_bench.py
  research_bench/      # metric spec + empty runner — stub until C
  ui_fixtures/
    seed_activity.py   # deterministic corpus + fault injection -> WS activity
frontend/tests/        # Playwright specs consume ui_fixtures
```
**Walking skeleton (first deliverable, green + cheap):** `benchlib` + `longmemeval_bench --tier fixture` end-to-end on 10 instances, run **twice** — the second run completes in minutes with ~zero ingest LLM calls (cache hit) — plus `extraction_bench` as co-gate from the same runner, plus `curation_bench` green against **current** supersession behavior. Proves DB isolation, offline ingest, judge pinning, caching, and the ledger before any feature work.

**Gates:** A — trace/event contract tests + Playwright over `ui_fixtures` + p95/phase timings. C — model doc + taxonomy diff + unlocked metric definitions. D — Phase 2/3 gates + `curation_bench` thresholds + `extraction_bench` green. E — groundedness ≥ threshold + citation coverage. B — event contract + timeline reconstruction.

## 4. Domain-model recommendation — hybrid B→A-lite; C firewalled in Part II
- **Topic = memory communities.** Reuse Phase 1's `CommunityDetector` generalization to the memory graph (`memory_communities`, impl-notes §1.4). Do **not** put topics into `entities` — they aren't extracted assertions and would pollute the closed `ENTITY_TYPES` fallback and the globally-unique `(name, entity_type)` key.
- **Knowledge = derived memory rows, not a new artifact class.** Phase 3 already commits to `insight`/`profile` memory types + `DERIVED_FROM` evidence edges. Everything is inherited free: lifecycle/supersession, TTL, retrieval, `memory_ids[]` provenance, the hygiene queue. This also makes E's groundedness metric definable now.
- **Personal vs knowledge-base = `project` namespaces** (consistent with review M3 "treat `project` as the tenancy unit").
- **Reject full A and C as wave-1 choices.** A maintained synthesized artifact with its own pages is Part II Doc-3 territory, deferred by the M8 firewall until Phase 1's gate is green.
- **Taxonomy-first obligations:** land `insight`/`episodic`/`procedural`/`profile` in `MEMORY_TYPES`; `DERIVED_FROM` in `RELATIONSHIP_TYPES` (resolve the `SUPPORTS` legacy alias, taxonomy.py:116); sweep `reason()` KNOWN_TYPES, the simple-7 extraction gate, UI filters; re-baseline.

## 5. Risks & corrections
- **R1 (Blocker).** Retrieval scores dropped at every consumer boundary; per-modality ranks never retained (`hybrid_search.py:180,193`; `memory.py:252-258`; `schemas/memory.py:36-58`; `mcp/server.py:179-180`). "Why retrieved" requires a backend retrieval-trace payload (per-modality rank, raw scores, `rrf_score`, pre/post-rerank position, confidence), contract-tested **before** the panel. Design it alongside Phase 0's entity-match arm so the schema doesn't churn twice — §2A's "entity-match" explain element refers to a signal that doesn't exist yet.
- **R2 (Blocker).** No pipeline start/progress events — one terminal broadcast per memory (pipeline.py:497-508). The live stepper, the "now processing" feed, and §5's stalled-heartbeat need at minimum a `pipeline.started` event (per-phase transitions/heartbeats to do it properly). Belongs in the backend contract package + `ui_fixtures` event contract.
- **R3 (High).** 90-day clamp (routes/analytics.py:114) blocks a 365-day heatmap; `MemorySearchRequest` has no date filter (schemas/memory.py:68-81). Both small, both backend.
- **R4 (High).** A's real dependencies: R1 trace, R2 events, R3 dates, a corpus-wide duplicates sweep (find_duplicates is per-memory), job run-history if the board shows runs (jobs.py snapshot-only), and no merge primitive (bulk "merge" needs M6's `supersede()`, Phase-3 machinery — wave-A hygiene actions must scope to deprecate / extend-TTL / delete). Reclassify A as frontend-led + a backend contract package.
- **R5 (High).** Harness omits the pipeline-boundary LLM cache that makes it affordable (§3.2). Without it, fixture-tier iteration re-pays ~10³ extraction calls per loop.
- **R6 (Medium).** E's row lacks the harness dependency D's has; E's gate is groundedness, which only the harness adjudicates.
- **R7 (Medium).** "Daily/weekly capture digest" and the "project profile page" are not backend-ready (no digest job; `profile` is a Phase-3 type). Move to post-Phase-3, or scope the profile page to existing aggregates (top entities/`technologies`/tags).
- **R8 (Medium).** `/activity` route is right, but must **move** `MaintenancePanel`, not duplicate it — two surfaces over the same `retry_locks`/failure state will drift.
- **R9 (Medium).** "Entity-level event/audit log" isn't greenfield — a memory-level audit trail exists (`audit_logs` at memory.py:113,126, read at routes/analytics.py:83-88). B extends that substrate.
- **R10 (Low).** "0–10 reranker score" — persisted `rerank_score` is max-normalized to 0–1 (reranker.py:82-86); rerank-delta needs the pre-rerank rank retained (part of R1).

**Part III/IV spot-checks:** the impl-notes' Part III/IV sequencing pointers hold. Additions: IV.1's `resolveGraphTokens` constraint should extend to the calendar's hover/drill states; III.1's marker-bounded write should get a `curation_bench`-style idempotency test (re-render twice → byte-identical block).

## 6. Recommended immediate next actions
1. **Correct the requirements doc:** §1 grounding + §4 A-row per the claim audit (R1–R4); reclassify A as frontend-led + a named backend contract package; fix §2A inline-edit + reranker wordings.
2. **Build the walking skeleton** (§3.3): `benchlib` + LongMemEval fixture tier with the pipeline-boundary LLM cache + `extraction_bench` co-gate + `curation_bench` green on current supersession. Record the granularity decision in `FROZEN.md`.
3. **Spec the wave-A backend contract package** (retrieval trace, pipeline start/progress events, date filters, clamp lift, duplicates sweep) as one reviewed contract doc — rides with Phase 0's SQL pushdown + entity-match arm.
4. **Adopt the §4 domain-model hybrid** and land the taxonomy edits + vocabulary sweep before any emitting feature.
5. **Ship `ui_fixtures` + the first Playwright spec** against the new events once the contract package lands, then resume wave-A design → spec → plan.
