# Pipeline Failure Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a centralized pipeline failure tracking system with a new `pipeline_failures` table, async retry endpoints, and WebSocket-based status updates, covering both memory ingestion and code indexing.

**Architecture:** A single `pipeline_failures` table with polymorphic `(entity_type, entity_id)` reference serves as the source of truth for current failure state. A `PipelineFailureService` centralizes reads and writes. A retry-handler registry dispatches per-pipeline retry logic. Pipeline integrations call `record()` or `resolve()` at the end of each run. The frontend listens for two new WebSocket events (`pipeline.failure.updated` and `pipeline.retry_batch.progress`) instead of polling.

**Tech Stack:** Python 3.12 (FastAPI, SQLAlchemy async, Alembic, pgvector), TypeScript (React 19, TanStack Router, TanStack Query, WebSocket), PostgreSQL

**Spec:** `docs/superpowers/specs/2026-04-10-pipeline-failure-tracking-design.md`

---

### Task 1: Migration for pipeline_failures table

**Files:**
- Create: `backend/migrations/versions/0003_pipeline_failures.py`

- [ ] **Step 1: Write the migration file**

```python
"""pipeline failures tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-10

Adds:
  - pipeline_failures table with polymorphic (entity_type, entity_id) reference
  - Partial unique index on unresolved rows for upsert semantics
  - Secondary indexes on pipeline_name and resolved_at
"""
from collections.abc import Sequence
from typing import Union

from alembic import op


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX idx_pipeline_failures_unresolved
        ON pipeline_failures(entity_type, entity_id, pipeline_name)
        WHERE resolved_at IS NULL
    """)

    op.execute("""
        CREATE INDEX idx_pipeline_failures_pipeline_name
        ON pipeline_failures(pipeline_name)
        WHERE resolved_at IS NULL
    """)

    op.execute("""
        CREATE INDEX idx_pipeline_failures_resolved_at
        ON pipeline_failures(resolved_at)
        WHERE resolved_at IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_resolved_at")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_pipeline_name")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_unresolved")
    op.execute("DROP TABLE IF EXISTS pipeline_failures")
```

- [ ] **Step 2: Run the migration**

Run: `cd backend && alembic upgrade head 2>&1 | tail -10`

Expected: `INFO [alembic.runtime.migration] Running upgrade 0002 -> 0003, pipeline failures tracking`.

- [ ] **Step 3: Verify schema**

Run:
```bash
cd backend && python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        cols = (await s.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name = 'pipeline_failures' ORDER BY ordinal_position\"))).scalars().all()
        print('columns:', cols)
        idx = (await s.execute(text(\"SELECT indexname FROM pg_indexes WHERE tablename = 'pipeline_failures'\"))).scalars().all()
        print('indexes:', idx)
asyncio.run(check())
" 2>&1
```

Expected: columns include `id, entity_type, entity_id, pipeline_name, failed_step, error_message, attempts, first_failed_at, last_attempt_at, resolved_at, metadata`. Indexes include the three created above plus `pipeline_failures_pkey`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0003_pipeline_failures.py
git commit -m "feat(db): add pipeline_failures table for centralized failure tracking"
```

---

### Task 2: PipelineFailure ORM model

**Files:**
- Create: `backend/app/models/pipeline_failure.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the model file**

Create `backend/app/models/pipeline_failure.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class PipelineFailure(Base):
    __tablename__ = "pipeline_failures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(50), nullable=False)
    failed_step: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```

Note: The Python attribute is named `extra_metadata` because `metadata` is reserved on SQLAlchemy `DeclarativeBase`. The DB column is still `metadata` via the explicit column name.

- [ ] **Step 2: Export from models package**

Edit `backend/app/models/__init__.py`. Find the existing import block and add:

```python
from .pipeline_failure import PipelineFailure
```

Find the `__all__` list and add `"PipelineFailure"` alongside the other model names.

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.models import PipelineFailure; print(PipelineFailure.__tablename__)"`

Expected: `pipeline_failures`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/pipeline_failure.py backend/app/models/__init__.py
git commit -m "feat(models): add PipelineFailure ORM model"
```

---

### Task 3: Pydantic schemas for API and events

**Files:**
- Create: `backend/app/schemas/pipeline_failures.py`
- Modify: `backend/app/schemas/events.py`

- [ ] **Step 1: Create the response schemas**

Create `backend/app/schemas/pipeline_failures.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    metadata: dict = Field(default_factory=dict)
    entity_preview: str | None = None


class PipelineFailureListResponse(BaseModel):
    items: list[PipelineFailureResponse]
    total: int
```

- [ ] **Step 2: Add new event schemas**

Edit `backend/app/schemas/events.py`. Find the existing class definitions and add these two new classes before the `EVENT_SCHEMAS` dict:

```python
class PipelineFailureUpdated(BaseModel):
    failure_id: str
    entity_type: str
    entity_id: str
    pipeline_name: str
    state: str  # "recorded" | "resolved" | "forgotten"
    failed_step: str | None
    attempts: int
    error_message: str | None


class PipelineRetryBatchProgress(BaseModel):
    batch_id: str
    current: int
    total: int
    processed: int
    errors: int
    entity_type: str | None
    entity_id: str | None
    state: str  # "started" | "progress" | "done"
```

Then add entries to the `EVENT_SCHEMAS` dict:

```python
EVENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "pipeline.completed": PipelineStatus,
    "pipeline.partial": PipelineStatus,
    "pipeline.failed": PipelineStatus,
    "pipeline.failure.updated": PipelineFailureUpdated,
    "pipeline.retry_batch.progress": PipelineRetryBatchProgress,
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
from app.schemas.pipeline_failures import PipelineFailureResponse, PipelineFailureListResponse
from app.schemas.events import PipelineFailureUpdated, PipelineRetryBatchProgress, EVENT_SCHEMAS
assert 'pipeline.failure.updated' in EVENT_SCHEMAS
assert 'pipeline.retry_batch.progress' in EVENT_SCHEMAS
print('OK')
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/pipeline_failures.py backend/app/schemas/events.py
git commit -m "feat(schemas): add pipeline failure response and event schemas"
```

---

### Task 4: PipelineFailureService with CRUD, retry registry, and retry locks

**Files:**
- Create: `backend/app/services/pipeline_failures.py`
- Create: `backend/tests/unit/test_pipeline_failures_helpers.py`

- [ ] **Step 1: Write failing tests for pure helpers**

Create `backend/tests/unit/test_pipeline_failures_helpers.py`:

```python
from uuid import uuid4

from app.services.pipeline_failures import (
    RetryLockSet,
    derive_memory_failed_step,
    derive_code_failed_step,
)


class TestDeriveMemoryFailedStep:
    def test_returns_none_when_all_ok(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok"}
        assert derive_memory_failed_step(status) is None

    def test_returns_none_when_extract_partial(self):
        # Partial extractions are not counted as failed
        status = {"embed": "ok", "extract": "partial", "vector": "ok", "graph": "ok"}
        assert derive_memory_failed_step(status) is None

    def test_returns_none_when_graph_skipped(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "skipped"}
        assert derive_memory_failed_step(status) is None

    def test_content_embedding_failure(self):
        status = {"embed": "error", "extract": "pending", "vector": "pending", "graph": "pending"}
        assert derive_memory_failed_step(status) == "content_embedding"

    def test_extraction_failure(self):
        status = {"embed": "ok", "extract": "error", "vector": "ok", "graph": "ok"}
        assert derive_memory_failed_step(status) == "extraction"

    def test_vector_write_failure(self):
        status = {"embed": "ok", "extract": "ok", "vector": "error", "graph": "ok"}
        assert derive_memory_failed_step(status) == "vector_write"

    def test_graph_write_failure(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "error"}
        assert derive_memory_failed_step(status) == "graph_write"

    def test_first_failed_step_wins(self):
        status = {"embed": "error", "extract": "error", "vector": "error", "graph": "error"}
        assert derive_memory_failed_step(status) == "content_embedding"


class TestDeriveCodeFailedStep:
    def test_empty_returns_other(self):
        assert derive_code_failed_step([]) == "other"

    def test_parse_prefix(self):
        assert derive_code_failed_step(["parse:src/foo.py:SyntaxError"]) == "parse"

    def test_embed_prefix(self):
        assert derive_code_failed_step(["embed:src/foo.py:RuntimeError"]) == "embeddings"

    def test_import_prefix(self):
        assert derive_code_failed_step(["import:src/foo.py:ModuleNotFound"]) == "import_resolution"

    def test_unknown_returns_other(self):
        assert derive_code_failed_step(["weird:something:Error"]) == "other"

    def test_first_matching_wins(self):
        errors = ["weird:x", "parse:src/foo.py:X"]
        assert derive_code_failed_step(errors) == "parse"


class TestRetryLockSet:
    def test_acquire_release(self):
        locks = RetryLockSet()
        uid = uuid4()
        assert locks.try_acquire(uid) is True
        assert locks.try_acquire(uid) is False
        locks.release(uid)
        assert locks.try_acquire(uid) is True

    def test_release_nonexistent_is_safe(self):
        locks = RetryLockSet()
        locks.release(uuid4())  # should not raise

    def test_is_locked(self):
        locks = RetryLockSet()
        uid = uuid4()
        assert locks.is_locked(uid) is False
        locks.try_acquire(uid)
        assert locks.is_locked(uid) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_pipeline_failures_helpers.py -v 2>&1 | tail -20`

Expected: `ModuleNotFoundError: No module named 'app.services.pipeline_failures'` or similar import failure.

- [ ] **Step 3: Create the service file**

Create `backend/app/services/pipeline_failures.py`:

```python
"""Centralized pipeline failure tracking and retry service.

Provides record/resolve/forget/list operations on the pipeline_failures
table, plus a retry-handler registry and an in-memory retry lock set
for concurrent retry protection.
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
# Retry handler registry (module-level singleton)
# ---------------------------------------------------------------------------

RETRY_HANDLERS: dict[str, Callable[[UUID], Awaitable[None]]] = {}


def register_retry_handler(pipeline_name: str):
    """Decorator or direct registration for retry handlers.

    Usage:
        @register_retry_handler("memory_ingest")
        async def _retry_memory(memory_id: UUID) -> None:
            ...

    Or imperatively:
        register_retry_handler("memory_ingest")(my_handler_fn)
    """
    def decorator(fn: Callable[[UUID], Awaitable[None]]):
        RETRY_HANDLERS[pipeline_name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# In-memory retry lock set (single-process guard)
# ---------------------------------------------------------------------------

class RetryLockSet:
    """Simple in-memory set tracking failures currently being retried.

    Not thread-safe across processes. darkmem is single-process single-admin
    per its deployment model, so in-memory is sufficient.
    """

    def __init__(self) -> None:
        self._locked: set[UUID] = set()

    def try_acquire(self, failure_id: UUID) -> bool:
        if failure_id in self._locked:
            return False
        self._locked.add(failure_id)
        return True

    def release(self, failure_id: UUID) -> None:
        self._locked.discard(failure_id)

    def is_locked(self, failure_id: UUID) -> bool:
        return failure_id in self._locked


# Module-level singleton — imported by the API layer
retry_locks = RetryLockSet()


# ---------------------------------------------------------------------------
# Pure helpers for deriving failed_step from pipeline status dicts
# ---------------------------------------------------------------------------

def derive_memory_failed_step(status: dict) -> str | None:
    """Return the failed_step for a memory pipeline status dict, or None
    if the memory succeeded (hard failures only — partial extraction is
    not counted as failed)."""
    if status.get("embed") == "error":
        return "content_embedding"
    if status.get("extract") == "error":
        return "extraction"
    if status.get("vector") == "error":
        return "vector_write"
    if status.get("graph") == "error":
        return "graph_write"
    return None


_CODE_ERROR_PREFIXES = {
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


def derive_code_failed_step(errors: list[str]) -> str:
    """Return the first recognized phase from a CodePipeline errors list,
    or 'other' if none match."""
    for err in errors:
        for pfx, step in _CODE_ERROR_PREFIXES.items():
            if err.startswith(pfx):
                return step
    return "other"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

BroadcastFn = Callable[[str, dict], Awaitable[None]]


class PipelineFailureService:
    def __init__(
        self,
        session: AsyncSession,
        broadcast: BroadcastFn | None = None,
    ) -> None:
        self.session = session
        self._broadcast = broadcast

    async def record(
        self,
        entity_type: str,
        entity_id: UUID,
        pipeline_name: str,
        failed_step: str,
        error_message: str,
        metadata: dict | None = None,
    ) -> dict:
        """Upsert a failure row. Returns the final row state as a dict."""
        meta_json = json.dumps(metadata or {})
        result = await self.session.execute(
            text("""
                INSERT INTO pipeline_failures (
                    entity_type, entity_id, pipeline_name,
                    failed_step, error_message, metadata
                )
                VALUES (
                    :entity_type, CAST(:entity_id AS uuid), :pipeline_name,
                    :failed_step, :error_message, CAST(:metadata AS jsonb)
                )
                ON CONFLICT (entity_type, entity_id, pipeline_name)
                WHERE resolved_at IS NULL
                DO UPDATE SET
                    attempts = pipeline_failures.attempts + 1,
                    last_attempt_at = NOW(),
                    failed_step = EXCLUDED.failed_step,
                    error_message = EXCLUDED.error_message,
                    metadata = EXCLUDED.metadata
                RETURNING
                    id, entity_type, entity_id, pipeline_name,
                    failed_step, error_message, attempts,
                    first_failed_at, last_attempt_at, resolved_at
            """),
            {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "pipeline_name": pipeline_name,
                "failed_step": failed_step,
                "error_message": error_message,
                "metadata": meta_json,
            },
        )
        row = result.mappings().one()
        out = {
            "id": str(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": str(row["entity_id"]),
            "pipeline_name": row["pipeline_name"],
            "failed_step": row["failed_step"],
            "error_message": row["error_message"],
            "attempts": row["attempts"],
            "first_failed_at": row["first_failed_at"],
            "last_attempt_at": row["last_attempt_at"],
            "resolved_at": row["resolved_at"],
        }
        if self._broadcast:
            try:
                await self._broadcast("pipeline.failure.updated", {
                    "failure_id": out["id"],
                    "entity_type": out["entity_type"],
                    "entity_id": out["entity_id"],
                    "pipeline_name": out["pipeline_name"],
                    "state": "recorded",
                    "failed_step": out["failed_step"],
                    "attempts": out["attempts"],
                    "error_message": out["error_message"],
                })
            except Exception as e:
                logger.warning("failure.updated broadcast failed: %s", e)
        return out

    async def resolve(
        self,
        entity_type: str,
        entity_id: UUID,
        pipeline_name: str,
    ) -> None:
        """Mark any unresolved failure for this key as resolved. No-op if
        no unresolved row exists."""
        result = await self.session.execute(
            text("""
                UPDATE pipeline_failures
                SET resolved_at = NOW()
                WHERE entity_type = :entity_type
                  AND entity_id = CAST(:entity_id AS uuid)
                  AND pipeline_name = :pipeline_name
                  AND resolved_at IS NULL
                RETURNING id, failed_step, attempts
            """),
            {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "pipeline_name": pipeline_name,
            },
        )
        row = result.mappings().first()
        if not row or not self._broadcast:
            return
        try:
            await self._broadcast("pipeline.failure.updated", {
                "failure_id": str(row["id"]),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "pipeline_name": pipeline_name,
                "state": "resolved",
                "failed_step": row["failed_step"],
                "attempts": row["attempts"],
                "error_message": None,
            })
        except Exception as e:
            logger.warning("failure.updated broadcast failed: %s", e)

    async def forget(self, entity_type: str, entity_id: UUID) -> int:
        """Hard-delete all failure rows for a specific entity across all
        pipelines. Returns the number of rows deleted."""
        result = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE entity_type = :entity_type
                  AND entity_id = CAST(:entity_id AS uuid)
                RETURNING id, pipeline_name
            """),
            {"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        rows = result.mappings().all()
        if self._broadcast and rows:
            for r in rows:
                try:
                    await self._broadcast("pipeline.failure.updated", {
                        "failure_id": str(r["id"]),
                        "entity_type": entity_type,
                        "entity_id": str(entity_id),
                        "pipeline_name": r["pipeline_name"],
                        "state": "forgotten",
                        "failed_step": None,
                        "attempts": 0,
                        "error_message": None,
                    })
                except Exception as e:
                    logger.warning("failure.updated broadcast failed: %s", e)
        return len(rows)

    async def forget_all_for_repo(self, repo_id: UUID) -> int:
        """Delete all failures tied to a code repository."""
        return await self.forget("code_repo", repo_id)

    async def prune_orphans(self) -> dict[str, int]:
        """Delete failure rows whose referenced entity no longer exists."""
        counts: dict[str, int] = {}

        mem_del = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE entity_type = 'memory'
                  AND NOT EXISTS (SELECT 1 FROM memories WHERE memories.id = pipeline_failures.entity_id)
                RETURNING id
            """)
        )
        counts["memory"] = len(mem_del.fetchall())

        repo_del = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE entity_type = 'code_repo'
                  AND NOT EXISTS (SELECT 1 FROM repositories WHERE repositories.id = pipeline_failures.entity_id)
                RETURNING id
            """)
        )
        counts["code_repo"] = len(repo_del.fetchall())

        return counts

    async def prune_resolved_older_than(self, days: int = 30) -> int:
        """Delete resolved rows older than N days."""
        result = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE resolved_at IS NOT NULL
                  AND resolved_at < NOW() - make_interval(days => :days)
                RETURNING id
            """),
            {"days": days},
        )
        return len(result.fetchall())

    async def list_unresolved(
        self,
        entity_type: str | None = None,
        pipeline_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List unresolved failures with entity_preview enrichment.
        Returns (items, total_count)."""
        where_parts = ["pf.resolved_at IS NULL"]
        params: dict = {"limit": limit, "offset": offset}
        if entity_type:
            where_parts.append("pf.entity_type = :entity_type")
            params["entity_type"] = entity_type
        if pipeline_name:
            where_parts.append("pf.pipeline_name = :pipeline_name")
            params["pipeline_name"] = pipeline_name
        where_sql = " AND ".join(where_parts)

        items_sql = f"""
            SELECT
                pf.id, pf.entity_type, pf.entity_id, pf.pipeline_name,
                pf.failed_step, pf.error_message, pf.attempts,
                pf.first_failed_at, pf.last_attempt_at, pf.resolved_at,
                pf.metadata,
                CASE
                    WHEN pf.entity_type = 'memory' THEN LEFT(m.content, 80)
                    WHEN pf.entity_type = 'code_repo' THEN r.name
                    ELSE NULL
                END AS entity_preview
            FROM pipeline_failures pf
            LEFT JOIN memories m ON pf.entity_type = 'memory' AND m.id = pf.entity_id
            LEFT JOIN repositories r ON pf.entity_type = 'code_repo' AND r.id = pf.entity_id
            WHERE {where_sql}
            ORDER BY pf.last_attempt_at DESC
            LIMIT :limit OFFSET :offset
        """
        result = await self.session.execute(text(items_sql), params)
        items = []
        for row in result.mappings().all():
            items.append({
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "entity_id": str(row["entity_id"]),
                "pipeline_name": row["pipeline_name"],
                "failed_step": row["failed_step"],
                "error_message": row["error_message"],
                "attempts": row["attempts"],
                "first_failed_at": row["first_failed_at"],
                "last_attempt_at": row["last_attempt_at"],
                "resolved_at": row["resolved_at"],
                "metadata": row["metadata"] or {},
                "entity_preview": row["entity_preview"],
            })

        count_sql = f"SELECT COUNT(*) FROM pipeline_failures pf WHERE {where_sql}"
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = (await self.session.execute(text(count_sql), count_params)).scalar_one()

        return items, int(total)

    async def get(self, failure_id: UUID) -> dict | None:
        result = await self.session.execute(
            text("""
                SELECT id, entity_type, entity_id, pipeline_name,
                       failed_step, error_message, attempts,
                       first_failed_at, last_attempt_at, resolved_at, metadata
                FROM pipeline_failures
                WHERE id = CAST(:id AS uuid)
            """),
            {"id": str(failure_id)},
        )
        row = result.mappings().first()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": str(row["entity_id"]),
            "pipeline_name": row["pipeline_name"],
            "failed_step": row["failed_step"],
            "error_message": row["error_message"],
            "attempts": row["attempts"],
            "first_failed_at": row["first_failed_at"],
            "last_attempt_at": row["last_attempt_at"],
            "resolved_at": row["resolved_at"],
            "metadata": row["metadata"] or {},
        }

    async def counts_by_pipeline(self) -> dict[str, int]:
        result = await self.session.execute(
            text("""
                SELECT pipeline_name, COUNT(*) AS c
                FROM pipeline_failures
                WHERE resolved_at IS NULL
                GROUP BY pipeline_name
            """)
        )
        return {row["pipeline_name"]: int(row["c"]) for row in result.mappings().all()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_pipeline_failures_helpers.py -v 2>&1 | tail -30`

Expected: All 14 tests pass.

- [ ] **Step 5: Verify top-level import**

Run:
```bash
cd backend && python -c "
from app.services.pipeline_failures import (
    PipelineFailureService, RETRY_HANDLERS, register_retry_handler,
    retry_locks, RetryLockSet, derive_memory_failed_step, derive_code_failed_step,
)
print('OK')
"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/pipeline_failures.py backend/tests/unit/test_pipeline_failures_helpers.py
git commit -m "feat(services): add PipelineFailureService with retry registry and locks"
```

---

### Task 5: Integrate memory pipeline with failure tracking

**Files:**
- Modify: `backend/app/services/pipeline.py`

- [ ] **Step 1: Find the end of process_batch**

Read `backend/app/services/pipeline.py` and locate the end of the `process_batch` method. It currently ends with a normalization loop that returns `normalized`. The insert point is after the normalization loop, before the `return normalized` statement.

- [ ] **Step 2: Add failure recording block**

In `backend/app/services/pipeline.py`, locate the `process_batch` method. Just before the final `return normalized` line, add:

```python
        # Feature 2: record pipeline failure state for each memory
        try:
            from app.services.pipeline_failures import (
                PipelineFailureService, derive_memory_failed_step,
            )
            from app.api.websocket import event_manager

            async with self.session_factory() as failure_session:
                failure_svc = PipelineFailureService(
                    failure_session, broadcast=event_manager.broadcast,
                )
                for entry, result in zip(entries, normalized):
                    if not isinstance(result, dict):
                        continue
                    mem_id_str = result.get("memory_id")
                    if not mem_id_str:
                        continue
                    try:
                        entity_id = UUID(mem_id_str) if isinstance(mem_id_str, str) else mem_id_str
                    except (ValueError, TypeError):
                        continue
                    failed_step = derive_memory_failed_step(result)
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
        except Exception as e:
            logger.warning("Failed to record pipeline failures for batch: %s", e)
```

The block is wrapped in a try/except so that a failure recording error never breaks the main pipeline return value.

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.services.pipeline import ProcessingPipeline; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Run existing pipeline-related tests**

Run: `cd backend && python -m pytest tests/unit/ -v 2>&1 | tail -20`

Expected: All tests pass (no tests for the new integration yet, existing ones should still pass).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py
git commit -m "feat(pipeline): record/resolve failures at end of process_batch"
```

---

### Task 6: Integrate code indexing with failure tracking

**Files:**
- Modify: `backend/app/services/code_pipeline.py`

`CodeIndexer.index_repo` is a thin wrapper around `CodePipeline.run(repo_id)`. The error list lives on `CodePipeline._stats["errors"]`. The integration belongs in `CodePipeline.run()`, not in `CodeIndexer`.

- [ ] **Step 1: Locate the success return in CodePipeline.run**

In `backend/app/services/code_pipeline.py`, find `CodePipeline.run` (around line 99). The success path currently ends with:

```python
            logger.info(
                "Pipeline complete for %s: %d changed, %d skipped, %d deleted, %d symbols, %d errors",
                repo.name, self._stats["files_changed"], self._stats["files_skipped"],
                self._stats["files_deleted"], self._stats["symbols_indexed"],
                len(self._stats["errors"]),
            )
            return self._stats
```

The failure recording block must run just before `return self._stats`.

- [ ] **Step 2: Add failure recording in the success path**

In `CodePipeline.run`, replace the success return block with:

```python
            logger.info(
                "Pipeline complete for %s: %d changed, %d skipped, %d deleted, %d symbols, %d errors",
                repo.name, self._stats["files_changed"], self._stats["files_skipped"],
                self._stats["files_deleted"], self._stats["symbols_indexed"],
                len(self._stats["errors"]),
            )

            # Feature 2: record code indexing failure state
            try:
                from app.services.pipeline_failures import (
                    PipelineFailureService, derive_code_failed_step,
                )
                failure_svc = PipelineFailureService(
                    self.session, broadcast=event_manager.broadcast,
                )
                errors = self._stats.get("errors", [])
                if errors:
                    failed_step = derive_code_failed_step(errors)
                    error_message = "\n".join(errors[:10])
                    await failure_svc.record(
                        entity_type="code_repo",
                        entity_id=repo_id,
                        pipeline_name="code_index",
                        failed_step=failed_step,
                        error_message=error_message,
                        metadata={"error_count": len(errors)},
                    )
                else:
                    await failure_svc.resolve(
                        entity_type="code_repo",
                        entity_id=repo_id,
                        pipeline_name="code_index",
                    )
                await self.session.commit()
            except Exception as e:
                logger.warning("Failed to record code indexing failure state: %s", e)

            return self._stats
```

`event_manager` is already imported at the top of `code_pipeline.py` (verify before editing — if not, add `from app.api.websocket import event_manager` to the imports).

- [ ] **Step 3: Also record failure in the exception path**

In the same `run` method, the exception handler sets `repo.status = "error"` and raises. Failures that raise an exception should also create a failure row. Update the exception block:

```python
        except Exception as exc:
            repo.status = "error"
            repo.status_message = str(exc)[:500]
            try:
                await self._delete_all_repo_data(repo.id)
            except Exception:
                logger.exception("Failed to clean up partial pipeline data for repo %s", repo.id)
            await self.session.commit()

            # Feature 2: record the exception as an unresolved failure
            try:
                from app.services.pipeline_failures import PipelineFailureService
                failure_svc = PipelineFailureService(
                    self.session, broadcast=event_manager.broadcast,
                )
                await failure_svc.record(
                    entity_type="code_repo",
                    entity_id=repo_id,
                    pipeline_name="code_index",
                    failed_step="other",
                    error_message=f"{type(exc).__name__}: {exc}"[:2000],
                )
                await self.session.commit()
            except Exception as e2:
                logger.warning("Failed to record pipeline exception as failure: %s", e2)

            raise
```

- [ ] **Step 4: Verify import**

Run: `cd backend && python -c "from app.services.code_pipeline import CodePipeline; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/code_pipeline.py
git commit -m "feat(code): record/resolve failures at end of CodePipeline.run"
```

---

### Task 7: Delete hooks for memory and repo cleanup

**Files:**
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/services/repo_manager.py`

- [ ] **Step 1: Hook delete_memory in MemoryService**

In `backend/app/services/memory.py`, find the `delete_memory` method (around line 76). It currently does:

```python
    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
            if self.pipeline:
                await self.pipeline.delete_memory(memory_id)
        return result
```

Modify it to call `forget` before the delete:

```python
    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        from app.services.pipeline_failures import PipelineFailureService
        from app.api.websocket import event_manager

        failure_svc = PipelineFailureService(self.session, broadcast=event_manager.broadcast)
        await failure_svc.forget("memory", memory_id)

        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
            if self.pipeline:
                await self.pipeline.delete_memory(memory_id)
        return result
```

- [ ] **Step 2: Hook merge_memories in MemoryService**

In the same file, find `merge_memories` (around line 244-260). It deletes the source memory via `self.pipeline.delete_memory(source_id)`. Before that delete, add:

```python
                # Feature 2: forget any failure rows for the source memory
                from app.services.pipeline_failures import PipelineFailureService
                from app.api.websocket import event_manager
                failure_svc = PipelineFailureService(self.session, broadcast=event_manager.broadcast)
                await failure_svc.forget("memory", source_id)
```

Place this immediately before the `await self.pipeline.delete_memory(source_id)` call.

- [ ] **Step 3: Hook RepoManager.delete**

In `backend/app/services/repo_manager.py`, find the `delete` method (around line 150). It currently deletes the repo row. Before the actual delete, add:

```python
        from app.services.pipeline_failures import PipelineFailureService
        from app.api.websocket import event_manager
        failure_svc = PipelineFailureService(self.session, broadcast=event_manager.broadcast)
        await failure_svc.forget_all_for_repo(repo_id)
```

Place this at the start of the `delete` method body (before the existing SQL operations).

- [ ] **Step 4: Verify imports**

Run:
```bash
cd backend && python -c "
from app.services.memory import MemoryService
from app.services.repo_manager import RepoManager
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/memory.py backend/app/services/repo_manager.py
git commit -m "feat(cleanup): hook delete paths to forget pipeline failures"
```

---

### Task 8: New API router for pipeline failures

**Files:**
- Create: `backend/app/api/routes/pipeline_failures.py`

- [ ] **Step 1: Create the router file**

Create `backend/app/api/routes/pipeline_failures.py`:

```python
"""Pipeline failures API routes.

Provides:
  - GET  /api/v1/pipeline-failures — list unresolved failures
  - GET  /api/v1/pipeline-failures/counts — counts by pipeline
  - GET  /api/v1/pipeline-failures/{id} — get one
  - POST /api/v1/pipeline-failures/{id}/retry — async single retry
  - POST /api/v1/pipeline-failures/retry-all — async bulk retry
  - DELETE /api/v1/pipeline-failures/{id} — forget a failure
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.websocket import event_manager
from app.database import async_session_factory, get_session
from app.services.pipeline_failures import (
    PipelineFailureService,
    RETRY_HANDLERS,
    retry_locks,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline-failures", tags=["pipeline-failures"])


async def _build_memory_entry(memory_id: UUID) -> dict | None:
    """Load a memory and build an entry dict for process_batch. Returns
    None if the memory has been deleted."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.memory import Memory

    async with async_session_factory() as session:
        mem = (await session.execute(
            select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        )).scalar_one_or_none()
        if not mem:
            return None
        return {
            "memory_id": mem.id,
            "content": mem.content,
            "source": mem.source,
            "tags": [t.name for t in mem.tags],
            "memory_type": mem.memory_type,
            "created_at": mem.created_at.isoformat() if mem.created_at else "",
        }


@router.get("")
async def list_failures(
    entity_type: str | None = None,
    pipeline_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    items, total = await svc.list_unresolved(
        entity_type=entity_type, pipeline_name=pipeline_name,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


@router.get("/counts")
async def counts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    return await svc.counts_by_pipeline()


@router.get("/{failure_id}")
async def get_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    return failure


@router.post("/{failure_id}/retry", status_code=202)
async def retry_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    if failure["resolved_at"] is not None:
        return {"accepted": True, "failure_id": str(failure_id), "note": "already resolved"}

    handler = RETRY_HANDLERS.get(failure["pipeline_name"])
    if not handler:
        return JSONResponse(
            status_code=503,
            content={
                "accepted": False,
                "reason": "no_handler",
                "pipeline_name": failure["pipeline_name"],
            },
        )

    if not retry_locks.try_acquire(failure_id):
        return JSONResponse(
            status_code=409,
            content={"accepted": False, "reason": "already_retrying"},
        )

    async def _run():
        try:
            await handler(UUID(failure["entity_id"]))
        except Exception as e:
            logger.exception("Retry handler failed for failure_id=%s", failure_id)
            try:
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
            except Exception:
                logger.exception("Failed to record retry exception")
        finally:
            retry_locks.release(failure_id)

    asyncio.create_task(_run())
    return {"accepted": True, "failure_id": str(failure_id)}


@router.post("/retry-all", status_code=202)
async def retry_all(
    entity_type: str | None = None,
    pipeline_name: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    svc = PipelineFailureService(session)
    failures, total = await svc.list_unresolved(
        entity_type=entity_type, pipeline_name=pipeline_name, limit=1000,
    )
    batch_id = str(uuid4())

    if total == 0:
        # Emit a done event immediately so the frontend can react
        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": 0, "total": 0,
            "processed": 0, "errors": 0,
            "entity_type": None, "entity_id": None, "state": "done",
        })
        return {"accepted": True, "batch_id": batch_id, "total": 0}

    pipeline_obj = getattr(request.app.state, "pipeline", None) if request else None

    async def _run_bulk():
        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": 0, "total": total,
            "processed": 0, "errors": 0,
            "entity_type": None, "entity_id": None, "state": "started",
        })

        processed = 0
        errors = 0

        # Memory bulk path — use process_batch for full batching benefit
        if pipeline_name == "memory_ingest" and pipeline_obj is not None:
            entries_with_failures: list[tuple[dict, dict]] = []
            for f in failures:
                fid = UUID(f["id"])
                if not retry_locks.try_acquire(fid):
                    continue
                entry = await _build_memory_entry(UUID(f["entity_id"]))
                if entry is None:
                    retry_locks.release(fid)
                    continue
                entries_with_failures.append((f, entry))

            try:
                results = await pipeline_obj.process_batch([e for _, e in entries_with_failures])
                for (f, _), result in zip(entries_with_failures, results):
                    processed += 1
                    if isinstance(result, dict) and result.get("error"):
                        errors += 1
                    await event_manager.broadcast("pipeline.retry_batch.progress", {
                        "batch_id": batch_id, "current": processed, "total": total,
                        "processed": processed, "errors": errors,
                        "entity_type": f["entity_type"], "entity_id": f["entity_id"],
                        "state": "progress",
                    })
            except Exception:
                logger.exception("Bulk memory retry failed")
                errors += len(entries_with_failures) - processed
                processed = len(entries_with_failures)
            finally:
                for f, _ in entries_with_failures:
                    retry_locks.release(UUID(f["id"]))
        else:
            # Sequential fallback: run the handler per failure
            for f in failures:
                fid = UUID(f["id"])
                if not retry_locks.try_acquire(fid):
                    continue
                try:
                    handler = RETRY_HANDLERS.get(f["pipeline_name"])
                    if handler:
                        await handler(UUID(f["entity_id"]))
                        processed += 1
                    else:
                        errors += 1
                        logger.warning("No retry handler for %s", f["pipeline_name"])
                except Exception:
                    logger.exception("Retry handler failed in bulk")
                    errors += 1
                finally:
                    retry_locks.release(fid)
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


@router.delete("/{failure_id}")
async def forget_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    await session.execute(
        __import__("sqlalchemy").text(
            "DELETE FROM pipeline_failures WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(failure_id)},
    )
    # Broadcast forgotten event
    try:
        await event_manager.broadcast("pipeline.failure.updated", {
            "failure_id": str(failure_id),
            "entity_type": failure["entity_type"],
            "entity_id": failure["entity_id"],
            "pipeline_name": failure["pipeline_name"],
            "state": "forgotten",
            "failed_step": None,
            "attempts": 0,
            "error_message": None,
        })
    except Exception as e:
        logger.warning("forgotten broadcast failed: %s", e)
    return {"ok": True}
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.api.routes.pipeline_failures import router; print(len(router.routes))"`

Expected: `6` (list, counts, get, retry, retry-all, delete — that's 6 routes, or possibly more depending on how FastAPI counts them).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/pipeline_failures.py
git commit -m "feat(api): add pipeline-failures router with async retry endpoints"
```

---

### Task 9: Remove legacy reprocess_failed endpoints

**Files:**
- Modify: `backend/app/services/analytics.py`
- Modify: `backend/app/api/routes/analytics.py`

- [ ] **Step 1: Remove reprocess_failed methods from AnalyticsService**

In `backend/app/services/analytics.py`, delete these methods entirely:

- `async def reprocess_failed(self) -> dict:` (around line 38)
- `async def reprocess_failed_stream(self):` (around line 105)

Keep `reprocess_all` and `reprocess_all_stream` intact.

Also remove the unused `AuditLog` import if it's only used by the removed methods. Check with grep before deleting:

Run: `cd backend && python -c "
import re
with open('app/services/analytics.py') as f:
    content = f.read()
print('AuditLog usages:', content.count('AuditLog'))
"`

If the count is 1 after your edits (just the import), remove the import line too. Otherwise leave the import.

- [ ] **Step 2: Remove reprocess-failed routes**

In `backend/app/api/routes/analytics.py`, delete these two routes entirely:

- `@router.post("/reprocess-failed")` and its handler (around line 61)
- `@router.post("/reprocess-failed/stream")` and its handler (around line 91)

Keep `/reprocess`, `/reprocess/stream`, and `/pipeline-logs` intact.

- [ ] **Step 3: Verify imports**

Run: `cd backend && python -c "from app.api.routes.analytics import router; from app.services.analytics import AnalyticsService; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/analytics.py backend/app/api/routes/analytics.py
git commit -m "refactor(analytics): remove legacy reprocess_failed endpoints"
```

---

### Task 10: Register retry handlers and cleanup task in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Register the retry handlers during lifespan**

In `backend/app/main.py`, inside the `lifespan` context manager, after the pipeline has been initialized (after `app.state.pipeline = pipeline` and similar lines), add the retry handler registration:

```python
    # Feature 2: register retry handlers for the failure tracking system
    from app.services.pipeline_failures import register_retry_handler
    from app.services.code_indexer import CodeIndexer
    from app.repositories.vector import PostgresVectorRepository

    if pipeline is not None:
        _pipeline_ref = pipeline

        @register_retry_handler("memory_ingest")
        async def _retry_memory(memory_id):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.memory import Memory
            async with async_session_factory() as s:
                mem = (await s.execute(
                    select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
                )).scalar_one_or_none()
                if not mem:
                    return
                entry = {
                    "memory_id": mem.id,
                    "content": mem.content,
                    "source": mem.source,
                    "tags": [t.name for t in mem.tags],
                    "memory_type": mem.memory_type,
                    "created_at": mem.created_at.isoformat() if mem.created_at else "",
                }
            await _pipeline_ref.process_batch([entry])

        @register_retry_handler("code_index")
        async def _retry_code_index(repo_id):
            async with async_session_factory() as s:
                embedding_dims = getattr(app.state, "embedding_dims", settings.embedding_dimensions)
                code_vector_repo = PostgresVectorRepository(s, embedding_dims, "code_chunks")
                active_llm = getattr(app.state, "llm", None)
                indexer = CodeIndexer(s, active_llm, code_vector_repo)
                await indexer.index_repo(repo_id)
                await s.commit()
```

Place this block after `app.state.pipeline = pipeline` and before the `async def periodic_repo_sync()` definition.

- [ ] **Step 2: Add the periodic cleanup task**

In the same `lifespan` function, find the existing `periodic_blocklist_cleanup` task definition. After it, add:

```python
    async def periodic_pipeline_failure_cleanup():
        while True:
            try:
                await asyncio.sleep(3600)
                from app.services.pipeline_failures import PipelineFailureService
                async with async_session_factory() as cleanup_session:
                    svc = PipelineFailureService(cleanup_session)
                    orphaned = await svc.prune_orphans()
                    resolved_pruned = await svc.prune_resolved_older_than(days=30)
                    await cleanup_session.commit()
                logger.info(
                    "Pipeline failure cleanup: orphaned=%s, resolved_pruned=%d",
                    orphaned, resolved_pruned,
                )
            except Exception as e:
                logger.error(f"Pipeline failure cleanup error: {e}")
```

Find the line that spawns `sync_task` and `cleanup_task`. After those, add:

```python
    failure_cleanup_task = asyncio.create_task(periodic_pipeline_failure_cleanup())
```

In the shutdown section (after `yield`), find the existing `sync_task.cancel()` and `cleanup_task.cancel()` lines. Add:

```python
    failure_cleanup_task.cancel()
```

- [ ] **Step 3: Include the new router**

Find the section where routers are included (`app.include_router(...)` calls). Add:

```python
from app.api.routes import pipeline_failures
app.include_router(pipeline_failures.router)
```

Add the import at the top of `main.py` alongside the other route imports, and the `include_router` call alongside the other ones.

- [ ] **Step 4: Verify import**

Run: `cd backend && python -c "from app.main import app; print([r.path for r in app.routes if hasattr(r, 'path') and 'pipeline-failures' in r.path])"`

Expected: Lists the new pipeline-failures routes.

- [ ] **Step 5: Verify retry handlers register on startup**

Run:
```bash
cd backend && python -c "
import asyncio
from app.main import app, lifespan

async def check():
    async with lifespan(app):
        from app.services.pipeline_failures import RETRY_HANDLERS
        print('registered handlers:', list(RETRY_HANDLERS.keys()))

asyncio.run(check())
" 2>&1 | tail -5
```

Expected: `registered handlers: ['memory_ingest', 'code_index']` (plus any startup logs).

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(main): register retry handlers and periodic failure cleanup"
```

---

### Task 11: Frontend WebSocket event types

**Files:**
- Modify: `frontend/src/lib/websocket-events.ts`

- [ ] **Step 1: Add new interfaces and map entries**

Edit `frontend/src/lib/websocket-events.ts`. After the `EnrichmentBatchCompleted` interface and before the `WebSocketEventMap` type, add:

```typescript
export interface PipelineFailureUpdated {
  failure_id: string
  entity_type: string
  entity_id: string
  pipeline_name: string
  state: "recorded" | "resolved" | "forgotten"
  failed_step: string | null
  attempts: number
  error_message: string | null
}

export interface PipelineRetryBatchProgress {
  batch_id: string
  current: number
  total: number
  processed: number
  errors: number
  entity_type: string | null
  entity_id: string | null
  state: "started" | "progress" | "done"
}
```

Then update `WebSocketEventMap` to include the two new event types:

```typescript
export type WebSocketEventMap = {
  "pipeline.completed": PipelineStatus
  "pipeline.partial": PipelineStatus
  "pipeline.failed": PipelineStatus
  "pipeline.failure.updated": PipelineFailureUpdated
  "pipeline.retry_batch.progress": PipelineRetryBatchProgress
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
git commit -m "feat(ui): add pipeline failure event types to WebSocketEventMap"
```

---

### Task 12: Frontend WebSocket hook handles new events

**Files:**
- Modify: `frontend/src/lib/websocket.ts`

- [ ] **Step 1: Add handlers for the two new events**

Edit `frontend/src/lib/websocket.ts`. In the `onmessage` handler inside `useWebSocket`, after the existing `memory.deleted` block and before the `repo.clone_*` block, add:

```typescript
      if (msg.event === "pipeline.failure.updated") {
        void qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
        void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
        const d = msg.data as WebSocketEventMap["pipeline.failure.updated"]
        if (d.state === "resolved") {
          toast.success(`${d.pipeline_name} retry resolved`)
        } else if (d.state === "recorded") {
          void qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
        }
      }

      if (msg.event === "pipeline.retry_batch.progress") {
        const d = msg.data as WebSocketEventMap["pipeline.retry_batch.progress"]
        // Store latest progress in a query cache keyed by batch_id so
        // the pipeline page can read it via useQuery
        qc.setQueryData(["retryBatchProgress", d.batch_id], d)
        if (d.state === "done") {
          void qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
          void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
          void qc.invalidateQueries({ queryKey: ["stats"] })
          void qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
        }
      }
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/websocket.ts
git commit -m "feat(ui): handle pipeline failure and retry batch WebSocket events"
```

---

### Task 13: Frontend API hooks for pipeline failures

**Files:**
- Modify: `frontend/src/hooks/api/use-pipeline-api.ts`

- [ ] **Step 1: Add types and hooks**

Edit `frontend/src/hooks/api/use-pipeline-api.ts`. At the top of the file after the existing `ReprocessProgress` interface, add:

```typescript
export interface PipelineFailure {
  id: string
  entity_type: string
  entity_id: string
  pipeline_name: string
  failed_step: string
  error_message: string | null
  attempts: number
  first_failed_at: string
  last_attempt_at: string
  resolved_at: string | null
  metadata: Record<string, unknown>
  entity_preview: string | null
}

export interface PipelineFailureListResponse {
  items: PipelineFailure[]
  total: number
}
```

Then, at the end of the file, add the new hooks:

```typescript
export function usePipelineFailures(filters?: { entity_type?: string; pipeline_name?: string }) {
  const qs = new URLSearchParams()
  if (filters?.entity_type) qs.set("entity_type", filters.entity_type)
  if (filters?.pipeline_name) qs.set("pipeline_name", filters.pipeline_name)
  const url = `/pipeline-failures${qs.toString() ? `?${qs}` : ""}`
  return useQuery<PipelineFailureListResponse>({
    queryKey: ["pipelineFailures", filters ?? {}],
    queryFn: () => apiFetch<PipelineFailureListResponse>(url),
  })
}

export function usePipelineFailureCounts() {
  return useQuery<Record<string, number>>({
    queryKey: ["pipelineFailureCounts"],
    queryFn: () => apiFetch<Record<string, number>>("/pipeline-failures/counts"),
  })
}

export function useRetryFailure() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ accepted: boolean; failure_id: string }>(
        `/pipeline-failures/${id}/retry`,
        { method: "POST" },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
    },
  })
}

export function useForgetFailure() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/pipeline-failures/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
      qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
    },
  })
}

export function useRetryAllFailures() {
  return useMutation({
    mutationFn: (filters?: { entity_type?: string; pipeline_name?: string }) => {
      const qs = new URLSearchParams()
      if (filters?.entity_type) qs.set("entity_type", filters.entity_type)
      if (filters?.pipeline_name) qs.set("pipeline_name", filters.pipeline_name)
      const url = `/pipeline-failures/retry-all${qs.toString() ? `?${qs}` : ""}`
      return apiFetch<{ accepted: boolean; batch_id: string; total: number }>(url, {
        method: "POST",
      })
    },
  })
}

export function useRetryBatchProgress(batchId: string | null) {
  return useQuery<import("@/lib/websocket-events").PipelineRetryBatchProgress | undefined>({
    queryKey: ["retryBatchProgress", batchId],
    queryFn: () => undefined,
    enabled: false,
    staleTime: Infinity,
  })
}
```

`useRetryBatchProgress` is a passive reader of the cache entry that `useWebSocket` writes to. It never fetches — the data source is WebSocket events via `setQueryData`.

Also remove any references to `useReprocessStream("/analytics/reprocess-failed/stream")` if they exist in other files. Grep first:

Run: `cd frontend && grep -rn "reprocess-failed" src/`

If any results, update those call sites to use `useRetryAllFailures` with `{ pipeline_name: "memory_ingest" }`.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: Either no errors, or only pre-existing ones unrelated to this change.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-pipeline-api.ts
git commit -m "feat(ui): add hooks for pipeline failures list, retry, forget"
```

---

### Task 14: Settings page Unresolved Failures card

**Files:**
- Modify: `frontend/src/routes/_authenticated/pipeline.tsx`
- Modify: `frontend/src/hooks/api/use-pipeline-api.ts` (narrow `useReprocessStream` endpoint type)

- [ ] **Step 1: Add the new card component**

Edit `frontend/src/routes/_authenticated/pipeline.tsx`. Before the `PipelinePage` function definition, add a new component `UnresolvedFailuresCard`:

```tsx
import { useState } from "react"
import {
  usePipelineFailures,
  usePipelineFailureCounts,
  useRetryFailure,
  useForgetFailure,
  useRetryAllFailures,
  useRetryBatchProgress,
} from "@/hooks/api"

type FilterTab = "all" | "memory_ingest" | "code_index"

function UnresolvedFailuresCard() {
  const [filter, setFilter] = useState<FilterTab>("all")
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null)
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set())

  const pipelineName = filter === "all" ? undefined : filter
  const { data: failuresData } = usePipelineFailures({ pipeline_name: pipelineName })
  const { data: counts } = usePipelineFailureCounts()
  const retry = useRetryFailure()
  const forget = useForgetFailure()
  const retryAll = useRetryAllFailures()
  const { data: batchProgress } = useRetryBatchProgress(activeBatchId)

  const totalCount = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : 0
  const memoryCount = counts?.memory_ingest ?? 0
  const codeCount = counts?.code_index ?? 0

  const handleRetry = (id: string) => {
    setRetryingIds((prev) => new Set(prev).add(id))
    retry.mutate(id, {
      onSettled: () => {
        // WebSocket event will trigger a refetch. Also remove local state on error.
      },
      onError: () => {
        setRetryingIds((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        toast.error("Retry failed to dispatch")
      },
    })
  }

  const handleForget = (id: string) => {
    forget.mutate(id, {
      onError: () => toast.error("Forget failed"),
    })
  }

  const handleRetryAll = () => {
    retryAll.mutate(
      filter === "all" ? undefined : { pipeline_name: filter },
      {
        onSuccess: (data) => {
          if (data.total === 0) {
            toast.info("No unresolved failures to retry")
            return
          }
          setActiveBatchId(data.batch_id)
          toast.info(`Retrying ${data.total} failures...`)
        },
        onError: () => toast.error("Bulk retry failed to dispatch"),
      },
    )
  }

  // Auto-clear batch when done
  useEffect(() => {
    if (batchProgress?.state === "done") {
      const timer = setTimeout(() => setActiveBatchId(null), 2000)
      return () => clearTimeout(timer)
    }
  }, [batchProgress?.state])

  const items = failuresData?.items ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Unresolved Failures</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRetryAll}
            disabled={retryAll.isPending || activeBatchId !== null || totalCount === 0}
          >
            {activeBatchId !== null ? "Retrying..." : "Retry all"}
          </Button>
        </div>
        <div className="flex gap-1 mt-3 rounded-md border border-border p-0.5 w-fit">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "all"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setFilter("memory_ingest")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "memory_ingest"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Memory ({memoryCount})
          </button>
          <button
            onClick={() => setFilter("code_index")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "code_index"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Code ({codeCount})
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {batchProgress && activeBatchId !== null && batchProgress.state !== "done" && (
          <div className="mb-4 p-3 border rounded-lg bg-muted/30 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Retrying failures...</span>
              <span className="text-muted-foreground tabular-nums">
                {batchProgress.current} / {batchProgress.total}
              </span>
            </div>
            <Progress value={batchProgress.total > 0 ? (batchProgress.current / batchProgress.total) * 100 : 0} />
            <div className="flex gap-3 text-xs text-muted-foreground">
              <span className="text-green-500">{batchProgress.processed} succeeded</span>
              {batchProgress.errors > 0 && (
                <span className="text-destructive">{batchProgress.errors} failed</span>
              )}
            </div>
          </div>
        )}

        {items.length === 0 && (
          <p className="text-muted-foreground text-sm py-4 text-center">
            No unresolved failures
          </p>
        )}

        {items.length > 0 && (
          <div className="divide-y divide-border rounded-md border border-border">
            {items.map((f) => {
              const isRetrying = retryingIds.has(f.id)
              return (
                <div key={f.id} className="p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Badge variant="outline">{f.entity_type}</Badge>
                      <span className="font-mono text-muted-foreground">{f.failed_step}</span>
                      <span className="text-muted-foreground">· {f.attempts} attempts</span>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRetry(f.id)}
                        disabled={isRetrying || retry.isPending}
                      >
                        {isRetrying ? "Retrying..." : "Retry"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleForget(f.id)}
                        disabled={forget.isPending}
                      >
                        Forget
                      </Button>
                    </div>
                  </div>
                  {f.entity_preview && (
                    <p className="text-sm text-foreground line-clamp-1">{f.entity_preview}</p>
                  )}
                  {f.error_message && (
                    <p className="text-xs text-destructive line-clamp-2">{f.error_message}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Last attempt: {new Date(f.last_attempt_at).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

Make sure `useEffect` is imported at the top of the file if it isn't already:

```tsx
import { useEffect, useRef, useState } from "react"
```

- [ ] **Step 2: Insert the new card into PipelinePage layout**

In the `PipelinePage` function's JSX return, place the `<UnresolvedFailuresCard />` after the action row (Retry Failed / Reprocess All buttons) and before the existing Reprocess progress bars. The layout should look like:

```tsx
  return (
    <div className="p-6">
      <PageHeader title="Pipeline Logs" />

      <div className="flex items-center justify-end gap-2 mb-4">
        {/* existing Retry Failed and Reprocess All buttons */}
      </div>

      <div className="mb-6">
        <UnresolvedFailuresCard />
      </div>

      <ReprocessProgress label="Reprocessing all memories..." stream={reprocessAll} />
      {/* rest unchanged */}
```

Remove the existing `<ReprocessProgress label="Retrying failed memories..." stream={reprocessFailed} />` line since `reprocessFailed` is about to be removed.

- [ ] **Step 3: Remove references to `useReprocessStream("/analytics/reprocess-failed/stream")`**

In the same file, the `PipelinePage` function currently uses:

```tsx
  const reprocessFailed = useReprocessStream("/analytics/reprocess-failed/stream")
```

Remove that line entirely. Also remove:
- The `handleRetryFailed` function
- The `<Button ... onClick={handleRetryFailed}>` for "Retry Failed" (it's now inside `UnresolvedFailuresCard` as "Retry all" scoped to memory)
- The `prevFailedPending` ref and its related `useEffect`
- Any other `reprocessFailed` references
- The `useReprocessStream` type in `use-pipeline-api.ts` should also have its second allowed endpoint (`/analytics/reprocess-failed/stream`) narrowed down to only `/analytics/reprocess/stream`.

For the `useReprocessStream` type change, edit `use-pipeline-api.ts`:

```tsx
export function useReprocessStream(endpoint: "/analytics/reprocess/stream") {
```

(change the literal union from both endpoints to just the one remaining endpoint).

- [ ] **Step 4: Type-check and build**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No errors.

Run: `cd frontend && npx vite build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/_authenticated/pipeline.tsx frontend/src/hooks/api/use-pipeline-api.ts
git commit -m "feat(ui): add Unresolved Failures card to pipeline page"
```

---

### Task 15: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest tests/unit/ -v 2>&1 | tail -30`

Expected: All unit tests pass, including the 14 new `test_pipeline_failures_helpers.py` tests.

- [ ] **Step 2: Restart the backend server**

Ask the user to restart the backend server so the new router and retry handlers are loaded.

- [ ] **Step 3: Verify endpoints respond**

Run these curl tests after the server is restarted (replace with auth cookies as needed):

```bash
# List endpoint should return empty initially
curl -s http://localhost:8000/api/v1/pipeline-failures -b "darkmem_session=<token>" | python -m json.tool

# Counts endpoint should return empty or zero counts
curl -s http://localhost:8000/api/v1/pipeline-failures/counts -b "darkmem_session=<token>" | python -m json.tool
```

Expected: `{"items": [], "total": 0}` and `{}`.

- [ ] **Step 4: Trigger a failure by ingesting a malformed memory**

Create a pipeline failure by temporarily triggering an error. The simplest way: shut down Ollama briefly and try to ingest a memory, which should cause content embedding to fail.

After the failure is recorded, re-query:

```bash
curl -s http://localhost:8000/api/v1/pipeline-failures -b "darkmem_session=<token>" | python -m json.tool
```

Expected: One item with `entity_type: "memory"`, `failed_step: "content_embedding"`.

- [ ] **Step 5: Restart Ollama and retry the failure**

With Ollama running again, POST to the retry endpoint:

```bash
curl -s -X POST http://localhost:8000/api/v1/pipeline-failures/<failure_id>/retry -b "darkmem_session=<token>" | python -m json.tool
```

Expected: `{"accepted": true, "failure_id": "..."}`.

Wait a few seconds for the background task to complete, then list again:

```bash
curl -s http://localhost:8000/api/v1/pipeline-failures -b "darkmem_session=<token>" | python -m json.tool
```

Expected: `{"items": [], "total": 0}` — the retry succeeded and the row was marked resolved.

- [ ] **Step 6: Verify the UI updates in real time**

Open the Pipeline page in the browser. Repeat the failure/retry flow from steps 4-5, watching the UI. The Unresolved Failures card should:
- Appear when the failure is recorded (via `pipeline.failure.updated` WebSocket event)
- Disappear after the retry succeeds (via another `pipeline.failure.updated` event with `state="resolved"`)

If the UI doesn't update, check the browser WebSocket console for the events and the React Query devtools for cache invalidation.

- [ ] **Step 7: Verify bulk retry flow**

Create multiple failures, open the Pipeline page, click "Retry all". The progress bar should appear and fill up as `pipeline.retry_batch.progress` events stream in. When done, the failures list should be empty.
