# Darkmem — business logic baseline

Centralized memory system for AI agents. Commands and layout first;
everything from "Domain model" down is contract, not implementation
detail. A refactor that breaks one of the listed invariants is a
behavior change, not a cleanup.

## Commands

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
- Stacks: dev `docker compose -f docker-compose.dev.yml up -d` (no
  .env needed); prod `docker compose up -d` (host networking; requires
  `DB_PASSWORD` + `JWT_SECRET` ≥ 32 chars in .env, `COOKIE_SECURE=false`
  for plain-HTTP LAN). Rebuild images first: `./scripts/build-push.sh`.
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
`backend/scripts` holds eval harnesses (`extraction_bench/`).
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
- `classified_type` / `classified_confidence` — regex classifier output.
- `llm_classified_type` / `llm_summary` / `llm_emotions` / `llm_flags` —
  enrichment output. Populated only when `llm_enrichment_enabled` is on.
- `technologies` (lowercase Text[]) — denormalised cache of entity names
  whose `entity_type` is in `TECH_TYPES`. The supersession detector and
  the retrieval filter both consult this column instead of joining.
- `confidence` (REAL, default 0.75) — content-quality estimate; used by
  `_apply_confidence_weighting` when `confidence_rank_gamma > 0`.

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

## Pipeline phases (`ProcessingPipeline.process_batch`)

A batch flows through five phases. Each phase is a hard checkpoint:

1. **Content embed.** All contents in one chunked call to the embedder.
   Returns `(vectors, fingerprint)`. Failure marks every memory's
   `embed=error` and skips writes. Fingerprint is registered exactly
   once (`_register_fingerprint`) before any partition write.
2. **Extract + (optional) classify.** Per-memory, bounded by
   `pipeline_concurrency`. Classification only runs when
   `llm_enrichment_enabled`. The classifier instance is chosen per
   batch: if the classification purpose has `ml_profile_ref` set, the
   pipeline swaps in `MLClassificationService`; otherwise it uses the
   LLM-backed one. The two implementations share the same surface
   (`classify(content, areas, prompt, mode) → {hall, summary, emotions, flags}`).
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
     (`delete_by_memory_id`) before writing the new set. This is what
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
- **Classification / enrichment** populates the `llm_*` columns and is
  gated behind `llm_enrichment_enabled`.

The **only** surviving ingestion-side behavioral flag besides the
classification toggles is `relation_rescue` (pattern-based rescue
layer for relations the LLM misses); retrieval has its own flags (see
Feature flags). All `ml_*` flags were removed in the 2026-05-01
LLM-only consolidation; do not reintroduce a generic ML on/off switch.

## Supersession (`detect_supersessions`)

Triggered inside Phase 5 when the new memory carries a `REPLACES`
relation. A candidate is flipped to `superseded` only if **all** hold:

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

Code search (`search_code`) is semantic-only — the
`code_chunk_embeddings__<slug>` partitions carry no FTS column, so
there is nothing to fuse with.

## Feature flags

Source of truth: `config` table row with key `feature_flags`. At read
time `get_feature_flags_dict` merges DB values **over**
`FEATURE_FLAGS_DEFAULTS` from `app/config.py`, so a flag absent from
the DB row falls back to its default. The pipeline reads the merged
dict through a 5-second TTL single-flight cache (`_get_feature_flags_cached`)
so per-call dispatching does not hammer the DB; concurrent refreshers
share one task. `_flag_cache_reset` is a test hook only.

Current behavioral flags (the rest govern concurrency or thresholds):
`llm_enrichment_enabled`, `hybrid_search_enabled`, `reranker_enabled`,
`relation_rescue`, `confidence_rank_gamma`.

## LLM configuration

Six purposes: `embedding`, `extraction`, `classification`, `reasoning`,
`summarization`, `reranker`. Each is an `LLMPurposeConfig` row that may
inline its connection details or reference an `llm_providers` row via
`provider_ref` (rotation in one place) and an `llm_profiles` row via
`profile_ref` (UI dropdown anchor). The classification purpose may also
reference an `ml_profiles` row via `ml_profile_ref` to swap the LLM
classifier for in-process HF dispatch.

`api_kind` selects the wire protocol and is the only place vendor
quirks live: `openai` (compat path), `ollama` (native, exposes
`think:false`), and reserved slots for `anthropic`, `google`, `deepseek`,
`zai` that today still dispatch through the OpenAI-compat path. Vendor
auth and reasoning-control quirks are handled inside the orchestrator;
do not paper over them at the call site. Some vendors (Anthropic,
DeepSeek today) lack embeddings — `LLMProviderProfile.supports_embedding`
gates the embedding-purpose profile picker.

LLM seeds for the six purposes live in `app/services/llm_seed.py`, not
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
expressions. Seven registered jobs (`app/main.py`): `repo_sync`,
`code_enrichment`, `token_blocklist_cleanup`,
`pipeline_failure_cleanup`, `graph_orphan_cleanup`,
`tag_orphan_cleanup`, `expired_memory_cleanup`. Five-field
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

## MCP endpoint

`/mcp` is unauthenticated (local-network trust model); its only
network defence is DNS-rebinding protection via a Host allowlist.
localhost is always allowed; `MCP_ALLOWED_HOSTS` (comma-separated,
`192.168.0.195:8000` or `host:*`) adds LAN hosts; `*` disables the
check entirely. Default (empty) is localhost-only — a foreign Host
gets 421. Fix a LAN 421 by extending the allowlist, never by
disabling the protection. Browser Origins are allowlisted to the same
hosts. `memory_batch_add` mirrors the HTTP 1–100 batch cap.

## Setup, auth, runtime config

- `/api/v1/setup/*` is trust-on-first-use: gated only by
  `require_uninitialized`, which 403s once the `admin_password_hash`
  config row exists. `SETUP_SECRET` no longer exists; do not
  reintroduce a pre-setup shared secret.
- Login rate limiting is per-IP with lockout; the client IP comes
  from `X-Real-IP` (set by the bundled nginx to the direct peer) when
  `trust_proxy_headers` is on — never the spoofable leftmost
  `X-Forwarded-For`. Refresh and change-password rotate (blocklist)
  the presented token; password change revokes all pre-change tokens
  via the `iat` check.
- `DATABASE_URL` is derived from the `DB_*` vars with percent-encoded
  credentials; an explicit `DATABASE_URL` overrides the derivation.
  `trust_proxy_headers` defaults to True (the API always sits behind
  the bundled nginx). `cookie_secure` is tri-state: unset = Secure
  only when `environment=production`; explicit false allows login
  over plain-HTTP LAN. There are no `LLM_*` env vars — all LLM config
  lives in the DB via the setup wizard.

## Code indexing

`POST /repos/{id}/reindex` accepts `{full, enrich_symbols,
generate_wiki}`, all default False. An unchanged HEAD sha
short-circuits the reindex unless `full=true`. Symbol enrichment and
wiki generation run only when their toggles are set; `GET /code/wiki`
is read-only and never implicitly generates.

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
  `BUILDS_ON` collapse to one bucket via `family_key` for rescue dedup.
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
