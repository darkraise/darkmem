# Phased Batch Pipeline with Entity Embedding Cache

**Date:** 2026-04-10
**Status:** Draft
**Feature:** 1 of 3 (Feature 2: pipeline failure tracking; Feature 3: model change handling — separate specs)

## Problem

When ingesting memories in batch, the pipeline produces two kinds of embedding traffic to Ollama:

1. **One content batch call** per MCP request (already efficient) — e.g., `embed_batch(20 contents)` once.
2. **Dozens of individual entity embedding calls** — inside `process_memory`, a per-entity loop calls `embed(name)` for every extracted entity. A batch of 20 memories yields ~56 individual HTTP requests, all streaming through the logs.

This defeats the benefit of batching. With `OLLAMA_NUM_PARALLEL=1`, these serial single-text requests dominate wall time. The same entity name ("PostgreSQL") is embedded repeatedly across memories and across batches because there's no cache.

## Solution

Restructure `process_batch` into explicit phases with entity embedding collected into a single batch call per MCP request, backed by a two-layer cache (persistent database table + in-memory TTL).

## Pipeline Phases

For a single `process_batch(entries)` call with N memories:

**Phase 1 — Content embedding**
Chunk `entries` into groups of `embedding_batch_size` (default 20). Run `embed_batch` on each chunk. Limit concurrent in-flight chunks to `embedding_concurrency` (default 1). Wait for all chunks to complete. Result: vectors for all N memories, in original order.

**Phase 2 — Extraction and LLM classification**
Run `extraction.extract(content)` for each of the N memories concurrently, gated by the existing `pipeline_concurrency` semaphore. Each call returns entities and relationships.

If `llm_enrichment_enabled` is true, `classification.classify(content, areas, cls_prompt, mode)` also runs per memory, concurrent with extraction under the same semaphore. Results are paired with their memory for phase 5.

**Phase 3 — Entity embedding with cache**
Collect the unique set of entity names across all N extractions, deduplicated by lowercase match. For each unique name:

1. Check the in-memory cache (keyed by lowercase name + model fingerprint).
2. On miss, check the persistent `entity_embedding_cache` table via a single `WHERE name_lower = ANY(:names) AND model_fingerprint = :fp` query.
3. On DB miss, add the name to the "uncached" list.

Call `embed_batch_chunked(uncached_names, embedding_batch_size, embedding_concurrency)`. Upsert new embeddings into the persistent cache and the in-memory cache. Build a `name_to_embedding: dict[str, list[float]]` covering all unique names.

**Phase 4 — Dedup lookup**
For each unique entity name, call `find_similar_entity(embedding, threshold=0.85)` to find an existing canonical entity in the graph. Build `canonical_map: dict[str, str]` mapping each name to its canonical form (if any). This runs once per unique name, not once per memory-entity pair.

**Phase 5 — Per-memory writes**
For each of the N memories, run these operations concurrently (gated by `pipeline_concurrency`):

1. Apply `canonical_map` to the memory's entities and relationships.
2. Run regex classification (`regex_classify(content, enabled_areas, mode)`) — this is a pure Python function, no LLM call.
3. Build the vector payload including regex and LLM classification results (if any).
4. Write the memory vector via `vector_repo.upsert`.
5. Update the `Memory` row with classification fields.
6. Create entities via `graph_repo.create_entity` and attach their embeddings from the name-to-embedding map built in phase 3.
7. Create relationships via `graph_repo.create_relationship`.
8. Build the per-memory status dict (`embed`, `extract`, `vector`, `graph`) and broadcast the pipeline event.
9. Compute and store crossrefs (`find_similar_memories` + `store_crossrefs`) in a separate session after the main write.

Steps 2–8 run inside a single nested transaction per memory. Step 9 runs in its own session. This mirrors current behavior.

Phases 1–4 run strictly sequentially. Phase N+1 starts only after Phase N has completed for all memories in the batch. Phase 5 is the only phase that runs per-memory in parallel.

## Entity Embedding Cache

### Database table

```sql
CREATE TABLE entity_embedding_cache (
    name_lower VARCHAR(255) NOT NULL,
    model_fingerprint VARCHAR(100) NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hit_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (name_lower, model_fingerprint)
);
CREATE INDEX idx_entity_cache_last_used ON entity_embedding_cache(last_used_at);
```

The composite primary key `(name_lower, model_fingerprint)` allows multiple embeddings for the same name when the model changes, without deleting old entries.

Upsert semantics:

```sql
INSERT INTO entity_embedding_cache (name_lower, model_fingerprint, embedding)
VALUES (:name, :fingerprint, :embedding)
ON CONFLICT (name_lower, model_fingerprint)
DO UPDATE SET last_used_at = NOW(), hit_count = entity_embedding_cache.hit_count + 1;
```

### In-memory layer

The `ProcessingPipeline` instance holds an in-memory cache:

```python
self._entity_cache: dict[tuple[str, str], tuple[list[float], float]] = {}
# key: (name_lower, model_fingerprint) → value: (embedding, cached_at_monotonic)
self._entity_cache_lock = asyncio.Lock()
```

**Lookup behavior:** Lazy load. When `process_batch` enters phase 3, for each unique name it checks the in-memory dict. If present and not stale (age < `entity_cache_ttl_minutes`), use it. Otherwise treat as miss and go to the DB layer. Stale entries are evicted from the dict during the lookup.

**Write behavior:** After embedding uncached names, both the DB table and the in-memory dict are updated under the lock.

**Single-memory paths** (e.g., REST `POST /memories` creating one memory at a time) bypass the in-memory layer entirely and hit the DB cache directly. The latency cost of one extra SQL query is negligible for single-item creation, and it avoids concurrency concerns for infrequent paths.

**Concurrent batches:** Multiple `process_batch` calls running concurrently share the same in-memory cache. The asyncio lock protects writes. Reads are safe without the lock (CPython dict reads are atomic). Two concurrent batches missing the same name both end up calling `embed_batch` independently, then both upsert — ON CONFLICT DO UPDATE makes this safe and idempotent.

### Model fingerprint

The fingerprint string identifies the current embedding model so that changing models doesn't corrupt cached lookups:

```python
fingerprint = f"{embedding_config.model}|{embedding_config.dimensions or 'auto'}"
# Example: "qwen3-embedding:0.6b|1024"
```

Computed once at pipeline startup, stored on `ProcessingPipeline` as `self.embedding_fingerprint`, and written on every cache insert.

Cache lookups filter by fingerprint. Entries written under a different model are ignored (not deleted), preserving history for Feature 3 to flag as obsolete.

## New Feature Flags

Add to `FEATURE_FLAGS_DEFAULTS` in `backend/app/config.py`:

```python
"embedding_batch_size": 20,
"embedding_concurrency": 1,
"entity_cache_ttl_minutes": 60,
```

All three are configurable via the settings UI.

## Model Fingerprint Columns

Add a `embedding_model_fingerprint VARCHAR(100)` column to four tables. This is used by Feature 3 (obsolete detection) but populated starting now so that Feature 3 can ship without another migration:

| Table | Column | Written by |
|-------|--------|-----------|
| `memory_embeddings` | `model_fingerprint` | Pipeline on memory embedding |
| `code_chunk_embeddings` | `model_fingerprint` | Code indexer on chunk embedding |
| `entities` | `model_fingerprint` | Pipeline on entity embedding (phase 3) |
| `entity_embedding_cache` | `model_fingerprint` | (primary key, new table) |

Feature 1 only writes these columns. Feature 3 will add obsolete detection and UI on top.

## Backend Changes

### `backend/app/services/llm.py`

Add method to `LLMOrchestrator`:

```python
async def embed_batch_chunked(
    self,
    texts: list[str],
    chunk_size: int,
    concurrency: int,
) -> list[list[float]]:
    """Embed many texts via multiple concurrent embed_batch calls.
    Preserves input order. Any chunk failure propagates."""
    if not texts:
        return []

    chunks = [texts[i:i+chunk_size] for i in range(0, len(texts), chunk_size)]
    semaphore = asyncio.Semaphore(concurrency)

    async def run_chunk(chunk):
        async with semaphore:
            return await self.embed_batch(chunk)

    results = await asyncio.gather(*[run_chunk(c) for c in chunks])
    return [v for chunk_result in results for v in chunk_result]
```

### `backend/app/services/pipeline.py`

Rewrite `process_batch` as a phased implementation. `process_memory` becomes a thinner function that handles single-memory cases by bypassing the in-memory cache.

New instance state on `ProcessingPipeline.__init__`:

```python
self.embedding_fingerprint = f"{llm.config['embedding'].model}|{llm.config['embedding'].dimensions or 'auto'}"
self._entity_cache: dict[tuple[str, str], tuple[list[float], float]] = {}
self._entity_cache_lock = asyncio.Lock()
```

New internal methods:

```python
async def _lookup_entity_embeddings(
    self,
    names: list[str],
    ttl_seconds: float,
    use_memory_cache: bool,
) -> tuple[dict[str, list[float]], list[str]]:
    """Return (hits, misses). Hits map lowercased name to embedding.
    Misses are names (lowercase) needing fresh embedding."""

async def _store_entity_embeddings(
    self,
    name_to_embedding: dict[str, list[float]],
    use_memory_cache: bool,
) -> None:
    """Write new embeddings to DB cache and (optionally) in-memory cache."""
```

New `process_batch` structure:

```python
async def process_batch(self, entries: list[dict]) -> list[dict]:
    flags = await _get_feature_flags(self.session_factory)
    pipeline_concurrency = flags.get("pipeline_concurrency", 5)
    embed_chunk_size = flags.get("embedding_batch_size", 20)
    embed_concurrency = flags.get("embedding_concurrency", 1)
    ttl_seconds = flags.get("entity_cache_ttl_minutes", 60) * 60

    # Phase 1: content embedding
    contents = [e["content"] for e in entries]
    vectors = await self.llm.embed_batch_chunked(contents, embed_chunk_size, embed_concurrency)

    # Phase 2: extraction
    ext_prompt = prompt.get("extraction")
    semaphore = asyncio.Semaphore(pipeline_concurrency)

    async def run_extract(content):
        async with semaphore:
            return await self.extraction.extract(content, system_prompt=ext_prompt)

    extractions = await asyncio.gather(*[run_extract(e["content"]) for e in entries])

    # Phase 3: entity embedding with cache
    unique_names: set[str] = set()
    for ext in extractions:
        if isinstance(ext, dict):
            for entity in ext.get("entities", []):
                unique_names.add(entity["name"].lower())

    unique_names_list = sorted(unique_names)
    hits, misses = await self._lookup_entity_embeddings(
        unique_names_list, ttl_seconds, use_memory_cache=True,
    )

    if misses:
        new_embeddings_list = await self.llm.embed_batch_chunked(
            misses, embed_chunk_size, embed_concurrency,
        )
        new_map = dict(zip(misses, new_embeddings_list))
        await self._store_entity_embeddings(new_map, use_memory_cache=True)
        hits.update(new_map)

    name_to_embedding = hits  # lowercase name → embedding

    # Phase 4: dedup lookup (one call per unique name, not per memory-entity)
    canonical_map: dict[str, str] = {}
    async with self.session_factory() as dedup_session:
        dedup_repo = PostgresGraphRepository(dedup_session)
        for lower_name, emb in name_to_embedding.items():
            match = await dedup_repo.find_similar_entity(emb, threshold=0.85)
            if match and match["name"].lower() != lower_name:
                canonical_map[lower_name] = match["name"]

    # Phase 5: per-memory graph and vector writes (concurrent)
    async def run_write(entry, vector, extraction):
        async with semaphore:
            return await self._write_memory(
                entry, vector, extraction, name_to_embedding, canonical_map,
            )

    results = await asyncio.gather(*[
        run_write(e, v, ext)
        for e, v, ext in zip(entries, vectors, extractions)
    ], return_exceptions=True)

    return results
```

`_write_memory` is the refactored tail of the current `process_memory` — it takes pre-computed vector, extraction, entity embeddings, and canonical map, and writes vector repo + graph repo. It does NOT call `embed` or `extract` itself.

`process_memory` (the old single-memory entry point) is rewritten as a thin wrapper that calls `process_batch([entry])` OR runs the same phases with `use_memory_cache=False` inline. Prefer the former for simplicity.

### `backend/app/repositories/graph.py`

Add repository methods:

```python
async def get_cached_entity_embeddings(
    self,
    name_lowers: list[str],
    model_fingerprint: str,
) -> dict[str, list[float]]:
    """Return {name_lower: embedding} for entries matching the fingerprint."""

async def upsert_entity_embeddings_cache(
    self,
    name_to_embedding: dict[str, list[float]],
    model_fingerprint: str,
) -> None:
    """Upsert cache entries. ON CONFLICT updates last_used_at and hit_count."""
```

### `backend/app/models/embedding.py`

Add new model class `EntityEmbeddingCache`. Add `model_fingerprint` columns to existing `MemoryEmbedding` and `CodeChunkEmbedding` models.

### `backend/app/models/graph.py`

The `Entity` ORM model does not currently declare the `embedding` column — it is added via raw SQL in the initial migration and written via `PostgresGraphRepository.upsert_entity_embedding`. Follow the same pattern for `model_fingerprint`: add the column via raw SQL in the migration, and update the repository write to include it. Do not add the field to the `Entity` ORM model.

### Migration

New Alembic revision that:
- Creates `entity_embedding_cache` table with composite PK and index (use `op.execute` for the `vector(1024)` column type, as with the initial schema)
- Adds `model_fingerprint VARCHAR(100)` column to `memory_embeddings` via ORM-aware `op.add_column`
- Adds `model_fingerprint VARCHAR(100)` column to `code_chunk_embeddings` via ORM-aware `op.add_column`
- Adds `model_fingerprint VARCHAR(100)` column to `entities` via `op.execute("ALTER TABLE entities ADD COLUMN model_fingerprint VARCHAR(100)")` to stay consistent with how the embedding column was added in `0001_initial_schema.py`
- Backfill is NOT performed — existing rows get NULL fingerprint, which Feature 3 will treat as "obsolete / unknown model"

### `backend/app/api/routes/config.py`

Update `FeatureFlagsResponse` and `FeatureFlagsUpdate` schemas to include the three new flags. Add validation: all three must be positive integers within reasonable bounds (e.g., `embedding_batch_size` between 1 and 200, `embedding_concurrency` between 1 and 10, `entity_cache_ttl_minutes` between 1 and 1440).

### `backend/app/services/code_pipeline.py`

The code indexer's existing `embed_batch` call at line 931 should be switched to `embed_batch_chunked` using the same feature flag values. This aligns code chunk embedding with the same chunking and concurrency controls.

## Frontend Changes

### `frontend/src/hooks/api/use-config-api.ts`

Add the three new fields to `FeatureFlags`:

```typescript
export interface FeatureFlags {
  llm_enrichment_enabled: boolean;
  hybrid_search_enabled: boolean;
  reranker_enabled: boolean;
  pipeline_concurrency: number;
  classification_areas: string[];
  classification_mode: "simple" | "expanded";
  embedding_batch_size: number;
  embedding_concurrency: number;
  entity_cache_ttl_minutes: number;
}
```

### `frontend/src/routes/_authenticated/settings.tsx`

Extend the existing `FeatureFlagsCard` component with a new "Embedding Pipeline" subsection showing three number inputs:

- **Embedding Batch Size** — texts per embedding request (tooltip: "How many texts are sent in one embedding HTTP call. Lower this if you hit token limits.")
- **Embedding Concurrency** — parallel embedding requests (tooltip: "How many embedding calls run at once. Set to 1 for Ollama with concurrent=1.")
- **Entity Cache TTL (minutes)** — in-memory entity embedding cache lifetime (tooltip: "How long entity embeddings are held in memory before re-checking the database.")

Each input uses the existing `Input type="number"` pattern from other numeric flags in the card.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/config.py` | Add 3 new feature flags to `FEATURE_FLAGS_DEFAULTS` |
| `backend/app/services/llm.py` | Add `embed_batch_chunked` method |
| `backend/app/services/pipeline.py` | Rewrite `process_batch` as phased implementation, add cache helpers, store fingerprint |
| `backend/app/services/code_pipeline.py` | Switch `embed_batch` call to `embed_batch_chunked` |
| `backend/app/repositories/graph.py` | Add cache get/upsert methods |
| `backend/app/models/embedding.py` | Add `EntityEmbeddingCache` model, `model_fingerprint` column on `MemoryEmbedding` and `CodeChunkEmbedding` |
| `backend/migrations/versions/<new>.py` | Create cache table, add fingerprint columns |
| `backend/app/api/routes/config.py` | Add schema fields and validation for 3 new flags |
| `frontend/src/hooks/api/use-config-api.ts` | Add flags to `FeatureFlags` type |
| `frontend/src/routes/_authenticated/settings.tsx` | Add "Embedding Pipeline" inputs |

## Out of Scope

The following are explicitly NOT part of this feature and will be addressed by Feature 2 (pipeline failure tracking) and Feature 3 (model change handling):

- Per-phase failure state on the memory record
- Retry UI for failed memories
- Model change detection and obsolete flagging
- "Obsolete entries" UI page
- Cache eviction beyond TTL (no size-based eviction in this feature)

Feature 1 establishes the fingerprint columns and persistent cache that Features 2 and 3 build on, but does not implement the failure tracking or obsolete detection logic itself.
