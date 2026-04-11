# Model Change Handling and Obsolete Re-embedding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/api/v1/reembed` API and a new "Obsolete Embeddings" card on the Pipeline page that let users detect and re-embed rows whose `model_fingerprint` doesn't match the current embedding model.

**Architecture:** Obsolete state is computed at query time from the existing `model_fingerprint` columns — no new schema. A new `ReembedService` provides counts, paginated listings, and batch re-embed operations that reuse Feature 1's `embed_batch_chunked` helper. A new API router exposes per-category re-embed endpoints plus a combined "re-embed all" endpoint. Progress is streamed via a new WebSocket event `pipeline.reembed_batch.progress`. The LLM config page modal appears immediately after a model change if obsolete data exists; the Pipeline page card is the persistent source of truth for obsolete counts and actions.

**Tech Stack:** Python 3.12 (FastAPI, SQLAlchemy async, pgvector), TypeScript (React 19, TanStack Query, darkraise-ui), PostgreSQL

**Spec:** `docs/superpowers/specs/2026-04-10-model-change-handling-design.md`

---

### Task 1: Pydantic schemas for response and event

**Files:**
- Modify: `backend/app/schemas/config.py`
- Modify: `backend/app/schemas/events.py`

- [ ] **Step 1: Add `LLMConfigUpdateResponse` to config schemas**

Edit `backend/app/schemas/config.py`. Find the existing `LLMConfigResponse` class (around line 26). After it, add:

```python
class LLMConfigUpdateResponse(LLMConfigResponse):
    """Returned by POST /api/v1/config/llm. Extends LLMConfigResponse with
    computed obsolete counts for the new embedding model."""
    obsolete_after_change: dict[str, int] | None = None
```

- [ ] **Step 2: Add `PipelineReembedBatchProgress` to event schemas**

Edit `backend/app/schemas/events.py`. Find the existing class definitions. After `PipelineRetryBatchProgress` (added in Feature 2), add:

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

Make sure `Literal` is imported at the top of the file — check with `grep "from typing" backend/app/schemas/events.py`. If `Literal` is not imported, add it to the existing typing import.

Then update the `EVENT_SCHEMAS` dict at the bottom of the file to include the new event:

```python
EVENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "pipeline.completed": PipelineStatus,
    "pipeline.partial": PipelineStatus,
    "pipeline.failed": PipelineStatus,
    "pipeline.failure.updated": PipelineFailureUpdated,
    "pipeline.retry_batch.progress": PipelineRetryBatchProgress,
    "pipeline.reembed_batch.progress": PipelineReembedBatchProgress,
    "memory.deleted": MemoryDeleted,
    "repo.clone_started": RepoCloneStarted,
    "repo.clone_completed": RepoCloneCompleted,
    "repo.clone_failed": RepoCloneFailed,
    "repo.indexing_started": RepoIndexingStarted,
    "repo.indexing_progress": RepoIndexingProgress,
    "repo.indexing_completed": RepoIndexingCompleted,
    "repo.indexing_failed": RepoIndexingFailed,
    "enrichment.batch_completed": EnrichmentBatchCompleted,
}
```

- [ ] **Step 3: Verify imports**

Run:
```bash
cd backend && python -c "
from app.schemas.config import LLMConfigUpdateResponse, LLMConfigResponse
assert issubclass(LLMConfigUpdateResponse, LLMConfigResponse)
from app.schemas.events import PipelineReembedBatchProgress, EVENT_SCHEMAS
assert 'pipeline.reembed_batch.progress' in EVENT_SCHEMAS
print('OK')
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/config.py backend/app/schemas/events.py
git commit -m "feat(schemas): add LLMConfigUpdateResponse and reembed progress event"
```

---

### Task 2: ReembedService core with helpers and lock set

**Files:**
- Create: `backend/app/services/reembed.py`
- Create: `backend/tests/unit/test_reembed_helpers.py`

- [ ] **Step 1: Write the failing test for the lock set and count logic**

Create `backend/tests/unit/test_reembed_helpers.py`:

```python
from app.services.reembed import ReembedLockSet


class TestReembedLockSet:
    def test_acquire_release(self):
        locks = ReembedLockSet()
        assert locks.try_acquire("memories") is True
        assert locks.try_acquire("memories") is False
        locks.release("memories")
        assert locks.try_acquire("memories") is True

    def test_release_nonexistent_is_safe(self):
        locks = ReembedLockSet()
        locks.release("memories")  # should not raise

    def test_is_locked(self):
        locks = ReembedLockSet()
        assert locks.is_locked("entities") is False
        locks.try_acquire("entities")
        assert locks.is_locked("entities") is True

    def test_multiple_categories_independent(self):
        locks = ReembedLockSet()
        assert locks.try_acquire("memories") is True
        assert locks.try_acquire("entities") is True
        assert locks.try_acquire("code_chunks") is True
        locks.release("entities")
        assert locks.is_locked("memories") is True
        assert locks.is_locked("entities") is False
        assert locks.is_locked("code_chunks") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/test_reembed_helpers.py -v 2>&1 | tail -20`

Expected: `ModuleNotFoundError: No module named 'app.services.reembed'`

- [ ] **Step 3: Create the service file skeleton with lock set and count methods**

Create `backend/app/services/reembed.py`:

```python
"""Obsolete embedding detection and re-embed service.

Detects rows whose model_fingerprint does not match the current embedding
model and re-embeds them in bulk. Used by Feature 3 (model change handling).
"""

from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory concurrent re-embed protection
# ---------------------------------------------------------------------------

class ReembedLockSet:
    """Tracks which categories are currently being re-embedded.

    Single-process, single-admin — in-memory is sufficient.
    """

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


BroadcastFn = Callable[[str, dict], Awaitable[None]]


class ReembedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_obsolete(self, current_fingerprint: str) -> dict[str, int]:
        """Return obsolete row counts for each category."""
        result = {}

        mem_count = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM memory_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        result["memories"] = int(mem_count)

        chunk_count = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM code_chunk_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        result["code_chunks"] = int(chunk_count)

        entity_count = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM entities
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        result["entities"] = int(entity_count)

        return result
```

- [ ] **Step 4: Run lock set tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_reembed_helpers.py -v 2>&1 | tail -15`

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reembed.py backend/tests/unit/test_reembed_helpers.py
git commit -m "feat(reembed): add ReembedService skeleton with lock set and count"
```

---

### Task 3: ReembedService list and prune methods

**Files:**
- Modify: `backend/app/services/reembed.py`

- [ ] **Step 1: Add list methods and prune method**

In `backend/app/services/reembed.py`, add the following methods to the `ReembedService` class, after `count_obsolete`:

```python
    async def list_obsolete_memories(
        self,
        current_fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Paginated list of memories with stale or missing fingerprints.
        Returns (items, total_count)."""
        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM memory_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()

        rows = (await self.session.execute(
            text("""
                SELECT me.id, me.memory_id, me.model_fingerprint,
                       LEFT(m.content, 120) AS content_preview
                FROM memory_embeddings me
                LEFT JOIN memories m ON m.id = me.memory_id
                WHERE me.model_fingerprint != :fp OR me.model_fingerprint IS NULL
                ORDER BY me.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"fp": current_fingerprint, "limit": limit, "offset": offset},
        )).mappings().all()

        items = [
            {
                "id": str(r["id"]),
                "memory_id": str(r["memory_id"]),
                "model_fingerprint": r["model_fingerprint"],
                "content_preview": r["content_preview"],
            }
            for r in rows
        ]
        return items, int(total)

    async def list_obsolete_code_chunks(
        self,
        current_fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Paginated list of code chunks with stale or missing fingerprints."""
        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM code_chunk_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()

        rows = (await self.session.execute(
            text("""
                SELECT id, file_path, symbol_name, model_fingerprint,
                       LEFT(chunk_content, 120) AS chunk_preview
                FROM code_chunk_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"fp": current_fingerprint, "limit": limit, "offset": offset},
        )).mappings().all()

        items = [
            {
                "id": str(r["id"]),
                "file_path": r["file_path"],
                "symbol_name": r["symbol_name"],
                "model_fingerprint": r["model_fingerprint"],
                "chunk_preview": r["chunk_preview"],
            }
            for r in rows
        ]
        return items, int(total)

    async def list_obsolete_entities(
        self,
        current_fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Paginated list of entities with stale or missing fingerprints."""
        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM entities
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()

        rows = (await self.session.execute(
            text("""
                SELECT id, name, entity_type, model_fingerprint
                FROM entities
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"fp": current_fingerprint, "limit": limit, "offset": offset},
        )).mappings().all()

        items = [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "model_fingerprint": r["model_fingerprint"],
            }
            for r in rows
        ]
        return items, int(total)

    async def prune_obsolete_cache_entries(self, current_fingerprint: str) -> int:
        """Delete entity_embedding_cache rows whose fingerprint is not current.
        Returns deleted row count."""
        result = await self.session.execute(
            text("""
                DELETE FROM entity_embedding_cache
                WHERE model_fingerprint != :fp
            """),
            {"fp": current_fingerprint},
        )
        await self.session.commit()
        return result.rowcount or 0
```

- [ ] **Step 2: Verify import**

Run:
```bash
cd backend && python -c "
from app.services.reembed import ReembedService
svc_methods = [m for m in dir(ReembedService) if not m.startswith('_')]
required = ['count_obsolete', 'list_obsolete_memories', 'list_obsolete_code_chunks',
            'list_obsolete_entities', 'prune_obsolete_cache_entries']
for m in required:
    assert m in svc_methods, f'Missing method: {m}'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/reembed.py
git commit -m "feat(reembed): add list obsolete methods and cache prune"
```

---

### Task 4: ReembedService re-embed methods with per-chunk commit

**Files:**
- Modify: `backend/app/services/reembed.py`

- [ ] **Step 1: Add `reembed_memories` method**

In `backend/app/services/reembed.py`, add this method after `prune_obsolete_cache_entries`:

```python
    async def reembed_memories(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        """Re-embed all obsolete memories. Returns {'processed': N, 'errors': N, 'last_error': str | None}."""
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)

        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM memory_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        total = int(total)

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "memories",
                "current": 0, "total": total, "processed": 0, "errors": 0,
                "state": "started", "error_message": None,
            })

        processed = 0
        errors = 0
        last_error: str | None = None
        chunk_size_rows = 100

        while True:
            rows = (await self.session.execute(
                text("""
                    SELECT me.id AS embedding_id, me.memory_id, m.content
                    FROM memory_embeddings me
                    JOIN memories m ON m.id = me.memory_id
                    WHERE me.model_fingerprint != :fp OR me.model_fingerprint IS NULL
                    LIMIT :limit
                """),
                {"fp": current_fingerprint, "limit": chunk_size_rows},
            )).mappings().all()

            if not rows:
                break

            texts = [r["content"] for r in rows]
            try:
                vectors = await llm.embed_batch_chunked(texts, embed_chunk_size, embed_concurrency)
            except Exception as e:
                logger.exception("Re-embed batch failed for memories")
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                if broadcast:
                    await broadcast("pipeline.reembed_batch.progress", {
                        "batch_id": batch_id, "category": "memories",
                        "current": processed + errors, "total": total,
                        "processed": processed, "errors": errors,
                        "state": "progress", "error_message": None,
                    })
                break

            updates = [
                {"id": str(r["embedding_id"]), "vec": str(vec)}
                for r, vec in zip(rows, vectors)
            ]
            try:
                await self.session.execute(
                    text("""
                        UPDATE memory_embeddings
                        SET embedding = v.vec::vector,
                            model_fingerprint = :fp
                        FROM jsonb_to_recordset(CAST(:updates AS jsonb)) AS v(id uuid, vec text)
                        WHERE memory_embeddings.id = v.id
                    """),
                    {"fp": current_fingerprint, "updates": json.dumps(updates)},
                )
                await self.session.commit()
                processed += len(rows)
            except Exception as e:
                logger.exception("Failed to persist re-embedded memories")
                await self.session.rollback()
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                break

            if broadcast:
                await broadcast("pipeline.reembed_batch.progress", {
                    "batch_id": batch_id, "category": "memories",
                    "current": processed + errors, "total": total,
                    "processed": processed, "errors": errors,
                    "state": "progress", "error_message": None,
                })

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "memories",
                "current": total, "total": total,
                "processed": processed, "errors": errors,
                "state": "done", "error_message": last_error,
            })

        return {"processed": processed, "errors": errors, "last_error": last_error}
```

- [ ] **Step 2: Add `reembed_code_chunks` method**

After `reembed_memories`, add:

```python
    async def reembed_code_chunks(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        """Re-embed all obsolete code chunks."""
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)

        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM code_chunk_embeddings
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        total = int(total)

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "code_chunks",
                "current": 0, "total": total, "processed": 0, "errors": 0,
                "state": "started", "error_message": None,
            })

        processed = 0
        errors = 0
        last_error: str | None = None
        chunk_size_rows = 100

        while True:
            rows = (await self.session.execute(
                text("""
                    SELECT id, chunk_content
                    FROM code_chunk_embeddings
                    WHERE (model_fingerprint != :fp OR model_fingerprint IS NULL)
                      AND chunk_content IS NOT NULL
                    LIMIT :limit
                """),
                {"fp": current_fingerprint, "limit": chunk_size_rows},
            )).mappings().all()

            if not rows:
                break

            texts = [r["chunk_content"] for r in rows]
            try:
                vectors = await llm.embed_batch_chunked(texts, embed_chunk_size, embed_concurrency)
            except Exception as e:
                logger.exception("Re-embed batch failed for code_chunks")
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                if broadcast:
                    await broadcast("pipeline.reembed_batch.progress", {
                        "batch_id": batch_id, "category": "code_chunks",
                        "current": processed + errors, "total": total,
                        "processed": processed, "errors": errors,
                        "state": "progress", "error_message": None,
                    })
                break

            updates = [
                {"id": str(r["id"]), "vec": str(vec)}
                for r, vec in zip(rows, vectors)
            ]
            try:
                await self.session.execute(
                    text("""
                        UPDATE code_chunk_embeddings
                        SET embedding = v.vec::vector,
                            model_fingerprint = :fp
                        FROM jsonb_to_recordset(CAST(:updates AS jsonb)) AS v(id uuid, vec text)
                        WHERE code_chunk_embeddings.id = v.id
                    """),
                    {"fp": current_fingerprint, "updates": json.dumps(updates)},
                )
                await self.session.commit()
                processed += len(rows)
            except Exception as e:
                logger.exception("Failed to persist re-embedded code chunks")
                await self.session.rollback()
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                break

            if broadcast:
                await broadcast("pipeline.reembed_batch.progress", {
                    "batch_id": batch_id, "category": "code_chunks",
                    "current": processed + errors, "total": total,
                    "processed": processed, "errors": errors,
                    "state": "progress", "error_message": None,
                })

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "code_chunks",
                "current": total, "total": total,
                "processed": processed, "errors": errors,
                "state": "done", "error_message": last_error,
            })

        return {"processed": processed, "errors": errors, "last_error": last_error}
```

- [ ] **Step 3: Add `reembed_entities` method with cache upsert**

After `reembed_code_chunks`, add:

```python
    async def reembed_entities(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        """Re-embed all obsolete entity names. Also upserts new embeddings
        into entity_embedding_cache so future ingestions benefit from the cache."""
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)

        total = (await self.session.execute(
            text("""
                SELECT COUNT(*) FROM entities
                WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()
        total = int(total)

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "entities",
                "current": 0, "total": total, "processed": 0, "errors": 0,
                "state": "started", "error_message": None,
            })

        processed = 0
        errors = 0
        last_error: str | None = None
        chunk_size_rows = 100

        while True:
            rows = (await self.session.execute(
                text("""
                    SELECT id, name
                    FROM entities
                    WHERE model_fingerprint != :fp OR model_fingerprint IS NULL
                    LIMIT :limit
                """),
                {"fp": current_fingerprint, "limit": chunk_size_rows},
            )).mappings().all()

            if not rows:
                break

            texts = [r["name"] for r in rows]
            try:
                vectors = await llm.embed_batch_chunked(texts, embed_chunk_size, embed_concurrency)
            except Exception as e:
                logger.exception("Re-embed batch failed for entities")
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                if broadcast:
                    await broadcast("pipeline.reembed_batch.progress", {
                        "batch_id": batch_id, "category": "entities",
                        "current": processed + errors, "total": total,
                        "processed": processed, "errors": errors,
                        "state": "progress", "error_message": None,
                    })
                break

            updates = [
                {"id": str(r["id"]), "vec": str(vec)}
                for r, vec in zip(rows, vectors)
            ]
            try:
                # Update entities table
                await self.session.execute(
                    text("""
                        UPDATE entities
                        SET embedding = v.vec::vector,
                            model_fingerprint = :fp
                        FROM jsonb_to_recordset(CAST(:updates AS jsonb)) AS v(id uuid, vec text)
                        WHERE entities.id = v.id
                    """),
                    {"fp": current_fingerprint, "updates": json.dumps(updates)},
                )

                # Dedupe by lowercase name for the cache upsert (multiple entities
                # can share the same name across types)
                cache_upserts: dict[str, list[float]] = {}
                for row, vec in zip(rows, vectors):
                    cache_upserts[row["name"].lower()] = vec

                for name_lower, vec in cache_upserts.items():
                    await self.session.execute(
                        text("""
                            INSERT INTO entity_embedding_cache
                                (name_lower, model_fingerprint, embedding, created_at, last_used_at, hit_count)
                            VALUES
                                (:name, :fp, CAST(:vec AS vector), NOW(), NOW(), 1)
                            ON CONFLICT (name_lower, model_fingerprint) DO UPDATE SET
                                embedding = EXCLUDED.embedding,
                                last_used_at = NOW(),
                                hit_count = entity_embedding_cache.hit_count + 1
                        """),
                        {"name": name_lower, "fp": current_fingerprint, "vec": str(vec)},
                    )

                await self.session.commit()
                processed += len(rows)
            except Exception as e:
                logger.exception("Failed to persist re-embedded entities")
                await self.session.rollback()
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                break

            if broadcast:
                await broadcast("pipeline.reembed_batch.progress", {
                    "batch_id": batch_id, "category": "entities",
                    "current": processed + errors, "total": total,
                    "processed": processed, "errors": errors,
                    "state": "progress", "error_message": None,
                })

        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": "entities",
                "current": total, "total": total,
                "processed": processed, "errors": errors,
                "state": "done", "error_message": last_error,
            })

        return {"processed": processed, "errors": errors, "last_error": last_error}
```

- [ ] **Step 4: Verify imports and method signatures**

Run:
```bash
cd backend && python -c "
from app.services.reembed import ReembedService
import inspect
methods = ['reembed_memories', 'reembed_code_chunks', 'reembed_entities']
for m in methods:
    sig = inspect.signature(getattr(ReembedService, m))
    params = list(sig.parameters.keys())
    assert params == ['self', 'current_fingerprint', 'llm', 'batch_id', 'broadcast', 'flags'], f'{m} signature mismatch: {params}'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reembed.py
git commit -m "feat(reembed): add re-embed methods with per-chunk commit and cache upsert"
```

---

### Task 5: Extend LLM config endpoint with obsolete counts

**Files:**
- Modify: `backend/app/api/routes/config.py`

- [ ] **Step 1: Update import and decorator**

In `backend/app/api/routes/config.py`, find the import of `LLMConfigResponse` (around line 10). Add `LLMConfigUpdateResponse`:

```python
from app.schemas.config import LLMConfigResponse, LLMConfigUpdate, LLMConfigUpdateResponse, LLMPurposeConfigSchema
```

Find the `update_llm_config` endpoint decorator (around line 26):

```python
@router.post("/llm", response_model=LLMConfigResponse)
```

Change to:

```python
@router.post("/llm", response_model=LLMConfigUpdateResponse)
```

- [ ] **Step 2: Update return statement**

In the same function, find the existing return statement (around line 75-76):

```python
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in updated_config.items()})
```

Replace with:

```python
    # Feature 3: compute obsolete counts for the new fingerprint
    obsolete_after_change = None
    if pipeline is not None:
        from app.services.reembed import ReembedService
        reembed_svc = ReembedService(session)
        obsolete_after_change = await reembed_svc.count_obsolete(pipeline.embedding_fingerprint)

    purpose_payload = {p: cfg_to_schema(c) for p, c in updated_config.items()}
    return LLMConfigUpdateResponse(
        **purpose_payload,
        obsolete_after_change=obsolete_after_change,
    )
```

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.api.routes.config import router; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/config.py
git commit -m "feat(config): return obsolete counts after LLM config update"
```

---

### Task 6: Re-embed API router

**Files:**
- Create: `backend/app/api/routes/reembed.py`

- [ ] **Step 1: Create the router file**

Create `backend/app/api/routes/reembed.py`:

```python
"""Re-embed API routes for Feature 3 (model change handling).

Provides:
  - GET  /api/v1/reembed/obsolete-counts
  - GET  /api/v1/reembed/obsolete/memories
  - GET  /api/v1/reembed/obsolete/code-chunks
  - GET  /api/v1/reembed/obsolete/entities
  - POST /api/v1/reembed/memories   (async, WebSocket progress)
  - POST /api/v1/reembed/code-chunks (async, WebSocket progress)
  - POST /api/v1/reembed/entities    (async, WebSocket progress)
  - POST /api/v1/reembed/all         (async, runs all three categories)
  - POST /api/v1/reembed/prune-cache (sync)
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.websocket import event_manager
from app.database import async_session_factory, get_session
from app.services.reembed import ReembedService, reembed_locks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reembed", tags=["reembed"])


async def _get_flags() -> dict:
    """Fetch feature flags in a fresh session (for background tasks)."""
    from app.services.pipeline import _get_feature_flags
    return await _get_feature_flags(async_session_factory)


@router.get("/obsolete-counts")
async def get_obsolete_counts(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        return {
            "memories": 0, "code_chunks": 0, "entities": 0,
            "current_fingerprint": "",
        }
    svc = ReembedService(session)
    counts = await svc.count_obsolete(pipeline.embedding_fingerprint)
    return {
        **counts,
        "current_fingerprint": pipeline.embedding_fingerprint,
    }


@router.get("/obsolete/memories")
async def list_obsolete_memories(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_memories(
        pipeline.embedding_fingerprint, limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


@router.get("/obsolete/code-chunks")
async def list_obsolete_code_chunks(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_code_chunks(
        pipeline.embedding_fingerprint, limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


@router.get("/obsolete/entities")
async def list_obsolete_entities(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_entities(
        pipeline.embedding_fingerprint, limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


async def _dispatch_single_category(
    category: str,
    pipeline,
    session: AsyncSession,
):
    """Shared logic for /reembed/memories, /code-chunks, /entities."""
    if not reembed_locks.try_acquire(category):
        return JSONResponse(
            status_code=409,
            content={"accepted": False, "reason": "already_running"},
        )

    snapshot_fingerprint = pipeline.embedding_fingerprint
    snapshot_llm = pipeline.llm
    batch_id = str(uuid4())

    svc = ReembedService(session)
    counts = await svc.count_obsolete(snapshot_fingerprint)
    total = counts.get(category, 0)

    method_name_map = {
        "memories": "reembed_memories",
        "code_chunks": "reembed_code_chunks",
        "entities": "reembed_entities",
    }
    method_name = method_name_map[category]

    async def _run():
        try:
            flags = await _get_flags()
            async with async_session_factory() as bg_session:
                bg_svc = ReembedService(bg_session)
                method = getattr(bg_svc, method_name)
                await method(
                    current_fingerprint=snapshot_fingerprint,
                    llm=snapshot_llm,
                    batch_id=batch_id,
                    broadcast=event_manager.broadcast,
                    flags=flags,
                )
        except Exception:
            logger.exception("Re-embed %s background task failed", category)
        finally:
            reembed_locks.release(category)

    asyncio.create_task(_run())
    return {"accepted": True, "batch_id": batch_id, "total": total}


@router.post("/memories", status_code=202)
async def reembed_memories(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("memories", pipeline, session)


@router.post("/code-chunks", status_code=202)
async def reembed_code_chunks(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("code_chunks", pipeline, session)


@router.post("/entities", status_code=202)
async def reembed_entities(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("entities", pipeline, session)


@router.post("/all", status_code=202)
async def reembed_all(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")

    # Try to acquire all three locks; release any acquired on failure
    acquired: list[str] = []
    for cat in ("memories", "entities", "code_chunks"):
        if reembed_locks.try_acquire(cat):
            acquired.append(cat)
        else:
            for released in acquired:
                reembed_locks.release(released)
            return JSONResponse(
                status_code=409,
                content={
                    "accepted": False, "reason": "already_running",
                    "conflict_category": cat,
                },
            )

    snapshot_fingerprint = pipeline.embedding_fingerprint
    snapshot_llm = pipeline.llm
    batch_id = str(uuid4())

    svc = ReembedService(session)
    totals = await svc.count_obsolete(snapshot_fingerprint)

    async def _run_all():
        try:
            flags = await _get_flags()
            async with async_session_factory() as bg_session:
                bg_svc = ReembedService(bg_session)
                sequence = [
                    ("memories", bg_svc.reembed_memories),
                    ("entities", bg_svc.reembed_entities),
                    ("code_chunks", bg_svc.reembed_code_chunks),
                ]
                for category, method in sequence:
                    try:
                        await method(
                            current_fingerprint=snapshot_fingerprint,
                            llm=snapshot_llm,
                            batch_id=batch_id,
                            broadcast=event_manager.broadcast,
                            flags=flags,
                        )
                    except Exception:
                        logger.exception(
                            "Re-embed %s failed under batch %s", category, batch_id,
                        )
        finally:
            for cat in ("memories", "entities", "code_chunks"):
                reembed_locks.release(cat)

    asyncio.create_task(_run_all())
    return {"accepted": True, "batch_id": batch_id, "totals": totals}


@router.post("/prune-cache")
async def prune_cache(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    svc = ReembedService(session)
    deleted = await svc.prune_obsolete_cache_entries(pipeline.embedding_fingerprint)
    return {"deleted": deleted}
```

- [ ] **Step 2: Verify import and route count**

Run:
```bash
cd backend && python -c "
from app.api.routes.reembed import router
paths = sorted([r.path for r in router.routes if hasattr(r, 'path')])
print('routes:', paths)
assert len(paths) == 9
"
```

Expected: Lists 9 paths (obsolete-counts, 3 list endpoints, 3 single-category POST, /all POST, /prune-cache POST).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/reembed.py
git commit -m "feat(api): add re-embed router with async endpoints and WebSocket progress"
```

---

### Task 7: Wire router into main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Import and include the new router**

In `backend/app/main.py`, find the existing route imports. Add `reembed` to the list:

```python
from app.api.routes import analytics, auth, chat, code, config, graph, memories, pipeline_failures, reembed, repos, tags, vectors
```

(Alphabetical ordering preserved — `reembed` goes between `pipeline_failures` and `repos`.)

Find the section where routers are included (the `app.include_router(...)` calls). Add:

```python
app.include_router(reembed.router)
```

Place it alongside the other include_router calls (order doesn't matter for FastAPI, but keep it grouped with the other backend routers for readability).

- [ ] **Step 2: Verify startup**

Run:
```bash
cd backend && python -c "
from app.main import app
paths = sorted([r.path for r in app.routes if hasattr(r, 'path')])
reembed_paths = [p for p in paths if 'reembed' in p]
print('reembed routes:')
for p in reembed_paths:
    print(' ', p)
assert len(reembed_paths) == 9
print('OK')
"
```

Expected: Lists 9 `/api/v1/reembed/*` routes and `OK`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(main): include reembed router"
```

---

### Task 8: Frontend WebSocket event type

**Files:**
- Modify: `frontend/src/lib/websocket-events.ts`

- [ ] **Step 1: Add the interface**

Edit `frontend/src/lib/websocket-events.ts`. After the `PipelineRetryBatchProgress` interface (added in Feature 2), add:

```typescript
export interface PipelineReembedBatchProgress {
  batch_id: string
  category: "memories" | "code_chunks" | "entities"
  current: number
  total: number
  processed: number
  errors: number
  state: "started" | "progress" | "done"
  error_message: string | null
}
```

Then update the `WebSocketEventMap` type to include the new event:

```typescript
export type WebSocketEventMap = {
  "pipeline.completed": PipelineStatus
  "pipeline.partial": PipelineStatus
  "pipeline.failed": PipelineStatus
  "pipeline.failure.updated": PipelineFailureUpdated
  "pipeline.retry_batch.progress": PipelineRetryBatchProgress
  "pipeline.reembed_batch.progress": PipelineReembedBatchProgress
  "memory.deleted": MemoryDeleted
  "repo.clone_started": RepoCloneStarted
  "repo.clone_completed": RepoCloneCompleted
  "repo.clone_failed": RepoCloneFailed
  "repo.indexing_started": RepoIndexingStarted
  "repo.indexing_progress": RepoIndexingProgress
  "repo.indexing_completed": RepoIndexingCompleted
  "repo.indexing_failed": RepoIndexingFailed
  "enrichment.batch_completed": EnrichmentBatchCompleted
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/websocket-events.ts
git commit -m "feat(ui): add PipelineReembedBatchProgress event type"
```

---

### Task 9: Frontend WebSocket hook handling for re-embed events

**Files:**
- Modify: `frontend/src/lib/websocket.ts`

- [ ] **Step 1: Add handler for re-embed progress**

Edit `frontend/src/lib/websocket.ts`. Inside the `onmessage` handler, find the existing `pipeline.retry_batch.progress` handler block (added in Feature 2). After it, add:

```typescript
      if (msg.event === "pipeline.reembed_batch.progress") {
        const d = msg.data as WebSocketEventMap["pipeline.reembed_batch.progress"]
        qc.setQueryData(["reembedBatchProgress", d.batch_id, d.category], d)
        if (d.state === "done") {
          void qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
          if (d.errors > 0) {
            toast.warning(`Re-embed ${d.category}: ${d.processed} succeeded, ${d.errors} failed`, {
              description: d.error_message || undefined,
            })
          } else if (d.processed > 0) {
            toast.success(`Re-embed ${d.category} complete: ${d.processed} updated`)
          }
        }
      }
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/websocket.ts
git commit -m "feat(ui): handle pipeline.reembed_batch.progress WebSocket event"
```

---

### Task 10: Frontend API hooks for re-embed

**Files:**
- Modify: `frontend/src/hooks/api/use-pipeline-api.ts`

- [ ] **Step 1: Add types and hooks**

Edit `frontend/src/hooks/api/use-pipeline-api.ts`. After the existing `PipelineFailure` interfaces and hooks (added in Feature 2), add:

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
        "/reembed/memories",
        { method: "POST" },
      ),
  })
}

export function useReembedCodeChunks() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/code-chunks",
        { method: "POST" },
      ),
  })
}

export function useReembedEntities() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/entities",
        { method: "POST" },
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

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-pipeline-api.ts
git commit -m "feat(ui): add obsolete counts and re-embed hooks"
```

---

### Task 11: Obsolete Embeddings card on Pipeline page

**Files:**
- Modify: `frontend/src/routes/_authenticated/pipeline.tsx`

- [ ] **Step 1: Add imports for new hooks**

Edit `frontend/src/routes/_authenticated/pipeline.tsx`. Find the existing import from `@/hooks/api` (the one that already imports pipeline failure hooks). Add the new re-embed hooks:

```tsx
import {
  usePipelineLogs,
  useHealth,
  useReprocessStream,
  usePipelineFailures,
  usePipelineFailureCounts,
  useRetryFailure,
  useForgetFailure,
  useRetryAllFailures,
  useObsoleteCounts,
  useReembedMemories,
  useReembedCodeChunks,
  useReembedEntities,
  useReembedAll,
  usePruneObsoleteCache,
  useReembedBatchProgress,
} from "@/hooks/api"
```

(Keep only the hooks you actually use — adjust the list to whatever `pipeline.tsx` already imports plus the new ones.)

- [ ] **Step 2: Add the ObsoleteEmbeddingsCard component**

Before the `PipelinePage` function definition, add a new component:

```tsx
type ReembedCategory = "memories" | "code_chunks" | "entities"

function CategoryProgressBar({
  batchId,
  category,
}: {
  batchId: string | null
  category: ReembedCategory
}) {
  const { data: progress } = useReembedBatchProgress(batchId, category)
  if (!progress || progress.state === "done") return null
  const pct = progress.total > 0 ? (progress.current / progress.total) * 100 : 0
  return (
    <div className="mt-2 space-y-1">
      <Progress value={pct} />
      <p className="text-xs text-muted-foreground">
        {progress.current} / {progress.total}
        {progress.errors > 0 && (
          <span className="text-destructive ml-2">({progress.errors} errors)</span>
        )}
      </p>
    </div>
  )
}

function ObsoleteEmbeddingsCard() {
  const { data: counts } = useObsoleteCounts()
  const reembedMemories = useReembedMemories()
  const reembedCodeChunks = useReembedCodeChunks()
  const reembedEntities = useReembedEntities()
  const reembedAll = useReembedAll()
  const pruneCache = usePruneObsoleteCache()

  const [batchIds, setBatchIds] = useState<Record<ReembedCategory, string | null>>({
    memories: null,
    code_chunks: null,
    entities: null,
  })

  if (!counts) return null

  const totalObsolete = counts.memories + counts.code_chunks + counts.entities
  const anyRunning =
    batchIds.memories !== null ||
    batchIds.code_chunks !== null ||
    batchIds.entities !== null

  if (totalObsolete === 0 && !anyRunning) return null

  const handleReembed = (
    category: ReembedCategory,
    mutation: typeof reembedMemories,
  ) => {
    mutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.total === 0) {
          toast.info(`No obsolete ${category}`)
          return
        }
        setBatchIds((prev) => ({ ...prev, [category]: data.batch_id }))
        toast.info(`Re-embedding ${data.total} ${category}...`)
      },
      onError: (err) => toast.error(`Re-embed ${category} failed: ${(err as Error).message}`),
    })
  }

  const handleReembedAll = () => {
    reembedAll.mutate(undefined, {
      onSuccess: (data) => {
        setBatchIds({
          memories: data.batch_id,
          code_chunks: data.batch_id,
          entities: data.batch_id,
        })
        toast.info(
          `Re-embedding all obsolete: ${data.totals.memories} memories, ${data.totals.entities} entities, ${data.totals.code_chunks} code chunks`,
        )
      },
      onError: (err) => toast.error(`Re-embed all failed: ${(err as Error).message}`),
    })
  }

  const handlePruneCache = () => {
    pruneCache.mutate(undefined, {
      onSuccess: (data) => toast.success(`Pruned ${data.deleted} old cache entries`),
      onError: (err) => toast.error(`Prune failed: ${(err as Error).message}`),
    })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Obsolete Embeddings</CardTitle>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleReembedAll}
              disabled={reembedAll.isPending || anyRunning || totalObsolete === 0}
            >
              Re-embed all obsolete
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handlePruneCache}
              disabled={pruneCache.isPending}
            >
              Prune old cache entries
            </Button>
          </div>
        </div>
        <p className="text-muted-foreground text-xs font-mono mt-1">
          Current: {counts.current_fingerprint}
        </p>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border rounded-md border border-border">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Memories</span>
              <p className="text-muted-foreground text-xs">
                {counts.memories} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.memories}
                category="memories"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("memories", reembedMemories)}
              disabled={
                reembedMemories.isPending ||
                batchIds.memories !== null ||
                counts.memories === 0
              }
            >
              Re-embed
            </Button>
          </div>
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Entities</span>
              <p className="text-muted-foreground text-xs">
                {counts.entities} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.entities}
                category="entities"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("entities", reembedEntities)}
              disabled={
                reembedEntities.isPending ||
                batchIds.entities !== null ||
                counts.entities === 0
              }
            >
              Re-embed
            </Button>
          </div>
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Code chunks</span>
              <p className="text-muted-foreground text-xs">
                {counts.code_chunks} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.code_chunks}
                category="code_chunks"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("code_chunks", reembedCodeChunks)}
              disabled={
                reembedCodeChunks.isPending ||
                batchIds.code_chunks !== null ||
                counts.code_chunks === 0
              }
            >
              Re-embed
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 3: Insert the card into PipelinePage layout**

Find the `PipelinePage` function's JSX return. Place `<ObsoleteEmbeddingsCard />` above the existing `<UnresolvedFailuresCard />` so it's the first section below the action row:

```tsx
      <div className="mb-6">
        <ObsoleteEmbeddingsCard />
      </div>

      <div className="mb-6">
        <UnresolvedFailuresCard />
      </div>
```

- [ ] **Step 4: Type-check and build**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No errors.

Run: `cd frontend && npx vite build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/_authenticated/pipeline.tsx
git commit -m "feat(ui): add Obsolete Embeddings card to pipeline page"
```

---

### Task 12: LLM config page modal after model change

**Files:**
- Modify: `frontend/src/routes/_authenticated/llm.tsx`
- Modify: `frontend/src/hooks/api/use-config-api.ts`

- [ ] **Step 1: Update `LLMConfigResponse` and `useUpdateLlmConfig` types**

Edit `frontend/src/hooks/api/use-config-api.ts`. Find the `LlmConfigResponse` interface and the `useUpdateLlmConfig` hook. Update the hook's mutation type to reflect the new `obsolete_after_change` field in the response:

Find:

```typescript
export function useUpdateLlmConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiFetch("/config/llm", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llmConfig"] }),
  });
}
```

Change to:

```typescript
export interface LlmConfigUpdateResponse extends LlmConfigResponse {
  obsolete_after_change: { memories: number; code_chunks: number; entities: number } | null
}

export function useUpdateLlmConfig() {
  const qc = useQueryClient();
  return useMutation<LlmConfigUpdateResponse, Error, Record<string, unknown>>({
    mutationFn: (data) =>
      apiFetch<LlmConfigUpdateResponse>("/config/llm", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmConfig"] });
      qc.invalidateQueries({ queryKey: ["obsoleteCounts"] });
    },
  });
}
```

- [ ] **Step 2: Add the modal and "re-embed now" flow to the LLM page**

Edit `frontend/src/routes/_authenticated/llm.tsx`. Add new imports at the top:

```tsx
import { useNavigate } from "@tanstack/react-router"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "darkraise-ui/components/dialog"
import { useReembedAll } from "@/hooks/api"
import { toast } from "sonner"
```

Then find the `LlmConfigPage` function (around line 236). Replace it with:

```tsx
function LlmConfigPage() {
  const { data, isLoading, error } = useLlmConfig()
  const updateConfig = useUpdateLlmConfig()
  const reembedAll = useReembedAll()
  const navigate = useNavigate()

  const [obsoleteDialog, setObsoleteDialog] = useState<{
    memories: number
    code_chunks: number
    entities: number
  } | null>(null)

  const handleSave = (purpose: string, purposeData: Partial<LlmPurposeConfig>) => {
    updateConfig.mutate(
      { [purpose]: purposeData },
      {
        onSuccess: (data) => {
          const obs = data.obsolete_after_change
          if (obs && (obs.memories > 0 || obs.code_chunks > 0 || obs.entities > 0)) {
            setObsoleteDialog(obs)
          } else {
            toast.success("LLM config updated")
          }
        },
        onError: (err) => toast.error(`Save failed: ${(err as Error).message}`),
      },
    )
  }

  const handleReembedNow = () => {
    reembedAll.mutate(undefined, {
      onSuccess: () => {
        toast.info("Re-embed started — track progress on the Pipeline page")
        setObsoleteDialog(null)
        navigate({ to: "/pipeline" })
      },
      onError: (err) => toast.error(`Re-embed failed: ${(err as Error).message}`),
    })
  }

  return (
    <div className="p-6">
      <PageHeader
        title="LLM Configuration"
        description="Configure LLM providers for each purpose. Changes take effect on the next memory operation."
      />
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mb-4">
          <p className="text-destructive text-sm">Failed to load config. Make sure your API key has admin scope.</p>
          <p className="text-xs text-muted-foreground mt-1">{(error as Error).message}</p>
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PurposeCard title="Embedding" config={data?.embedding} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Extraction" config={data?.extraction} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Reasoning" config={data?.reasoning} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Summarization" config={data?.summarization} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Reranker" config={data?.reranker} onSave={handleSave} saving={updateConfig.isPending} />
      </div>

      <Dialog
        open={obsoleteDialog !== null}
        onOpenChange={(open) => {
          if (!open) setObsoleteDialog(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Embedding Model Changed</DialogTitle>
          </DialogHeader>
          {obsoleteDialog && (
            <div className="space-y-4 py-2">
              <p className="text-sm">
                You changed the embedding model. The following data still uses the old model
                and should be re-embedded:
              </p>
              <ul className="text-sm space-y-1 pl-4 list-disc">
                {obsoleteDialog.memories > 0 && (
                  <li>{obsoleteDialog.memories} memories</li>
                )}
                {obsoleteDialog.entities > 0 && (
                  <li>{obsoleteDialog.entities} entities</li>
                )}
                {obsoleteDialog.code_chunks > 0 && (
                  <li>{obsoleteDialog.code_chunks} code chunks</li>
                )}
              </ul>
              <p className="text-xs text-muted-foreground">
                Re-embedding will not re-run extraction or classification, only the vector
                embeddings. Search quality will be degraded until re-embedding completes.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setObsoleteDialog(null)}>
              Later
            </Button>
            <Button
              onClick={handleReembedNow}
              disabled={reembedAll.isPending}
            >
              {reembedAll.isPending ? "Starting..." : "Re-embed now"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

- [ ] **Step 3: Type-check and build**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

Run: `cd frontend && npx vite build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/_authenticated/llm.tsx frontend/src/hooks/api/use-config-api.ts
git commit -m "feat(ui): show re-embed prompt modal after LLM config change"
```

---

### Task 13: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Run unit tests**

Run: `cd backend && python -m pytest tests/unit/ -v 2>&1 | tail -20`

Expected: All tests pass, including the 4 new `TestReembedLockSet` tests.

- [ ] **Step 2: Verify app boots and routes register**

Run:
```bash
cd backend && python -c "
from app.main import app
paths = sorted([r.path for r in app.routes if hasattr(r, 'path')])
reembed_paths = [p for p in paths if '/reembed' in p]
print('reembed routes:')
for p in reembed_paths:
    print(' ', p)
assert len(reembed_paths) == 9
print('OK')
"
```

Expected: 9 `/api/v1/reembed/*` routes listed.

- [ ] **Step 3: Restart the backend server**

Ask the user to restart the backend so the new router is loaded.

- [ ] **Step 4: Fetch obsolete counts via API**

After the user restarts the server:

```bash
curl -s http://localhost:8000/api/v1/reembed/obsolete-counts \
  -b "darkmem_session=<token>" | python -m json.tool
```

Expected: JSON response with `memories`, `code_chunks`, `entities`, and `current_fingerprint`.

- [ ] **Step 5: Induce an obsolete state**

Either:
- Manually UPDATE some memory_embeddings rows in Postgres to set `model_fingerprint = 'old-model|1024'`, then re-query obsolete counts — should show the altered rows.
- OR change the LLM embedding config in the UI to a different model name, which flips the pipeline's fingerprint. All existing rows become obsolete relative to the new fingerprint.

Re-run the counts endpoint to verify the new obsolete counts.

- [ ] **Step 6: Trigger a re-embed via API**

```bash
curl -s -X POST http://localhost:8000/api/v1/reembed/memories \
  -b "darkmem_session=<token>" | python -m json.tool
```

Expected: 202 with `{"accepted": true, "batch_id": "...", "total": N}`.

Watch the backend server logs for the progress events and the eventual `done` event. Fetch the counts again — should show 0 for memories.

- [ ] **Step 7: Visual check in the browser**

Navigate to the Pipeline page. The "Obsolete Embeddings" card should only appear when counts are non-zero. Induce obsolete state again and verify:
- Card appears with current fingerprint and per-category counts
- Per-row Re-embed buttons work, show a progress bar, and update the count when done
- "Re-embed all obsolete" runs all three categories
- "Prune old cache entries" toasts the deletion count

Then navigate to the LLM config page, change the embedding model, and verify the modal prompt appears with correct counts. Click "Later" to dismiss, or "Re-embed now" to navigate to the Pipeline page with the re-embed running.
