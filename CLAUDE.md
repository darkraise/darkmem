# Darkmem — business logic baseline

Centralized memory system for AI agents. Commands and layout first;
everything from "Domain model" down is contract, not implementation
detail. A refactor that breaks one of the listed invariants is a
behavior change, not a cleanup.

## Commands

- **Merge gate (from the repo root): `./scripts/gate.sh`** — one command for
  the whole floor: the alembic single-revision assertion, backend pytest,
  frontend typecheck/test/build, the benchlib harness suite, and the F1 bench
  in `--algo-only` mode. `--full` adds the retrieval eval, the API e2e
  suite (`backend/scripts/e2e/`, boots its own disposable stack), the
  Playwright e2e run, and a port-hygiene diff.
  Exits non-zero naming the failing gate; `GATE BLOCKED` (exit 2) means a
  missing toolchain, not a red gate. **`pyproject.toml` sets
  `testpaths = ["tests"]`, so plain `pytest -q` does NOT collect
  `scripts/benchlib/tests`** — run the gate, or the harness can break while the
  floor stays green.
- Backend tests (from `backend/`): `python -m pytest -q`. Needs a
  `darkmem_test` database on the dev-compose Postgres
  (127.0.0.1:5433); create it once:
  `psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test;"`.
  conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` (default
  `postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test`),
  then runs `DROP SCHEMA public CASCADE` and `alembic upgrade head` —
  never point it at a real database.
- Frontend (from `frontend/`): `npm run typecheck` (= `tsc -b`; plain
  `tsc` misses the project refs), `npm test` (vitest; excludes
  `tests/`, which is Playwright e2e via `npm run test:e2e`),
  `npm run build`. `npm run lint` is advisory.
- Dev servers: `./scripts/start_dev_server.sh` = alembic upgrade +
  uvicorn :8000 `--reload --timeout-keep-alive 75` (the 75 prevents
  sporadic 502s through the vite proxy); `cd frontend && npm run dev`
  = vite :3636 proxying `/api`, `/health`, `/ws` to :8000.
- Migrations (from `backend/`): `python -m alembic upgrade head`.
  `migrations/env.py` reads `DATABASE_URL` via app settings (default
  port 5432) and ignores `alembic.ini`'s URL; the dev-compose Postgres
  is on 5433, so set `DATABASE_URL` explicitly for host-side runs.
  Containers migrate at startup via `entrypoint.sh`;
  docker-compose.dev.yml overrides the command and skips migrations.
- **The schema is ONE revision — `0001_baseline.py` — and it is not
  frozen yet.** Until the freeze, a schema change **regenerates that
  file in place** and you drop/recreate the database; it never appends
  a `0002`. `./scripts/gate.sh` asserts exactly one revision and fails
  loudly otherwise. Schema changes **serialise through one owner per
  epic**: the baseline is a single shared mutable file, so two lanes
  editing it conflict every time. The freeze is an **event, not a
  date** — the first deploy whose data must survive (the homelab
  cutover). At that event the revision is tagged `schema-frozen`, the
  gate assertion stands down, and every later change is an ordinary
  additive revision forever. **Freeze date: not yet frozen.** Full
  protocol and the object inventory the baseline implements:
  `docs/planning/baseline-schema-inventory.md`.
- Stacks: dev `docker compose -f docker-compose.dev.yml up -d` (no
  .env needed); prod `docker compose up -d` (host networking; requires
  `DB_PASSWORD` + `JWT_SECRET` ≥ 32 chars in .env, `COOKIE_SECURE=false`
  for plain-HTTP LAN). Rebuild the image first:
  `./scripts/build-push.sh` — **one** image now (`darkraise/darkmem-api`),
  built from the repo-root `Dockerfile`, carrying the API and the built SPA
  together; the app serves the UI on `:8000` and nothing binds `:80`.
- Backend lock: regenerate only with
  `uv pip compile --universal pyproject.toml -o requirements.lock` —
  a non-universal Windows resolve leaks pywin32 and drops uvloop.
  `entrypoint.sh` must stay LF (.gitattributes enforces it).

## Layout

`backend/app`: `api/routes` (REST), `api/mcp` (FastMCP, mounted at
`/mcp`), `services` (pipeline.py, extraction_clean.py,
code_pipeline.py, job_registry.py, ...), `repositories`
(graph/relational/vector), `models`, `schemas`; entry point
`app/main.py`. `backend/migrations/versions` is Alembic;
`backend/scripts` holds the eval harnesses: `extraction_bench/` (the F1
bench and its gold files) and `benchlib/` (corpus loader, offline ingest
driver, run ledger, retrieval gold + scorer, latency/token twin,
full-context comparator, and the `run_*.py` runners).
`frontend/src`: `features/*` plus TanStack Router file-based `routes/`
— `routeTree.gen.ts` is generated, never hand-edit it. `docs/` holds
dated audit reports, `api-rest-conventions.md` (the REST contract new
endpoints must match: 201 create, 204 delete, 202 async-accepted,
POST `.../search` for complex queries), `superpowers/specs/` design
specs, and `e2e/` runbooks.

## Domain model

Memory rows live in `memories`. Each row has a status lifecycle:
`active → superseded → deprecated`. The CHECK constraint
`chk_superseded_has_pointer` forbids `status='superseded'` without
`superseded_by` set; supersession code must always set both atomically.
Memories may carry `expires_at` (nullable TTL); the
`expired_memory_cleanup` job deletes rows past it. Before deleting any
memory that others reference via `superseded_by` (TTL sweep or
interactive delete), demote those dependents to `status='deprecated'`
with `superseded_by=NULL` first — the FK is ON DELETE SET NULL, so
skipping the demotion violates `chk_superseded_has_pointer` and aborts
the whole batch.

A memory carries:

- `content` (Text) and `source` (where it came from: `mcp`, `api`, ...).
- `project` (Text, default `default`) — the supersession scope.
- `memory_type` from `MEMORY_TYPES` in `app.taxonomy`.
- `classified_type` / `summary` / `emotions` / `flags` —
  classification/enrichment output, populated on every ingest. The `llm_`
  prefix was dropped in the baseline (doc 04 §3.1) because the classifier
  may be the local model, and T1.42e (2026-07-28) retired the prefix from
  every wire surface too: REST (`MemoryResponse`, `app/utils/serialization.py`)
  and the websocket broadcast payload (`app/services/pipeline.py`) now read
  `classified_type` / `summary` / `emotions` / `flags`, matching the columns
  exactly, with no compatibility shim and no dual emission. The regex
  classifier and its `classified_confidence` column are gone; classification
  runs through the LLM, or the in-process classifier when the classification
  purpose's inline `classifier_kind` is `local`.
- `origin_key` (Text, nullable) — capture-session identity, the
  corroboration-independence key facts count `DISTINCT` on. **It has writers on
  both doors** since T1.11 (`resolve_origin_key`, called from
  `api/routes/memories.py` and `api/mcp/server.py`, and on the raw entry dicts
  for batch adds) — the "no writer yet" note here was stale and was corrected
  2026-07-28. **No response echoes it**: it is absent from `MemoryResponse`, so
  it is write-only over the wire and only a direct database read can observe it.
  A test asserting it through any door's response will assert nothing.
- `updated_at` is bumped by the **`touch_updated_at` SQL trigger**, not by
  SQLAlchemy's client-side `onupdate`: a raw-SQL UPDATE must move it too.
- `technologies` (lowercase Text[]) — denormalised cache of entity names
  whose `entity_type` is in `TECH_TYPES`. The supersession detector and
  the retrieval filter both consult this column instead of joining.
- `confidence` (REAL, default 0.75) — content-quality estimate; used by
  `_apply_rank_fusion_factor` when `confidence_rank_gamma > 0`.

Entities and relations live in `entities` / `entity_relations` and are
**not memory-scoped**: each row carries a `memory_ids` UUID[] of every
memory that asserts it. Uniqueness is `(entities.name, entity_type)` and
`(entity_relations.source_entity_id, target_entity_id, rel_type)`.
Creating an entity or relation that already exists must append the new
memory to `memory_ids`, not insert a duplicate row.

## Taxonomy is closed

`ENTITY_TYPES` and `RELATIONSHIP_TYPES` in `app/taxonomy.py` are the
**only** values stored. The LLM may emit anything; everything must pass
through `normalize_entity_type` / `normalize_relation_type` first.
Unknown entity types fall back to `concept`; unknown relations fall
back to `RELATED_TO`. `LEGACY_*_TYPE_MAP` rewrites historical names
(e.g. `framework → tool`, `RUNS_ON → DEPLOYED_ON`) at runtime so old
rows keep matching new code. Adding a type means editing those tables;
relying on a free-form value will silently get rewritten.

## Capture is buffered (`memory_buffer`, doc 05 §2)

All four capture doors — REST `POST /memories` (+`/batch`) and MCP
`memory_add` / `memory_batch_add` — validate, resolve `source` and
`origin_key`, enqueue a `memory_buffer` row and return **202** with a
`CaptureAck`. The ack's id is the **pre-minted memory id**, which rides
the buffer row's `metadata_`; the buffer row's own id is a separate
tracking handle — never conflate the two. `wait_process=true` is the
opt-in synchronous escape: it drives that row's flush inline through the
same `FOR UPDATE SKIP LOCKED` claim the scheduled job uses and returns
the processed memory (201), bounded by `buffer_wait_timeout_seconds`
before degrading to the plain ack. The `buffer_flush` job drains the
queue; its four thresholds (`buffer_claim_batch`, `buffer_max_attempts`,
`buffer_claim_visibility_seconds`, `buffer_done_retention_hours`) are the
job's `config_schema`, persisted in the `config` row `job:buffer_flush`.
A batch that fails to materialize retries row-at-a-time so the poisonous
row settles alone into `error` with a `last_error` naming the real
failure; a flush overrunning its deadline returns the batch to `pending`
with the attempt refunded and shrinks the next claim. `error` rows are
retained until resolved (the sweep deletes only `done`) and are triaged
over `GET /api/v1/memory-buffer` (REST single-door; requeue resets
attempts and journals `buffer_requeued`, discard journals
`buffer_discarded`). The claim SQL bounds its batch with a
`WITH ... AS MATERIALIZED` CTE — a plain sub-select lets the planner
re-execute it per outer row and claim the entire backlog, ignoring the
`LIMIT`; do not "simplify" it.

## Pipeline phases (`ProcessingPipeline.process_batch`)

A batch flows through five phases. Each phase is a hard checkpoint:

1. **Content embed.** All contents in one chunked call to the embedder.
   Returns `(vectors, fingerprint)`. Failure marks every memory's
   `embed=error` and skips writes. Fingerprint is registered exactly
   once (`_register_fingerprint`) before any partition write.
2. **Extract + classify.** Per-memory, bounded by `pipeline_concurrency`.
   Classification always runs alongside extraction. The classifier
   instance is chosen per
   batch: if the classification purpose's inline `classifier_kind` is
   `local`, the pipeline swaps in the in-process classifier; otherwise it
   uses the LLM-backed one. (`ml_profiles` and the `*_ref` indirection were
   dropped in the baseline; wiring the dispatch to read `classifier_kind`
   is T1.04's.) The two implementations share the same surface
   (`classify(content, areas, prompt, mode) → {hall, summary, emotions, flags}`).
   **Single-call merge:** when the classifier is the LLM-backed one
   (`classifier_kind` not `local`) AND `classification_mode == 'simple'`, the
   pipeline folds classification into the one extraction call
   (`extract(..., with_classification=True)`) instead of a second LLM
   round-trip — the merged schema adds `summary`/`emotions`/`flags`, and
   extraction's `memory_type` (already the simple-7 vocabulary) doubles
   as the classification label written to `classified_type`. Any
   other config (an ML classifier, or an area-grained non-simple mode
   whose larger label space the extraction schema does not carry) keeps
   the two concurrent calls. Because the gate changes the extraction
   prompt, re-extracting the same content under a different gate state
   (mode flip, `classifier_kind` set/cleared) is not bit-identical even
   with the same content seed.
3. **Entity embed with cache.** Lookup `(name_lower, fingerprint)` in
   memory cache, fall back to DB cache, fall back to embedding the
   misses. Newly produced embeddings are written to both. The fingerprint
   may change between Phase 1 and Phase 3 if the active embedder rotated;
   in that case Phase 3 registers and switches to the new fingerprint.
4. **Dedup.** One ANN probe per unique `(name, entity_type)` pair —
   `find_similar_entity` is type-constrained at threshold 0.85, so
   same-named entities of different types dedup separately. A match
   only canonicalizes when `names_distinct(lower_name, match)` is
   False: names that differ by a discriminating token (numbers, dates,
   versions, month names) never merge despite high cosine similarity.
   Record `(name_lower, entity_type) → canonical_name` in
   `canonical_map`; Phase 5 resolves relation endpoints by the same
   key. Probes fan out bounded by `pipeline_concurrency`.
5. **Write.** Per memory, in two savepoints — A: vector upsert +
   memory-row enrichment; B: entity/relationship graph + technologies
   + supersession — so a graph failure does not roll back the vector
   write:
   - Strip prior contributions of this `memory_id` from the graph
     (`delete_by_memory_id`) before writing the new set, **inside
     savepoint B** (T1.21, 2026-07-28). The strip and the write are one
     atomic replace: a savepoint-B failure rolls the strip back so the
     prior graph survives, and an extraction failure never enters B so
     the strip never runs. Running it outside the savepoints — which is
     what doc 05 §8's flowchart used to show — silently left a memory
     with **no** graph on either path. A failed strip fails savepoint B;
     it must never be swallowed and written over. This is what
     makes re-extraction idempotent. `delete_by_memory_id` deletes a
     relation only when no live memory still asserts it (self-healing
     dangling `memory_ids`), and an entity only when no live memory
     asserts it and no surviving relation references it (the FK
     cascades, so deleting a referenced entity would destroy another
     memory's edge). Entities shared with other live memories survive.
     The hourly `graph_orphan_cleanup` job runs the unscoped sweep
     (`prune_orphan_entities`) as a backstop so Phase-4 dedup never
     merges fresh entities onto stale ghosts.
   - Apply `canonical_map` to entity names and relationship endpoints.
   - Lowercase entity names on write; if the original casing differs,
     stash it in `properties.display_name` so the UI can render it back.
   - Write rows; recompute `memories.technologies` from entities whose
     type is in `TECH_TYPES`; run supersession.
   - Compute crossrefs in a separate session after the main commit.

After Phase 5, `derive_memory_failed_step` records or resolves a row in
`pipeline_failures` per memory. The websocket broadcasts
`pipeline.completed | partial | failed` based on the per-step status.

## Pipeline terminology — never conflate

- **Extraction** builds the entity/relationship graph and is always on.
- **Classification / enrichment** populates the `llm_*` columns and also
  always runs. There is no longer a regex classifier or an
  `llm_enrichment_enabled` gate; the only choice is which model-backed
  classifier serves the `classification` purpose (LLM by default, or the
  in-process classifier when `classifier_kind` is `local`).

The **only** surviving ingestion-side behavioral flag is `relation_rescue`
(pattern-based rescue layer for relations the LLM misses); retrieval has
its own flags (see Feature flags). All `ml_*` flags were removed in the
2026-05-01 LLM-only consolidation; do not reintroduce a generic ML on/off
switch, and do not reintroduce a classification on/off flag.

## Supersession (`detect_supersessions`)

Triggered inside Phase 5 when the new memory carries a relation in the
**`REPLACES` family** — `REPLACES`, `IMPROVES_ON`, or the legacy
`BUILDS_ON` — not the literal `REPLACES` alone (T1.36, 2026-07-28). The
predicate lives in both `pipeline.py` and `supersession.py` and they must
change together; narrowing one is a silent behaviour change, not a
cleanup. A candidate is flipped to `superseded` only if **all** hold:

1. Same `project` as the new memory.
2. Candidate `status = 'active'`.
3. `candidate.technologies` overlaps the lowercased `REPLACES` targets
   (the GIN index on `memories.technologies` carries this).
4. `candidate.created_at >= now - SUPERSESSION_WINDOW_DAYS` (90 days).
5. Candidate is older, with an id tie-break for equal timestamps:
   `created_at < new.created_at OR (created_at = new.created_at AND
   id < new.id)`. Same-batch rows share one server-side `created_at`,
   so the tie-break lets within-batch supersession fire while still
   blocking the mutual flip (without this guard a reprocess flips two
   same-relation memories into mutual supersession; both vanish from
   the default `active` view).
6. The speculative gate, scoped per target: only the sentences
   mentioning that `REPLACES` target are checked for
   `SPECULATIVE_REPLACES_MARKERS` ("might", "considering", "planning
   to switch", ...), falling back to the whole text only when no
   sentence mentions the target — an unrelated speculative aside
   elsewhere in the memory does not suppress a definitive replacement.
   This is the per-relation confidence gate until the extractor emits
   a numeric one.

The detector lowercases REPLACES targets because `memories.technologies`
is lowercase; do not change either side without the other.

## Embedders are partitioned by fingerprint

Pgvector requires a fixed-dim `vector(N)` column, so every fingerprint
gets its own child table:
`memory_embeddings__<slug>`, `entity_embeddings__<slug>`,
`code_chunk_embeddings__<slug>`, `entity_embedding_cache__<slug>`.
The `embedders` table is the registry; `embedder_registry.register`
inserts the row and runs the four `CREATE TABLE IF NOT EXISTS` once,
idempotently. Application code never names a child table directly —
always go through `child_table(parent, fingerprint)`. A query that
joins across fingerprints is a bug; cross-fingerprint comparisons
have no defined cosine distance.

`_register_fingerprint` must be called before any insert into a
partition. Phase 1 does this for the content fingerprint; Phase 3 does
it again if the active embedder rotated mid-batch.

## Retrieval

Default semantic search delegates to `HybridSearchService.search` when
`hybrid_search_enabled`:

- Semantic side: `1 - (embedding <=> :vec)` against the per-fingerprint
  `memory_embeddings__<slug>` table.
- Keyword side: `ts_rank` against `memories.search_vector` with
  `plainto_tsquery('english', :q)`.
- Fusion: Reciprocal Rank Fusion with `k = 60`, weighted by
  `semantic_weight` (default 0.7). Output rows carry `rrf_score` as
  the ordering signal; the per-modality `score` key survives on the
  row (the first-seen side's raw score), so consumers must prefer
  `rrf_score`.
- When `reranker_enabled`, `RerankerService` LLM-scores the top 40
  RRF-ranked rows (0–10; the unscored tail is appended) after fusion.
- If `confidence_rank_gamma > 0`, weighting multiplies `rrf_score` by
  `(1 + γ·(confidence - 0.75))`; after a rerank it runs with
  `preserve_order=True`, rescaling scores without reordering.

Code search (`CodeQueryService.search_code`) **does** fuse, contrary to
what this file said until 2026-07-28: a vector arm over
`code_chunk_embeddings__<slug>` and an `ILIKE` arm over `CodeSymbol.name`
/ `source_code`, combined under RRF. What it has no FTS column for is a
`ts_rank` arm — the partitions carry none — so the keyword side is
`ILIKE`, not Postgres full-text. `code_query.py` **imports** `RRF_K` from
`app/services/rank_fusion.py` since T2.58 (2026-08-04) — it used to
declare its own copy, and this file used to say no task owned closing
that. Two AST scans now fail the build on a second RRF constant
*declared* anywhere outside `rank_fusion.py`; they check the binding, not
the literal 60, so renaming the value does not evade them. MCP's
`code_search` and `code_blast_radius` route through this service
(T1.42c); before that they held parallel implementations and had already
diverged.

**Chat retrieval is the same path, not a third one.** `ChatService` used
to call `vector_repo.search` directly — semantic-only, no keyword arm, no
RRF, no trace — so a chat answer and the search surface could rank one
corpus differently. Since T2.58 it goes through
`LayerCompositionService.search`, whose memory channel is
`HybridSearchService.search_with_trace`, and `ChatService` holds no vector
repository at all. **Ranking parity between the two doors is asserted on
order, not on shape** (`tests/test_chat_retrieval_parity.py`): a
shape-comparison test passes while orders diverge, which is why the
assertion is written the way it is. Note parity is only proven while every
rank arm sits at weight 0 — the doors weight `confidence_rank_gamma` on
different bases, so activating an arm obliges re-measuring both.

## Feature flags

Source of truth: `config` table row with key `feature_flags`. At read
time `get_feature_flags_dict` merges DB values **over**
`FEATURE_FLAGS_DEFAULTS` from `app/config.py`, so a flag absent from
the DB row falls back to its default. The pipeline reads the merged
dict through a 5-second TTL single-flight cache (`_get_feature_flags_cached`)
so per-call dispatching does not hammer the DB; concurrent refreshers
share one task. `_flag_cache_reset` is a test hook only.

Current behavioral flags (the rest govern concurrency or thresholds):
`hybrid_search_enabled`, `reranker_enabled`, `relation_rescue`,
`confidence_rank_gamma`. The graph arms landed inert with T2.32 —
`ppr_enabled` / `dual_level_enabled` / `community_injection_enabled` off,
`w_ppr` / `w_dual` at 0. `w_ppr` and `w_dual` are RRF **list** weights
(`rank_fusion.LIST_WEIGHT_KEYS`), never `RankArm` multipliers, and both
doors derive the PPR weight through `rank_fusion.ppr_list_weight` so a
half-flipped config cannot mean one thing to chat and another to search.
The dual-level channel itself is T2.49's; only its flag exists today. The ranking arms `w_importance` / `w_heat` /
`w_recency` / `w_context_boost` exist at weight 0 and are provably inert
there (`rank_fusion.RANK_ARMS`); each flips only on a measured retrieval
win reported with its latency/cost twin, recorded in the gate ledger's
arm activation log — never by intuition.

## LLM configuration

Eight purposes. **Seven are live**: `embedding`, `extraction`,
`classification`, `reasoning`, `summarization`, `reranker`, and —
since T2.26 landed — `verification`, which `app/services/verification_judge.py`
resolves and dispatches on. Only **`synthesis`** is still seeded inert
(first consumer T3.02): resolvable from day one per doc 11 §6, but nothing
dispatches on it yet. This paragraph described both Tier-C rows as inert
until 2026-08-02; the `verification` half was stale, and a task reading it
would wrongly believe activating that purpose was still an unmade decision.
Note `verification` being dispatched is not the same as it being *usable*:
`VerificationJudge.judge()` refuses unconditionally without a qualification
record, which T2.41 mints and which is behind T2.54's gold. Each purpose is
**one inline `llm_purpose_configs`
row** carrying its own `{model, base_url, api_key, api_kind, params,
dimensions?, reasoning?}` — resolution is one row read and no joins. The
`llm_providers` / `llm_profiles` / `ml_profiles` indirection tables and
their `*_id` columns were **dropped in the baseline** (doc 04 §7); the
classification purpose carries an inline `classifier_kind` (`llm` |
`local`) where it used to reference a profile. The eight rows are written
by the setup wizard's finalize step from `app/services/llm_seed.py`, never
by a migration. T1.01 owns asserting the one-query property with a
query-counting test.

`api_kind` selects the wire protocol and is the only place vendor
quirks live: `openai` (compat path), `ollama` (native, exposes
`think:false`), and reserved slots for `anthropic`, `google`, `deepseek`,
`zai` that today still dispatch through the OpenAI-compat path. Every
quirk — auth scheme, reasoning-disable knob, structured-output and seed
acceptance, embeddings capability, output-cap key, model-probe endpoint —
is **one `VendorQuirks` row in `app/services/llm_quirks.py`**, which the
orchestrator, the health check and the setup wizard's probe all read; no
call site may compare `api_kind` to a vendor name, and a test fails the
build if one does. Adding a vendor is the four-step rule in doc 11 §4:
enum, quirk row, doc table, seed. Some vendors (Anthropic, DeepSeek
today) lack embeddings; the runtime guard against an embed call landing
on a no-embeddings vendor is the `api_kind`-keyed `assert_can_embed`
(reached via `LLMOrchestrator._assert_can_embed`), and the settings
picker derives its cannot-embed hint from `api_kind` the same way.
Anthropic needs `x-api-key` + `anthropic-version` rather than Bearer;
DeepSeek and z.ai need `thinking:{type:disabled}`; Gemini's compat shim
honours only `reasoning_effort=none`; and `minimal` is no longer in
OpenAI's effort set, so a config carrying it fails loud instead of 400ing
at the vendor.

LLM seeds for the eight purposes live in `app/services/llm_seed.py`, not
in any migration. The setup wizard finalize step writes seed-plus-overlay
into the `llm_*` config rows.

## Reproducibility

Extraction and classification calls forward `seed = sha256(content)[:8]`
as a 32-bit int so the same input produces the same JSON across calls.
Vendors that honour the parameter (OpenAI, DeepSeek, z.ai, Google compat,
Ollama) do; Anthropic ignores it, which is harmless. Removing the seed
forwarding will unstick reproducibility tests and make extraction E2E
flaky.

## Jobs (`JobRegistry`)

Periodic work is unified under `JobRegistry` and dispatched by cron
expressions. **Twenty-one** registered jobs (`app/main.py`) in two groups
(count corrected 2026-08-07: it had read "Sixteen" / "ten live ones" since
T2.49 landed `relation_embedding_refresh` without updating it, and four
concurrent lanes each found it stale independently — a stale count on a
"here is the full list" sentence is exactly invariant 23's concern.
`tests/test_code_deriver.py` now derives the roster from `app/main.py`'s
AST, so the next job added cannot silently desynchronise this list).
The fifteen live ones: `repo_sync`,
`buffer_flush`, `code_enrichment`, `code_reconcile`, `code_deriver`,
`token_blocklist_cleanup`, `pipeline_failure_cleanup`,
`graph_orphan_cleanup`, `tag_orphan_cleanup`,
`expired_memory_cleanup`, `ppr_snapshot`,
`relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge`, `citation_reverify`. Note
`buffer_flush`, `code_reconcile`, `code_deriver`, `ppr_snapshot`,
`relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge` and `citation_reverify` register via
the constants `BUFFER_FLUSH_JOB_KEY`, `CODE_RECONCILE_JOB_KEY`,
`CODE_DERIVER_JOB_KEY`, `PPR_SNAPSHOT_JOB_KEY`,
`RELATION_EMBEDDING_JOB_KEY`, `REPO_ENTITY_ANCHORING_JOB_KEY`,
`REPO_ENTITY_MERGE_JOB_KEY` and `CITATION_REVERIFY_JOB_KEY` rather
than string literals, so a grep for quoted keys undercounts the list —
which is precisely how this sentence went stale for four landings.
**`ppr_snapshot`, `relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge`, `code_deriver` and `citation_reverify` are Tier C but
are deliberately not dream-job family members** (T2.32, T2.49, T2.97,
T2.101, T2.96, T2.48): contract 6 fixes that family as
the consolidation passes, while doc 07 §4 and doc 10 §6 own their
artefact refreshes separately. Invariant 15 is unaffected either way —
retrieval reads the cached snapshot and Phase 4 reads the entity
partition, never the job.

**`code_deriver` is the production trigger for
`code_deriver.assert_repo_graph`** (doc 10 §6, T2.96) — T2.27 shipped
that primitive with no caller anywhere in `backend/app`. The job sweeps
every repo with a non-null `last_indexed_commit` on its own hourly cron
and journals a derivation failure under `pipeline_failures` with
`pipeline_name="code_deriver"`, distinct from `"code_index"`, so a
derivation failure never fails an index run. The withdrawal half lives
in `RepoManager.delete`, which calls
`PostgresGraphRepository.strip_repo_assertions` before removing the
repository row — `entities.repo_ids[]` / `entity_relations.repo_ids[]`
carry no foreign key to `repositories`, so without it an entity's
`repo_ids` keeps a dangling id after the repo is gone.

**`citation_reverify` is doc 10 §6's second sanctioned crossing** (T2.48): it
re-resolves each code citation's recorded `symbol_key` against its repository's
current HEAD, marks a citation that no longer resolves stale, and **enqueues the
citing fact for the verification recompute, which downgrades the badge — never
expiring the fact**, because a deleted symbol may be a rename a human should
confirm. It reads the code graph and writes the memory-side vault, one direction,
no join. Note it does **not** scope by the run's changed-file set as doc 10 §6
describes: that scoping key is `detail.symbol_key`, which for an import-basis
citation is a module name (`httpx`), never a path, so the doc's literal predicate
would match only language citations. The job scopes by comparing a citation's
`detail.reverified_at_sha` against the repository's `last_indexed_commit`
instead — self-healing where an event-payload design is not, since `record_event`
never raises. The doc correction is owed and is tracked as a Tier-3 amendment.

**`repo_entity_anchoring` is what makes the code bridge's anchoring
reach past an exact name match** (T2.97): the deriver is LLM-free by
structural guard, so the embed that lets Phase 4's ANN probe see a
repo-minted entity happens in this job, one tick behind derivation. That
closes **one order only** — repo indexed, anchored, then the memory
ingested.

**`repo_entity_merge` closes the other order, which is the common one**
(T2.101). A repo indexed *after* a memory already minted the near-named
node used to leave two rows forever: Phase 4 dedups at write time,
`assert_from_repo` is an exact-key `ON CONFLICT (name, entity_type)`
upsert with no probe, and the strip-and-rewrite is keyed the same way, so
re-derivation reproduces them. That is what every existing install
produces the first time it indexes a repo. The job re-runs Phase 4's own
comparison after the fact — `find_similar_entity` at the same 0.85 under
the same `names_distinct` gate, with the query vector read out of the
partition rather than re-embedded, so both sides of every cosine come
from one child table and the pass needs no embedder call. **The survivor
is the repo-asserted row**, older `created_at` with an id tie-break when
both are, so the two indexing orders converge on the same node rather
than trading an order-dependent node count for an order-dependent node
name. A merge moves, in one savepoint per pair: the `memory_ids` /
`repo_ids[]` unions, **every** relation endpoint in both directions
(a repointed endpoint colliding with the `(source, target, rel_type)`
uniqueness is a relation merge of its own — union, keep the greater
weight, drop the duplicate — never an error left for the constraint),
`knowledge_triples.subject_id` / `object_id` (entity ids carrying **no**
foreign key, which `review_ranking`'s salience arm reads as zero
neighbours when they dangle), and the lowercase `technologies` denorm for
every memory whose entity set changed. The losing row's vectors go with
it through the `entity_embeddings__<slug>` cascade, in every partition.
A relation the repointing missed **fails the savepoint** rather than
being swallowed by that same cascade. The six added by T2.08 are the
**Tier-C dream-job family** (`app/services/dream_jobs.py`, wired at boot
by `register_dream_jobs`): `verification_recompute`, `fact_lift`,
`contradiction_scan`, `memory_dream`, `article_synthesis`,
`topic_detection`. Each is scheduled, locked and configurable for real,
and a member's body is a `PlaceholderJobRunner` until its owning task
lands (T2.09, T2.10, T2.11, T2.12, T3.02, T2.53 respectively) — the
marker is a type a test asserts, not a comment, so a placeholder can
never be mistaken for a shipped job. **Five of the six now have real
runners** (corrected 2026-08-06, when this paragraph's "its body is a
`PlaceholderJobRunner`" had been stale through four landings and read as
a claim that the whole family was inert): `fact_lift`,
`verification_recompute`, `contradiction_scan`, `memory_dream` and
`topic_detection` are live bodies. **`article_synthesis` is the one
remaining placeholder** — its productive run is a Phase-3 task behind
G-D, and T2.14 landed only its inert registration. **Invariant 15 binds the family: none of the
six may be reached from capture or retrieval** to "accelerate" a gate,
and a source scan over `backend/app` fails the build if one is. Five-field
expressions are minute-precision; six-field expressions put the seconds
field first, Quartz-style. `min_interval_seconds` is a per-job floor
that protects against runaway expressions; the loop will not fire more
often than the floor regardless of what the cron computes. Per-job
state lives in `config` rows keyed `job:<key>`. Manual `trigger(key)`
acquires the **same** per-job `asyncio.Lock` the loop uses, so a
manual run and a scheduled run can never race; a trigger while the
lock is held returns busy (HTTP 409) rather than queueing. Jobs may
declare a `config_schema` (FieldDescriptor list); `set_config`
validates partial updates against it (type + min/max, unknown keys
rejected) and writes under that same lock
(`PUT /api/v1/jobs/{key}/config`).

## Events journal (`events` — `audit_log` is gone)

`events` is the sole, append-only audit substrate; `audit_log` was
dropped at the baseline's genesis and no such table, model or query
exists. Every subsystem journals through one writer, `record_event`
(`app/services/events.py`), which degrades loudly but never raises into
its caller. `EVENT_TYPES` / `OBJECT_TYPES` are closed vocabularies living
beside the writer, deliberately NOT in `app.taxonomy`: event types are
never LLM output, so an unknown value logs a warning instead of being
rewritten to a fallback. Widening is taxonomy-first — land the value in
the vocabulary before its emitter ships. The table is RANGE-partitioned
by month; every partition-creating path goes through the SQL function
`events_ensure_partition` (boot reconciliation plus a maintenance arm on
`pipeline_failure_cleanup`), and append-only is enforced by three trigger
kinds — a row-level UPDATE/DELETE guard on the parent, a statement-level
TRUNCATE guard on the parent, and a per-child TRUNCATE guard stamped by
`events_ensure_partition`, because statement triggers do not cascade to
children. Readers: `GET /events`, `/events/timeline`, `/events/calendar`
(the calendar bucket expression must match `ix_events_day`'s immutable
UTC expression verbatim), and `GET /auth/audit`, which filters
`auth_*`/`setup_*` rows from the same table. Journal payloads may carry
content previews that **outlive deletion of their memory** — append-only
by design. **The retention policy is settled (T2.59, ruled 2026-08-06):
accept the residue and document it.** Deleting a memory is not a content
purge and the DELETE route says so. The residue is wider than two stores —
full refine summaries in `consolidated`/`undone`, contradiction counterparts
in `verified`, `knowledge_triples.fact` by design, 24h of raw content in
`memory_buffer` done rows, and `messages.context` keeping cited fact rows
untrimmed. The pasted-secret case is answered by an operator break-glass
procedure (`docs/runbook-content-purge.md`), **never an in-app
journal-rewriting path**: that would put "make this never have happened" one
bug away from the audit substrate. The ruling's load-bearing argument is
measured, not aesthetic — the assistant's own unbounded `messages.content`
prose and the storage substrate sit *below* every option considered, so the
alternatives pay permanent costs to narrow a gap none of them closes.
**Write-time minimization is the standing rule**: a new event payload copies
content only when a feature demonstrably needs it, and says so at the writer.

`undone` joined the vocabulary with T2.13, and it is the **first by-id
consumer of `events`** — the composite `PRIMARY KEY (id, created_at)`
means a bare `WHERE id = :id` scans every monthly child, so every undo
lookup carries a `created_at` bound and prunes to one or two of them.
The **dream digest** (`app/services/dream_digest.py`) reads the
`consolidated` stream grouped by `payload.cycle_id`, and within a cycle
by object, in `(created_at, id)` order — journal order is application
order, and regrouping by action kind would describe a cycle that did not
occur. **Undo is all-or-nothing per request and has no per-action code
path**: a single-action undo is a batch of one through
`dream_undo.undo`, whose result types have no field that could carry a
per-item outcome and whose module owns no savepoint, no commit and no
`try` — an AST scan fails the build on all five shapes. That makes the
module unable to self-heal, so it has **three** outcomes, not two: only
`UndoRefused` guarantees nothing was written, and **any other raise
leaves restores in the caller's session for the caller to roll back**.
The HTTP door gets that from the request-scoped session dependency; an
in-process caller does not. **An undo that could not be journalled does
not happen** — `record_event` never raises, so the batch counts its own
`undone` rows back and raises when short. An undone subsumption leaves a
suppression tombstone at
`memories.metadata.dream.undone_subsume.<counterpart_id>`, keyed on both
memories' `content_sha` so it lapses when either text changes; it is
read at **nomination** time by `generate_pairs`, which is not a
lifecycle change — `supersede()` still retires that exact pair for any
caller that asks.

## MCP endpoint

`/mcp` is unauthenticated (local-network trust model); its only
network defence is DNS-rebinding protection via a Host allowlist.
localhost is always allowed; `MCP_ALLOWED_HOSTS` (comma-separated,
`192.168.0.195:8000` or `host:*`) adds LAN hosts; `*` disables the
check entirely. Default (empty) is localhost-only — a foreign Host
gets 421. Fix a LAN 421 by extending the allowlist, never by
disabling the protection. Browser Origins are allowlisted to the same
hosts. `memory_batch_add` mirrors the HTTP 1–100 batch cap.

Memory writes resolve `source` per call: explicit arg (the literal `mcp`
counts as unspecified) > `X-Darkmem-Client` header > User-Agent product
map > `mcp`; `memory_batch_add` resolves on the raw entry dicts before
validation. `source_agent` defaults to the caller's raw User-Agent.

**Why raw-dict resolution still matters after T1.42a** (updated 2026-07-28).
The original reason — `MemoryCreate` stamping an `api` default that erased
the absent-vs-explicit distinction — is gone: T1.42a removed that default,
so `MemoryCreate.source` has no default and the erasure is no longer
representable. But the discipline is **not** merely historical, and the
doors differ. Restoring the default and resolving post-hoc still *passes*
on REST, where `api` is REST's own sentinel so absent and explicit resolve
identically — and *fails* on MCP with `'api' != 'codex'`, because there
`api` is a foreign literal that dodges MCP's `mcp` sentinel. So the
raw-dict rule has a live, demonstrated justification on the MCP door and a
by-construction one on REST. Do not "simplify" it away on the strength of
the REST case alone.

## Setup, auth, runtime config

- `/api/v1/setup/*` is trust-on-first-use: gated only by
  `require_uninitialized`, which 403s once the `admin_password_hash`
  config row exists. `SETUP_SECRET` no longer exists; do not
  reintroduce a pre-setup shared secret.
- Login rate limiting is per-IP with lockout. The IP source is a posture
  selector and **both postures are live and tested**: with
  `trust_proxy_headers` off (the default) the transport peer wins and no
  request header is read; with it on, `X-Real-IP` wins and the **rightmost**
  `X-Forwarded-For` hop is the fallback. The spoofable **leftmost**
  `X-Forwarded-For` is read in neither. Layer 3 is not the whole ladder:
  uvicorn's own `ProxyHeadersMiddleware` defaults on and would rewrite the
  peer from `X-Forwarded-For` for any loopback client, so **all three launch
  paths pass `--no-proxy-headers`** (`entrypoint.sh`,
  `scripts/start_dev_server.sh`, and `docker-compose.dev.yml`'s `command:`).
  Dropping it from any one of them re-opens the bucket the flag closes.
  Refresh and change-password rotate (blocklist) the presented token;
  password change revokes all pre-change tokens via the `iat` check.
- `DATABASE_URL` is derived from the `DB_*` vars with percent-encoded
  credentials; an explicit `DATABASE_URL` overrides the derivation.
  `trust_proxy_headers` defaults to False — the app is the network edge and
  serves the SPA itself, so nothing trustworthy sits in front; the prod
  compose passes it through so a posture change stays a config flip.
  `cookie_secure` is tri-state: unset = Secure
  only when `environment=production`; explicit false allows login
  over plain-HTTP LAN. There are no `LLM_*` env vars — all LLM config
  lives in the DB via the setup wizard.

## Live model endpoints (dev machine)

Recorded at the owner's explicit instruction, 2026-07-28. **The key below
is a real credential in a private repo; it is committed knowingly and is to
be rotated before the repo is ever published.** Note that removing it in a
later commit does not remove it from git history — that needs a history
rewrite or a rotated key.

- **Extraction / classification / reasoning — DeepSeek.**
  `base_url=https://api.deepseek.com/v1`, `api_kind=deepseek`,
  key `REDACTED-DEEPSEEK-KEY-ROTATE-ME`. Models offered:
  **`deepseek-v4-flash`** and `deepseek-v4-pro`. **The F1 baseline and every
  gate re-measurement use `deepseek-v4-flash`** — the gate ledger fixes the
  model, so a run on `-pro` is not comparable and must not be used for
  parity. Export as `DEEPSEEK_API_KEY` for `run_bench.py` and
  `benchlib/run_smoke.py`.
- **Embeddings — Ollama on the LAN.** `http://192.168.0.196:11434`,
  `api_kind=ollama`. Two embedding models, and the choice is load-bearing
  because the fingerprint partitions on it:

  | Model | Dims | Context |
  |---|---|---|
  | `nomic-embed-text:latest` | 768 | 2048 |
  | `qwen3-embedding:0.6b` | 1024 | 32768 |

  Switching between them is an embedder rotation, not a config tweak: each
  fingerprint gets its own `memory_embeddings__<slug>` child table and a
  cross-fingerprint comparison has no defined cosine distance. DeepSeek has
  **no** embeddings capability, so `assert_can_embed` will refuse an embed
  call routed there — that guard is working, not a misconfiguration.

## Code indexing

`POST /repos/{id}/reindex` accepts `{full, enrich_symbols,
generate_wiki}`, all default False. An unchanged HEAD sha
short-circuits the reindex unless `full=true` **or the repo carries
outstanding index debt** (below). Symbol enrichment and
wiki generation run only when their toggles are set; `GET /code/wiki`
is read-only and never implicitly generates.

An incremental run re-traces the callers of every changed file, because
re-indexing a file deletes every call edge pointing into it. That
re-trace is capped at `DEPENDENT_RETRACE_CAP` (500); the callers past
the cap are **persisted to `repositories.index_debt`, never dropped** —
dropping them leaves a graph that is quietly wrong, with no error and
no symptom but missing callers. Later runs fold a bounded batch
(`config` row `code_index_debt`, default the cap) of that queue back
into their changed set until it reaches zero, and the batch leaves the
queue only after the run that re-traced it succeeded. Debt files are
only ever *added* to a changed set: their content hash is unchanged, so
phase 03 skips them and the drain deletes nothing. Both the deferral
and the drain journal a `repo_indexed` `events` row and surface on
`RepoResponse.index_debt`.

## Cross-cutting invariants

- **memory_id type drift.** Hybrid search returns string ids; the
  vector repo returns `UUID`. Every consumer must normalize at the
  boundary or matches drop silently.
- **Lowercase entity names** on disk; preserve original casing in
  `properties.display_name`. The supersession detector and the
  `technologies` denorm both assume lowercase.
- **No cross-fingerprint joins** on embedding tables.
- **Idempotent re-extraction.** Always strip prior `memory_id` graph
  contributions before writing a new set.
- **`technologies` is lowercase, denormalised, GIN-indexed.** Keep all
  three; dropping any one breaks supersession or retrieval.
- **REPLACES family.** `REPLACES`, `IMPROVES_ON`, and the legacy
  `BUILDS_ON` collapse to one bucket via `family_key` for rescue dedup
  **and they are the supersession trigger** — the family scopes both, not
  rescue dedup alone.
  Adding a new replacement-family relation means editing
  `REPLACES_FAMILY` too.
- **Async session lifetime.** Never open a fresh session while the
  request transaction still holds locks on the same rows; commit first.
- **asyncpg needs CAST on raw-SQL params.** Any bound param whose
  type Postgres cannot infer must be cast (`CAST(:vec AS vector)`,
  `CAST(:id AS uuid)`, `CAST(:props AS jsonb)`), especially with
  variadic ANY / unnest / jsonb_build_object — otherwise
  `IndeterminateDatatypeError`. And roll back the session before
  mutating ORM objects in an error handler.
