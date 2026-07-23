# Adversarial Review — darkmem Evolution Plan (2026-07-22)

**Reviewed:** `2026-07-22-darkmem-evolution-plan.md` + `2026-07-22-darkmem-evolution-implementation-notes.md`
**Method:** every load-bearing claim was checked against `backend/app` source directly, and the port sketches were cross-checked against the cloned reference repos (`D:/Repositories/Community/*`: graphiti, HippoRAG, LightRAG, mem0, memobase, langmem, A-mem, MemoryOS, generative_agents, LongMemEval) by three source-level fact-check passes.

## Verdict

**Conditionally sound — proceed, but not as written.** Confidence: **high** on the code-verified findings below; **medium** on market/strategic judgments (several are unverifiable).

The plan's factual foundation is unusually good for a strategy document: the central architectural claims all verify (the graph is genuinely unused in retrieval; `HybridSearchService.search` fuses exactly two channels; `entities.memory_ids`/`entity_relations.memory_ids` exist and do form a bipartite passage↔entity graph; mem0's April-2026 retreat to append-only is real, commit-dated). The reference-repo port sketches are faithful to the source with only minor deviations.

But the plan has three defects serious enough to derail implementation if uncorrected: (1) the celebrated "activate `knowledge_triples`" move is a **rebuild dressed as an activation** — the existing service is untested demo scaffolding actively fought by the hourly orphan sweep; (2) the triple lifecycle as sketched **breaks two hard darkmem invariants** (idempotent re-extraction and `chk_superseded_has_pointer`); (3) Phase 2's plan text puts a per-edge LLM contradiction check **on the ingest hot path**, contradicting the plan's own thesis #2. Part II is correctly diagnosed as a surface over the same engine but is scoped like a second product and needs an explicit gate.

---

## Findings ledger

| ID | Severity | Location | Finding (one line) |
|---|---|---|---|
| B1 | **Blocker** | Notes §2.2 step 5 | Triple→memory-status bridge sets `status='superseded'` with no successor pointer — violates `chk_superseded_has_pointer` |
| B2 | **Blocker** | Notes §2.1–2.2, Phase 2 | No re-extraction semantics for triples: invalidate-don't-delete collides with the strip-before-rewrite idempotency invariant |
| B3 | **Blocker** | Plan §Phase 2 | Plan text runs the LLM contradiction check "on ingest" — on the hot path the plan's own thesis #2 says to vacate |
| M1 | Major | Plan §1.1, Notes header, Notes "first moves" #3 | "The expensive part is built" — false; `KnowledgeGraphService` is untested demo scaffolding the hourly orphan sweep actively deletes entities out from under |
| M2 | Major | Notes §0.3, §3.4 | Reflection/evolution features use `DERIVED_FROM`, `SUPPORTS`, `memory_type='insight'` — all silently rewritten by the closed taxonomy the notes themselves warn about |
| M3 | Major | Plan §Phase 4, §11.6 | Multi-tenancy badly underestimated: entities are globally unique and cross-project; graph channel, PPR cache, and community summaries all need ACL partitioning nobody scoped |
| M4 | Major | Plan §Phase 0, Notes §0.4 | The eval loop the whole plan gates on has no cost/latency budget; full-500 LongMemEval ingestion through darkmem's extraction pipeline is tens of thousands of LLM calls per run |
| M5 | Major | Plan §1.2 | mem0's landing spot mischaracterized: reconciliation was **dropped**, not "moved to background jobs" — no background reconciliation exists in mem0 OSS |
| M6 | Major | Notes §3.1 | Resolver UPDATE mapped onto `detect_supersessions`, whose trigger conditions (REPLACES + tech overlap + 90-day window) resolver output won't satisfy |
| M7 | Major | Plan §Phase 1, Notes §1.1 | PPR called "the single highest-leverage change" pre-measurement; hub-dominated small graphs may not reward it, hourly snapshot blinds it to fresh memories, and the in-process cache conflicts with Phase 4's multi-replica goal |
| M8 | Major | Plan §9, §12 | "darkmem is ~80% of a personal wiki" is engine-centric accounting; Doc-3/4/5 is a second product with no gate protecting the core roadmap |
| M9 | Major | Notes effort columns | Systematic underestimates: edge invalidation L→XL, memory types S→M, LongMemEval M-L→L, Doc-0 unsized but ≥L |
| m1 | Minor | Plan §3.1 | Reranker is not "40 serial LLM calls" — it is 8-way concurrent (`Semaphore(8)`) |
| m2 | Minor | Plan §3.2, §10, Doc-0 | "Hard 6000-char truncation" overstated: cap applies only to extraction/classification LLM input; storage, FTS, and embedding see full content |
| m3 | Minor | Notes §0.2 | "Populate `importance` at ingest" — it already is populated from extraction; only the ranking usage is missing |
| m4 | Minor | Notes §1.2 | Weak-slice numbers (paraphrase 0.745 / typo 0.76) and "bge-base/large (darkmem's embedders)" are stale — they come from the deleted 2026-04 fine-tuning effort, not the current production embedder |
| m5 | Minor | Notes §1.1 | HippoRAG seed formula deviates from source: numerator is the query→**fact** score (post DSPy filter, averaged per phrase), not entity cosine |
| m6 | Minor | Notes §2.1 | Graphiti `EntityEdge` has a fifth timestamp (`reference_time`, episode anchor) worth porting; "four-timestamp model" is incomplete |
| m7 | Minor | Notes §3.4 | A-mem rebuilds Chroma every 100 **evolution events**, not every 100 additions |
| m8 | Minor | Plan §Phase 0, Notes §3.2 | Query-time entity linking for the entity-match signal is unspecified — an LLM call per search would blow the latency budget |
| m9 | Minor | Notes cross-cutting | New embedding parents (`triple_`/`relation_`/`block_embeddings`) require `embedder_registry` changes plus a creation sweep for already-registered fingerprints |
| m10 | Minor | Notes §1.1 | The PPR channel must emit **string** memory ids at the fusion boundary (memory_id str/UUID drift invariant) — noted for the resolver, missed for the new channel |
| m11 | Minor | Plan §Phase 0 | `HybridSearchService.search` takes no project/status args at all — the SQL pushdown is a hard prerequisite of Phases 1/3/4, not a "quick win" |
| m12 | Minor | Plan §1.3, §2 | Unverifiable claims presented as fact: "OpenMemory deprecated into exactly darkmem's shape", "best UI in the category", Zep's 58.44 recompute |
| m13 | Minor | Notes §0.4 | LongMemEval judge lives in `evaluate_qa.py`; `eval_utils.py` holds only the retrieval metrics |
| m14 | Minor | Notes §2 generally | Every `knowledge_triples` repo helper has literally never executed (zero callers ⇒ empty table); treat all of `repositories/graph.py:537-710` as untested, including bind-type/CAST behavior |

---

## Findings in detail

### B1 — Status bridge violates `chk_superseded_has_pointer`

Notes §2.2 step 5: "when a triple whose `source_memory_ids` includes M is invalidated and M has no remaining live triples → set `memories.status='superseded'/'deprecated'`." The DB CHECK constraint (`chk_superseded_has_pointer`, documented invariant) forbids `status='superseded'` without `superseded_by`. A triple-level invalidation frequently has **no single superseding memory** — the contradicting triple may aggregate several `source_memory_ids`, or the invalidation may be temporal (stale-on-arrival) with no successor at all. As sketched, the bridge either aborts the transaction or forces an arbitrary pointer.
**Fix:** specify the rule precisely: `superseded` + pointer only when the invalidating triple has exactly one live source memory; otherwise `deprecated` with `superseded_by=NULL`. Write the constraint interaction into the Phase 2 design doc, with a test.

### B2 — Re-extraction idempotency undefined for triples

darkmem's Phase 5 invariant: strip prior `memory_id` graph contributions (`delete_by_memory_id`) before writing the new set — that is what makes re-extraction idempotent (CLAUDE.md; `pipeline.py` Phase 5). The bi-temporal layer's rule is the opposite: invalidate, never delete. The notes never reconcile the two. Concretely: memory M is re-processed after an edit; its old triples (asserted only by M) remain **live** with M in `source_memory_ids`; the new extraction emits different triples; nothing expires the stale ones — `triple_key` upsert only dedups *identical* facts. Repeat reprocessing (a routine darkmem operation) accretes contradictory live triples from a single memory. Also unhandled: `source_memory_id` is `ON DELETE SET NULL` today — memory deletion silently orphans triples.
**Fix:** define the triple analog of `delete_by_memory_id` before any write path lands: on re-extraction, expire (not delete) every live triple whose `source_memory_ids` would become empty after removing M; on memory deletion, same sweep. This is a fifth-phase-B design item, not an afterthought.

### B3 — Plan text puts LLM contradiction checks on the ingest hot path

Plan §Phase 2: "on ingest, LLM-check a new edge against semantically-related same-endpoint edges." That is one-plus LLM round-trips per extracted edge, inside the already-synchronous ingest path — precisely the write-time reconciliation cost the plan's thesis #2 argues the field is abandoning (and Phase 3 exists to remove). The notes hedge ("gate behind a flag and/or run bulk re-evaluation as a JobRegistry job") but the plan commits.
**Fix:** make the ingest side append-only for triples (deterministic temporal passes only — they're plain Python and cheap); run the LLM duplicate/contradiction resolution exclusively in the Phase 3 consolidation job over the dirty set. This also collapses a false sequencing dependency: Phase 2's riskiest piece becomes a Phase 3 consumer.

### M1 — "The expensive part is built" is false; this is a rebuild

Verified: `KnowledgeGraphService` has zero callers (`knowledge_graph.py` is imported nowhere) and `knowledge_triples` matches the schema the migration sketch assumes (`app/models/graph.py:47-61`). But "the work is a schema upgrade + wiring, not a greenfield build" (notes header) does not survive reading the service:

- `seed_from_entity_facts` (`knowledge_graph.py:162-202`) is LOCOMO-style demo seeding — `married_to`, `is_pet_of`, `loves`, `.capitalize()` display names. This was benchmark scaffolding, not a substrate.
- Triple endpoints are free-text `_slugify` strings, not FKs into `entities` — a parallel identity system the notes only partially address.
- `add_triple` inserts entity stubs with `entity_type='unknown'` (not in `ENTITY_TYPES`; the taxonomy would normalize it to `concept` but this path bypasses normalization) and **no `memory_ids`** — and the code's own comment (`repositories/graph.py:552-556`) says the hourly `graph_orphan_cleanup` sweep will reclaim exactly these rows. The production system actively garbage-collects this path's writes.
- Free-form predicates (`_normalize_predicate` lowercasing) vs the closed `RELATIONSHIP_TYPES` vocabulary is unreconciled with the "derive triples from `entity_relations`" open decision.

The one genuinely good consequence of "zero callers": the table is **empty everywhere**, so the column-rename migration itself is trivial and risk-free. The cost is entirely in the new build: population/backfill from `entity_relations`, `fact` rendering, resolver, tests.
**Fix:** reframe as "keep the table name, rebuild the layer"; strike "activation" from the first-moves list (see Sequencing); budget accordingly (see Effort).

### M2 — The notes walk into the taxonomy trap they themselves flag

`normalize_relation_type` rewrites any unknown relation to `RELATED_TO`, and `SUPPORTS` is *currently a legacy alias mapped to `RELATED_TO`* (`taxonomy.py:116`); `normalize_memory_type` rewrites unknown types to `fact` (`taxonomy.py:214-226`). The notes correctly forbid persisting `SYNONYM` edges for exactly this reason (§1.2) — then §0.3 proposes `DERIVED_FROM` evidence edges and `memory_type='insight'` reflection rows, and §3.4 proposes "new SUPPORTS" edges, none of which are in the taxonomy and all of which would silently degrade. `memory.py:318-321` additionally hard-codes the 7-type `KNOWN_TYPES` tuple in `reason()`.
**Fix:** adopt a rule: any new relation or memory type ships as a `taxonomy.py` edit (plus `LEGACY_*` audit — promoting `SUPPORTS` means removing the legacy alias, and historical rows were already rewritten) plus a sweep of hard-coded vocabularies (`reason()`, extraction_clean simple-7 gate, UI filters) **before** the feature that emits it.

### M3 — Multi-tenancy and shared-document ACLs are deeper than scoped

"The write side is half-built (`api_key_id` already plumbed into the audit path)" — a stretch: every call site passes `api_key_id=None` (`routes/memories.py:47-163`, `mcp/server.py:140-287`); only the audit log accepts it. The real cost is the graph: `entities` are globally unique on `(name, entity_type)` with cross-project `memory_ids[]`; two tenants asserting "postgres" share one row. Tenant scoping means changing the uniqueness key, per-tenant dedup/canonicalization in pipeline Phases 4–5, and per-tenant `delete_by_memory_id` semantics. Part II §11.6's "permission-at-retrieval-time inside the search SQL" covers only the vector/FTS channels — a PPR walk over a shared graph, a cached igraph snapshot, and LLM community summaries computed over mixed-ACL content all leak across boundaries at read time. Nobody scoped ACL-aware community reports.
**Fix:** treat `project` as the tenancy unit from Phase 1 onward (the notes' per-project graph is the right instinct — make it mandatory, not open); scope Phase 4 as a schema change (entity uniqueness + pipeline), not plumbing; require every new retrieval channel (PPR, communities, blocks) to take the same ACL predicate as the SQL pushdown from day one.

### M4 — The scoreboard has no budget

Every phase gates on LongMemEval, but nobody priced a run. LongMemEval_S is ~500 instances × ~40–50 haystack sessions; ingesting through darkmem's real pipeline means an extraction (+classification) LLM call per memory — order 10⁴–10⁵ LLM calls per full ingest, plus per-question judging, plus a "full-context baseline" that needs a 100k+-token-context model. On a local model that is days of wall-clock; on cloud APIs it is real money per iteration — and the plan's cadence assumes iterating per flag. The notes' fixture-first instinct (5–10 checked-in instances, `_oracle` start) is right but not developed into a protocol. Separately, fit caveats: LongMemEval is chat-session QA; darkmem is an agent fact-store — the ingestion-granularity open decision (per-turn vs per-session vs per-fact) *changes what is being measured*, and judge-LLM variance needs a pinned judge + seeds or phase gates will be noise.
**Fix:** write the eval protocol into Phase 0: pinned judge model, fixture tier (10) for inner-loop, oracle tier for reader isolation, full-500 only at phase gates, token/wall-clock budget per tier, granularity decision made once and frozen, and `extraction_bench` kept green as the regression co-gate.

### M5 — mem0's landing spot is mischaracterized (the retreat itself is real)

Verified against the clone: commit dated 2026-04-14 ("port v3 pipeline… additive scoring", #4805) made the write path ADD-only (`ADDITIVE_EXTRACTION_PROMPT`, "sole operation is ADD", `prompts.py:472`); `get_update_memory_messages` survives as dead code called only by tests. So thesis #2's factual core stands. But the plan says reconciliation moved "to retrieval time and to background jobs" — mem0 OSS has **no background reconciliation job**; it has inline hash-dedup, retrieval-time expiry filtering, and manual API edits. Reconciliation wasn't relocated; it was largely dropped. That matters because the plan cites mem0 as evidence for the consolidation-job direction, when the actual precedents are letta/langmem — and it weakens "background consolidation is the biggest capability every leader has" (the leader by adoption shipped *nothing*). The direction is still defensible; the evidence attribution is wrong. (Also noteworthy from the source: mem0's UUID→int mapping is now vestigial — built but never read back, with the additive prompt asking for real UUIDs — so "port verbatim" should port the *idea*, not that code.)
**Fix:** re-attribute the consolidation precedent to letta/langmem/A-MEM; add "mem0 dropped reconciliation entirely" as a data point for the conservative default (deletes off).

### M6 — Resolver UPDATE cannot ride `detect_supersessions`

Notes §3.1 maps resolver UPDATE → "insert new active + `detect_supersessions`". But `detect_supersessions` fires only when the new memory carries a `REPLACES` relation whose lowercased targets overlap `candidate.technologies`, within same project + 90-day window + strictly-older guard. A resolver verdict ("row 3 is updated by this new fact") satisfies none of those triggers — non-technology facts have empty `technologies`, and no `REPLACES` relation exists. Routed as written, most resolver UPDATEs silently supersede nothing.
**Fix:** add a direct supersede primitive (set `status='superseded'` + `superseded_by` atomically, honoring the strictly-older/id-tiebreak guard) that both the resolver and `detect_supersessions` call; keep the detector as the write-time trigger and the resolver as the job-time trigger of the same primitive.

### M7 — PPR: right experiment, oversold and under-plumbed

Calling Phase 1 "the single highest-leverage change" before any measurement contradicts the plan's own prime directive; the notes even list "is the memory graph dense enough for PPR to beat plain RRF" as an open decision. Real risks: a personal-dev memory graph is small and hub-dominated (postgres, docker, python) — PPR mass concentrates on hubs; the IDF damping (verified faithful to HippoRAG's `weight /= |chunk_ids|`, modulo m5) helps but the gain over RRF + `technologies` filtering is unproven. Operationally: the hourly-cached snapshot means memories ingested since the last build are invisible to the graph channel — exactly the fresh memories agent workflows query next ("what did we just decide") — so the channel must degrade gracefully to hybrid for unseen ids (the notes' sum>0 fallback covers empty seeds, not stale snapshots). The in-process cache is viable today because prod runs a single uvicorn worker (`entrypoint.sh`: no `--workers`), but Phase 4's two-replica goal invalidates it; dev `--reload` wipes it every save.
**Fix:** keep Phase 1 but frame it as a measured hypothesis; append fresh memory ids to the snapshot bipartite edges at query time (cheap: one `unnest(memory_ids)` delta query); write down now that the cache is per-process and Phase 4 requires either sticky routing, a serialized snapshot table, or acceptance of per-replica duplication.

### M8 — Part II is a second product wearing a surface's clothing

The correct parts: blocks-as-the-atom is the right keystone; links-as-`entity_relations` is real (the bipartite provenance verified); retrieval upgrades (BM25, cross-encoder, late chunking) genuinely serve both surfaces; proposition ingestion is the one genuinely darkmem-native differentiator. The over-claim: "~80% of an LLM-native personal wiki" counts engine work as the product. For a PKM, the majority of user-facing surface is the editor, views, transclusion UX, canvas, import — Doc-3/4/5 territory — and "embed BlockSuite" is not a small integration (CRDT-native document model meeting a server-authoritative Postgres + TanStack app). Obsidian's moat is its editor+ecosystem, not search. Meanwhile Doc-0 depends on nothing in Part I, which is exactly the danger: it can start immediately and consume the core roadmap's oxygen.
**Fix:** commit in the plan to a gate: no Doc-track work before Phase 1 ships its eval gate; scope Part II v1 to Doc-0/1/2 (parse → blocks → grounded citations — a "chat with your documents" feature of the memory product, not a wiki); move Doc-3/4/5 to an explicit "not planned until v1 proves demand" appendix; delete the 80% claim.

### M9 — Effort estimates (see the Effort section below for the full table)

### Minor findings — corrections in brief

- **m1:** `reranker.py:49` — `Semaphore(8)` + `asyncio.gather`; concurrent, not serial. The real critique is 40 LLM calls/search and uncalibrated 0–10 scores, which the cross-encoder swap (§11.2) fixes.
- **m2:** `_MAX_CONTENT_CHARS=6000` truncates only extraction/classification LLM input (`classification_llm.py:13,42`; `extraction.py:39`). Stored content is full; the FTS trigger indexes full content (migration 0001:313); `embed_batch` sends full text. The true gap: long tails are missing from the **graph and classification**, not from retrieval. Doc-0's rationale should say that.
- **m3:** `pipeline.py:342-387` already writes `mem_record.importance` from extraction output (0–1 scale; prompt examples emit it). The gap is purely that ranking never reads it — no new "poignancy rubric" plumbing needed, though calibration may be.
- **m4:** the 0.745/0.76 slice MRRs and "bge-base/large (darkmem's embedders)" date from the fine-tuning effort deleted in the 2026-05-01 ML removal; the production embedder is whatever the LLM config row says. Re-derive weak slices on the Phase 0 harness before tuning the 0.8 synonymy threshold against them.
- **m5:** HippoRAG's phrase seed numerator is the query→fact similarity of DSPy-filtered facts, then averaged per phrase (`HippoRAG.py:1594-1615`) — the notes' "cosine / COALESCE(array_length(memory_ids,1),1)" substitutes entity cosine. Acceptable simplification; label it as a deviation and tune independently rather than assuming HippoRAG's constants transfer.
- **m6:** `graphiti_core/edges.py:280-282` adds `reference_time` (episode reference timestamp) — five datetime fields, not four. darkmem has a natural analog (source memory `created_at`); worth carrying.
- **m7:** A-mem's rebuild triggers on `evo_cnt % 100` where the counter increments only on `should_evolve=True` (`memory_system.py:260-263`) — per-100 evolutions.
- **m8:** decide the entity-linking mechanism for the entity-match arm now: exact/`pg_trgm` string match against `entities.name` + the GIN `technologies` denorm (cheap), or entity-ANN via the query embedding already computed (one extra probe). Not an LLM call.
- **m11:** `hybrid_search.py:24-56` — `search()` has no project/status/archived parameters; `memory.py:240-258` over-fetches (limit+offset+50) then filters in Python. Cross-project leakage confirmed; superseded rows also burn candidate slots. Everything in Phases 1/3/4 that says "scoped" assumes this fix exists.
- **m14:** because zero callers means the triple SQL never ran, smoke-testing must cover asyncpg bind types (the CAST invariant), `NULLS LAST` ordering, and the read-then-write race in `add_triple` (`knowledge_graph.py:53-58`) the `triple_key` upsert is meant to kill.

### What holds up (verified, briefly)

Thesis #1 is true as stated: `memory_search`/`memory_reason` never touch the graph (`memory.py`, `pipeline.py:848-876`); chat does entity-expansion only. The two-channel fusion, `rank_fusion_factor` as the single multiplier home (`confidence.py:75`, `pipeline.py:878-931`), `confidence_rank_gamma` default 0.0, `ApiKey` unwired, regex confidence placeholder, Leiden-on-code-only, orphaned `src/demo/` (zero importers), and the 52 hard-coded hex values (32 in `_authenticated/index.tsx` + 20 in `source-colors.ts`) all verify. igraph+leidenalg are already hard deps (`pyproject.toml:56-57`); `JobRegistry` really does support `max_run_seconds` (`job_registry.py:364`). The anti-ports are all well-judged and source-confirmed: LightRAG's Postgres graph genuinely requires AGE (`postgres_impl.py:818`) — avoiding it is right; memobase's double-flush FIXME is verbatim in the source (`buffer.py:124`) and `FOR UPDATE SKIP LOCKED` is the correct Redis-free replacement; Graphiti's stale-on-arrival rule, disjoint-window guard, continuous-index prompt contract, and entropy-gate thresholds are all faithfully transcribed. Generative-agents weights (0.5/3/2), MemoryOS heat, langmem `enable_deletes=False` defaults, LongMemEval judge/metrics/oracle-variant: verified. mem0's entity+BM25+semantic fusion is in OSS (not platform-only), supporting the Phase-0 entity-match move.

---

## Sequencing critique

1. **The notes contradict the plan on the keystone.** Plan §Phase 0 decides "wire, don't delete… substrate for *Phase 2*… if Phase 2 slips, delete it." Notes' "recommended first three moves" #3 pulls the bi-temporal migration into the opening moves — before any temporal metric exists, and before B1/B2/B3 are resolved. Front-loading the plan's riskiest, least-tested subsystem inverts the plan's own measurement-first directive. **Recommendation:** Phase 0 = harness + entity-match arm + `llm_summary` arm + SQL pushdown + UI quick wins, nothing else. Smoke-test the triple path (cheap, satisfies "wire or delete" due diligence) but migrate in Phase 2 proper.
2. **SQL filter pushdown is a dependency, not a quick win.** Per-project PPR seeding (Phase 1), resolver candidate scoping (Phase 3), tenancy/ACLs (Phase 4, Doc-5) all assume `HybridSearchService.search` can filter in SQL. Name it as a blocking prerequisite with its own contract (project, status, archived pushed into both channels).
3. **Phase 2's LLM resolver belongs to Phase 3's machinery** (B3). Re-drawing that line removes the scariest Phase 2 item and lets Phase 2 ship as: migration + append-only triple writes + deterministic temporal passes + point-in-time reads. Cleaner, testable, reversible.
4. **Phase 1 vs Phase 4 cache conflict** (M7): decide the snapshot story once, now — otherwise Phase 4 forces a Phase 1 rewrite.
5. **Phase 0's own harness wants Phase 3's ingestion.** Ingesting 500 haystacks through the synchronous API is painful; run the bench through `process_batch` directly (offline harness), or pull a minimal async/batch ingest forward. Don't let the harness build silently become the buffer/flush build.
6. **Taxonomy/extraction changes invalidate baselines.** Widening the simple-7 vocabulary or the merge gate changes extraction prompts, and re-extraction under a different gate state is not bit-identical (documented pipeline property). Land Phase 3's taxonomy widening either before baselining or as an explicitly re-baselined step — not mid-stream.
7. **Part II needs a gate, not a vibe** (M8): no Doc-0 work before Phase 1's eval gate is green.
8. §7.5's "Phase 1 ↔ Phase 2 can swap" is true only after B3's fix — as written, Phase 2 carries hidden Phase 3 machinery and cannot go first.

## Effort-realism critique

| Item | Plan | Realistic | Why |
|---|---|---|---|
| Edge-invalidation algorithm | L | **XL** | It is: supersession generalization + new LLM purpose + prompt port + two temporal passes + B1 bridge design + B2 re-extraction semantics + backfill of `entity_relations`-derived facts + eval. Graphiti's equivalent spans three modules plus prompts. |
| Bi-temporal migration | M | S + hidden M-L | The rename itself is trivial (table provably empty). The real work — `fact` rendering, deriving triples from `entity_relations`, `valid_at` inference for historical rows, dual-store consistency — is where M-L lives, and it's listed as an "open decision" rather than costed. |
| LongMemEval harness | M-L | **L** | Harness code is M; the affordable-run protocol, ingestion-granularity decision, judge pinning, and paying for full-500 ingest runs are the majority of the cost (M4). |
| Memory types | S | **M** | Taxonomy edit is S; but the notes' own gotcha (simple-7 classifier vocabulary + merge gate) plus `reason()` KNOWN_TYPES, type-filtered retrieval, and UI filters make it M. |
| Entity-boost signal | S-M | S-M | Fair — *if* linking is string/ANN-based (m8). |
| PPR channel | L | L | Fair, plus budget the tuning cycles (damping, seed weights, synonymy threshold are all re-tuned, per m4/m5). |
| Buffer/flush | M | M | Fair; the memobase mechanics verified simple. |
| Consolidation job | M | M–L | Scheduler is M (JobRegistry genuinely fits); the resolver+evolution content it runs is where risk lives, and A-mem's index-alignment fragility (verified in source) argues for the gated-conservative default. |
| Doc-0 (blocks) | unsized | **L minimum** | Parser dependency integration, blocks schema + new embedding parent (m9), provenance, re-ingest idempotency, API surface, and UI rendering — presented as a thin stage, it is the largest single migration in Part II. |

## If you change only 5 things

1. **Reframe Phase 2 as a rebuild and fix its correctness holes before any code**: contradiction resolution runs off the hot path only (B3); triple re-extraction/deletion semantics defined as the analog of `delete_by_memory_id` (B2); the memory-status bridge specified against `chk_superseded_has_pointer` (B1). Strike "activate `knowledge_triples`" from the first-moves list; keep the smoke test.
2. **Write the eval protocol and budget into Phase 0** (M4): pinned judge, three-tier runs (fixture / oracle / full-500 at gates only), token+wall-clock cost stated, ingestion granularity frozen, `extraction_bench` as co-gate. The plan's credibility rests entirely on this scoreboard being cheap enough to consult.
3. **Promote the SQL filter pushdown to a named cross-phase dependency** (m11) — project/status/archived pushed into both retrieval channels, contract-tested, before Phase 1 seeding or Phase 3 scoping.
4. **Adopt the taxonomy-first rule** (M2): no feature may emit a relation type or memory type that isn't already landed in `app/taxonomy.py` (plus the legacy-map and hard-coded-vocabulary sweep). Three of the plan's own features currently violate it on paper.
5. **Gate Part II** (M8): Doc-0/1/2 only, starting after Phase 1's gate is green; editor/canvas/CRDT explicitly out of the committed plan; delete the "~80% of a wiki" framing and re-attribute the consolidation precedent from mem0 to letta/langmem (M5).

---

## Remediation status (v2 — applied 2026-07-22)

Both plan documents were updated to v2 in response to this review. Resolution per finding:

| ID | Status | Where fixed |
|---|---|---|
| B1 | **Fixed** | notes §2.2 (status bridge: `superseded`+pointer only with one live successor, else `deprecated`); plan Phase 2 [logic] |
| B2 | **Fixed** | notes §2.2 (triple re-extraction/deletion sweep = analog of `delete_by_memory_id`); plan Phase 2 [flow] |
| B3 | **Fixed** | contradiction LLM check moved to the Phase 3 consolidation job; ingest is append-only + deterministic passes — notes §2.2, plan Phase 2/3 + §6 guardrail |
| M1 | **Fixed** | reframed as a rebuild that keeps the table name (demo scaffolding, orphan-swept) — plan §1.1/§6/Phase 2, notes header/§2 |
| M2 | **Fixed** | taxonomy-first rule added — plan §6, notes §3.4/§3.5/§0.3 |
| M3 | **Fixed** | multi-tenancy reframed as a schema change with ACLs on every retrieval channel — plan §3.3/Phase 4/§11.6 |
| M4 | **Fixed** | eval affordability protocol (pinned judge, 3 tiers, budget, `process_batch` ingest) — plan Phase 0, notes §0.4 |
| M5 | **Fixed** | mem0 dropped reconciliation; precedent re-attributed to Letta/LangMem/A-MEM — plan §1.2/§2/Phase 3, notes §3.3 |
| M6 | **Fixed** | direct `supersede()` primitive both resolver and `detect_supersessions` call — notes §3.1 |
| M7 | **Fixed** | PPR framed as a measured hypothesis; snapshot freshness + per-worker cache/Phase-4 conflict written down — plan Phase 1, notes §1.1 |
| M8 | **Fixed** | Part II firewalled to Doc-0/1/2; Doc-3/4/5 deferred; "~80%" deleted — plan §9/§12/§14 |
| M9 | **Fixed** | effort corrections (edge-invalidation→XL, bi-temporal split, LongMemEval→L, memory-types→M, Doc-0≥L) — notes tables + cross-cutting |
| m1 | **Fixed** | reranker = 8-way concurrent (`Semaphore(8)`) — plan §3.1 |
| m2 | **Fixed** | 6000-char cap scoped to extraction/classification input — plan §3.2/§10 |
| m3 | **Fixed** | `importance` already populated at ingest; only ranking usage missing — plan §3.1, notes §0.2 |
| m4 | **Fixed** | weak-slice MRRs labeled stale (deleted fine-tuning); re-derive on harness — notes §1.2 |
| m5 | **Fixed** | HippoRAG seed = query→fact; entity-cosine substitution labeled a deviation — notes §1.1, plan Phase 1 |
| m6 | **Fixed** | `reference_time` (5th timestamp) added — notes §2.1, plan Phase 2 |
| m7 | **Fixed** | A-mem rebuild = per-100 evolutions — notes §3.4 |
| m8 | **Fixed** | entity-match linking = string/pg_trgm/ANN, not an LLM call — notes §3.2, plan Phase 0 |
| m9 | **Fixed** | new embedding parents need `embedder_registry` change + creation sweep — notes cross-cutting, plan §10 |
| m10 | **Fixed** | PPR channel emits string memory ids — notes §1.1, plan Phase 1 |
| m11 | **Fixed** | SQL filter pushdown promoted to a named blocking prerequisite — plan Phase 0/§4, notes cross-cutting |
| m12 | **Fixed** | unverifiable claims softened (OpenMemory shape, "best UI", the mem0↔Zep dispute) — plan §1 |
| m13 | **Fixed** | judge lives in `evaluate_qa.py`, not `eval_utils.py` — notes §0.4 |
| m14 | **Fixed** | all triple SQL flagged untested; smoke-test asyncpg bind/CAST + read-then-write race — notes §2/§0, plan Phase 0 |

**Not yet resolved (deferred to per-phase TDD plans, not plan-level):** the concrete Phase-2 design doc + tests for the triple lifecycle (B1/B2/B3 mechanics), the frozen LongMemEval ingestion-granularity decision (M4), and the Phase-1↔Phase-4 PPR-cache mechanism choice (M7) — each is named in the v2 plan as a decision to make when its phase is planned.
