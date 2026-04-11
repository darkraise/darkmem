# Pipeline Failure Tracking and Retry

**Date:** 2026-04-10
**Status:** Draft
**Feature:** 2 of 3 (Feature 1: phased batch pipeline — shipped. Feature 3: model change handling — separate spec.)

## Problem

The current pipeline has no persistent record of which entities are currently in a failed state. The existing "Retry Failed" flow queries `audit_log` for entries where `details.error != null`, which is fragile because the audit log is append-only: once a memory is retried successfully, the old failure entry remains in the audit log and the memory still appears "failed". The audit log is simultaneously acting as event history and state signal, and those concerns conflict.

In addition, the problem is not specific to memory ingestion. Code indexing runs a 13-phase pipeline whose failures currently accumulate in `self._stats["errors"]` as string messages, never surfaced to the user and never retried. Future pipelines (document ingestion, web scraping, etc.) will have the same needs. A memory-only solution would not scale.

This is a greenfield feature — the existing audit-log-based `reprocess_failed` flow is simply replaced, no backward compatibility with historical audit log entries is required.

## Solution

Introduce a centralized `pipeline_failures` table that tracks unresolved failures across all entity types. A single `PipelineFailureService` provides record, resolve, retry, list, and cleanup operations. A retry-handler registry maps each `pipeline_name` to a function that re-runs the appropriate pipeline. The existing Pipeline Logs UI gains an Unresolved Failures section with filter tabs, per-row retry/forget actions, and a bulk retry button that reuses Feature 1's batch pipeline for throughput.

The audit log is preserved as history. The new table is the source of truth for current state.

## Data Model

### New table: `pipeline_failures`

```sql
CREATE TABLE pipeline_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    pipeline_name VARCHAR(50) NOT NULL,
    failed_step VARCHAR(100) NOT NULL,
    error_message TEXT,
    attempts INTEGER NOT NULL DEFAULT 1,
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX idx_pipeline_failures_unresolved
    ON pipeline_failures(entity_type, entity_id, pipeline_name)
    WHERE resolved_at IS NULL;

CREATE INDEX idx_pipeline_failures_pipeline_name
    ON pipeline_failures(pipeline_name) WHERE resolved_at IS NULL;

CREATE INDEX idx_pipeline_failures_resolved_at
    ON pipeline_failures(resolved_at) WHERE resolved_at IS NOT NULL;
```

The partial unique index guarantees at most one unresolved row per `(entity_type, entity_id, pipeline_name)` combination. New failures for an already-failing entity update the existing row rather than creating duplicates.

Polymorphic references have no foreign key constraints. Cleanup is handled by explicit hooks on delete paths plus an hourly orphan-sweep task.

### Initial entity types and pipelines

| entity_type | pipeline_name | Granularity |
|---|---|---|
| `memory` | `memory_ingest` | Per memory item |
| `code_repo` | `code_index` | Per repository (v1) |

Per-file code indexing granularity is deferred; the table schema supports adding `entity_type='code_file'` later without migration.

### Initial `failed_step` values

Step names are scoped by `entity_type`, so no prefix is needed.

**For `entity_type='memory'`:**
`content_embedding`, `extraction`, `entity_embedding`, `dedup_lookup`, `vector_write`, `graph_write`, `other`

**For `entity_type='code_repo'`:**
`parse`, `structure`, `import_resolution`, `call_tracing`, `heritage`, `community_detection`, `process_detection`, `embeddings`, `enrichment_queue`, `other`

## Which failures are recorded

Recorded failures are hard failures only — states where the memory is genuinely unusable without intervention. Partial extractions (LLM returned some entities plus a `_error` hint) are not counted as failed because the partial data is typically usable and flooding the retry UI with partial rows would obscure real failures. Soft degradations (classification failure, dedup lookup failure, crossref failure) are logged only and do not create failure rows.

For `memory_ingest`, the mapping from the existing `status` dict to `failed_step`:

```python
def _derive_memory_failed_step(status: dict) -> str | None:
    if status["embed"] == "error":
        return "content_embedding"
    if status["extract"] == "error":
        return "extraction"
    if status["vector"] == "error":
        return "vector_write"
    if status["graph"] == "error":
        return "graph_write"
    return None
```

When this returns `None`, the memory is successful (or partial but acceptable) and any existing unresolved failure row is resolved via `resolve()`. Partial extractions continue to broadcast `pipeline.partial` over WebSocket for observability in the execution history feed, but do not create or update a failure row.

For `code_index`, the mapping from the `self._stats["errors"]` list:

```python
def _derive_code_failed_step(errors: list[str]) -> str:
    prefixes = {
        "parse:": "parse",
        "structure:": "structure",
        "import:": "import_resolution",
        "call:": "call_tracing",
        "heritage:": "heritage",
        "community:": "community_detection",
        "process:": "process_detection",
        "embed:": "embeddings",
        "enrichment:": "enrichment_queue",
    }
    for err in errors:
        for pfx, step in prefixes.items():
            if err.startswith(pfx):
                return step
    return "other"
```

When `errors` is empty, `resolve()` is called for the repo.

## Service Layer

New module: `backend/app/services/pipeline_failures.py`

### PipelineFailureService

```python
class PipelineFailureService:
    def __init__(self, session: AsyncSession): ...

    async def record(
        self,
        entity_type: str,
        entity_id: UUID,
        pipeline_name: str,
        failed_step: str,
        error_message: str,
        metadata: dict | None = None,
    ) -> None:
        """Upsert a failure. If an unresolved row exists for the key
        (entity_type, entity_id, pipeline_name), increment attempts and
        update failed_step/error_message/last_attempt_at/metadata.
        Otherwise insert a new row with attempts=1."""

    async def resolve(
        self,
        entity_type: str,
        entity_id: UUID,
        pipeline_name: str,
    ) -> None:
        """Mark any unresolved failure for this key as resolved
        (sets resolved_at=NOW()). No-op if no unresolved row exists."""

    async def forget(self, entity_type: str, entity_id: UUID) -> None:
        """Hard-delete all failure rows for a specific entity across all
        pipelines. Called from entity delete paths."""

    async def forget_all_for_repo(self, repo_id: UUID) -> None:
        """Hard-delete code_repo failures for this repo. Called from
        RepoManager.delete."""

    async def prune_orphans(self) -> dict[str, int]:
        """Delete failure rows whose referenced entity no longer exists.
        Checks memories and repositories tables. Returns
        {'memory': N, 'code_repo': N} for logging."""

    async def prune_resolved_older_than(self, days: int = 30) -> int:
        """Delete resolved rows older than N days. Returns count."""

    async def list_unresolved(
        self,
        entity_type: str | None = None,
        pipeline_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """List unresolved failures with optional filters. Enriches each
        row with entity_preview (first 80 chars of memory content or
        repo name) via LEFT JOIN."""

    async def get(self, failure_id: UUID) -> dict | None: ...

    async def counts_by_pipeline(self) -> dict[str, int]:
        """Return {'memory_ingest': N, 'code_index': N, ...} for dashboard."""
```

### Retry handler registry

```python
# module-level
RETRY_HANDLERS: dict[str, Callable[[UUID], Awaitable[None]]] = {}

def register_retry_handler(pipeline_name: str):
    def decorator(fn):
        RETRY_HANDLERS[pipeline_name] = fn
        return fn
    return decorator
```

Handlers are registered during app startup in `main.py` lifespan, bound to the already-initialized pipeline and service instances:

```python
@register_retry_handler("memory_ingest")
async def _retry_memory(memory_id: UUID) -> None:
    async with async_session_factory() as session:
        mem = (await session.execute(
            select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        )).scalar_one_or_none()
        if not mem:
            return  # orphan will be cleaned by periodic task
        entry = {
            "memory_id": mem.id,
            "content": mem.content,
            "source": mem.source,
            "tags": [t.name for t in mem.tags],
            "memory_type": mem.memory_type,
            "created_at": mem.created_at.isoformat() if mem.created_at else "",
        }
    await pipeline.process_batch([entry])
    # process_batch internally calls failure_svc.record() or .resolve()

@register_retry_handler("code_index")
async def _retry_code_index(repo_id: UUID) -> None:
    async with async_session_factory() as session:
        indexer = CodeIndexer(session, llm, vector_repo)
        await indexer.index_repo(repo_id)
        await session.commit()
```

The retry endpoint looks up the handler by `pipeline_name` and invokes it with `entity_id`. The handler is responsible for calling `failure_service.record()` or `.resolve()` on completion — this happens naturally because `process_batch` and `index_repo` already integrate with the failure service.

## Pipeline Integration

### Memory ingest (`ProcessingPipeline.process_batch`)

After the existing `gather` that collects per-memory results, a new block writes the failure state for each memory. The `_write_memory` return value is the existing `status` dict, untouched.

```python
# At the end of process_batch, after the normalize loop
async with self.session_factory() as failure_session:
    failure_svc = PipelineFailureService(failure_session)
    for entry, result in zip(entries, normalized):
        entity_id = UUID(result["memory_id"]) if isinstance(result["memory_id"], str) else result["memory_id"]
        failed_step = _derive_memory_failed_step(result)
        if failed_step is not None:
            await failure_svc.record(
                entity_type="memory",
                entity_id=entity_id,
                pipeline_name="memory_ingest",
                failed_step=failed_step,
                error_message=result.get("error") or "Unknown error",
            )
        else:
            await failure_svc.resolve(
                entity_type="memory",
                entity_id=entity_id,
                pipeline_name="memory_ingest",
            )
    await failure_session.commit()
```

### Code indexing (`CodeIndexer.index_repo`)

At the end of `index_repo` (before returning), record or resolve based on `self._stats["errors"]`. Uses the existing `self.session`:

```python
failure_svc = PipelineFailureService(self.session)
errors = self._stats.get("errors", [])
if errors:
    failed_step = _derive_code_failed_step(errors)
    await failure_svc.record(
        entity_type="code_repo",
        entity_id=repo_id,
        pipeline_name="code_index",
        failed_step=failed_step,
        error_message="\n".join(errors[:10]),
        metadata={"error_count": len(errors)},
    )
else:
    await failure_svc.resolve(
        entity_type="code_repo",
        entity_id=repo_id,
        pipeline_name="code_index",
    )
# session commit happens in the caller
```

### Delete-path cleanup hooks

| File | Method | Hook |
|---|---|---|
| `backend/app/services/memory.py` | `delete_memory` | `await failure_svc.forget("memory", memory_id)` before calling pipeline.delete_memory |
| `backend/app/services/memory.py` | `merge_memories` | `await failure_svc.forget("memory", source_id)` before deleting source |
| `backend/app/services/repo_manager.py` | `delete` | `await failure_svc.forget_all_for_repo(repo_id)` before deleting repo |

### Periodic cleanup task

Added to `backend/app/main.py` lifespan alongside the existing `periodic_blocklist_cleanup`:

```python
async def periodic_pipeline_failure_cleanup():
    while True:
        try:
            await asyncio.sleep(3600)
            async with async_session_factory() as session:
                svc = PipelineFailureService(session)
                orphaned = await svc.prune_orphans()
                resolved_pruned = await svc.prune_resolved_older_than(days=30)
                await session.commit()
            logger.info(
                "Pipeline failure cleanup: orphaned=%s, resolved_pruned=%d",
                orphaned, resolved_pruned,
            )
        except Exception as e:
            logger.error("Pipeline failure cleanup error: %s", e)

# In lifespan:
failure_cleanup_task = asyncio.create_task(periodic_pipeline_failure_cleanup())
# ... shutdown
failure_cleanup_task.cancel()
```

## Event Layer

Retry status updates flow through the existing WebSocket infrastructure (`EventManager.broadcast` on the backend, `lib/websocket.ts` + `lib/websocket-events.ts` on the frontend). No polling. Two new event types are added to `EVENT_SCHEMAS`.

### New event: `pipeline.failure.updated`

```python
class PipelineFailureUpdated(BaseModel):
    failure_id: str
    entity_type: str
    entity_id: str
    pipeline_name: str
    state: str                    # "recorded" | "resolved" | "forgotten"
    failed_step: str | None
    attempts: int
    error_message: str | None
```

Broadcast automatically from `PipelineFailureService` whenever `record()`, `resolve()`, or `forget()` commits a change. The service holds a reference to the broadcast function (passed in at construction) and emits after each successful write.

### New event: `pipeline.retry_batch.progress`

```python
class PipelineRetryBatchProgress(BaseModel):
    batch_id: str
    current: int
    total: int
    processed: int
    errors: int
    entity_type: str | None
    entity_id: str | None
    state: str                    # "started" | "progress" | "done"
```

Broadcast during bulk retry execution. The `batch_id` is a UUID generated when the bulk retry request is accepted, so the frontend can filter progress events to its own batch.

Both schemas are registered in `backend/app/schemas/events.py` and mirrored in `frontend/src/lib/websocket-events.ts` with matching TypeScript interfaces.

## API Layer

New router: `backend/app/api/routes/pipeline_failures.py` mounted at `/api/v1/pipeline-failures`. All endpoints require `require_auth`. All retry endpoints are async — they accept the request, dispatch a background task, and return immediately. Status updates arrive via WebSocket.

### Endpoints

```
GET  /api/v1/pipeline-failures
     Query: entity_type?, pipeline_name?, limit=100, offset=0
     Returns: { items: PipelineFailureResponse[], total: int }

GET  /api/v1/pipeline-failures/counts
     Returns: { memory_ingest: int, code_index: int, ... }

GET  /api/v1/pipeline-failures/{id}
     Returns: PipelineFailureResponse

POST /api/v1/pipeline-failures/{id}/retry
     Async. Dispatches a background task to run the registered handler.
     Returns 202 with: { "accepted": true, "failure_id": "..." }
     Returns 409 with: { "accepted": false, "reason": "already_retrying" } if in progress
     Returns 503 with: { "accepted": false, "reason": "no_handler" } if no handler registered

POST /api/v1/pipeline-failures/retry-all
     Query: entity_type?, pipeline_name?
     Async. Computes matching failure list, dispatches a background task.
     Returns 202 with: { "accepted": true, "batch_id": "...", "total": N }

DELETE /api/v1/pipeline-failures/{id}
     Forget this failure without retrying. Hard-delete the row.
     Broadcasts pipeline.failure.updated with state="forgotten".
```

### Schemas

New module: `backend/app/schemas/pipeline_failures.py`

```python
class PipelineFailureResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    pipeline_name: str
    failed_step: str
    error_message: str | None
    attempts: int
    first_failed_at: datetime
    last_attempt_at: datetime
    resolved_at: datetime | None
    metadata: dict
    entity_preview: str | None

class PipelineFailureListResponse(BaseModel):
    items: list[PipelineFailureResponse]
    total: int
```

`entity_preview` is populated during `list_unresolved` via LEFT JOINs:
- For `entity_type='memory'`: first 80 chars of `memories.content`
- For `entity_type='code_repo'`: value of `repositories.name`

### Concurrent retry protection

`PipelineFailureService` (or a module-level singleton passed into the API layer) holds an `_retries_in_progress: set[UUID]` containing the IDs of failures currently being retried. This is an in-memory, single-process guard — sufficient for a single-process single-admin tool.

- Single retry endpoint: check set membership → if present, return 409. Otherwise add to set, spawn task, return 202. Task removes the ID in a `finally` block.
- Bulk retry task: iterates failure IDs, skips any already in the set (logs and emits an error progress event but continues), adds each one before dispatching.

If the process restarts mid-retry, the set is lost. The next frontend fetch shows the failure still unresolved, and the user can click retry again — no data corruption risk.

### Single retry execution flow

```python
@router.post("/{failure_id}/retry", status_code=202)
async def retry_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session=Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(404, "Failure not found")
    if failure["resolved_at"]:
        return {"accepted": True, "failure_id": str(failure_id), "note": "already resolved"}

    handler = RETRY_HANDLERS.get(failure["pipeline_name"])
    if not handler:
        return JSONResponse(
            status_code=503,
            content={"accepted": False, "reason": "no_handler", "pipeline_name": failure["pipeline_name"]},
        )

    if not _retry_locks.try_acquire(failure_id):
        return JSONResponse(
            status_code=409,
            content={"accepted": False, "reason": "already_retrying"},
        )

    async def _run():
        try:
            await handler(UUID(failure["entity_id"]))
        except Exception as e:
            logger.exception("Retry handler failed for failure_id=%s", failure_id)
            # Handler failures typically leave the failure row updated via
            # the pipeline's own record() call; if not, do a manual update.
            async with async_session_factory() as s:
                manual_svc = PipelineFailureService(s, broadcast=event_manager.broadcast)
                await manual_svc.record(
                    entity_type=failure["entity_type"],
                    entity_id=UUID(failure["entity_id"]),
                    pipeline_name=failure["pipeline_name"],
                    failed_step=failure["failed_step"],
                    error_message=f"Retry handler raised: {e}",
                )
                await s.commit()
        finally:
            _retry_locks.release(failure_id)

    asyncio.create_task(_run())
    return {"accepted": True, "failure_id": str(failure_id)}
```

`_retry_locks` is a simple wrapper around a `set[UUID]` with `try_acquire(id) -> bool` and `release(id)` methods. Single-process, no external state.

### Bulk retry execution flow

```python
@router.post("/retry-all", status_code=202)
async def retry_all(
    entity_type: str | None = None,
    pipeline_name: str | None = None,
    _user=Depends(require_auth),
    session=Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    failures = await svc.list_unresolved(entity_type=entity_type, pipeline_name=pipeline_name, limit=1000)
    batch_id = str(uuid4())
    total = len(failures)

    async def _run_bulk():
        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": 0, "total": total,
            "processed": 0, "errors": 0, "entity_type": None, "entity_id": None, "state": "started",
        })

        processed = 0
        errors = 0

        # Memory bulk retry: collect all entries and use process_batch for
        # full Feature 1 batching benefit. Code retries: one at a time.
        if pipeline_name == "memory_ingest":
            entries = []
            async with async_session_factory() as s:
                for f in failures:
                    if not _retry_locks.try_acquire(UUID(f["id"])):
                        continue
                    entry = await _build_memory_entry(s, UUID(f["entity_id"]))
                    if entry is not None:
                        entries.append((f, entry))
            try:
                results = await pipeline.process_batch([e for _, e in entries])
                for (f, _), result in zip(entries, results):
                    processed += 1
                    if isinstance(result, dict) and result.get("error"):
                        errors += 1
                    await event_manager.broadcast("pipeline.retry_batch.progress", {
                        "batch_id": batch_id, "current": processed, "total": total,
                        "processed": processed, "errors": errors,
                        "entity_type": f["entity_type"], "entity_id": f["entity_id"],
                        "state": "progress",
                    })
            finally:
                for f, _ in entries:
                    _retry_locks.release(UUID(f["id"]))
        else:
            for f in failures:
                if not _retry_locks.try_acquire(UUID(f["id"])):
                    continue
                try:
                    handler = RETRY_HANDLERS.get(f["pipeline_name"])
                    if handler:
                        await handler(UUID(f["entity_id"]))
                    processed += 1
                except Exception:
                    logger.exception("Bulk retry handler failed")
                    errors += 1
                finally:
                    _retry_locks.release(UUID(f["id"]))
                    await event_manager.broadcast("pipeline.retry_batch.progress", {
                        "batch_id": batch_id, "current": processed + errors, "total": total,
                        "processed": processed, "errors": errors,
                        "entity_type": f["entity_type"], "entity_id": f["entity_id"],
                        "state": "progress",
                    })

        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": total, "total": total,
            "processed": processed, "errors": errors,
            "entity_type": None, "entity_id": None, "state": "done",
        })

    asyncio.create_task(_run_bulk())
    return {"accepted": True, "batch_id": batch_id, "total": total}
```

`_build_memory_entry` is a helper that loads a `Memory` row and returns the entry dict consumed by `process_batch`. Returns `None` if the memory has been deleted (the failure row is orphaned and will be cleaned by the periodic sweep).

### Removed: legacy endpoints

The existing audit-log-driven endpoints are removed in this feature since the project is greenfield:

| Endpoint | Status |
|---|---|
| `POST /api/v1/analytics/reprocess-failed` | **Removed** |
| `POST /api/v1/analytics/reprocess-failed/stream` | **Removed** |

`POST /api/v1/analytics/reprocess` and `POST /api/v1/analytics/reprocess/stream` (reprocess ALL memories, not failed-only) are **unchanged** — they serve a different purpose.

`GET /api/v1/analytics/pipeline-logs` is **unchanged** — still reads `audit_log` for the execution history feed.

The `reprocess_failed` and `reprocess_failed_stream` methods on `AnalyticsService` are also removed, along with the `AuditLog.memory_id / details.error` query they used.

## Frontend

The existing `frontend/src/routes/_authenticated/pipeline.tsx` gains a new Unresolved Failures card at the top of the page.

### Updated page layout (top to bottom)

1. Page header (existing)
2. Action row — Retry Failed and Reprocess All buttons (existing, rewired)
3. **Unresolved Failures card (new)**
4. Reprocess progress bars (existing, shown during active runs)
5. Stats cards row (existing: Pipeline, Service Health, Successful, Failed/Partial)
6. Recent Pipeline Executions card (existing, unchanged)

### Unresolved Failures card

```
┌─ Unresolved Failures ─────────────────────────────────────┐
│ [All] [Memory] [Code]                    [Retry all]     │
├─────────────────────────────────────────────────────────────┤
│ memory · extraction · 3 attempts                          │
│ "The OOM crash in the indexer was caused by..."           │
│ Extraction returned invalid JSON                           │
│ Last attempt 2m ago         [Retry]  [Forget]             │
├─────────────────────────────────────────────────────────────┤
│ code_repo · parse · 1 attempt                             │
│ darkmem                                                    │
│ embed:src/foo.py:RuntimeError: ...                         │
│ Last attempt 1h ago         [Retry]  [Forget]             │
└─────────────────────────────────────────────────────────────┘
```

Filter tabs use counts from `/pipeline-failures/counts` (`All` is the sum, `Memory` is `memory_ingest`, `Code` is `code_index`).

Per-row Retry calls `POST /pipeline-failures/{id}/retry`, receives a 202 immediately, marks the row locally as "retrying" (spinner), and waits for a `pipeline.failure.updated` WebSocket event matching the `failure_id`. On `state="resolved"`: row animates out, query cache invalidated. On `state="recorded"` (retry ran but failed again): row updates in place with new attempts and error.

Per-row Forget calls `DELETE /pipeline-failures/{id}` and removes the row immediately. Broadcasts `pipeline.failure.updated` with `state="forgotten"` so other connected clients also see the removal.

Retry All at the top-right of the card calls `POST /pipeline-failures/retry-all` with the current filter, receives a `batch_id` and `total`, stores them in local state, and listens for `pipeline.retry_batch.progress` events matching that `batch_id`. The existing `ReprocessProgress` component is reused to render the progress bar, receiving `{current, total, processed, errors}` from the event stream instead of from SSE.

### New API hooks in `use-pipeline-api.ts`

```typescript
export interface PipelineFailure {
  id: string;
  entity_type: string;
  entity_id: string;
  pipeline_name: string;
  failed_step: string;
  error_message: string | null;
  attempts: number;
  first_failed_at: string;
  last_attempt_at: string;
  resolved_at: string | null;
  metadata: Record<string, unknown>;
  entity_preview: string | null;
}

export function usePipelineFailures(filters?: { entity_type?: string; pipeline_name?: string }): UseQueryResult<{ items: PipelineFailure[]; total: number }>;
export function usePipelineFailureCounts(): UseQueryResult<Record<string, number>>;
export function useRetryFailure(): UseMutationResult<{ accepted: boolean; failure_id: string }, Error, string>;
export function useForgetFailure(): UseMutationResult<void, Error, string>;
export function useRetryAllFailures(): UseMutationResult<{ accepted: boolean; batch_id: string; total: number }, Error, { entity_type?: string; pipeline_name?: string } | undefined>;
```

`useRetryFailure` returns immediately — it does NOT wait for completion. The caller is responsible for tracking the in-progress state locally until a WebSocket event arrives.

`useRetryAllFailures` returns the `batch_id` and `total`. The caller stores these and listens for matching `pipeline.retry_batch.progress` events.

### WebSocket event consumption

TypeScript definitions for the two new events are added to `frontend/src/lib/websocket-events.ts`:

```typescript
export interface PipelineFailureUpdated {
  failure_id: string;
  entity_type: string;
  entity_id: string;
  pipeline_name: string;
  state: "recorded" | "resolved" | "forgotten";
  failed_step: string | null;
  attempts: number;
  error_message: string | null;
}

export interface PipelineRetryBatchProgress {
  batch_id: string;
  current: number;
  total: number;
  processed: number;
  errors: number;
  entity_type: string | null;
  entity_id: string | null;
  state: "started" | "progress" | "done";
}

// added to WebSocketEventMap:
// "pipeline.failure.updated": PipelineFailureUpdated
// "pipeline.retry_batch.progress": PipelineRetryBatchProgress
```

The pipeline page uses the existing WebSocket consumption pattern (whatever `lib/websocket.ts` exposes — `useWebSocketEvent(type, handler)` or similar) to subscribe to both new event types. Handlers invalidate React Query caches and update local progress state:

```typescript
useWebSocketEvent("pipeline.failure.updated", (event) => {
  retryingIds.delete(event.failure_id);
  qc.invalidateQueries({ queryKey: ["pipelineFailures"] });
  qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] });
});

useWebSocketEvent("pipeline.retry_batch.progress", (event) => {
  if (event.batch_id !== activeBatchId) return;
  setProgress({ current: event.current, total: event.total, processed: event.processed, errors: event.errors });
  if (event.state === "done") {
    setActiveBatchId(null);
    toast.success(`Retried ${event.processed}/${event.total}`);
  }
});
```

### Existing buttons rewired

- **Retry Failed** button (top of page) — calls `useRetryAllFailures({ pipeline_name: "memory_ingest" })` instead of the removed `useReprocessStream("/analytics/reprocess-failed/stream")`. Display count comes from `usePipelineFailureCounts().memory_ingest`. Progress UI driven by `pipeline.retry_batch.progress` WebSocket events.
- **Reprocess All** button — unchanged. Still calls the existing `/analytics/reprocess/stream` SSE endpoint (that flow is not part of Feature 2).

## Files Changed

| File | Change |
|---|---|
| `backend/migrations/versions/0003_pipeline_failures.py` | New migration: create `pipeline_failures` table, indexes |
| `backend/app/models/pipeline_failure.py` | New ORM model |
| `backend/app/models/__init__.py` | Export new model |
| `backend/app/schemas/pipeline_failures.py` | New response/list schemas |
| `backend/app/schemas/events.py` | Add `PipelineFailureUpdated` and `PipelineRetryBatchProgress` schemas to `EVENT_SCHEMAS` |
| `backend/app/services/pipeline_failures.py` | New `PipelineFailureService` + retry handler registry + `_retry_locks` helper |
| `backend/app/services/pipeline.py` | `process_batch` records failures/resolutions at end |
| `backend/app/services/code_indexer.py` | `index_repo` records failures/resolutions at end |
| `backend/app/services/memory.py` | `delete_memory` and `merge_memories` call `forget` |
| `backend/app/services/repo_manager.py` | `delete` calls `forget_all_for_repo` |
| `backend/app/services/analytics.py` | **Remove** `reprocess_failed` and `reprocess_failed_stream` methods (no longer used) |
| `backend/app/api/routes/analytics.py` | **Remove** `/reprocess-failed` and `/reprocess-failed/stream` routes |
| `backend/app/api/routes/pipeline_failures.py` | New router with async single/bulk retry endpoints |
| `backend/app/main.py` | Register retry handlers on startup, add `periodic_pipeline_failure_cleanup` task, include new router |
| `frontend/src/hooks/api/use-pipeline-api.ts` | Add new hooks: `usePipelineFailures`, `usePipelineFailureCounts`, `useRetryFailure`, `useForgetFailure`, `useRetryAllFailures`. **Remove** the `reprocess-failed/stream` variant of `useReprocessStream` |
| `frontend/src/lib/websocket-events.ts` | Add `PipelineFailureUpdated` and `PipelineRetryBatchProgress` types to `WebSocketEventMap` |
| `frontend/src/routes/_authenticated/pipeline.tsx` | Add Unresolved Failures card, filter tabs, per-row actions, rewire Retry Failed button to WebSocket-based flow |

## Out of Scope

The following are explicitly NOT part of this feature:

- Per-file code indexing granularity (tracked at repo level in v1)
- Model-change obsolete tracking (Feature 3)
- Notification UI for model swaps (Feature 3)
- Retry attempt limit enforcement (unlimited retries per Q3)
- Distinction between "re-embed only" and "full pipeline re-run" (Feature 3)

Feature 3 will reuse the same `pipeline_failures` table but add a new `reason` concept or a separate mechanism for obsolete tracking — that design is deferred until Feature 2 stabilizes.
