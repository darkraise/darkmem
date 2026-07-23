# darkmem Evolution Plan — Competitive Re-Architecture

**Date:** 2026-07-22 · **v2 (remediated after adversarial review).**
**Scope mandate (from the maintainer):** ambitious re-architecture · target audience is an **open-source project** · address **all four** weakness axes — retrieval accuracy, feature breadth, UI/UX, performance/scale.
**Method:** two 4-agent cited competitive surveys + a 4-agent code audit of darkmem, then a 4-agent source-level study of the cloned reference repos, then a **Fable adversarial review** (`2026-07-22-darkmem-evolution-plan-review.md`) that verified every load-bearing claim against the code. Implementation detail lives in the companion `2026-07-22-darkmem-evolution-implementation-notes.md`.

> **v2 remediation summary (from the review):** the factual foundation verified, but three defects were corrected — (B1/B2/B3) the bi-temporal triple lifecycle broke `chk_superseded_has_pointer` and re-extraction idempotency and put an LLM on the ingest hot path; (M1) the "activate `knowledge_triples`" move is a **rebuild**, not a cheap activation (the service is untested LOCOMO demo scaffolding the orphan sweep actively deletes); (M8) Part II was scoped like a second product. This version fixes the framing, re-sequences (bi-temporal migration → Phase 2, not a first move), adds an eval cost budget, promotes the SQL filter pushdown to a named prerequisite, adopts a taxonomy-first rule, and firewalls Part II to Doc-0/1/2. Minor factual corrections (reranker concurrency, the 6000-char cap's scope, `importance` already populated, mem0's retreat) are applied inline.

---

## 1. Executive thesis

darkmem is not behind the field — it is **mispositioned relative to the assets it already owns.** Three facts drive this plan:

1. **darkmem pays for a knowledge graph on every ingest but never spends it on retrieval.** The entity/relationship graph powers only visualization and chat entity-expansion. Neither `memory_search` nor `memory_reason` does any graph traversal, multi-hop expansion, or graph-augmented ranking — the exact capability Zep/Graphiti, HippoRAG, LightRAG, and cognee are built around. There is even an empty `knowledge_triples` table + a `KnowledgeGraphService` in the tree — **but it is untested LOCOMO demo scaffolding (zero callers) whose stub writes the hourly orphan sweep actively reclaims, not a ready bi-temporal substrate.** Keeping the table name is free; building the temporal layer is real work (see Phase 2). The graph-for-retrieval reward, though, is genuinely uncollected.

2. **The field is splitting on *where* reconciliation happens, and darkmem sits on the side the leader is abandoning.** mem0's April-2026 rewrite **retreated from its famous write-time ADD/UPDATE/DELETE loop to single-pass append-only** — and, notably, mem0 OSS **dropped reconciliation entirely** (no background job; retrieval-time expiry + manual edits only). The systems that actually run background consolidation are **Letta (sleep-time agents), LangMem (ReflectionExecutor), A-MEM (evolution), and cognee (memify)** — that is the precedent to follow. darkmem's supersession is write-time, synchronous, and fires only on an explicit `REPLACES` relation — narrow, blocking, and on the losing side of this trend.

3. **darkmem has genuine, defensible moats the competitors lack** — and should lean into them, not just close gaps:
   - a ~2,150-line deterministic extraction post-processor (~40 tested cleanup passes) that hardens LLM output far past mem0/cognee defaults (F1 history: relations 0.64→0.96, entity name+type 0.68→0.93);
   - **per-embedder-fingerprint HNSW partitioning** — embedder rotation is first-class, which most competitors cannot do at all;
   - a **tree-sitter code knowledge graph** (blast-radius, communities, processes, rename) exposed over MCP — **no memory competitor has this**;
   - three live, theme-reactive graph visualizations — among the richest UIs in the category (mem0/cognee ship thin dashboards; Zep's graph UI is cloud-only and closed) — a comparative claim worth stating, though not independently benchmarked;
   - a single-Postgres/pgvector footprint that is *cleaner* than the category it is consolidating toward (OpenMemory was folded into a unified self-hosted mem0 server + dashboard — local-first, MCP+REST, close to darkmem's shape).

**The strategy in one line:** *Spend the graph darkmem already builds — for retrieval, for time, and for macro views — while moving reconciliation off the hot path, and measure every change against a real, affordable benchmark. Then package it for open-source adoption and surface the new power in the UI.*

**Prime directive — measurement first.** Every competitor's headline number is self-reported or contested (the mem0↔Zep LOCOMO dispute had each side recomputing the other's numbers downward; mem0 warns its SOTA is the *managed platform*, not the OSS SDK). darkmem has **no published benchmark at all.** An "ambitious re-architecture" without an eval harness is rebuilding on vibes. Phase 0 builds the harness — **and its affordability protocol** (§Phase 0) — and nothing else ships without a before/after number.

---

## 2. Competitive landscape — what to take, and from whom

All systems below are MIT or Apache-2.0 (code is liftable with attribution; the CC-BY-NC / GLiREL trap in darkmem's own history does **not** apply here).

| System | License | The one idea to take | Stack fit |
|---|---|---|---|
| **Graphiti** (getzep/graphiti) | Apache-2.0 | **Bi-temporal edges** (valid_at/invalid_at *world-time* + created_at/expired_at *system-time* + reference_time); **invalidate-don't-delete**; node-distance & episode-mentions rerankers | Algorithm ports to Postgres (do **not** adopt Neo4j) |
| **LightRAG** (HKUDS/LightRAG) | MIT | **dual-level retrieval** (local entity facts vs global relationship themes); incremental set-merge. NB: its Postgres graph backend *requires* Apache AGE — darkmem should use native SQL instead | High — Python/Postgres |
| **HippoRAG 2** (OSU-NLP-Group) | MIT | **Personalized PageRank** over the KG for multi-hop associative recall; synonymy-edge dedup; passage-as-node | Port PPR to in-process igraph |
| **mem0** (mem0ai/mem0) | Apache-2.0 | **Multi-signal retrieval** (semantic + BM25 + **entity-match**); **the append-only lesson** (it dropped reconciliation) | High — heed the retreat |
| **Memobase** (memodb-io) | Apache-2.0 | **Same stack (FastAPI+Postgres)**; **buffer/flush ingestion**; **event timeline** | Highest — largely liftable |
| **Letta / MemGPT** (letta-ai) | Apache-2.0 | **Sleep-time compute** (background consolidation); memory blocks; **ADE context-window viewer** (gold-standard observability UI) | Ideas + code; Postgres-backed |
| **cognee** (topoteretes) | Apache-2.0 | Ontology grounding + trust flag; temporal cognification; cross-doc coreference | High — Python, graph+vector |
| **LangMem** (langchain-ai) | MIT | **Memory-type taxonomy** (semantic/episodic/procedural); **ReflectionExecutor** debounced consolidation | Patterns; LangGraph-coupled |
| **A-MEM** (agiresearch/A-mem) | MIT | **Memory evolution** (a new memory rewrites neighbors' context/tags/links) | Prompts portable |
| **MemoryOS** (BAI-LAB) | Apache-2.0 | **Heat score** = f(visit frequency, interaction length, recency) → promotion/forgetting prior | Heat-update adaptable |
| **Generative Agents** (joonspk) | Apache-2.0 | The canonical **recency × importance × relevance** ranking; **reflection** | Design reference |
| **GraphRAG / nano-graphrag** | MIT | Hierarchical **community summaries** → global/thematic queries | Study; extend darkmem's Leiden |
| **Supermemory** (supermemoryai) | MIT | **User/project PROFILE** primitive; **self-expiring dated facts** | Study-only (TypeScript) |
| **LongMemEval** (xiaowu0162) | MIT | **The eval harness to adopt** — knowledge-update, temporal, abstention | Wire into backend/scripts |

**What the field agrees on (cross-cutting):**
- **Multi-signal retrieval** (vector + keyword + entity) is now table stakes. darkmem already fuses vector + FTS via RRF and stores entities + a lowercase `technologies` denorm — **adding entity-match is near-drop-in.**
- **Bi-temporal / event-timeline** is the clearest differentiator on temporal queries and darkmem's *latent* strength.
- **Background consolidation** is the biggest capability the *consolidating* leaders (Letta/LangMem/A-MEM) have and darkmem lacks — note the adoption leader (mem0) shipped none.
- **Don't chase LOCOMO** — small, defect-ridden, lacks knowledge-update questions. Adopt **LongMemEval** and always report **p95 latency + token cost + accuracy vs a full-context baseline**.

---

## 3. Gap analysis, mapped to the four axes

### 3.1 Logic / algorithms (retrieval accuracy)
| Gap | Evidence | Competitor answer |
|---|---|---|
| Graph unused in retrieval | search/reason are pure vector+FTS+LLM (verified) | HippoRAG PPR, LightRAG dual-level |
| Only 2 fusion signals | `hybrid_search.search` = semantic + keyword only (verified) | mem0 3-signal (add entity-match) |
| No recency/heat in ranking; `importance` populated but unread | `importance` written at ingest, never read by retrieval; `confidence_rank_gamma` defaults 0.0 | Generative Agents recency×importance×relevance; MemoryOS heat |
| Confidence is a regex placeholder | `confidence.py` keyword matcher | numeric per-relation confidence |
| Reranker LLM pointwise, off by default | 40 LLM calls/search (8-way concurrent, `Semaphore(8)`), uncalibrated 0–10 | cross-encoder / structural rerankers |
| Post-ANN filtering in Python | project/status filtered after the ANN probe → cross-project + superseded leakage | **push predicates into SQL (blocking prerequisite)** |
| No query understanding | single embedding + `plainto_tsquery('english')` | entity-linking, time-aware & fact-augmented expansion |

### 3.2 Flow / architecture (performance & scale)
| Gap | Evidence | Competitor answer |
|---|---|---|
| Blocking synchronous ingestion | `create_memory`/`batch_create` await the full pipeline inline | Zep 202-accept; Memobase buffer/flush |
| 6000-char cap on extraction/classification INPUT | `_MAX_CONTENT_CHARS=6000` truncates the LLM input only — storage, FTS, and embedding see full content; the gap is long tails missing from the **graph + classification** | chunking / episodic segmentation |
| No background consolidation | writes idempotent but never revisit old memories | Letta sleep-time, A-MEM evolution, LangMem ReflectionExecutor |
| Shallow single-timeline temporal model | supersession only, row-level, 90-day window; the triple layer is unwired demo code | Graphiti bi-temporal edges; cognee/Memobase timelines |
| Single-instance | in-process jobs/events/caches, host networking, no leader election | advisory-lock jobs, externalized event bus |
| No metrics/trace export | plain logging | standard observability |

### 3.3 Features (breadth vs peers)
| Gap | Evidence | Competitor answer |
|---|---|---|
| No multi-tenancy / scoping | single global namespace; **`entities` globally unique on `(name,entity_type)` with cross-project `memory_ids[]`** (a schema change, not plumbing) | mem0/Zep `user_id`/`agent_id`/`session_id` |
| `ApiKey` model unwired | every write passes `api_key_id=None` | programmatic API-key auth + scopes |
| MCP unauthenticated | LAN-trust only | optional bearer over streamable-HTTP |
| No client SDKs | REST/MCP only | mem0/Letta/Memobase ship Python+TS SDKs (**adoption-critical**) |
| Flat `memory_type` | 7 types, no episodic/procedural | LangMem semantic/episodic/procedural |
| No profile primitive | individual rows + graph only | Supermemory/Memobase profile; Letta blocks |
| No community/macro view over memory | Leiden runs on **code** graph only | GraphRAG/Graphiti community summaries |
| Native vendor adapters are stubs | all dispatch via OpenAI-compat → no Anthropic prompt caching, no failover, no persisted cost | real `/v1/messages`, failover, cost tracking |

### 3.4 UI / UX & design
| Gap | Evidence | Competitor answer |
|---|---|---|
| No retrieval explainability | backend has RRF/rerank/confidence signals; UI shows none | **Letta ADE context-window viewer** |
| No temporal/lifecycle/provenance view | one amber badge + related-memories list | Zep/Graphiti temporal story |
| No unified Insights page | `/analytics` `/vectors` `/graph` removed in slim-down | "what does my memory know" |
| `project` not a UI dimension | first-class in domain, absent in UI | project switcher/filter |
| Chat is secondary | floating overlay + side route | Letta ADE primary workspace |
| Hard-coded chart palette | 52 hex (32 in `index.tsx` + 20 in `source-colors.ts`) → break in light mode (verified) | tokenize via existing `resolveGraphTokens` |
| Dead/under-used assets | orphaned `src/demo/`, 3 Storybook stories, unmounted layout switcher (verified) | reap / document |

---

## 4. The roadmap

Six phases, each with a **goal**, changes tagged **[logic] [flow] [feature] [ui]**, **repos to study**, and an **eval gate**. Sequencing: measurement → cheap wins → graph-retrieval → temporal → consolidation → platform → UI. **Two named cross-phase dependencies** (from the review): (a) the **SQL filter pushdown** blocks Phases 1/3/4; (b) the **taxonomy-first rule** (§6) blocks any feature that emits a new relation/memory type.

### Phase 0 — Foundation & measurement *(prerequisite; low risk, high leverage)*
**Goal:** be able to prove — affordably — that every subsequent change helps, and clear the debts that block the re-architecture.
- **[flow]** Port **LongMemEval** (MIT) into `backend/scripts/longmemeval_bench/` (mirror `extraction_bench`). **Affordability protocol (required):** a **pinned judge model + seeds** (judge lives in `evaluate_qa.py`); **three tiers** — fixture (10 checked-in instances) for the inner loop, `_oracle` for reader isolation, **full-500 only at phase gates** with a stated token+wall-clock budget (full ingest is ~10⁴–10⁵ LLM calls); **ingest via `process_batch` directly** (offline), not the sync API; **freeze the ingestion-granularity decision once**; keep `extraction_bench` green as a co-gate. Record baselines (incl. a full-context baseline + p95 latency + token cost).
- **[logic] SQL filter pushdown (blocking prerequisite).** `HybridSearchService.search` takes no project/status/archived args today; add them to **both** channels, contract-tested. Phases 1/3/4 all assume this. (Fixes a real correctness bug: cross-project + superseded candidate leakage.)
- **[logic]** Add **entity-match as a third RRF signal** (mem0 parity) and the **fact-augmented `llm_summary` RRF arm** — reuse stored entities + `technologies` denorm; entity linking is string/`pg_trgm`/ANN, **not** an LLM call. Cheapest measurable wins.
- **[flow] Smoke-test — do not migrate — the triple path.** `knowledge_triples` is empty and its service is untested (its SQL has literally never run). Smoke-test asyncpg bind/CAST + the read-then-write race to satisfy "wire or delete" due diligence; the bi-temporal migration + rebuild belong in **Phase 2**, after a temporal metric exists.
- **[ui]** Quick wins: tokenize the dashboard/source-color palettes via `resolveGraphTokens` (fixes light-mode breakage); delete orphaned `src/demo/`.
- **Study:** LongMemEval, mem0 (retrieval fusion). **Gate:** harness runs green and affordable; entity-match + `llm_summary` arm show measurable recall lift or are reverted.

### Phase 1 — Spend the graph on retrieval *(the core experiment; [logic])*
**Goal:** turn the already-built entity graph into a retrieval signal — a **measured hypothesis**, not a certainty. A small, hub-dominated personal-dev memory graph may not beat RRF + `technologies` filtering; the Phase-0 harness decides before this ships on by default.
- **[logic]** **Graph-augmented retrieval channel (HippoRAG PPR):** the graph already exists — `entities` are phrase nodes, `memories` are passage nodes, and `entities.memory_ids[]` is the passage↔entity edge set (no new table). Build an **in-process igraph** snapshot in a **cached JobRegistry job** (never per query); seed from query→entity ANN links (IDF-penalized) + a small passage seed; run converged `personalized_pagerank`; fuse the memory-node mass as a third RRF list behind `graph_search_enabled`. **Emit string memory ids at the fusion boundary** (memory_id drift). **Append fresh memory ids to the snapshot at query time** so recent ingests aren't invisible. **The cache is per-worker** (single uvicorn today; dev `--reload` wipes it) — Phase 4's multi-replica goal forces sticky routing or a serialized snapshot table; decide now. *(HippoRAG's exact seed formula uses a query→fact score; the entity-cosine substitution is a labeled deviation — re-tune, don't assume constants transfer.)*
- **[logic]** **Dual-level retrieval** (LightRAG): local (entity ANN → 1-hop via `_build_neighbors`) + global (a `relation_embeddings` index or FTS fallback), fused into RRF. **No Apache AGE** — plain SQL + a recursive CTE covers it.
- **[logic]** **Synonymy edges** (ephemeral, cosine≥0.8, in the cached build — NOT `entity_relations` rows) to lift paraphrase/typo recall.
- **[logic]** **Community tier:** generalize `community_detector.py` (already Leiden on the code graph) to the memory graph → `memory_communities` + an off-path report job. Local = context injection; global map-reduce = a separate MCP tool.
- **Study:** HippoRAG 2, LightRAG (dual-level), nano-graphrag. **Gate:** multi-hop / multi-session slices of LongMemEval improve vs Phase 0 baseline; latency within budget; **degrades gracefully to hybrid** when the graph adds nothing.

### Phase 2 — Temporal re-architecture *(a rebuild that keeps the table name; [logic][feature])*
**Goal:** move from row-level, single-timeline supersession to **fact-level bi-temporal edges**. This is a **rebuild** of the (empty, demo-only) `knowledge_triples` layer, not a cheap activation. See impl-notes §2 for the corrected lifecycle (B1/B2/B3).
- **[logic]** Migrate the empty `knowledge_triples` to Graphiti's **five timestamps** — `valid_at/invalid_at` (world-time), `created_at/expired_at` (system-time), `reference_time`. "Live" = `expired_at IS NULL`. Resolve triple endpoints to real `entities` ids; add an embeddable `fact` column; **derive triples from `entity_relations`** (single source of truth — avoids a drifting parallel store).
- **[flow] Define the triple re-extraction / deletion sweep (B2) before any write path** — the analog of `delete_by_memory_id`: on re-extraction or memory deletion, expire (never delete) every live triple whose `source_memory_ids` would empty. Without this, reprocessing accretes stale live triples.
- **[flow] Contradiction invalidation runs in the Phase 3 consolidation job, NOT on ingest (B3).** Ingest writes triples append-only + runs the cheap deterministic temporal passes (stale-on-arrival, disjoint-window — plain Python, order-independent). The LLM same-endpoint contradiction check is a **Phase-3 consumer** — this collapses a false dependency and removes Phase 2's scariest piece.
- **[feature]** **Point-in-time queries** ("what did we believe / what was true as of date X") over MCP + REST.
- **[logic] Status bridge honors `chk_superseded_has_pointer` (B1):** on triple invalidation, set `superseded` + `superseded_by` **only** when the invalidating triple has exactly one live source memory; otherwise `deprecated` with `superseded_by=NULL`.
- **[feature]** **Self-expiring dated facts** (Supermemory): populate `expires_at` from a fact's own stated date at extraction.
- **Study:** Graphiti (`edges.py`, invalidation), cognee (temporal cognification), Memobase (timeline). **Gate:** LongMemEval **knowledge-update + temporal** slices improve; `extraction_bench` stays green.

### Phase 3 — Consolidation, memory types & fast ingestion *(off the hot path; [flow][logic][feature])*
**Goal:** move reconciliation off the hot path, add the memory types the field standardized on, and make ingestion non-blocking.
- **[flow]** **Async ingestion:** return **202** immediately, process on a background worker — reuse `JobRegistry` + `pipeline_failures` + the websocket lifecycle. Add **buffer/flush** (Memobase; `FOR UPDATE SKIP LOCKED`, no Redis) for chatty sources.
- **[flow]** **Background consolidation job** (JobRegistry `memory_consolidation`, per-project watermark, langmem-debounce front): the mem0 four-op resolver mapped onto darkmem's status lifecycle via a **direct `supersede()` primitive** (the resolver cannot ride `detect_supersessions`' REPLACES+tech triggers — review M6); A-MEM evolution (gated: rewrite `llm_summary`/tags only, audit trail); Generative-Agents reflection into `insight` memories. **Deletes OFF by default** → route through supersession. **This is the consolidation Letta/LangMem/A-MEM pioneered — mem0 dropped it, which is itself the argument for the conservative default.** Also hosts the Phase-2 LLM contradiction check (B3).
- **[flow]** **Semantic chunking + episodic segmentation** so long inputs decompose into atomic memories (removes the 6000-char *extraction-input* cap).
- **[feature]** **Memory types** (LangMem): add `episodic`/`procedural`/`profile` — **taxonomy-first** (§6): land them in `taxonomy.py` + sweep `reason()`'s KNOWN_TYPES, the extraction simple-7 gate, and UI filters **before** emitting them, and re-baseline (widening the vocabulary changes extraction prompts). `profile` = one rewritten row per `(project,label)`, token-capped + `read_only`.
- **[logic]** **Ranking priors:** add `access_count`+`last_accessed` columns (bump off-path on read); compute heat/recency in SQL; fold heat + recency + the already-populated `importance` into the single `rank_fusion_factor` multiplier, each behind a flag defaulting to 0.
- **Study:** Letta (sleep-time), A-MEM (evolution), LangMem (ReflectionExecutor, types), MemoryOS (heat), Generative Agents (reflection). **Gate:** consolidation reduces duplicate rate without recall loss; ingestion p95 drops; abstention + extraction slices improve.

### Phase 4 — Platform for open-source *(adoption; [feature][flow])*
**Goal:** the things an OSS project needs that a personal homelab doesn't.
- **[feature]** **Multi-tenancy / scoping — a schema change, not plumbing (review M3):** the real cost is the graph — `entities` are globally unique on `(name,entity_type)` with cross-project `memory_ids[]`, so two tenants asserting "postgres" share one row. Tenancy means changing the uniqueness key, per-tenant dedup/canonicalization in pipeline Phases 4–5, per-tenant `delete_by_memory_id`, and **every retrieval channel (vector/FTS, PPR walk, cached igraph snapshot, LLM community summaries) taking the same ACL predicate from day one.** Treat `project` as the tenancy unit from Phase 1 onward. (`api_key_id` is only in the audit path today — every call passes `None`.)
- **[feature]** **Wire the dormant `ApiKey` model** → programmatic API-key auth (hashed key + scopes + expiry); optional **MCP auth** (bearer over streamable-HTTP) without abandoning the localhost default.
- **[feature]** **Client SDKs — Python + TypeScript.** Adoption-critical; keep the surface small (OpenMemory's 4-tool north star). Arguably the highest-ROI *adoption* item — consider pulling a minimal Python SDK forward.
- **[feature]** Real **native Anthropic adapter** (`/v1/messages` + `cache_control`), **provider failover**, **persisted token/cost** tracking.
- **[flow]** **Observability:** Prometheus `/metrics`, OpenTelemetry, request-id, structured logs; **distributed-safe jobs** (advisory lock / leader election) + a run-history table so 2+ replicas don't double-fire (and reconcile the Phase-1 per-worker PPR cache here).
- **[feature]** **Publish a benchmark + docs + examples** with the honest protocol.
- **Study:** mem0 (multi-tenant server + SDK shape), Letta, Memobase. **Gate:** SDK smoke tests green; two-replica deploy fires each cron once; benchmark published.

### Phase 5 — Surface the power (UI/UX) *([ui])*
**Goal:** darkmem's UI is already ahead — make it *show* the backend's newly-activated signals.
- **[ui]** **Retrieval explainability** — an **ADE-style context/composition viewer** (Letta ADE): which memories, their scores (RRF / rerank / PPR / confidence / heat), token budget, per-memory provenance.
- **[ui]** **Temporal / lifecycle / provenance view:** supersession lineage, valid-time timeline, an "as of date X" slider, episodic timeline — the story Phase 2 now actually supports.
- **[ui]** **Insights / Analytics page** (reclaim the removed surface).
- **[ui]** **`project` as a first-class dimension** — switcher/filter across dashboard, Memories, graphs.
- **[ui]** **Chat → primary agent-memory workspace** with inline editing/pinning + memory-block editor.
- **[ui]** **Memory-graph community navigator + summaries**; reap remaining palette/Storybook/layout debt.
- **Study:** Letta ADE, Zep temporal graph UI. **Gate:** usability pass; charts survive light/dark; explainability renders real signals.

---

## 5. Ranked repos to clone (for deeper study)

All MIT/Apache-2.0. All cloned to `D:\Repositories\Community`.

1. **getzep/graphiti** (Apache-2.0) — bi-temporal edge model + invalidation. *Phase 2.*
2. **HKUDS/LightRAG** (MIT) — dual-level retrieval + incremental set-merge (its AGE requirement is the anti-port). *Phase 1.*
3. **OSU-NLP-Group/HippoRAG** (MIT) — Personalized PageRank multi-hop. *Phase 1.*
4. **memodb-io/memobase** (Apache-2.0) — same stack; buffer/flush + timeline. *Phase 2–3.*
5. **mem0ai/mem0** (Apache-2.0) — multi-signal retrieval + the append-only/dropped-reconciliation lesson. *Phase 0, 4.*
6. **letta-ai/letta** (Apache-2.0) — sleep-time consolidation + ADE viewer. *Phase 3, 5.*
7. **agiresearch/A-mem** (MIT) — memory evolution. *Phase 3.*
8. **topoteretes/cognee** (Apache-2.0) — ontology grounding + temporal cognification. *Phase 2–3.*
9. **langchain-ai/langmem** (MIT) — memory-type taxonomy + ReflectionExecutor. *Phase 3.*
10. **xiaowu0162/LongMemEval** (MIT) — the eval harness. *Phase 0.*
11. **gusye1234/nano-graphrag** (MIT) — readable community-detection reference. *Phase 1.*
12. **BAI-LAB/MemoryOS** (Apache-2.0) — heat-based promotion. *Phase 3.*
13. **joonspk-research/generative_agents** (Apache-2.0) — recency×importance×relevance + reflection. *Phase 3.*
14. **supermemoryai/supermemory** (MIT, study-only TS) — profile + self-expiring facts. *Phase 2–3.*

---

## 6. What NOT to do (guardrails)

- **Don't adopt Neo4j / a graph DB or Apache AGE.** Every temporal/graph idea reimplements on Postgres/pgvector (recursive CTEs); converged PPR lives in in-process igraph. The single-Postgres footprint is a *feature* the category is consolidating toward.
- **Taxonomy-first rule (review M2).** No feature may emit a relation type or memory type that isn't already landed in `app/taxonomy.py` — plus a sweep of the hard-coded vocabularies (`reason()`'s KNOWN_TYPES, the extraction simple-7 gate, UI filters). `SUPPORTS` is *currently a legacy alias of `RELATED_TO`*; `DERIVED_FROM`, `insight`, `episodic`, `procedural`, `profile` are not in the taxonomy yet. Land them before the feature that emits them.
- **The bi-temporal layer is a rebuild, not dead code you "activate."** Keep the empty table's name; rebuild the service. Smoke-test in Phase 0, migrate in Phase 2 — don't front-load it.
- **Never put an LLM contradiction/consolidation/evolution call on the ingest hot path.** All off-path JobRegistry jobs.
- **Don't chase LOCOMO SOTA.** Optimize LongMemEval; report honestly (p95 + tokens + full-context baseline).
- **Don't let the deterministic post-processor rot into a maintenance sink.** Shrink corpus-specific overrides into config tables, eval-gated by `extraction_bench`; keep the structural passes.
- **Don't feature-gate the OSS core.** Zep killed its Community Edition rather than cripple it; keep the full core open and differentiate on execution.

---

## 7. Open decisions for the maintainer

1. **Graph traversal engine:** in-process `igraph` on the RRF-seeded/cached snapshot (recommended — converged PPR needs it) vs Postgres recursive CTEs (multi-hop expansion only, bounded depth). *Do not adopt AGE.*
2. **Bi-temporal substrate:** extend `entity_relations` with valid-time columns vs rebuild the (empty, demo-only) `knowledge_triples` table. *Recommendation: keep the `knowledge_triples` name but rebuild the layer, and **derive triples from `entity_relations`** (single source of truth) to avoid two drifting graph stores. Smoke-test the existing SQL first — it has never run.*
3. **Consolidation aggressiveness:** conservative (dedup + summary refinement, deletes off) vs aggressive (A-MEM-style neighbor rewriting). *Recommendation: conservative, guarded by supersession pointers + an evolution audit trail.*
4. **SDK priority:** ship Python+TS SDKs in Phase 4 or pull a minimal Python SDK forward as an adoption accelerant.
5. **Sequencing:** Phase 1 (retrieval) before Phase 2 (temporal) — swappable **only after** B3's fix (as written, Phase 2's LLM resolver is Phase 3 machinery, so it cannot go first). Both depend on Phase 0.

---

## 8. Immediate next actions

> **Companion docs:** `2026-07-22-darkmem-evolution-implementation-notes.md` (source-verified port sketches, v2) and `2026-07-22-darkmem-evolution-plan-review.md` (the adversarial review ledger). Read both before starting a phase.

1. Stand up the **Phase 0 eval harness with the affordability protocol** (pinned judge; fixture/oracle/full-500-at-gates; ingest via `process_batch`) and record baselines.
2. Land the **SQL filter pushdown** (a blocking prerequisite of Phases 1/3/4), the **entity-match RRF signal**, and the **fact-augmented `llm_summary` RRF arm** behind the harness. **Smoke-test — do not migrate — the `knowledge_triples` path.**
3. **Resolve the open decisions in §7** and the review's open questions.
4. Turn Phase 0 into a **detailed TDD implementation plan** (`docs/superpowers/plans/`), then the next phase.

---

# Part II — Documents & Personal-Wiki surface ("Notion/Obsidian but LLM-native")

*From a second 4-agent cited survey. **Scope firewall (review M8): the committed Part II is Doc-0/1/2 only — a "chat with your documents" feature of the memory product. The editor/canvas/CRDT track (Doc-3/4/5) is a separate product, deferred and NOT committed until v1 proves demand. No Doc-track work starts before Phase 1's eval gate is green.***

## 9. Thesis: darkmem already owns the retrieval + graph half of an LLM-native personal wiki

Should darkmem grow a documents + personal-wiki surface that retrieves via LLM? **Yes, incrementally** — because darkmem already ships the **two hardest engine pieces** every Notion/Obsidian-with-AI competitor had to build:

1. **A typed entity/relationship graph with `memory_ids[]` provenance IS the wiki link model.** A `[[wikilink]]`/backlink is a typed edge between two addressable nodes with a reverse index — exactly darkmem's `entity_relations` (bipartite provenance verified). "Notion/Obsidian bolt a graph onto a document store; **darkmem would bolt a document store onto a graph**." Anytype validates this: its Type+Relation object graph *is* darkmem's `entities`/`entity_relations` + closed taxonomy.
2. **Hybrid pgvector + Postgres-FTS + RRF + reranker IS the "chat with your notes" engine** Obsidian lacks and Notion had to build. Anthropic's Contextual Retrieval names darkmem's *exact* stack as the winning recipe.

**Caveat (M8):** owning the engine is *not* owning the product. The majority of a PKM's user-facing surface — editor, views, transclusion UX, canvas, import — is Doc-3/4/5 territory, and "embed BlockSuite" is a large integration (a CRDT document model meeting server-authoritative Postgres). So: darkmem is the retrieval+graph *half*; commit to the half that reuses the core (Doc-0/1/2), and treat the wiki-authoring half as a separate, demand-gated product. Postgres is a proven single substrate for the engine half (Morphik runs docs+vectors+KG on Postgres at scale).

## 10. The one gap that unlocks four features: GRANULARITY (a `blocks` table)

darkmem's atom today is a **whole-memory row with no sub-row addressing** (and its *extraction input* is capped at 6000 chars). Every serious system converges on a smaller atom:

> Add a **`blocks` table** modeled on Notion/SiYuan: `(id UUID, document_id, parent_id, order_index, type, text, properties JSONB, char_span)` + a per-fingerprint **`block_embeddings__<slug>`** partition (needs an `embedder_registry` change + a creation sweep for existing fingerprints). **One block abstraction is simultaneously the CHUNK unit (RAG), the CITATION anchor, the LINK endpoint, and the TRANSCLUSION target.** Getting it right unlocks all four at once.

darkmem's idempotency discipline transfers: "strip prior `memory_id` contributions before rewrite" generalizes to "delete blocks by `document_id` before re-ingest."

## 11. What darkmem needs to ADD (front-end + data model + UI), by axis

darkmem **does not need a retrieval rewrite** — its mechanics already match the leaders. It needs an **ingestion front-end, a block data model, and an authoring/citation UI.** All building blocks are MIT/Apache unless flagged.

### 11.1 [flow] Ingestion & chunking front-end (Doc-0 — the biggest gap)
Every strong system separates **parse** → **chunk**.
- **Parse:** **Docling** (MIT — layout/tables/OCR/provenance bboxes, local) high-fidelity; **MarkItDown** (MIT) fast default; **Unstructured** (Apache — `chunk_by_title`) for the structural recipe. Optional user-configured **LlamaParse** as a pluggable "parsing provider" for hard PDFs — never the default.
- **Chunk:** **recursive/structure-aware** first (~512 tokens, 15–20% overlap — beats semantic at a fraction of the cost). Then **late chunking** (Jina, Apache) — darkmem owns its embedder registry, so it's a localized, LLM-free embedding-phase change. **Contextual retrieval** (Anthropic): fold the situating blurb into the LLM call darkmem already makes.

### 11.2 [logic] Retrieval upgrades that apply to memories AND documents (converge with Phase 0/1)
- **`ts_rank` → true BM25** (VectorChord-bm25, Postgres extension).
- **LLM reranker → `bge-reranker-v2-m3`** cross-encoder (cheaper/faster/more accurate; behind `reranker_enabled`).
- **Query rewrite node** before retrieval (Quivr). *(Do these once, for both surfaces.)*

### 11.3 [feature] Grounded citations (Doc-2 — "chat with your notes")
- **Span-anchored attribution:** carry `(document_id, block_id, char_span/page/bbox)` on every returned row. Render Notion/NotebookLM-style inline citations; block-level precision beats NotebookLM's coarse anchoring (kotaemon's PDF-highlight is the gold standard).
- **Grounding verification:** **Vectara HHEM** / **RAGAS/DeepEval faithfulness** → a groundedness badge; **faithfulness is the ship gate**.

### 11.4 [feature] The wiki data model (Doc-3 — DEFERRED) — blocks + links + views + canvas
- Blocks with stable IDs = sub-row addressing → transclusion + block embeddings + deep-link citations.
- **Links = `entity_relations`.** A wikilink is a `REFERENCES`/`MENTIONS` edge (must be in the taxonomy first); the backlink panel is a reverse query. AI can *suggest* links from embedding similarity.
- **Transclusion:** Logseq's `((block-id))` window vs `{{embed}}` portal.
- **Properties + saved views = "databases":** `properties JSONB` + a saved-view definition; render in the existing React stack.
- **Canvas:** adopt **JSON Canvas** (MIT) directly — buys Obsidian interop for an adapter's cost.

### 11.5 [feature] Advanced / opt-in (DEFERRED)
- **RAPTOR** (MIT) recursive summary tree — reuse `llm_summary`; index in the same pgvector table; JobRegistry rebuild.
- **Proposition / "deep ingest"** (Dense X): a proposition *is* a darkmem memory → reuse the entire pipeline and **dedupe/supersede facts across documents** (the one differentiator no competitor can easily match). Opt-in behind cheap chunking.
- **ColBERT/ColPali** for scanned/visual PDFs — separate multivector index, **not v1**.

### 11.6 [feature] Multi-tenancy & connectors (Doc-5 — DEFERRED; converges with Phase 4)
- Collections/workspaces = namespaces → darkmem's `project` scope.
- **Permission-at-retrieval-time** (Onyx): ACLs *inside the search SQL* on **every** channel (see M3), never UI-only.
- **Connectors** (Notion/Drive/Confluence import).

### 11.7 [ui] Editor & local-first (Doc-4/5 — DEFERRED, separate product)
- **Block editor + edgeless canvas:** embed **BlockSuite** (MPL-2.0) rather than build one — but note this is a large integration, not a thin add.
- **Local-first/CRDT:** the deepest fork from server-authoritative Postgres. Pragmatic path (AFFiNE/AppFlowy): **Yjs/Yrs** (MIT) on the client, update log **append-only in Postgres**, committed snapshots feed extraction. **Obsidian has no CRDT** — ship Obsidian-grade local-first *without* CRDT first; add Yjs only when real-time collab is a proven requirement.

## 12. Documents-track sub-roadmap (committed = Doc-0/1/2; Doc-3+ deferred)

| Stage | Status | Goal | Reuses from Part I |
|---|---|---|---|
| **Doc-0** | **committed** (≥L; largest single Part-II migration) | parse → recursive chunk → `blocks` + `block_embeddings`; provenance | pgvector partitioning, RRF, idempotent re-ingest |
| **Doc-1** | **committed** | late chunking, `ts_rank`→BM25, bge reranker, contextual blurbs | HybridSearchService, reranker flag, per-ingest LLM call |
| **Doc-2** | **committed** | grounded block-anchored citations + faithfulness gate + query-rewrite | memory_reason, chat UI, SourceBadges |
| **Doc-3** | *deferred* | wiki data model (links, transclusion, views, JSON Canvas) | entity graph, graph viz, project scope |
| **Doc-4** | *deferred* | BlockSuite editor; RAPTOR + proposition deep-ingest | knowledge-graph canvas, summarization, JobRegistry |
| **Doc-5** | *deferred* | local-first / CRDT; connectors; retrieval-time ACLs | Phase 4 |

**Gate & scope firewall (review M8):** **no Doc-track work before Phase 1's eval gate is green.** Committed v1 is Doc-0/1/2 — a "chat with your documents" capability of the memory product. Doc-3/4/5 (editor/canvas/CRDT/connectors) is a **second product**, not committed until v1 proves demand. Doc-1's retrieval upgrades are the *same engineering* as Phase 0/1 (do once, for both surfaces); Doc-0 depends on nothing in Part I, which is exactly why it must be gated — it can start immediately and starve the core roadmap otherwise.

## 13. Repos to study — documents & PKM track

**Ingestion/parse/chunk (adopt as deps):** `docling-project/docling` (MIT), `microsoft/markitdown` (MIT), `Unstructured-IO/unstructured` (Apache), `jina-ai/late-chunking` (Apache), `anthropics/anthropic-cookbook` Contextual Retrieval (MIT), `parthsarthi03/raptor` (MIT), `chentong0/factoid-wiki` propositions.
**Retrieval/rerank/eval:** `FlagOpen/FlagEmbedding` bge-reranker (MIT), `tensorchord/VectorChord-bm25` (permissive), `explodinggradients/ragas` / `confident-ai/deepeval` (Apache), `vectara HHEM` (Apache), `NirDiamant/RAG_Techniques`.
**Doc-RAG apps (study):** `Cinnamon/kotaemon` (Apache — citation UX), `infiniflow/ragflow` (Apache), `onyx-dot-app/onyx` (MIT CE — connectors + retrieval-time ACLs), `QuivrHQ/MegaParse` (Apache). *Study-don't-vendor:* `morphik-org/morphik-core` (BSL — Postgres docs+vectors+KG twin), Open WebUI (branding clause).
**PKM data model / editor (deferred track; adopt the MIT bits):** **JSON Canvas** `obsidianmd/jsoncanvas` (MIT), **BlockSuite** `toeverything/blocksuite` (MPL-2.0), **Yjs** `yjs/yjs` (MIT). *Study-reimplement (AGPL):* `siyuan-note/siyuan`, `logseq/logseq`, `khoj-ai/khoj` (closest Python+Postgres+pgvector sibling), `AppFlowy`. Already in `D:\Repositories\Community`: **`dify`**, **`notion-sdk-net`**, **`readest`**.

## 14. Strategic recommendation on Part II

**Pursue Doc-0/1/2 as a surface over the same engine; defer Doc-3/4/5 as a separate, demand-gated product.** The discipline: (1) the `blocks` table + fingerprint-partitioned `block_embeddings` is the keystone — build it once, right, gated behind Phase 1; (2) do the shared retrieval upgrades (BM25, cross-encoder, late chunking) once for both surfaces; (3) treat the editor/canvas/CRDT as a large second effort, not a thin add — Obsidian's moat is its editor + ecosystem, not its (absent) search; (4) the one genuinely darkmem-native differentiator is **proposition ingestion** (documents → memory-shaped rows → one graph, cross-document supersession) — it needs the extraction+graph+supersession stack darkmem already has. **Guardrail:** don't build parsers or an editor from scratch — Docling/MarkItDown and BlockSuite exist and are license-clean.

---

*Sources: two 4-agent cited surveys (2026-07-22) — (I) agent-memory: mem0 arXiv:2504.19413, Zep arXiv:2501.13956, MemGPT arXiv:2310.08560, HippoRAG arXiv:2502.14802, A-MEM arXiv:2502.12110, MemoryOS arXiv:2506.06326, Generative Agents arXiv:2304.03442, GraphRAG arXiv:2404.16130, LightRAG arXiv:2410.05779, LongMemEval arXiv:2410.10813; (II) doc-RAG & PKM: Khoj, RAGFlow, Onyx, kotaemon, AnythingLLM, Morphik, Docling, Unstructured, late chunking (arXiv:2409.04701), Contextual Retrieval, RAPTOR (arXiv:2401.18059), Dense X (arXiv:2312.06648), Notion/Obsidian/SiYuan/Logseq/Anytype/AFFiNE, JSON Canvas, BlockSuite, Yjs — plus primary repos/docs. Grounded in a 4-agent code audit of `darkmem/backend`+`frontend` and a Fable adversarial review that verified load-bearing claims against source. Competitor benchmark numbers are self-reported/contested; treat as directional and re-measure locally.*

---

# Part III — Distribution & last-mile integration ("get memory into and out of every tool")

*From a 5-angle adversarially-verified competitive scan (2026-07-23) triggered by the commercial product **1AIVault** (StoicSoft, closed-source desktop app) and its category. **Framing:** Parts I–II rebuild the memory/document **engine**; Part III is the **last-mile layer** that carries that engine into every AI client. Additive to Phase 4 (platform), not a replacement.*

## 15. What the scan found — the engine is validated; the gap is distribution

Every serious "one memory layer for all AI tools" product converges on **darkmem's exact architecture** — hybrid vector+keyword retrieval fused with RRF over an LLM/NER-extracted knowledge graph. `MihaiBuilds/memory-vault` is nearly a darkmem clone (Postgres 16 + pgvector, RRF, spaCy-NER graph); EchoVault and `fusae/Memory-Vault` run the same pattern on SQLite+Ollama; `graphiti-mcp` uses LLM-extracted temporal graphs. On the **engine**, darkmem matches or exceeds them — Mem0's OSS graph is *boost-only* (only semantic search expands recall; darkmem's RRF expands on both sides), and several competitors use co-occurrence graphs where darkmem uses LLM extraction + supersession/TTL.

**So the differentiation these products actually ship is not retrieval — it is the last-mile integration layer this plan omits.** Two structural gaps:
- **Darkmem is pull-only.** An agent gets memory *only* if it explicitly calls `memory_search`. Every competitor in this consumer-facing category adds a **push** path.
- **Darkmem is single-endpoint.** One hand-configured `/mcp`. Competitors ship one-click/one-command onboarding to many clients.

## 16. The commitments

| # | Item | Source precedent | vs current plan | Tag |
|---|---|---|---|---|
| III.1 | **Auto-inject memory (push)** | 1AIVault Auto-Inject | Absent everywhere — **highest value** | [feature] |
| III.2 | **Browser capture of web AI chats** | 1AIVault, Supermemory, MemoryPlugin | Part II ingests *documents*, not web chats | [feature][flow] |
| III.3 | **One-command per-client onboarding** | EchoVault `memory setup <client>` | Phase 4 has SDKs, not this UX | [feature][flow] |
| III.4 | E2EE device-transfer; versioning/consolidation as tools | Engram, fusae, Letta MemFS | Low architectural fit — **decision, not commitment** | [feature] |

**III.1 — Auto-inject: turn darkmem from pull to push.** A JobRegistry job (or CLI) renders the top-N most relevant memories for a `project` into a **marker-bounded managed block** written directly into each tool's instruction file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, Codex, Windsurf, OpenCode), so a session opens pre-loaded before the first prompt. Reuse the already-computed `llm_summary` + retrieval ranking; offer a **verbosity budget** (Minimal/Standard/Rich/Max); **preview** the exact block; **never overwrite** content outside the markers. **Open decision (plan §7):** this writes to files darkmem's own convention treats as user-authored — the marker-bounded block is the reconciliation, and it must be strictly opt-in and idempotent (a re-render replaces only within the markers — the same discipline as `delete_by_memory_id`). This is the single biggest conceptual gap: pull → push.

**III.2 — Browser capture.** A browser extension that captures ChatGPT/Claude/Gemini **web** conversations via a local bridge and feeds them into `process_batch`. A new *ingestion source* distinct from Part II's document parsing — this is where a "brain for every AI tool" earns the name, since much AI usage never touches an MCP client.

**III.3 — One-command onboarding.** `darkmem connect claude-code | cursor | codex | …` writes each client's MCP config automatically (EchoVault's pattern), plus a connection-status view (which clients are wired). Pairs with the Phase 4 SDKs; pure adoption UX, low risk.

**III.4 — Decisions, not commitments.** Client-side **E2EE + encrypted device-transfer** (Engram/fusae/1AIVault) and **memory versioning** (Letta MemFS git-backed history) fit a *desktop-app* model more than darkmem's server model. Record them as open decisions; do not schedule until a multi-device need is real.

## 17. Guardrails, gate & sources

- **Don't feature-gate the core** (plan §6 holds): auto-inject and browser capture are opt-in additions, never paywalled behind the OSS core.
- **Reuse, don't rebuild:** auto-inject rides `llm_summary` + ranking + `JobRegistry`; browser capture rides `process_batch`; onboarding rides existing MCP config.
- **Gate:** auto-inject writes *and refreshes* a managed block without clobbering user content; one-command onboarding wires a real client end-to-end; a captured web chat round-trips into a retrievable memory.
- **Sources (2026-07-23 deep-research, adversarially verified; largely vendor self-report — 1AIVault is closed-source):** 1aivault.com (v1.12, StoicSoft); github: MihaiBuilds/memory-vault, fusae/Memory-Vault, mraza007/echovault, Flo976/graphiti-mcp-ollama, EvolvingLMMs-Lab/engram, supermemoryai/supermemory; docs.mem0.ai; blog.memoryplugin.com.

---

# Part IV — Product surface, engagement & memory hygiene (the human-facing layer)

*The maintainer's observation, adopted as a correction: **Parts I–III are backend-weighted; the roadmap under-scopes user-facing features and design.** Phase 5 exists but is reactive ("make the backend's signals visible") and sits at the *end*. Part IV owns the product/design vision as a **parallel track**, not a trailing phase.*

## 18. Thesis: the mechanisms exist; the surface doesn't

Darkmem already runs, or plans, most of the machinery a human-facing memory product needs — consolidation (Phase 3), TTL expiry + orphan sweeps + supersession + dedup (shipped), `access_count`/heat (Phase 3), three theme-reactive graph visualizations (shipped). **What's missing is a product surface that makes the vault feel alive to feed, trustworthy to rely on, and safe to prune.** Three surfaces close that.

## 19. The surface

**IV.1 [ui] Dashboard revamp — the "living vault" home.** Replace the stat grid with a home that answers *"what does my brain know, and is it growing?"* Centerpiece: a **memory contribution calendar** — a GitHub-commit-style heatmap of memories added (and accessed) per day, per project. Cheap to build (`created_at` exists; wire the Phase-3 `access_count`/`last_accessed`), engagement-driving, and doubles as an activity audit. Around it: a recent-memory stream, top entities/`technologies`, project breakdown, a growth sparkline. Reclaims the removed `/analytics` surface (Phase 5 already flags this) with a point of view. **Design constraint:** the heatmap's color ramp must tokenize through `resolveGraphTokens` (the Phase-0 palette fix) or it breaks in light mode exactly like today's 52 hard-coded chart hexes.

**IV.2 [feature][ui] "Dreaming" — consolidation as a visible, controllable act.** Phase 3 builds background consolidation (A-MEM evolution, reflection into `insight` memories, dedup) — today that would be an invisible cron. Surface it:
- A manual **"Dream now"** trigger (MCP tool + UI button) reusing `JobRegistry.trigger` (it already carries the per-job lock + 409-busy semantics).
- A **dream digest**: after each cycle, show what changed — memories merged, summaries rewritten, contradictions resolved, new `insight` memories synthesized — with an **audit trail and undo** (rides the Phase-3 evolution audit trail + supersession pointers).

This turns the plan's scariest piece (an LLM rewriting stored memories) into a transparent, reviewable event — which is simultaneously the safety story. Darkmem's version is *auditable* precisely because it routes through supersession, not deletion (fusae's `memory_dream` / Letta sleep-time have no such lineage).

**IV.3 [feature][ui] Memory hygiene & curation.** TTL, orphan sweeps, supersession, and dedup are all invisible. Add a **review queue**: candidate duplicates (from the Phase-4 dedup ANN probe), low-confidence rows, stale/expiring-soon memories, and superseded lineage — with **bulk** keep / merge / deprecate / extend-TTL actions routed through supersession (never a raw delete). Make **confidence and staleness visible signals** so a human can trust or prune — and note this is a concrete reason to replace the regex `confidence` placeholder (plan §3.1) with a real number. The human-in-the-loop counterpart to IV.2's automation.

**IV.4 [ui] Onboarding & empty states.** Tied to III.3: first-run shows per-client connection status and teaching empty states. Adoption-critical for OSS.

**IV.5 Design posture (the meta-fix).** Elevate UI/UX from a trailing Phase 5 to a **parallel track with its own gate**. Rule: **every backend phase that adds a signal ships with the UI that exposes it** — the PPR score and graph channel (Phase 1), temporal validity (Phase 2), heat/recency and the dream digest (Phase 3) — instead of deferring all surfacing to the end. Phase 5 becomes the consolidation/polish pass, not the *first* time the backend becomes visible.

## 20. Gate & study

- **Gate:** dashboard + calendar survive light/dark (tokenized); the calendar renders real `created_at`/access data; the dream digest shows a real consolidation diff with working undo; the hygiene queue performs bulk actions safely through supersession.
- **Study:** Letta **ADE** (gold-standard observability/curation UI), the GitHub contribution-graph pattern (`cal-heatmap`, MIT), Supermemory's dashboard, fusae's `memory_dream`/`memory_consolidate` tool surface.

---

*Parts III–IV added 2026-07-23 from a 5-angle deep-research competitive scan (1AIVault + category) and the maintainer's product/design critique. Evidence is largely vendor self-report and, for 1AIVault, closed-source; treat as directional. No Part III/IV work preempts Phase 0's eval gate or Phase 1's — distribution and design surface the engine; they do not substitute for measuring it.*
