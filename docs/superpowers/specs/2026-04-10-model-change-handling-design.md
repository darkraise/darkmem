# Model Change Handling and Obsolete Re-embedding

**Date:** 2026-04-10
**Status:** Draft
**Feature:** 3 of 3 (Feature 1: phased batch pipeline — shipped. Feature 2: pipeline failure tracking — shipped.)

## Problem

When a user changes the embedding model via the settings UI, existing embeddings in the database were produced by the old model and are no longer semantically comparable with queries embedded by the new model. Search quality degrades silently. Feature 1 added `model_fingerprint` columns to all embedding-carrying tables so the mismatch is detectable, but nothing currently acts on that mismatch.

Darkmem has four embedding-carrying tables:

- `memory_embeddings` — content vectors for memory search
- `code_chunk_embeddings` — code chunk vectors for code search
- `entities` — entity name vectors for dedup lookups
- `entity_embedding_cache` — persistent cache keyed by `(name_lower, model_fingerprint)`

All four need handling when the model changes. The first three should be re-embedded with the new model. The cache can be left alone (its compound primary key means old entries are simply ignored on lookup) or pruned to reclaim disk space.

## Solution

Obsolete state is **computed at query time** from the existing `model_fingerprint` columns — no new schema, no new state tracking. A new `ReembedService` provides obsolete counts, paginated listings, and batch re-embed operations that use Feature 1's `embed_batch_chunked` helper for efficient bulk re-embedding. A new API router at `/api/v1/reembed` exposes per-category re-embed endpoints plus a combined "re-embed all" endpoint. Progress is streamed via a new WebSocket event `pipeline.reembed_batch.progress`. The settings page shows a modal prompt immediately after a model change if any obsolete data exists, and the Pipeline page gains an "Obsolete Embeddings" card that is the persistent source of truth for obsolete counts and re-embed actions.

## Data Model

**No schema changes.** Feature 3 reuses the `model_fingerprint` columns already added in Feature 1:

- `memory_embeddings.model_fingerprint VARCHAR(100)`
- `code_chunk_embeddings.model_fingerprint VARCHAR(100)`
- `entities.model_fingerprint VARCHAR(100)` (added via raw SQL in Feature 1's migration)
- `entity_embedding_cache.model_fingerprint VARCHAR(100)` (composite primary key)

Obsolete rows are computed via:

```sql
SELECT COUNT(*) FROM memory_embeddings
WHERE model_fingerprint != :current_fp OR model_fingerprint IS NULL;

SELECT COUNT(*) FROM code_chunk_embeddings
WHERE model_fingerprint != :current_fp OR model_fingerprint IS NULL;

SELECT COUNT(*) FROM entities
WHERE model_fingerprint != :current_fp OR model_fingerprint IS NULL;
```

The `OR model_fingerprint IS NULL` branch catches rows written before Feature 1 (or any other row with a missing fingerprint). These are treated as obsolete so a user can backfill them by running a re-embed.

When a re-embed operation updates a row with the new embedding, it also writes the current fingerprint to the row. The row naturally drops out of the obsolete query on its next evaluation. There is no separate "resolved" flag to manage.

## Service Layer

New module: `backend/app/services/reembed.py`

### ReembedService

```python
class ReembedService:
    def __init__(self, session: AsyncSession): ...

    async def count_obsolete(self, current_fingerprint: str) -> dict[str, int]:
        """Return obsolete row counts for each category.
        Returns {'memories': N, 'code_chunks': N, 'entities': N}."""

    async def list_obsolete_memories(
        self, current_fingerprint: str, limit: int = 100, offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Return (items, total_count). Each item: id, content_preview,
        model_fingerprint (old one or None)."""

    async def list_obsolete_code_chunks(
        self, current_fingerprint: str, limit: int = 100, offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Each item: id, file_path, symbol_name, chunk_preview,
        model_fingerprint."""

    async def list_obsolete_entities(
        self, current_fingerprint: str, limit: int = 100, offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Each item: id, name, entity_type, model_fingerprint."""

    async def reembed_memories(
        self, current_fingerprint: str, llm, batch_id: str,
        broadcast: Callable[[str, dict], Awaitable[None]] | None,
        flags: dict,
    ) -> dict:
        """Re-embed all obsolete memories. Returns {'processed': N, 'errors': N}."""

    async def reembed_code_chunks(
        self, current_fingerprint: str, llm, batch_id: str,
        broadcast, flags: dict,
    ) -> dict:
        """Re-embed all obsolete code chunks."""

    async def reembed_entities(
        self, current_fingerprint: str, llm, batch_id: str,
        broadcast, flags: dict,
    ) -> dict:
        """Re-embed all obsolete entity names.

        In addition to updating entities.embedding, this method also
        upserts the new (name_lower, current_fingerprint, embedding) into
        entity_embedding_cache so that future ingestions benefit from the
        cache instead of re-embedding the same names."""

    async def prune_obsolete_cache_entries(self, current_fingerprint: str) -> int:
        """Delete entity_embedding_cache rows whose fingerprint is not current.
        Returns deleted row count."""
```

### Re-embed execution pattern

Each `reembed_*` method follows the same pattern. The method takes a pre-opened `AsyncSession` in the constructor, an `LLMOrchestrator` passed by the caller, and commits incrementally after each chunk so progress is durable.

```python
async def reembed_memories(self, current_fingerprint, llm, batch_id, broadcast, flags):
    embed_chunk_size = flags.get("embedding_batch_size", 20)
    embed_concurrency = flags.get("embedding_concurrency", 1)

    # 1. Get total count for progress reporting
    total = await self._count_obsolete_memories(current_fingerprint)

    if broadcast:
        await broadcast("pipeline.reembed_batch.progress", {
            "batch_id": batch_id, "category": "memories",
            "current": 0, "total": total, "processed": 0, "errors": 0,
            "state": "started",
        })

    processed = 0
    errors = 0
    last_error: str | None = None
    chunk_size_rows = 100  # rows fetched per round

    while True:
        # 2. Fetch a chunk of obsolete rows (memory_id + content)
        rows = await self._fetch_obsolete_memory_rows(
            current_fingerprint, limit=chunk_size_rows,
        )
        if not rows:
            break

        # 3. Batch-embed the content via Feature 1's helper
        texts = [r["content"] for r in rows]
        try:
            vectors = await llm.embed_batch_chunked(texts, embed_chunk_size, embed_concurrency)
        except Exception as e:
            logger.exception("Re-embed batch failed for memories: %s", e)
            errors += len(rows)
            last_error = f"{type(e).__name__}: {e}"[:500]
            if broadcast:
                await broadcast("pipeline.reembed_batch.progress", {
                    "batch_id": batch_id, "category": "memories",
                    "current": processed + errors, "total": total,
                    "processed": processed, "errors": errors, "state": "progress",
                })
            # Cannot continue: the failed rows would just be refetched on next loop.
            # Break to let the user retry later.
            break

        # 4. Update rows with new embeddings and current fingerprint, then commit.
        #    Committing per-chunk makes progress durable and ensures the next
        #    _fetch_obsolete_memory_rows call does not return the rows we just flipped.
        try:
            await self._update_memory_embeddings(rows, vectors, current_fingerprint)
            await self.session.commit()
            processed += len(rows)
        except Exception as e:
            logger.exception("Failed to persist re-embedded memories: %s", e)
            await self.session.rollback()
            errors += len(rows)
            last_error = f"{type(e).__name__}: {e}"[:500]
            break

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "memories",
                "current": processed + errors, "total": total,
                "processed": processed, "errors": errors, "state": "progress",
            })

    if broadcast:
        await broadcast("pipeline.reembed_batch.progress", {
            "batch_id": batch_id, "category": "memories",
            "current": total, "total": total,
            "processed": processed, "errors": errors, "state": "done",
            "error_message": last_error,
        })

    return {"processed": processed, "errors": errors, "last_error": last_error}
```

**Per-chunk commit rationale.** Without committing after each chunk update:
- The next `_fetch_obsolete_memory_rows` in the same transaction may return the same rows (depending on PostgreSQL read behavior within a single transaction) and the loop would infinite-loop.
- A mid-loop crash rolls back all prior work in the current transaction, losing all progress.
- Frontend WebSocket consumers see progress events but the underlying rows are not durable yet.

Committing after each successful `_update_memory_embeddings` call makes progress durable and ensures the next fetch sees an advancing cursor through the obsolete set.

`reembed_code_chunks` follows the same pattern but fetches `id` and `chunk_content` from `code_chunk_embeddings` and updates the same table:

```python
# Fetch
SELECT id, chunk_content FROM code_chunk_embeddings
WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
LIMIT :limit
```

`reembed_entities` follows the same pattern but fetches from the `entities` table and also maintains the `entity_embedding_cache`:

```python
# Fetch
SELECT id, name FROM entities
WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
LIMIT :limit

# After a successful batch update of entities.embedding and entities.model_fingerprint,
# also upsert into entity_embedding_cache. Dedupe by lowercase name first because
# multiple entities can share the same name (e.g., "PostgreSQL" as service and technology).

cache_upserts: dict[str, list[float]] = {}
for row, vec in zip(rows, vectors):
    cache_upserts[row["name"].lower()] = vec

for name_lower, vec in cache_upserts.items():
    await self.session.execute(
        text("""
            INSERT INTO entity_embedding_cache (name_lower, model_fingerprint, embedding)
            VALUES (:name, :fp, CAST(:vec AS vector))
            ON CONFLICT (name_lower, model_fingerprint) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                last_used_at = NOW(),
                hit_count = entity_embedding_cache.hit_count + 1
        """),
        {"name": name_lower, "fp": current_fingerprint, "vec": str(vec)},
    )
# commit() happens at the end of the outer try block, same as memories/code_chunks.
```

Best-effort failure handling (per Q5 answer B): a failing chunk increments the error count and breaks the loop. Rows that failed retain their old fingerprint and will appear in the next obsolete query. The user can click re-embed again to retry — the operation is idempotent.

### Bulk row update

Row updates use a single UPDATE statement driven by a `jsonb_to_recordset` to zip the id and vector arrays correctly:

```sql
UPDATE memory_embeddings
SET embedding = v.vec::vector,
    model_fingerprint = :fp
FROM jsonb_to_recordset(CAST(:updates AS jsonb)) AS v(id uuid, vec text)
WHERE memory_embeddings.id = v.id
```

The `:updates` parameter is bound to a JSON string of the form `[{"id": "...", "vec": "[0.1, 0.2, ...]"}, ...]`. Using `jsonb_to_recordset` avoids the PostgreSQL `unnest` cross-product pitfall (where `SELECT unnest(a), unnest(b)` produces an N×N cross-product instead of a parallel zip).

This applies N embedding updates in a single round trip per chunk.

### Concurrent re-embed protection

A module-level helper `ReembedLockSet` mirrors Feature 2's `RetryLockSet` pattern for consistency:

```python
class ReembedLockSet:
    def __init__(self) -> None:
        self._locked: set[str] = set()

    def try_acquire(self, category: str) -> bool:
        if category in self._locked:
            return False
        self._locked.add(category)
        return True

    def release(self, category: str) -> None:
        self._locked.discard(category)

    def is_locked(self, category: str) -> bool:
        return category in self._locked

# Module-level singleton imported by the API router
reembed_locks = ReembedLockSet()
```

Values: `"memories"`, `"code_chunks"`, `"entities"`. The single-category endpoints acquire the category name; the `/reembed/all` endpoint acquires all three before starting (and releases any it acquired if a later acquire fails). Released in a `finally` block after the background task completes. Single-process, single-admin — in-memory is sufficient.

### Background task session management

**Important:** `ReembedService` takes an `AsyncSession` in its constructor and uses `self.session` throughout. Re-embed runs in an `asyncio.create_task()` background task that outlives the HTTP request. The request's session (from `Depends(get_session)`) is closed when the endpoint returns, so the background task **must not** reuse it. Instead, the background task opens a new session via `async_session_factory()` and constructs a fresh `ReembedService` for that session.

The LLM orchestrator is captured at dispatch time from `request.app.state.pipeline.llm` (or `request.app.state.llm` if the pipeline is None). The captured reference is closed over by the background task's inner function.

Example (inside the `/reembed/memories` endpoint handler):

```python
@router.post("/memories", status_code=202)
async def reembed_memories(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")

    if not reembed_locks.try_acquire("memories"):
        return JSONResponse(
            status_code=409,
            content={"accepted": False, "reason": "already_running"},
        )

    # Snapshot the inputs the background task needs
    snapshot_fingerprint = pipeline.embedding_fingerprint
    snapshot_llm = pipeline.llm
    batch_id = str(uuid4())

    # Compute total with the request session before dispatching
    svc = ReembedService(session)
    total = (await svc.count_obsolete(snapshot_fingerprint))["memories"]

    async def _run():
        try:
            from app.database import async_session_factory
            from app.services.pipeline import _get_feature_flags
            flags = await _get_feature_flags(async_session_factory)
            async with async_session_factory() as bg_session:
                bg_svc = ReembedService(bg_session)
                await bg_svc.reembed_memories(
                    current_fingerprint=snapshot_fingerprint,
                    llm=snapshot_llm,
                    batch_id=batch_id,
                    broadcast=event_manager.broadcast,
                    flags=flags,
                )
        except Exception:
            logger.exception("Re-embed memories background task failed")
        finally:
            reembed_locks.release("memories")

    asyncio.create_task(_run())
    return {"accepted": True, "batch_id": batch_id, "total": total}
```

The same pattern applies to `/reembed/code-chunks`, `/reembed/entities`, and `/reembed/all`. The combined endpoint acquires all three locks up front and releases them all in its `finally`.

### `/reembed/all` failure semantics and event flow

When `/reembed/all` runs memories → entities → code_chunks in sequence, all three categories share the **same `batch_id`** but emit events with distinct `category` values. The frontend listens for events filtered by `batch_id` and routes each event to the correct progress bar based on `category`.

Each category runs independently. If `reembed_memories` fails mid-batch, the task records the error count, emits a `done` event for the memories category, then proceeds to `reembed_entities`. A category-level Python exception (e.g., database connection lost) is caught, logged, and the task continues to the next category. The frontend receives `done` events for each of the three categories in sequence; at any time during the run, exactly one category is actively progressing.

If all three categories complete with zero errors, the obsolete counts drop to zero and the card disappears. If any category has errors, the non-zero count remains and the user can click its individual "Re-embed" button to retry.

Pseudo-flow inside the `/reembed/all` background task:

```python
async def _run_all():
    try:
        async with async_session_factory() as bg_session:
            svc = ReembedService(bg_session)
            for category, method in [
                ("memories", svc.reembed_memories),
                ("entities", svc.reembed_entities),
                ("code_chunks", svc.reembed_code_chunks),
            ]:
                try:
                    await method(
                        current_fingerprint=snapshot_fingerprint,
                        llm=snapshot_llm,
                        batch_id=batch_id,
                        broadcast=event_manager.broadcast,
                        flags=flags,
                    )
                except Exception:
                    logger.exception("Re-embed %s failed under batch %s", category, batch_id)
                    # Continue to the next category regardless of this category's outcome
    finally:
        for cat in ("memories", "entities", "code_chunks"):
            reembed_locks.release(cat)
```

### Mid-batch model change race

The re-embed task snapshots `current_fingerprint = pipeline.embedding_fingerprint` at the moment it is dispatched. If the user changes the LLM config again while the task is running, `pipeline.embedding_fingerprint` updates to a new value but the task continues with the old snapshot. Rows processed during this window will have the stale snapshot as their fingerprint and will appear as obsolete on the next check.

This is an acceptable edge case: the user sees the remaining obsolete count after the task finishes and can click re-embed again to catch up. The alternative — reading the fingerprint fresh on every iteration — would make the progress target shift mid-run and is harder to reason about.

To reduce the likelihood of this race, the settings page disables the "Save" button for the LLM config form while any re-embed batch is in progress (driven by the same `useReembedBatchProgress` hook the Pipeline page uses). This is a UI-level guard, not a backend invariant.

## API Layer

New router: `backend/app/api/routes/reembed.py` mounted at `/api/v1/reembed`. All endpoints require `require_auth`.

### Endpoints

```
GET /api/v1/reembed/obsolete-counts
    Returns: { memories: int, code_chunks: int, entities: int,
               current_fingerprint: string }

GET /api/v1/reembed/obsolete/memories
    Query: limit=100, offset=0
    Returns: { items: [...], total: int }

GET /api/v1/reembed/obsolete/code-chunks
    Query: limit=100, offset=0
    Returns: { items: [...], total: int }

GET /api/v1/reembed/obsolete/entities
    Query: limit=100, offset=0
    Returns: { items: [...], total: int }

POST /api/v1/reembed/memories
    Async. Dispatches reembed_memories as background task.
    Returns 202: { accepted: true, batch_id: string, total: int }
    Returns 409: { accepted: false, reason: "already_running" }

POST /api/v1/reembed/code-chunks
    Same pattern as /reembed/memories.

POST /api/v1/reembed/entities
    Same pattern as /reembed/memories.

POST /api/v1/reembed/all
    Async. Acquires locks for all three categories, dispatches a single
    background task that runs reembed_memories, reembed_entities, and
    reembed_code_chunks in sequence under one batch_id.
    Returns 202: { accepted: true, batch_id: string,
                   totals: { memories: int, entities: int, code_chunks: int } }
    Returns 409 if any category is already running.

POST /api/v1/reembed/prune-cache
    Synchronous. Deletes entity_embedding_cache rows whose fingerprint
    is not the current one. Returns: { deleted: int }
```

### Hook into LLM config change

The existing `POST /api/v1/config/llm` handler already computes the new fingerprint and swaps it on the pipeline (Feature 1). Feature 3 extends the handler to also return obsolete counts in the response.

**Important:** the existing endpoint is declared `@router.post("/llm", response_model=LLMConfigResponse)`. FastAPI strips any return field not declared on the response model, so simply returning `{**dump, "obsolete_after_change": ...}` would silently drop the new field. We must change the response model to a new wrapper type.

Add a new response schema in `backend/app/schemas/config.py`:

```python
class LLMConfigUpdateResponse(LLMConfigResponse):
    """Returned by POST /config/llm. Extends LLMConfigResponse with
    the computed obsolete counts for the new embedding model."""
    obsolete_after_change: dict[str, int] | None = None
```

Change the endpoint decorator:

```python
@router.post("/llm", response_model=LLMConfigUpdateResponse)
async def update_llm_config(...):
    ...
```

At the end of `update_llm_config`, after the existing fingerprint swap:

```python
# Feature 3: compute obsolete counts for the new fingerprint
obsolete_after_change = None
if pipeline is not None:
    from app.services.reembed import ReembedService
    svc = ReembedService(session)
    obsolete_after_change = await svc.count_obsolete(pipeline.embedding_fingerprint)

purpose_payload = {p: cfg_to_schema(c) for p, c in updated_config.items()}
return LLMConfigUpdateResponse(
    **purpose_payload,
    obsolete_after_change=obsolete_after_change,
)
```

The `pipeline is not None` check is sufficient — `pipeline` was already fetched from `request.app.state.pipeline` earlier in the handler. No need for a redundant second check.

The frontend reads `data.obsolete_after_change` from the mutation success payload and shows the modal prompt if any count is non-zero.

## Event Schema

New event added to `backend/app/schemas/events.py`:

```python
class PipelineReembedBatchProgress(BaseModel):
    batch_id: str
    category: Literal["memories", "code_chunks", "entities"]
    current: int
    total: int
    processed: int
    errors: int
    state: Literal["started", "progress", "done"]
    error_message: str | None = None
```

The optional `error_message` field is populated on the final `state="done"` event if the batch had at least one error, containing the last exception message observed during the run (truncated to 500 chars). Users see this in a toast alongside the "X failed" count so they know why without having to dig through server logs.

Registered in `EVENT_SCHEMAS` alongside the existing events. Mirrored in `frontend/src/lib/websocket-events.ts`.

## Frontend

### Settings page modal

File: `frontend/src/routes/_authenticated/settings.tsx`

The existing `useUpdateLlmConfig` mutation already handles the save. When the mutation succeeds:

1. Invalidate the `obsoleteCounts` query so the Pipeline page's card refreshes on next render (`qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })`).
2. Read `data.obsolete_after_change`. If any count is non-zero, open a darkraise-ui Dialog with the message and actions described in the design discussion. "Re-embed now" triggers `useReembedAll()` and navigates to the Pipeline page. "Later" closes the dialog.

The settings page also disables the LLM config "Save" button while any re-embed batch is in progress (see "Mid-batch model change race" in the service section). It reads `useObsoleteCounts()` or checks for any active `reembedBatchProgress` cache entry.

### Pipeline page "Obsolete Embeddings" card

File: `frontend/src/routes/_authenticated/pipeline.tsx`

New `ObsoleteEmbeddingsCard` component placed above the existing `UnresolvedFailuresCard`. Shows:

- The current embedding fingerprint as a small muted header
- A three-row table (memories / entities / code_chunks) with counts and per-row Re-embed buttons
- A "Re-embed all obsolete" button at the bottom
- A "Prune old cache entries" button next to it
- Per-row progress bars driven by `useReembedBatchProgress` when a re-embed is active

Counts come from `useObsoleteCounts()` which fetches `/api/v1/reembed/obsolete-counts` and polls every 30 seconds. WebSocket events trigger cache invalidation on `state="done"`.

The card is only rendered if any count is non-zero, OR if a re-embed batch is currently in progress. When all counts are zero and nothing is running, the card is hidden to reduce visual clutter.

### New API hooks in `use-pipeline-api.ts`

```typescript
export interface ObsoleteCounts {
  memories: number
  code_chunks: number
  entities: number
  current_fingerprint: string
}

export function useObsoleteCounts() {
  return useQuery<ObsoleteCounts>({
    queryKey: ["obsoleteCounts"],
    queryFn: () => apiFetch<ObsoleteCounts>("/reembed/obsolete-counts"),
    refetchInterval: 30_000,
  })
}

export function useReembedMemories() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/memories", { method: "POST" },
      ),
  })
}

export function useReembedCodeChunks() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/code-chunks", { method: "POST" },
      ),
  })
}

export function useReembedEntities() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/entities", { method: "POST" },
      ),
  })
}

export function useReembedAll() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{
        accepted: boolean
        batch_id: string
        totals: { memories: number; entities: number; code_chunks: number }
      }>("/reembed/all", { method: "POST" }),
  })
}

export function usePruneObsoleteCache() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ deleted: number }>("/reembed/prune-cache", { method: "POST" }),
  })
}

export function useReembedBatchProgress(
  batchId: string | null,
  category: "memories" | "code_chunks" | "entities",
) {
  return useQuery<
    import("@/lib/websocket-events").PipelineReembedBatchProgress | undefined
  >({
    queryKey: ["reembedBatchProgress", batchId, category],
    queryFn: () => undefined,
    enabled: false,
    staleTime: Infinity,
  })
}
```

### WebSocket event handler

File: `frontend/src/lib/websocket.ts`

Add a branch for `pipeline.reembed_batch.progress` in the existing `onmessage` handler:

```typescript
if (msg.event === "pipeline.reembed_batch.progress") {
  const d = msg.data as WebSocketEventMap["pipeline.reembed_batch.progress"]
  qc.setQueryData(["reembedBatchProgress", d.batch_id, d.category], d)
  if (d.state === "done") {
    void qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
  }
}
```

### WebSocket event types

File: `frontend/src/lib/websocket-events.ts`

Add `PipelineReembedBatchProgress` interface and register it in `WebSocketEventMap`.

## Files Changed

| File | Change |
|---|---|
| `backend/app/services/reembed.py` | New `ReembedService` with count/list/reembed/prune methods |
| `backend/app/api/routes/reembed.py` | New router with obsolete counts, list, and re-embed endpoints |
| `backend/app/api/routes/config.py` | Extend `update_llm_config` response with `obsolete_after_change` |
| `backend/app/schemas/events.py` | Add `PipelineReembedBatchProgress` and register in `EVENT_SCHEMAS` |
| `backend/app/schemas/config.py` | Add new `LLMConfigUpdateResponse(LLMConfigResponse)` subclass with the optional `obsolete_after_change` field |
| `backend/app/main.py` | Include the new router |
| `frontend/src/lib/websocket-events.ts` | Add `PipelineReembedBatchProgress` type and map entry |
| `frontend/src/lib/websocket.ts` | Handle `pipeline.reembed_batch.progress` event |
| `frontend/src/hooks/api/use-pipeline-api.ts` | Add obsolete counts and re-embed hooks |
| `frontend/src/routes/_authenticated/pipeline.tsx` | Add `ObsoleteEmbeddingsCard` component |
| `frontend/src/routes/_authenticated/settings.tsx` | Add modal prompt on model change |

No database migration. No changes to Feature 1 or Feature 2 tables.

## Impact Assessment

**Scope:** Backend changes are additive (one new service, one new router, plus event schema and config route extension). No database migration, no changes to Feature 1 or Feature 2 tables. Frontend changes add one new card on the Pipeline page, one modal on the settings page, and a handful of hooks. Estimated implementation size is roughly 500 lines, smaller than Feature 2.

**Risks:**
- The bulk UPDATE SQL uses `jsonb_to_recordset`, which requires Postgres 9.4+. Darkmem already runs on Postgres with pgvector, so version is not a concern.
- Long-running re-embed tasks have no cancellation mechanism. A user who accidentally kicks off a re-embed on 10,000 rows must wait for it to complete or restart the server. Acceptable for a single-admin deployment; noted in Out of Scope.
- Concurrent `POST /config/llm` during a running re-embed creates a minor race. Mitigated by disabling the settings save button while a re-embed is in progress, but not enforced at the backend level.
- Re-embed chunk failures break the loop rather than continuing. This is intentional (Q5 answer B) but means transient LLM failures can strand progress. The user retries by clicking again — idempotent, safe.

**Performance:**
- Re-embed of 10,000 memories at `embedding_concurrency=1` and `embedding_batch_size=20` takes roughly `10000/20 × latency_per_embed_call ≈ 500 × 1s = ~8 minutes` on Ollama with a small model. Batched bulk UPDATE means database writes are not the bottleneck.
- Obsolete counts query hits the fingerprint column directly. Without a dedicated index on `model_fingerprint`, large tables may do sequential scans. For the darkmem deployment sizes (thousands, not millions) this is fine. A follow-up could add `CREATE INDEX ... ON memory_embeddings(model_fingerprint) WHERE model_fingerprint IS NOT NULL` if counts become slow.
- The `count_obsolete` call runs synchronously inside `POST /config/llm` before returning the response. On very large tables it could add seconds to the save latency. Acceptable for darkmem's deployment size; mitigation would be computing the count asynchronously and pushing it via a follow-up WebSocket event.
- `pipeline.reembed_batch.progress` events fire once per chunk (not once per row). For a batch of 10,000 memories with chunk size 20 that's 500 WebSocket messages — manageable.

## Testing Strategy

Given darkmem's existing test infrastructure (unit tests in `backend/tests/unit/`, no reliable integration test database in the current environment), Feature 3 tests focus on pure-function and behavior units that don't require a database:

**Unit tests** (`backend/tests/unit/test_reembed_service.py`):
- `count_obsolete` returns zero when all rows match the current fingerprint (mock session)
- `count_obsolete` counts rows with different fingerprint and rows with NULL fingerprint
- Bulk UPDATE SQL generation produces valid `jsonb_to_recordset` clause
- `reembed_memories` loop handles empty obsolete set (no iterations, emits started + done events)
- `reembed_memories` loop breaks on first chunk failure and emits progress + done events with error count
- `_reembed_in_progress` lock set prevents double-dispatch

**Integration tests** (deferred until test DB is reliable):
- Full re-embed flow against a seeded database
- `/config/llm` endpoint returns correct `obsolete_after_change`
- `/reembed/all` endpoint runs all three categories end-to-end
- `prune_obsolete_cache_entries` deletes only non-current rows

The plan's E2E verification task covers runtime behavior manually (change the embedding model in settings, observe the modal and the Pipeline page card, click re-embed and watch progress).

## Out of Scope

The following are explicitly NOT part of Feature 3:

- Fingerprint tracking for extraction, reasoning, summarization, or reranker models (Q6 answer A — embedding model only)
- Integration with Feature 2's `pipeline_failures` table for per-item retry of re-embed errors (Q5 answer B — best-effort only, failed rows stay obsolete)
- Automatic cache pruning (pruning is user-triggered only)
- Manual per-row re-embed (re-embed is always bulk per category)
- UI for viewing individual obsolete rows (list endpoints exist for future use, but v1 only shows aggregate counts on the Pipeline page)
- Historical fingerprint tracking or "which model was this embedded with" reporting (only current vs not-current matters)
- Re-embed cancellation (a running batch cannot be gracefully cancelled by the user; requires server restart)
- Backend-side enforcement against concurrent LLM config changes during an active re-embed (UI-only guard)
- Index on `model_fingerprint` column for faster obsolete counts (add in a follow-up if count queries become slow)
