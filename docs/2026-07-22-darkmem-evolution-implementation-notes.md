# darkmem Evolution — Implementation Notes (source-verified port sketches)

**Date:** 2026-07-22 · **v2 (remediated 2026-07-22 after adversarial review — see `2026-07-22-darkmem-evolution-plan-review.md`).** Companion to `2026-07-22-darkmem-evolution-plan.md` — which gained **Parts III–IV** on 2026-07-23 (distribution/last-mile + product surface/design). Those are directional competitive-scan additions, **not yet source-verified port sketches**, so they are not expanded in these notes; see the sequencing pointer at the end of this doc.
**Source:** a 4-agent source-level study of the cloned repos in `D:\Repositories\Community` (graphiti, HippoRAG, LightRAG, nano-graphrag, mem0, letta, A-mem, langmem, memobase, MemoryOS, generative_agents, cognee, LongMemEval) cross-referenced against darkmem's `backend/app`. Full verbatim prompts/algorithms in the transcript (`…/tasks/wdhh8wkcf.output`).

## v2 changes (what the review corrected)
- **B1 fixed** (status bridge vs `chk_superseded_has_pointer`), **B2 fixed** (triple re-extraction/deletion semantics), **B3 fixed** (LLM contradiction check moved off the ingest hot path into the Phase 3 job) — see §2.2.
- **M1 corrected:** `knowledge_triples`/`KnowledgeGraphService` is **untested LOCOMO demo scaffolding**, not a ready substrate — this is a **rebuild that keeps the table name**, not a cheap activation. Migration is trivial (table is provably empty); the cost is the new build. **Removed from "first moves."**
- **M2/M6 corrected:** taxonomy-first rule for new relation/memory types; resolver UPDATE gets a direct supersede primitive (it cannot satisfy `detect_supersessions`'s triggers).
- **M4 added:** an eval cost budget + protocol in §0.4.
- Factual corrections: HippoRAG seed = query→fact score (m5); Graphiti has a 5th timestamp `reference_time` (m6); A-mem rebuilds per-100 *evolutions* (m7); `importance` is already populated at ingest (m3); weak-slice MRRs are stale (m4); PPR must emit string ids (m10); new embedding parents need `embedder_registry` changes (m9); the SQL filter pushdown is a prerequisite, not a quick win (m11); all triple SQL is untested (m14).

**Sequencing correction (review §Sequencing):** the bi-temporal migration is **not a Phase-0 first move**. Phase 0 = eval harness + entity-match arm + `llm_summary` arm + **SQL filter pushdown** + UI quick wins. The triple path gets a cheap **smoke test** in Phase 0 (satisfies "wire or delete" due diligence — see m14), but the migration + rebuild land in **Phase 2 proper**, after a temporal metric exists.

---

## Phase 2 — Temporal & contradiction invalidation *(this is a rebuild, not an activation)*

**Reality check (M1, verified):** `KnowledgeGraphService` has zero callers, and reading it shows why "the expensive part is built" is false: `seed_from_entity_facts` (knowledge_graph.py:162-202) is LOCOMO demo seeding (`married_to`, `is_pet_of`, `.capitalize()`); triple endpoints are free-text `_slugify` strings, **not** FKs into `entities`; `add_triple` inserts `entity_type='unknown'` stubs with **no `memory_ids`**, which the hourly `graph_orphan_cleanup` **actively reclaims** (the comment at repositories/graph.py:552-556 says so); predicates are free-form vs the closed `RELATIONSHIP_TYPES`. The one genuine win: the table is **empty everywhere**, so the column-rename migration is trivial and risk-free. Everything else — endpoint→entity FK resolution, `fact` rendering, deriving triples from `entity_relations`, backfill, the resolver, and tests — is new build. **m14: every helper in `repositories/graph.py:537-710` has literally never executed; smoke-test asyncpg bind types/CAST, `NULLS LAST` ordering, and the read-then-write race in `add_triple` (knowledge_graph.py:53-58) before trusting any of it.**

| Mechanism | Source | Effort (v2) | Port in one line |
|---|---|---|---|
| Bi-temporal 5-timestamp schema | graphiti `edges.py::EntityEdge` | S migration + hidden M-L build | migrate empty `knowledge_triples` to valid_at/invalid_at + **new** expired_at + reference_time + fact/rel_type/project/source_memory_ids[] |
| Ingest-side triple writes (append-only + deterministic temporal passes) | graphiti temporal passes | M | plain-Python stale-on-arrival + disjoint-window; **no LLM on ingest** |
| **Triple re-extraction / deletion semantics (B2)** | darkmem invariant | M | analog of `delete_by_memory_id`: expire live triples whose `source_memory_ids` empties |
| LLM contradiction resolution (B3 — Phase 3 job, not ingest) | graphiti `resolve_edge` | **XL** | runs in the consolidation job over the dirty set only |
| Entity resolution pre-pass | graphiti `dedup_helpers.py` | S | entropy gate + exact-first before the ANN probe; resolve triple endpoints to real entity ids |
| Deterministic triple identity | cognee `DataPoint.py::id_for` | S | `triple_key` generated col + partial unique index → idempotent upsert |
| Fuzzy taxonomy snap | cognee `RDFLibOntologyResolver` | S | `difflib` cutoff 0.85 inside `normalize_relation_type` |
| Structured Timestamp + NL interval | cognee `temporal_graph` | M | partial-date model + `extract_query_time` as-of queries |

### 2.1 Bi-temporal schema (the one cheap part)
Graphiti separates **two orthogonal time axes** darkmem collapses today: **valid-time** (`valid_at`, `invalid_at` = world truth) and **transaction-time** (`created_at`, **`expired_at`** = belief). "Live" = `expired_at IS NULL`, *not* `valid_to IS NULL`. **m6: there is a fifth timestamp, `reference_time`** (edges.py:280-282 — the source-episode anchor used to resolve relative dates); darkmem's analog is the source memory's `created_at`, worth carrying.

Alembic migration on the **empty** `knowledge_triples` (app/models/graph.py:47): `valid_from→valid_at`, `valid_to→invalid_at` (widen `Date`→`TIMESTAMPTZ`), **ADD** `expired_at TIMESTAMPTZ NULL`, `reference_time TIMESTAMPTZ`, `fact TEXT` (embeddable — load-bearing for contradiction search), `rel_type TEXT`, `project TEXT NOT NULL DEFAULT 'default'`, `source_memory_id → source_memory_ids UUID[]`. Indexes: partial `(subject,predicate,object) WHERE expired_at IS NULL`; btree `(valid_at,invalid_at)`. Invalidation is a **re-save, never a delete** (`SET expired_at=:now, invalid_at=COALESCE(invalid_at,:invalid_at)`). Resolve endpoints to real `entities` ids (not `_slugify` ghosts) via the entity-resolution pre-pass. **Gotcha:** conflating `expired_at` (belief withdrawn) with `invalid_at` (fact ended) defeats bi-temporality.

### 2.2 Triple lifecycle — the corrected design (B1 + B2 + B3)
The v1 sketch broke two invariants and put an LLM on the hot path. Corrected split:

**Ingest side (Phase 5B) — append-only, no LLM (fixes B3):** emit new triples for the memory; run **only the two deterministic temporal passes** in plain Python (cheap, order-independent):
- **stale-on-arrival:** if a live candidate `valid_at > new.valid_at`, set `new.invalid_at = candidate.valid_at; new.expired_at = now`.
- **supersede-older:** for a contradicting candidate, skip if windows are **disjoint** (`candidate.invalid_at <= new.valid_at OR new.invalid_at <= candidate.valid_at`); else if `candidate.valid_at < new.valid_at`, set `candidate.invalid_at = new.valid_at; candidate.expired_at = now`.
- Candidate set here is the cheap same-endpoint / `pg_trgm`-on-`fact` lookup, **not** an LLM call.

**Re-extraction / deletion semantics (fixes B2) — a fifth-phase-B design item, not an afterthought:** darkmem's idempotency rule is *strip prior `memory_id` contributions before rewrite* (`delete_by_memory_id`); the triple layer's rule is *invalidate, never delete* — these must be reconciled or reprocessing a memory accretes stale live triples. Define the analog: **on re-extraction of memory M, expire (not delete) every live triple whose `source_memory_ids` would become empty after removing M**; append M to survivors; then write the new set (the `triple_key` upsert only dedups *identical* facts, so it does not cover this). **On memory deletion, run the same sweep** (`source_memory_id` is `ON DELETE SET NULL` today → would silently orphan triples). Add to the TTL/orphan job.

**Contradiction resolution (LLM) runs ONLY in the Phase 3 consolidation job (fixes B3):** over the dirty set, build Graphiti's two-list continuous-index context on `knowledge_triples.fact` and call the `resolve_edge` prompt (returns `{duplicate_facts, contradicted_facts}`); apply invalidations via the triple update path. Keep darkmem's proven guards as a pre-filter (same-project, strictly-older-with-id-tiebreak — prevents the bidirectional mutual-flip on reprocess; `SUPERSESSION_WINDOW_DAYS`). Gate behind a flag. **This collapses a false dependency: Phase 2's riskiest piece becomes a Phase 3 consumer.**

**Status bridge (fixes B1):** when a triple asserted by M is invalidated and M has no remaining live triples, set `memories.status` per `chk_superseded_has_pointer`: **`superseded` + `superseded_by` ONLY when the invalidating triple has exactly one live source memory; otherwise `deprecated` with `superseded_by=NULL`.** (Temporal stale-on-arrival invalidations often have *no* successor at all → `deprecated`.) Write this constraint interaction into the Phase 2 design doc with a test.

### 2.3 Cheap de-risking borrows *(unchanged, verified faithful)*
- **Deterministic identity** (cognee): `triple_key = uuid5(project, subject_slug, predicate_norm, object_slug)` + **partial** unique index `WHERE expired_at IS NULL` → `insert_triple` becomes an `ON CONFLICT … DO UPDATE SET source_memory_ids=array_append(...)`, killing the read-then-write race. Partial index required (want many historical rows, one live).
- **Entity resolution pre-pass** (graphiti `dedup_helpers.py`): entropy gate (reject len<6 & <2-token or char-entropy<1.5 names from fuzzy matching) + exact-first, **before** the ANN probe; also used to bind triple endpoints to real `entities` ids.
- **Fuzzy taxonomy** (cognee): `difflib.get_close_matches(cutoff=0.85)` inside `normalize_relation_type` *after* exact+legacy-map. **Gotcha:** guard the Python 3.14 `SequenceMatcher` KeyError (`debug_aggregator_difflib_python314`).

---

## Phase 1 — Graph-augmented retrieval *(a measured hypothesis, not a certainty)*

**M7 framing correction:** the plan called PPR "the single highest-leverage change" *before measurement* — that contradicts the measurement-first directive. A personal-dev memory graph is small and hub-dominated (postgres/docker/python); the gain over RRF + `technologies` filtering is **unproven** until the Phase-0 harness says so. Treat Phase 1 as a measured experiment.

| Mechanism | Source | Effort | Port in one line |
|---|---|---|---|
| Personalized PageRank channel | HippoRAG `retrieve`/`run_ppr` | L (+tuning) | in-process igraph over `entities`+`entity_relations`+`memory_ids`, fuse into RRF |
| Synonymy edges | HippoRAG `add_synonymy_edges` | S | ephemeral cosine≥0.8 entity KNN at graph-build (NOT relations rows) |
| Recognition-memory fact reranker | HippoRAG `rerank_facts` | S | optional LLM fact-filter before PPR seeding |
| Dual-level retrieval | LightRAG `kg_query` | M | 1 keyword-split LLM call → local entity ANN + global relation index |
| Apache-AGE backend | LightRAG postgres_impl | **avoid** | ANTI-PORT (verified: LightRAG's PG graph *requires* AGE, postgres_impl.py:818); use native SQL + recursive CTE |
| Leiden communities + reports | nano-graphrag | M | generalize `CommunityDetector` to the memory graph → `memory_communities` |

### 1.1 Personalized PageRank (the central retrieval port)
The graph already exists: entities are `entities` rows; **passage nodes = `memories`; passage↔entity edges = `entities.memory_ids UUID[]`** (verified bipartite) — no new table. New `app/services/graph_retrieval.py::GraphRetrievalService`: build in-process `igraph.Graph(directed=False)` per project (igraph is already a dep); phrase nodes from `entities`, fact edges from `entity_relations(weight)`, passage edges by `unnest(entities.memory_ids)`, synonymy edges (§1.2, ephemeral).

Retrieve: embed query → ANN vs `entity_embeddings__<slug>` to link query→seed entities → run `igraph.personalized_pagerank(damping=0.5, directed=False, reset=seed_weights)` in a thread executor (like `community_detector.detect()`) → read PR mass at memory nodes. **m5 (deviation to label): HippoRAG's seed numerator is the query→FACT similarity of DSPy-filtered facts, averaged per phrase (HippoRAG.py:1594-1615)** — the v1 sketch's `cosine / COALESCE(array_length(memory_ids,1),1)` substitutes *entity* cosine for the fact score. This is an acceptable simplification (darkmem has no fact-embedding store yet) but it is a **deviation**: do not assume HippoRAG's constants transfer; tune the IDF penalty + damping independently on the harness. **m10: the channel must emit string memory ids at the fusion boundary** (memory_id str/UUID drift invariant — noted for the resolver, easy to miss here). Fuse as a third ranked list into a generalized `HybridSearchService._rrf_fuse`, behind `graph_search_enabled`.

**M7 operational fixes (write these down now):** (1) the hourly-cached snapshot makes memories ingested since the last build **invisible** to the graph channel — exactly the fresh memories agent workflows query next. **Append fresh memory ids to the snapshot's bipartite edges at query time** (one cheap `unnest(memory_ids)` delta query) so the channel degrades to hybrid for unseen ids rather than dropping them. (2) The in-process cache is viable *today* only because prod runs a **single** uvicorn worker (`entrypoint.sh` has no `--workers`) and dev `--reload` wipes it each save; **Phase 4's two-replica goal invalidates it** — decide now between sticky routing, a serialized snapshot table, or accepting per-replica duplication.

### 1.2 Synonymy edges *(cheapest densification; ephemeral only)*
Entity-KNN edges (cosine≥0.8, cap 100, skip ≤2-alnum) computed **inside** the cached graph build via a self-join over `entity_embeddings__<slug>`. **Must stay ephemeral / in-igraph — NOT `entity_relations` rows** (closed taxonomy would rewrite a `SYNONYM` rel_type to `RELATED_TO`). **m4: the weak-slice MRRs (paraphrase 0.745 / typo 0.76) and "bge-base/large" are STALE** — they date from the fine-tuning effort deleted in the 2026-05-01 ML removal, not the current production embedder (whatever the LLM config row says). Re-derive weak slices on the Phase-0 harness before tuning the 0.8 threshold against them.

### 1.3 Dual-level retrieval + the AGE anti-port *(unchanged, verified)*
One LLM call splits the query into `{high_level, low_level}` keywords. Local (low-level): entity ANN → 1-hop expand (`GraphRepository._build_neighbors`). Global (high-level): a **relation** vector store — the one net-new index (`relation_embeddings__<slug>` embedding `"src rel_type tgt"`, or an FTS fallback). **Do NOT install Apache AGE** — every AGE Cypher maps to plain SQL darkmem has (`_build_neighbors` = 1-hop; a `WITH RECURSIVE` CTE = multi-hop), and AGE brings `ag_catalog` search_path juggling, dollar-quote injection surface, and non-atomic upsert races darkmem already avoids.

### 1.4 Community tier (nano-graphrag) — reuse darkmem's Leiden *(unchanged, verified)*
`community_detector.py::CommunityDetector` already runs leidenalg+igraph on the **code** graph. Generalize to the memory graph → new `memory_communities` tables + a JobRegistry report job (LLM `community_report` prompt). Two query shapes, **do not conflate**: local = inject `report_string` as context alongside RRF; global map-reduce = a **separate MCP tool** (`memory_overview`), never the per-memory RRF. Re-prompt the generic "0-10 impact" rating toward operational importance for a dev graph.

---

## Phase 3 — Reconciliation, consolidation & memory types

| Mechanism | Source | Effort (v2) | Port in one line |
|---|---|---|---|
| Update-resolver ADD/UPDATE/DELETE/NOOP | mem0 `get_update_memory_messages` | M | resolver → **a direct supersede primitive** (M6), deletes OFF, off hot path |
| Entity-boost fusion signal | mem0 `_search_vector_store` | S-M | fan boost across `memory_ids`, IDF-damped, multiplicative on rrf_score |
| Sleep-time consolidation | letta `run_sleeptime_agents` | M-L | scheduling+watermark → JobRegistry `memory_consolidation` job |
| Debounced reflection | langmem `ReflectionExecutor` | S-M | per-project cancel-on-new debounce → `JobRegistry.trigger` |
| Memory evolution | A-mem `process_memory` | M-L | neighbor `llm_summary`/tags rewrite (gated) + `evolution_history` audit |
| Memory-type taxonomy | langmem | **M** | add `episodic`/`procedural`/`profile` — **taxonomy-first** (M2) |

### 3.1 Reconciliation resolver — with a direct supersede primitive (fixes M6)
`app/services/reconciliation.py::ReconciliationResolver` ports mem0's four-op resolver but maps onto darkmem's status lifecycle. **M6 correction:** the v1 sketch routed UPDATE → `detect_supersessions`, but that detector fires **only** on a `REPLACES` relation whose targets overlap `candidate.technologies`, same project, 90-day window, strictly-older — a resolver verdict satisfies **none** of these (non-tech facts have empty `technologies`; there is no `REPLACES` edge), so most resolver UPDATEs would silently supersede nothing. **Fix:** extract a **direct supersede primitive** `supersede(old, new)` that sets `status='superseded'` + `superseded_by` atomically, honoring the strictly-older/id-tiebreak guard; **both** the resolver (job-time) and `detect_supersessions` (write-time) call it. Deletes OFF by default (mem0 retreated to additive; langmem defaults `enable_deletes=False`) → route DELETE through `status='deprecated'`. Candidates via `HybridSearchService.search`. **m5-adjacent (mem0):** the UUID→int remap the v1 sketch said to "port verbatim" is **vestigial in current mem0** (built, never read back; the additive prompt asks for real UUIDs) — port the *idea* (don't let the LLM invent ids), not that code. Run in the consolidation job, not on ingest.

### 3.2 Entity-boost retrieval signal *(keep RRF, add the signal)*
Add `HybridSearchService._entity_boosts(query)`: fan a boost across `entity_relations.memory_ids`, damped `1/(1+0.001*(n-1)^2)` so hub technologies don't dominate; fold multiplicatively into `rrf_score` (mirrors `confidence_rank_gamma`), behind `entity_boost_enabled`. **m8: the query→entity linking is string/`pg_trgm` match against `entities.name` + the GIN `technologies` denorm, OR one ANN probe with the already-computed query embedding — NOT an LLM call** (an LLM call per search blows the latency budget). Entity cosine 0.5 is deliberately looser than the 0.85 dedup threshold — keep separate.

### 3.3 Consolidation scheduling (JobRegistry + debounce) *(unchanged, verified)*
`memory_consolidation` JobRegistry job (cron + per-job lock + `min_interval` + busy-409) reading a **per-project watermark** config row, over the dirty set. Front it with a langmem-style **debounce** (`schedule(project, after_seconds≈120)`, cancel-on-new) that calls `JobRegistry.trigger` (already lock-serialized). Cron is the durable backstop. **M5 (precedent correction):** the background-consolidation precedent is **letta / langmem / A-MEM — NOT mem0** (mem0 OSS *dropped* reconciliation; it has no background job). mem0's retreat is instead a data point for the conservative default (deletes off).

### 3.4 Memory evolution (A-mem) — riskiest, gated *(with taxonomy fix)*
In the consolidation job: neighbors via `HybridSearchService.search(top_k=5)`; LLM emits `{should_evolve, actions, new_context_neighborhood[], new_tags_neighborhood[]}`. `strengthen` → upsert graph edges appending `memory_ids`; `update_neighbor` → **rewrite neighbor `llm_summary`/tags only, never content**, with an `evolution_history JSONB` audit. **M2: any new edge type (`SUPPORTS`, `DERIVED_FROM`) must be added to `app/taxonomy.py` FIRST** — `SUPPORTS` is *currently a legacy alias mapped to `RELATED_TO`* (taxonomy.py:116), so "new SUPPORTS edges" would silently degrade; promoting it means removing the legacy alias (and noting historical rows were already rewritten). Honor the index-alignment contract (clamp + drop mismatches). **m7: A-mem rebuilds Chroma every 100 EVOLUTION events (`evo_cnt % 100`, counter increments only on `should_evolve=True`, memory_system.py:260-263), not every 100 additions** — darkmem does incremental HNSW re-embed of touched rows instead.

### 3.5 Memory types — taxonomy-first (fixes M2)
Extend `MEMORY_TYPES` (app/taxonomy.py) with `episodic`, `procedural`, `profile` + `LEGACY_MEMORY_TYPE_MAP` aliases. **Adopt the rule: no feature may emit a relation type or memory type that isn't already landed in `taxonomy.py` — plus a sweep of the hard-coded vocabularies BEFORE the emitting feature ships:** `reason()`'s 7-type `KNOWN_TYPES` tuple (memory.py:318-321), `extraction_clean.py`'s simple-7 classifier gate, and the UI type filters. Otherwise `normalize_memory_type` rewrites the new types to `fact` and `reason()` ignores them. Store langmem's four-field Episode payload (`observation/thoughts/action/result`) in JSONB so episodic memories are replayable few-shots. `profile` = one continuously-rewritten row per `(project,label)` (letta Block + langmem `enable_inserts=False`), token-capped + `read_only` honored by the job + null-byte strip. **Effort M (not S):** the taxonomy edit is S, but the hard-coded-vocabulary sweep makes it M. **Sequencing (review §6):** widening the simple-7 vocabulary changes extraction prompts and re-extraction is not bit-identical — land this **before baselining, or as an explicitly re-baselined step**, never mid-stream.

---

## Phase 0 / 3 — Ingestion, ranking priors & eval

| Mechanism | Source | Effort (v2) | Port in one line |
|---|---|---|---|
| Buffer/flush async ingestion | memobase `buffer.py` | M | `memory_buffer` table + `FOR UPDATE SKIP LOCKED` + `buffer_flush` job |
| Heat + recency + importance prior | MemoryOS + generative_agents | M | unify into ONE flag-gated multiplier on `rrf_score` |
| Reflection loop | generative_agents `run_reflect` | L | `memory_reflection` job → insight memories + evidence links |
| **LongMemEval harness + protocol** | LongMemEval | **L** | `backend/scripts/longmemeval_bench/`, per-qtype judge, budgeted tiers |
| Time-aware + fact-augmented retrieval | LongMemEval | M | 3rd RRF arm over `llm_summary`; `infer_time_range` soft ±2-day rerank |

### 0.1 Buffer/flush (Memobase is the exact stack twin) *(unchanged, verified)*
`memory_buffer(id, project, source, content, token_size, status, created_at)`; over-threshold flush via `process_batch`; **claim idle rows with Postgres `SELECT … FOR UPDATE SKIP LOCKED`** (no Redis; fixes memobase's own double-flush FIXME, verified verbatim at buffer.py:124); `buffer_flush` JobRegistry job sweeps stragglers. Keep a `wait_process` param for interactive MCP callers needing immediate queryability.

### 0.2 Ranking priors — unify into ONE multiplier
**m3 correction:** `importance` is **already populated at ingest** (pipeline.py:342-387 writes `mem_record.importance` from extraction output, 0-1 scale) — the gap is purely that **ranking never reads it**. No poignancy-rubric plumbing needed (calibration maybe). Add `memories.access_count INT DEFAULT 0` + `last_accessed TIMESTAMPTZ`; bump off-hot-path on read. **Compute heat at query time in SQL** (no stored heat column = no staleness), inside the same SELECT `_apply_confidence_weighting` runs (the verified single multiplier home, confidence.py:75 `rank_fusion_factor`):
```
multiplier = max(0, 1 + w_conf*(confidence-0.75)
                     + w_imp*(importance-0.5)
                     + w_rec*exp(-age_hours/tau)        -- tau ≈ 168h, wall-clock
                     + w_heat*log1p(access_count)_norm)
```
RRF cosine+FTS stays the dominant relevance base (gen-agents weights relevance 3× importance 2× recency 0.5×). Every `w_*` is a flag defaulting to 0, tuned on the harness before enabling.

### 0.3 Reflection loop → `memory_reflection` job *(with taxonomy fix)*
Salience-triggered: focal questions → `HybridSearchService.search` → LLM synthesizes insights → write each as a new memory, `expires_at=now+30d`, linked to evidence. **M2: `memory_type='insight'` and the `DERIVED_FROM` evidence edge must be added to `taxonomy.py` first** (else rewritten to `fact` / `RELATED_TO`). Cap insights per run; they can recurse.

### 0.4 The eval harness — with a cost budget & protocol (fixes M4)
`backend/scripts/longmemeval_bench/` mirroring `extraction_bench`'s cache-and-iterate. **Cost reality (M4):** LongMemEval_S is ~500 instances × ~40-50 sessions → ingesting through darkmem's pipeline is **10⁴–10⁵ extraction/classification LLM calls per full run**, plus per-question judging, plus a 100k+-token full-context baseline — days of local wall-clock or real API money *per iteration*, and the plan assumed iterating per flag. **Protocol (write into Phase 0):**
- **Pinned judge model + seeds** (judge lives in `evaluate_qa.py`, not `eval_utils.py` — m13; `eval_utils.py` holds only the retrieval metrics) so gate diffs aren't judge noise.
- **Three tiers:** fixture (10 checked-in instances) for the inner loop; `_oracle` (evidence-only) to isolate reader/judge from retrieval; **full-500 only at phase gates**, with a stated token+wall-clock budget per tier.
- **Ingest via `process_batch` directly** (offline harness), not the synchronous API (review §5) — and don't let the harness build silently become the buffer/flush build.
- **Freeze the ingestion-granularity decision once** (memory-per-turn vs per-session vs per-fact — it *changes what is measured* and thus recall comparability).
- **`extraction_bench` stays green as a co-gate.** Per-type accuracy (temporal off-by-one, knowledge-update stale-answer, abstention refusal) + `recall_all@k`/`ndcg_any@k` (skip the 30 abstention instances for retrieval). This scoreboard's *affordability* is what the plan's credibility rests on.

### 0.5 Two retrieval boosters that compose with RRF *(unchanged, verified)*
Fact-augmented expansion = a third RRF arm over the already-produced `llm_summary` (cheapest win). Time-aware pruning = an `infer_time_range` LLM pre-pass → a **soft ±2-day rerank** multiplier (a wrong inference costs position, never recall; cache by query hash).

---

## Cross-cutting decisions, prerequisites & first moves

**Named cross-phase prerequisite (m11 — promote from "quick win"):** `HybridSearchService.search` currently takes **no project/status/archived args** (hybrid_search.py:24-56); `memory.py:240-258` over-fetches then filters in Python (confirmed cross-project + superseded leakage). **The SQL filter pushdown — project/status/archived pushed into BOTH channels, contract-tested — is a blocking prerequisite of Phases 1/3/4 and Doc-5, not a Phase-0 nicety.** Every "scoped" claim downstream assumes it exists.

**m9:** new embedding parents (`triple_`/`relation_`/`block_embeddings__<slug>`) require `embedder_registry` changes **plus a one-time creation sweep for already-registered fingerprints** (the registry creates child tables on register; existing fingerprints won't have the new parents).

**Confirmed anti-ports (do NOT do):** Apache AGE (native SQL + recursive CTE); synonymy edges as `entity_relations`; cognee's pipeline framework (JobRegistry + 5-phase is already the DAG); Redis for buffering; per-query PPR/community rebuilds; **any LLM contradiction/consolidation/evolution call on the ingest hot path** (all off-path jobs).

**Effort realism (M9 — corrected):** edge-invalidation resolver **L→XL** (generalization + LLM purpose + prompt + two passes + B1 bridge + B2 re-extraction semantics + backfill + eval); bi-temporal migration **S + hidden M-L** (rename trivial; `fact` rendering + derive-from-`entity_relations` + historical `valid_at` inference + dual-store consistency is the real cost); LongMemEval harness **M-L→L** (the affordable-run protocol is the majority); memory types **S→M**; Doc-0 blocks **≥L** (largest single migration in Part II).

**Recommended first moves (v2, review-aligned — Phase 0 only):**
1. **LongMemEval harness + the affordability protocol** (§0.4) and baselines — nothing ships without a cheap, pinned scoreboard.
2. **SQL filter pushdown** (m11) — the blocking prerequisite; contract-test project/status/archived on both channels.
3. **Entity-match RRF signal** (§3.2) and the **fact-augmented `llm_summary` RRF arm** (§0.5) — cheapest measurable recall wins.
4. **Smoke-test the triple path** (m14) to satisfy "wire or delete" due diligence — but the bi-temporal migration + rebuild land in **Phase 2 proper**, not now.

**Parts III–IV pointer (added 2026-07-23 — sequencing, not yet port-sketched).** The companion plan now carries **Part III** (distribution/last-mile: III.1 auto-inject, III.2 browser web-chat capture, III.3 one-command client onboarding) and **Part IV** (product surface: IV.1 contribution-calendar dashboard, IV.2 "Dreaming" consolidation UX, IV.3 memory-hygiene queue). These come from a 2026-07-23 competitive scan (1AIVault + category), are directional, and are **intentionally absent from these source-verified notes** until they earn a real port sketch. Their phase dependencies, so sequencing stays consistent:
- **III.1 auto-inject** reuses `llm_summary` + ranking + `JobRegistry` → lands *after* Phase 3's consolidation/ranking exist; the marker-bounded idempotent write is the analog of `delete_by_memory_id`.
- **IV.2 "Dreaming"** is the UI/trigger over the **Phase 3** `memory_consolidation` job (§3.1/§3.3); its audit/undo rides the same supersession pointers + `evolution_history` (§3.4) — build it *with* that job, not after.
- **IV.1 dashboard calendar** depends on the **Phase 3** `access_count`/`last_accessed` columns (§0.2) and must tokenize via `resolveGraphTokens` (the Phase-0 palette fix).
- **IV.3 hygiene queue** depends on the **SQL filter pushdown** (m11) + the Phase-4 dedup ANN probe + supersession.
- **III.2/III.3** are net-new surfaces with no Part-I dependency; like Doc-0 they must be **gated** so they don't starve the core roadmap. None precede Phase 0/1 gates. Full rationale in plan §15–20.

*Full verbatim prompts/constants/`file:line` refs in `…/tasks/wdhh8wkcf.output` (digest `…/tool-results/b36ggvpev.txt`). Corrections in this v2 are ledgered in `2026-07-22-darkmem-evolution-plan-review.md`.*
