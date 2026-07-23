# darkmem — Product-surface & self-organizing-knowledge requirements + harness-first proposal

**Date:** 2026-07-23 · Branch `feat/memory-graph-theming`.
Companion to the evolution plan (`docs/2026-07-22-darkmem-evolution-plan.md`, Parts I–IV) and its implementation notes / review.

**Status:** requirements capture + decomposition. Reviewed 2026-07-23 (see §0). The maintainer confirms the harness scope + domain model before any build.

---

## 0. Corrections from the Fable review (2026-07-23)

The companion `docs/2026-07-23-darkmem-product-surface-and-harness-review.md` verified this doc against source at file:line and corrected several load-bearing claims. Read it before acting. Material changes:

- **Sub-project A is frontend-led + a backend contract package, NOT "UI over the existing engine."** Verified blockers/highs: **(R1)** retrieval scores are computed but *dropped at every API boundary* (`_rrf_fuse` pops the per-modality key; `search_memories` rebuilds from ORM rows; `MemoryResponse` has no score field) — "why retrieved" needs a new backend **retrieval-trace payload**; **(R2)** the pipeline broadcasts *one terminal event per memory*, no start/progress events — the live stepper, "now processing" feed, and stalled-heartbeat need new `pipeline.started`/progress events; **(R3)** the analytics endpoint is 90-day-clamped and `MemorySearchRequest` has no date filter — the 365-day calendar + click-to-drill need small backend changes. Also: `find_duplicates` is per-memory (a hygiene queue needs a corpus-wide sweep that doesn't exist), and bulk "merge" needs the Phase-3 `supersede()` primitive — so wave-A hygiene actions scope to deprecate / extend-TTL / delete only.
- **Harness (R5):** add a **pipeline-boundary LLM cache** keyed `(content, prompt, gate-state)`, or fixture-tier iteration re-pays ~10³ extraction calls per loop. Build order: shared `benchlib` skeleton → LongMemEval fixture tier → `ui_fixtures` generator (walking skeleton per review §3.3).
- **Domain model (§3) resolved (pending maintainer confirmation):** topic = memory communities; knowledge = derived memory rows (`insight`/`profile` + `DERIVED_FROM` edges); personal-vs-knowledge-base = `project` namespaces. **No new "knowledge base" artifact** — that is Part-II Doc-3, firewalled until Phase 1's gate is green.
- **Minor:** inline memory edit backend already exists (`PUT /memories/{id}` + MCP `memory_update`) — only the UI is missing; the persisted reranker score is 0–1 normalized (not 0–10); the "entity-level event log" extends the existing memory-level `audit_logs`, not greenfield.

---

## 1. How we got here (session trail)

1. Researched the commercial product **1AIVault** and its category → appended **Part III (distribution/last-mile)** and **Part IV (product surface/design)** to the evolution plan.
2. Ran a lean 3-agent UX research pass (observability/explainability UIs; consumer memory-vault dashboards; pipeline-processing visualization patterns) → produced a feature menu grounded in real tools (Letta ADE, Zep, mem0, Supermemory, Obsidian, Pieces, RAGFlow, Dify, Temporal, Dagster, Bull Board, …).
3. Maintainer expanded scope from "UI over the existing engine" to a **self-organizing knowledge system**, and directed: (a) get a **Fable adversarial review**, and (b) **build a harness first**, grounded in the requirements + sub-projects (i.e. honor the plan's Phase-0 "measurement-first" directive before feature work).

Key grounding fact from the code audit this session: **darkmem already computes or broadcasts most of the data these features need.** The `pipeline.completed|partial|failed` websocket events carry per-phase status per memory (`embed`, `extract`, `vector`, `graph`) + entity/relation counts + error; hybrid search already computes `rrf_score`, per-modality `score`, and a 0–10 reranker score; `entities.memory_ids[]` encodes provenance; `memory_find_duplicates`, `confidence`, `created_at`, and the `active→superseded→deprecated` lineage all exist. **Correction (§0/R1–R3):** the data *shapes* exist, but the retrieval scores are dropped before the API boundary and the pipeline emits only a terminal event, so wave A is **frontend-led plus a named backend contract package** (retrieval-trace payload, pipeline start/progress events, date filters), not pure frontend work.

## 2. Requirements (maintainer asks)

### 2A. UI / observability wave (backend mostly ready)
- **Pipeline observability** — live 5-phase ingest stepper; a "now processing" feed; a failure-triage queue over `pipeline_failures` with one-click retry; a JobRegistry run board.
- **Retrieval explainability** — a per-result "why retrieved" panel (RRF, semantic-vs-keyword rank, rerank delta, confidence, entity-match).
- **Curation & hygiene** — a review queue (duplicates, low-confidence, expiring-soon, superseded lineage) with approve/dismiss + bulk keep/merge/deprecate/extend-TTL; provenance drill-down; ingest-decision badges; inline edit (backend `PUT`/`memory_update` exists — only the UI is missing).
- **Engagement** — a **memories contribution calendar** (GitHub-style; CONFIRMED: replace the Activity bar chart, hover tooltip + click-to-drill into that day's memories); daily/weekly capture digest; a "what darkmem knows about this project" profile page; star/bookmark.

### 2B. New capabilities (larger; a self-organizing knowledge system)
- **Event/operation tracking** across memory / knowledge / topic / project.
- **Auto-process memories → a knowledge base.**
- **A memory/knowledge timeline.**
- **Auto-evaluate & mark outdated** when a newer correction arrives.
- **Auto-research & arrange knowledge on request** into personal knowledge / a knowledge base.

### 2C. Where 2B already lives in the existing plan (reaffirm, don't redesign)
- "Auto-process → knowledge" and "mark outdated on correction" are the core of **Part I Phase 2** (bi-temporal + contradiction invalidation) and **Phase 3** (background consolidation, the mem0 four-op resolver mapped onto supersession, reflection→`insight` memories). darkmem's `active→superseded→deprecated` lifecycle + `expires_at` are the substrate.
- "Knowledge base / documents" overlaps **Part II** (blocks + block-embeddings + grounded citations).
- Genuinely NEW vs the plan: a first-class **topic** unit, a **knowledge tier distinct from raw memory**, a **personal-knowledge vs shared-knowledge-base** split, an **entity-level event/audit log**, and an **auto-research→KB agent**.

## 3. Open keystone — the domain model

darkmem today has: `memories`, `entities`/`entity_relations` (not memory-scoped, `memory_ids[]` provenance), `tags`, and a `project` scope. It has **no "topic" unit and no "knowledge" artifact separate from a memory**. The maintainer's 2B asks repeatedly say "memory / knowledge / topic / project" and "personal knowledge or knowledge base." Whether "knowledge base" is a genuinely new layer or a reuse of `project` scoping **changes the whole architecture**. This is the fork that gates sub-projects B, C, D-surfacing, and E. Candidate models to evaluate:
- **A. Layered refinement:** memories → auto-grouped by topic → synthesized into knowledge → organized into a KB (shared) vs personal knowledge (private). Knowledge is a derived, maintained artifact.
- **B. Tag/scope reuse:** knowledge == memory rows; topic == a tag/cluster; personal-vs-KB == `project` namespaces. No new artifact; cheapest.
- **C. Documents/wiki:** knowledge lives as Part-II blocks/pages built from memories; topics == pages; KB == the wiki.

## 4. Sub-project decomposition

| ID | Sub-project | Depends on | Maps to plan | Notes |
|---|---|---|---|---|
| **A** | Observability & dashboard wave (§2A) | SQL pushdown + backend contract package (R1 trace, R2 events, R3 dates, dup sweep) | Part IV.1–3, Phase 5 | frontend-led + a named backend contract package (see §0); NOT pure UI |
| **B** | Event tracking & knowledge timeline | **C** | Part IV, Phase 5 | per-entity activity log + timeline |
| **C** | Knowledge-organization model (topic / knowledge / personal-vs-KB) | — (keystone) | new (touches taxonomy) | gates B, D-surfacing, E |
| **D** | Auto-processing & self-maintenance (auto-consolidate, auto-outdated) | Phase 0 harness | **Phase 2 + Phase 3** (already planned) | reaffirm, don't redesign |
| **E** | Auto-research → KB agent | **C** | new (reuses extraction + deep-research pattern) | "research on request, file into KB" |

**Proposed order (pre-harness):** A (ready, independent) → C (the model) → B + E; D delivered by Phase 2/3. Maintainer chose to design **A** first — now parked behind the harness per §6.

## 5. Wave-A design so far (captured — Section 1 only)

- **Scope:** all four §2A buckets + calendar, as independently-buildable components (build order sequenced in the plan).
- **Information architecture** (sidebar is 7 items / 3 groups; websocket already wired app-wide in `_authenticated.tsx`; pipeline/maintenance currently live as Settings tabs; no inline memory-edit UI exists):
  - **Dashboard (`/`)** — contribution calendar (replaces Activity bar chart) + a compact "Processing now" strip → links to
  - **New `/activity` route** (Workspace group) — live 5-phase stepper feed, failure-triage queue with retry, JobRegistry run board (promotes jobs/failures out of Settings). Sidebar 7→8.
  - **Memories (`/memories`)** — "why retrieved" expansion, ingest-decision badges, provenance drill-down, inline edit, calendar date-filter click-through.
  - **Hygiene queue** — a tab on `/activity`.
- **Open fork:** new `/activity` route (recommended) vs folding observability into Settings tabs (keeps sidebar at 7, but buries the "watch it process" experience).
- **Design rules from the research (bake in):** pair every status color with an icon/label (color-only isn't colorblind-safe); give each in-flight phase a timeout/heartbeat so a stalled memory shows a "stalled" state, not a permanent spinner.

## 6. Harness-first proposal (the item to pressure-test)

**Rationale.** The evolution plan's Phase 0 is already "measurement first — port LongMemEval, record baselines, nothing ships without a before/after number." The maintainer is extending that discipline to this new work: **before building features, build the harness that defines and checks each sub-project's success criteria.** This doc's §2 requirements + §4 sub-projects are the basis for those criteria.

**Candidate harness scope (for Fable + maintainer to confirm / cut):**
- **Engine/knowledge eval (extends Phase-0 LongMemEval).** Retrieval: recall@k / nDCG, knowledge-update, temporal, abstention slices. New-capability metrics derived from §2B: **outdated-marking precision/recall** on a curated "newer-correction" test set; **consolidation dedup-rate without recall loss**; **auto-research groundedness/faithfulness**. Keep `extraction_bench` green as a co-gate.
- **Pipeline / throughput.** p95 ingest latency, per-phase timings, failure rate — these ALSO become the observability wave's own displayed metrics (build once, use twice).
- **UI harness.** Frontend unit (vitest) + E2E (Playwright, already present as `tests/`) for wave-A surfaces, plus a **fixture generator that drives deterministic pipeline activity** so the observability UI can be built and verified without a live ingest load.
- **Affordability protocol (from the plan, mandatory):** pinned judge model + seeds; fixture / `_oracle` / full-500-at-gates tiers with a stated token+wall-clock budget; ingest via `process_batch` offline, not the sync API; freeze the ingestion-granularity decision once.

**Open decisions for the review:**
1. Which face of the harness comes first — the **engine/knowledge eval foundation** (Phase 0 proper, gates C/D/E and the whole plan) vs the **UI test + activity-fixture scaffold** (what wave A needs to be built and verified)?
2. How much of the §2B new-capability eval (outdated-marking, consolidation, auto-research) to define **now** vs after the §3 domain model (C) lands and makes those metrics concrete?
3. Does the harness stay a single `backend/scripts/*_bench/` family (mirroring `extraction_bench`), or split eval-harness from UI-test-harness?

## 7. Next actions

1. ✅ **Fable adversarial review complete** — `docs/2026-07-23-darkmem-product-surface-and-harness-review.md` (summarized in §0).
2. Confirm with the maintainer: the §4/§0 **domain-model hybrid**, and the **harness walking-skeleton scope**.
3. **Build the walking skeleton** (review §3.3): `benchlib` + LongMemEval fixture tier + pipeline-boundary LLM cache + `extraction_bench` co-gate + `curation_bench` green on current supersession; record the granularity decision in `FROZEN.md`.
4. **Spec the wave-A backend contract package** (retrieval trace, pipeline start/progress events, date filters, clamp lift, duplicates sweep) alongside Phase 0's SQL pushdown + entity-match arm.
5. Land the **taxonomy edits + vocabulary sweep** for the domain model, then resume wave-A design → spec → plan.

*Sources for the feature menu (2026-07-23 lean 3-agent UX research pass): Letta ADE (context-window viewer, memory blocks), Zep/Graphiti (temporal graph, named reranker signals, episodes/provenance, fact ratings), mem0 (server dashboard, memory-history audit), Supermemory (graph, Spaces), ChatGPT/Claude memory management, Obsidian (contribution-graph plugin, local graph/backlinks), Pieces (activity timeline, roll-ups), Rewind/Limitless (recap, bookmarking); pipeline-viz: RAGFlow, Dify, LangGraph Studio, Prefect, Temporal, Arize Phoenix/LangSmith, Airflow, Dagster, n8n, Celery Flower, Bull Board, Sidekiq, LlamaCloud. Vendor self-report where noted; treat as directional.*
