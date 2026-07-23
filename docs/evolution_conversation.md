# darkmem Evolution — Session Handoff / Resume Notes

**Session date:** 2026-07-22 · **Branch:** `feat/memory-graph-theming` · **Repo:** `D:/Repositories/_local_projects/darkmem`
**Purpose of this file:** a cold-start index so a new session can resume the darkmem evolution work without replaying the conversation. The **source-of-truth artifacts are the three `docs/2026-07-22-darkmem-evolution-*.md` files** (below); this file is the narrative map to them.

---

## 1. What happened this session (the arc)

Five linked pieces of work, in order:

1. **OmniRoute extraction-model selection** — discovered the user's LLM gateway, benchmarked candidate models on darkmem's own extraction F1 harness, recommended one, saved facts to darkmem. (§4 below.)
2. **darkmem evolution plan** — two parallel research workflows (competitive survey of ~20 agent-memory systems + a 4-agent code audit of darkmem), synthesized into a strategic re-architecture plan. (Part I of the plan.)
3. **Document-RAG / personal-wiki research** — a second competitive survey (PKM apps, doc-RAG platforms, parsing/chunking techniques, Notion/Obsidian data models) → a documents/wiki track. (Part II of the plan.)
4. **Source-level study** — 4 agents read the actual code of the cloned reference repos and produced implementation-ready port sketches. (The implementation-notes doc.)
5. **Fable adversarial review + remediation** — a stronger-model review verified claims against the code, found 3 blockers + majors + factual errors; both plan docs were remediated to **v2** and the review ledger records the fixes.

---

## 2. Deliverables (source of truth — read these first)

| File | What it is |
|---|---|
| `docs/2026-07-22-darkmem-evolution-plan.md` | **The strategy (v2).** Part I = agent-memory re-architecture, Phases 0–5. Part II = documents/personal-wiki, Doc-0–5 (firewalled to Doc-0/1/2). |
| `docs/2026-07-22-darkmem-evolution-implementation-notes.md` | **The "how" (v2).** Source-verified port sketches for Phases 0–3: schemas, algorithms, prompts, `file:line` refs, effort, gotchas. |
| `docs/2026-07-22-darkmem-evolution-plan-review.md` | **The adversarial review ledger** + a remediation-status table (every finding → where fixed). Verdict: *conditionally sound, now proceed-ready*. |

If resuming, read the plan first, then the notes for the phase you're starting, and check the review ledger's remediation table for context on why v2 differs from v1.

---

## 3. The strategy in brief

**Thesis:** darkmem is mispositioned relative to assets it already owns. It builds an entity/relationship knowledge graph on every ingest but **never uses it for retrieval** (verified: `memory_search`/`memory_reason` are pure vector+FTS+LLM). The whole competitive frontier (Zep/Graphiti, HippoRAG, LightRAG, cognee) is graph-native + temporal retrieval. So: **spend the graph on retrieval, add fact-level bi-temporal edges, move reconciliation off the hot path, measure everything against an affordable benchmark, then package for OSS and surface in the UI.**

**Part I phases:** 0 = eval harness + cheap RRF wins + SQL filter pushdown; 1 = HippoRAG-style Personalized PageRank retrieval channel + communities; 2 = bi-temporal `knowledge_triples` **rebuild** + contradiction invalidation; 3 = background consolidation (JobRegistry) + memory types + async/buffer ingestion + ranking priors; 4 = OSS platform (multi-tenancy, API keys, SDKs, observability); 5 = UI (retrieval explainability, temporal view, Insights).

**Part II (documents/wiki), firewalled:** committed = **Doc-0/1/2 only** ("chat with your documents" — parse→chunk→`blocks` table, retrieval upgrades, grounded citations). **Doc-3/4/5 (editor/canvas/CRDT) deferred as a separate product**, not committed until v1 proves demand. No Doc work before Phase 1's eval gate is green.

**Keystone data-model move:** a `blocks` table (stable ids, `parent_id`, `order_index`, `properties JSONB`, `char_span`) + `block_embeddings__<slug>` partition — one atom = chunk unit + citation anchor + link endpoint + transclusion target.

---

## 4. OmniRoute extraction-model finding (already actioned)

- **Gateway:** `http://192.168.0.196:20128`, OpenAI-compatible `/v1`, no API key on LAN. It aggregates ~393 models but **silently substitutes** (all `openai/*`→free `gpt-oss-120b`; `auto/*`→`mistral-large-latest`), many routes 429/timeout/403, and **defaults to SSE streaming unless `stream:false` is sent**. Mistral routes reject the `seed` param (HTTP 422).
- **Benchmark (darkmem's own F1 harness, 26-memory gold):** top quality = `mistral/mistral-medium-3-5` (ent 0.949 / rel 0.923) but it rejects seed; **recommended = `cerebras/gpt-oss-120b`** (ent 0.941 / rel 0.923, 0 errs, works with darkmem's pipeline unmodified). Config: `base_url .../v1`, `api_kind openai`, params `{temperature:0, max_tokens:8192, stream:false, reasoning_effort:low}`.
- **Status:** saved to darkmem (ids `888173f9…` gateway facts, `3de71b1c…` benchmark). **Not yet wired into darkmem's extraction config** — the `stream:false` orchestrator gap is a real fix worth doing.

---

## 5. Cloned reference repos

All in `D:\Repositories\Community` (verified present): graphiti, HippoRAG, LightRAG, nano-graphrag, mem0, letta, A-mem, langmem, memobase, MemoryOS, generative_agents, cognee, LongMemEval, supermemory. Plus adjacent: dify, memobase, memora, mempalace, notion-sdk-net, readest, GitNexus. The implementation-notes doc cites specific `file:line` in these for each port.

---

## 6. Critical decisions & corrections (from the v2 remediation)

- **`knowledge_triples`/`KnowledgeGraphService` is NOT a ready substrate** — it's untested LOCOMO demo scaffolding (hardcoded `married_to`/`is_pet_of` seeding, `entity_type='unknown'` stubs the orphan sweep actively deletes; verified at `repositories/graph.py:552-556`). The bi-temporal work is a **rebuild that keeps the table name**, sequenced into **Phase 2**, not a cheap Phase-0 "activation".
- **Contradiction/consolidation/evolution LLM calls run OFF the ingest hot path** (JobRegistry jobs), never inline. mem0's 2026 retreat to append-only is the evidence; the consolidation precedent is **Letta/LangMem/A-MEM** (mem0 OSS *dropped* reconciliation, no background job).
- **Three darkmem invariants that fixes must respect:** `chk_superseded_has_pointer` (status bridge: `superseded`+pointer only with exactly one live successor, else `deprecated`); idempotent re-extraction (define a triple analog of `delete_by_memory_id`); memory_id str/UUID drift (emit string ids at fusion boundaries).
- **Taxonomy-first rule:** any new relation/memory type (`SUPPORTS`, `DERIVED_FROM`, `insight`, `episodic`, `procedural`, `profile`) must land in `app/taxonomy.py` + a hard-coded-vocabulary sweep (`reason()` KNOWN_TYPES, extraction simple-7 gate, UI filters) BEFORE the feature emits it. (`SUPPORTS` is currently a legacy alias of `RELATED_TO`.)
- **SQL filter pushdown** (project/status/archived into both retrieval channels) is a **blocking prerequisite** of Phases 1/3/4, not a quick win.
- **Anti-ports:** no Neo4j, no Apache AGE (native SQL + recursive CTE + in-process igraph for PPR), no Redis (use `FOR UPDATE SKIP LOCKED`), synonymy edges stay ephemeral (not `entity_relations` rows).
- **Eval must be affordable:** full-500 LongMemEval ingest is ~10⁴–10⁵ LLM calls; protocol = pinned judge (`evaluate_qa.py`), 3 tiers (fixture/oracle/full-500-at-gates), ingest via `process_batch`, granularity frozen once, `extraction_bench` as co-gate.
- **`importance` is already populated at ingest** (`pipeline.py:342-387`) — only *ranking* ignores it. The single ranking multiplier home is `rank_fusion_factor`/`_apply_confidence_weighting`.

---

## 7. Open decisions still to resolve (named, not dropped)

1. Graph traversal engine (in-process igraph vs recursive CTE) — recommend igraph for converged PPR.
2. Bi-temporal substrate — recommend keep `knowledge_triples` name, rebuild, derive triples from `entity_relations` (single source of truth).
3. Consolidation aggressiveness — recommend conservative (deletes off, evolution audited).
4. SDK priority — consider pulling a minimal Python SDK forward.
5. Phase 1↔Phase 2 ordering (swappable only after B3's off-hot-path fix).
6. **Deferred to per-phase TDD plans:** the Phase-2 triple-lifecycle design doc + tests; the frozen LongMemEval ingestion granularity; the Phase-1↔4 PPR-cache mechanism (per-worker cache vs serialized snapshot vs sticky routing).

---

## 8. Recommended next steps

1. **Turn Phase 0 into a task-level TDD plan** under `docs/superpowers/plans/` (eval harness + affordability protocol, SQL filter pushdown, entity-match + `llm_summary` RRF arms, triple-path smoke test, UI palette quick wins).
2. Optionally wire `cerebras/gpt-oss-120b` into darkmem's extraction config and fix the orchestrator's `stream:false` gap (so OmniRoute works without the params workaround).
3. Save the durable facts to darkmem (the three evolution docs, the verified "knowledge_triples is demo scaffolding" finding, the strategic thesis) — offered but not yet done.

---

## 9. darkmem memories saved this session

- `888173f9…` — OmniRoute gateway integration facts (streaming default, seed-422, model substitution).
- `3de71b1c…` — extraction-model benchmark + `cerebras/gpt-oss-120b` recommendation.
- (Not yet saved: the evolution-plan pointer + the `knowledge_triples`-is-scaffolding finding — pending user confirmation.)

## 10. Where the raw research lives (may not persist)

Workflow transcripts under `~/.claude/projects/D--Repositories--local-projects-darkmem/<session>/subagents/workflows/` (competitive research, doc-RAG research, source study). The digested outputs were in the session scratchpad/tasks dir (session-scoped — likely gone in a new session). **The repo `docs/` files are the durable record; rely on them, not the transcripts.**
