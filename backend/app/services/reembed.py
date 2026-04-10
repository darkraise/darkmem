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
