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
                WHERE (model_fingerprint != :fp OR model_fingerprint IS NULL)
                  AND chunk_content IS NOT NULL
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
                WHERE (model_fingerprint != :fp OR model_fingerprint IS NULL)
                  AND chunk_content IS NOT NULL
            """),
            {"fp": current_fingerprint},
        )).scalar_one()

        rows = (await self.session.execute(
            text("""
                SELECT id, file_path, symbol_name, model_fingerprint,
                       LEFT(chunk_content, 120) AS chunk_preview
                FROM code_chunk_embeddings
                WHERE (model_fingerprint != :fp OR model_fingerprint IS NULL)
                  AND chunk_content IS NOT NULL
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
                WHERE (model_fingerprint != :fp OR model_fingerprint IS NULL)
                  AND chunk_content IS NOT NULL
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
