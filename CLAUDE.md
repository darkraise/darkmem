# Darkmem — business logic baseline

Centralized memory system for AI agents. Everything below is contract,
not implementation detail. A refactor that breaks one of the listed
invariants is a behavior change, not a cleanup.

## Domain model

Memory rows live in `memories`. Each row has a status lifecycle:
`active → superseded → deprecated`. The CHECK constraint
`chk_superseded_has_pointer` forbids `status='superseded'` without
`superseded_by` set; supersession code must always set both atomically.

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
4. **Dedup.** For each unique entity name, ANN-probe `find_similar_entity`
   at threshold 0.85. If a different canonical name comes back, record
   `lower_name → canonical_name` in `canonical_map`. Probes fan out
   bounded by `pipeline_concurrency`.
5. **Write.** Per memory, in a savepoint:
   - Strip prior contributions of this `memory_id` from the graph
     (`delete_by_memory_id`) before writing the new set. This is what
     makes re-extraction idempotent. `delete_by_memory_id` only deletes
     entities whose `memory_ids` array becomes empty; entities shared
     with other memories survive.
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

The **only** surviving runtime behavioral flag besides classification
toggles is `relation_rescue` (pattern-based rescue layer for relations
the LLM misses). All `ml_*` flags were removed in the 2026-05-01
LLM-only consolidation; do not reintroduce a generic ML on/off switch.

## Supersession (`detect_supersessions`)

Triggered inside Phase 5 when the new memory carries a `REPLACES`
relation. A candidate is flipped to `superseded` only if **all** hold:

1. Same `project` as the new memory.
2. Candidate `status = 'active'`.
3. `candidate.technologies` overlaps the lowercased `REPLACES` targets
   (the GIN index on `memories.technologies` carries this).
4. `candidate.created_at >= now - SUPERSESSION_WINDOW_DAYS` (90 days).
5. `candidate.created_at < new_memory.created_at` — strict older. Skip
   this guard and a reprocess flips two same-relation memories into
   mutual supersession; both vanish from the default `active` view.
6. The new memory text contains no `SPECULATIVE_REPLACES_MARKERS`
   ("might", "considering", "planning to switch", ...). This is the
   per-relation confidence gate until the extractor emits a numeric
   one.

The detector lowercases REPLACES targets because `memories.technologies`
is lowercase; do not change either side without the other.

## Embedders are partitioned by fingerprint

Pgvector requires a fixed-dim `vector(N)` column, so every fingerprint
gets its own child table:
`memory_embeddings__<slug>`, `entity_embeddings__<slug>`,
`code_chunk_embeddings__<slug>`, `entity_embeddings_cache__<slug>`.
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
  `semantic_weight` (default 0.7). Output rows carry `rrf_score`;
  individual `score` is replaced. If the caller wants
  `confidence_rank_gamma > 0`, weighting multiplies `rrf_score` by
  `(1 + γ·(confidence - 0.75))`.

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

Periodic work (repo sync, enrichment worker, ...) is unified under
`JobRegistry` and dispatched by cron expressions. Five-field
expressions are minute-precision; six-field expressions put the seconds
field first, Quartz-style. `min_interval_seconds` is a per-job floor
that protects against runaway expressions; the loop will not fire more
often than the floor regardless of what the cron computes. Per-job
state lives in `config` rows keyed `job:<key>`. Manual `trigger(key)`
acquires the **same** per-job `asyncio.Lock` the loop uses, so a
manual run and a scheduled run can never race.

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
