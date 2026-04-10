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
