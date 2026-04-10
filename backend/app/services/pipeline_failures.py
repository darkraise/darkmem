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
        row_raw = result.mappings().one_or_none()
        if row_raw is None:
            logger.error(
                "PipelineFailureService.record returned no row for (%s, %s, %s)",
                entity_type, entity_id, pipeline_name,
            )
            raise RuntimeError(
                f"Failed to upsert pipeline failure for {entity_type}/{entity_id}/{pipeline_name}"
            )
        row = row_raw
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

    async def forget_by_id(self, failure_id: UUID) -> dict | None:
        """Hard-delete a specific failure row by primary key.

        Returns the deleted row's payload (for broadcasting) or None if
        no row was found.
        """
        result = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE id = CAST(:id AS uuid)
                RETURNING id, entity_type, entity_id, pipeline_name
            """),
            {"id": str(failure_id)},
        )
        row = result.mappings().first()
        if not row:
            return None
        payload = {
            "id": str(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": str(row["entity_id"]),
            "pipeline_name": row["pipeline_name"],
        }
        if self._broadcast:
            try:
                await self._broadcast("pipeline.failure.updated", {
                    "failure_id": payload["id"],
                    "entity_type": payload["entity_type"],
                    "entity_id": payload["entity_id"],
                    "pipeline_name": payload["pipeline_name"],
                    "state": "forgotten",
                    "failed_step": None,
                    "attempts": 0,
                    "error_message": None,
                })
            except Exception as e:
                logger.warning("failure.updated broadcast failed: %s", e)
        return payload

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
            """)
        )
        counts["memory"] = mem_del.rowcount or 0

        repo_del = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE entity_type = 'code_repo'
                  AND NOT EXISTS (SELECT 1 FROM repositories WHERE repositories.id = pipeline_failures.entity_id)
            """)
        )
        counts["code_repo"] = repo_del.rowcount or 0

        return counts

    async def prune_resolved_older_than(self, days: int = 30) -> int:
        """Delete resolved rows older than N days."""
        result = await self.session.execute(
            text("""
                DELETE FROM pipeline_failures
                WHERE resolved_at IS NOT NULL
                  AND resolved_at < NOW() - make_interval(days => :days)
            """),
            {"days": days},
        )
        return result.rowcount or 0

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
