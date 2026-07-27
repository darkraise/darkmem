"""Missing-fingerprint backfill service.

In the per-fingerprint world, "obsolete" no longer means "wrong fingerprint";
it means "memory/entity/code chunk has no row in the active fingerprint's
table". This service detects and backfills those rows by producing fresh
vectors with the active embedder and inserting into the matching child table.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table
from app.utils.scope_labels import SCOPE_LABEL_COLUMNS, scope_labels

logger = logging.getLogger(__name__)


class ReembedLockSet:
    """Tracks which categories are currently being re-embedded."""

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


reembed_locks = ReembedLockSet()


BroadcastFn = Callable[[str, dict], Awaitable[None]]


def _where(clause: str | None) -> str:
    return f" WHERE {clause}" if clause else ""


class ReembedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _table_exists(self, table: str) -> bool:
        return (
            await self.session.execute(
                text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}
            )
        ).scalar_one_or_none() is not None

    async def _anti_join(self, table: str, anti_join: str) -> str | None:
        """The anti-join selecting rows absent from the active partition, or
        ``None`` when that partition does not exist.

        Until the partition exists (fresh install, or right after an embedder
        rotation), no row is embedded under this fingerprint, so every row is
        'missing' and the anti-join cannot run against a non-existent relation.
        Callers branch on ``None`` rather than substituting a predicate that
        matches every row: the counts are exact either way, but a listing whose
        only filter cannot discriminate would page previews of the whole table.
        """
        return anti_join if await self._table_exists(table) else None

    async def _non_active_code_chunk_tables(self, fingerprint: str) -> list[str]:
        active = child_table("code_chunk_embeddings", fingerprint)
        tables = (await self.session.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename LIKE 'code_chunk_embeddings__%'"
        ))).scalars().all()
        return [t for t in tables if t != active]

    async def _count_missing_code_chunks(self, fingerprint: str) -> int:
        """Distinct logical code chunks present under another fingerprint but
        absent from the active partition.

        Code-chunk content lives only inside the per-fingerprint embedding
        tables, so after a rotation the chunks exist under the old fingerprint
        while the active partition is empty. A logical chunk is keyed by
        ``(repo_id, file_path, line_start, line_end)`` since the row ``id`` is
        regenerated per fingerprint.
        """
        others = await self._non_active_code_chunk_tables(fingerprint)
        if not others:
            return 0
        union = " UNION ALL ".join(
            f"SELECT repo_id, file_path, line_start, line_end FROM {t}" for t in others
        )
        active = child_table("code_chunk_embeddings", fingerprint)
        distinct = f"SELECT DISTINCT repo_id, file_path, line_start, line_end FROM ({union}) u"
        if await self._table_exists(active):
            sql = f"""
                SELECT COUNT(*) FROM ({distinct}) d
                WHERE NOT EXISTS (
                    SELECT 1 FROM {active} a
                    WHERE a.repo_id = d.repo_id AND a.file_path = d.file_path
                      AND a.line_start IS NOT DISTINCT FROM d.line_start
                      AND a.line_end IS NOT DISTINCT FROM d.line_end
                )
            """
        else:
            sql = f"SELECT COUNT(*) FROM ({distinct}) d"
        return int((await self.session.execute(text(sql))).scalar_one())

    # -- counts -------------------------------------------------------------

    async def count_missing(self, fingerprint: str) -> dict[str, int]:
        mem_table = child_table("memory_embeddings", fingerprint)
        ent_table = child_table("entity_embeddings", fingerprint)

        mem_anti = await self._anti_join(
            mem_table, f"NOT EXISTS (SELECT 1 FROM {mem_table} me WHERE me.memory_id = m.id)"
        )
        mem_count = (await self.session.execute(
            text(f"SELECT COUNT(*) FROM memories m{_where(mem_anti)}"),
        )).scalar_one()

        # Code chunks live only inside per-fingerprint tables; after a rotation
        # they sit under the old fingerprint, missing from the active partition.
        chunk_count = await self._count_missing_code_chunks(fingerprint)

        ent_anti = await self._anti_join(
            ent_table, f"NOT EXISTS (SELECT 1 FROM {ent_table} ee WHERE ee.entity_id = e.id)"
        )
        entity_count = (await self.session.execute(
            text(f"SELECT COUNT(*) FROM entities e{_where(ent_anti)}"),
        )).scalar_one()

        return {
            "memories": int(mem_count),
            "code_chunks": int(chunk_count),
            "entities": int(entity_count),
        }

    count_obsolete = count_missing

    # -- listings -----------------------------------------------------------

    async def list_obsolete_memories(
        self,
        fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int, bool]:
        """Memories with no vector in the active partition, newest first.

        Returns ``(items, total, partition_missing)``. When the partition is
        absent every memory is missing from it, so the anti-join cannot single
        any row out; the count stays exact and the enumeration is withheld
        rather than paging a content preview of the entire table under a filter
        that discriminates nothing.

        The queue stays deployment-wide, and every previewed row names its
        project and lifecycle state — that label is what an operator reads a
        foreign or retired row by, and it is the trade the queue makes for
        staying wide instead of being narrowed into hiding unembedded rows.
        """
        mem_table = child_table("memory_embeddings", fingerprint)
        mem_anti = await self._anti_join(
            mem_table, f"NOT EXISTS (SELECT 1 FROM {mem_table} me WHERE me.memory_id = m.id)"
        )
        total = int((await self.session.execute(
            text(f"SELECT COUNT(*) FROM memories m{_where(mem_anti)}"),
        )).scalar_one())

        if mem_anti is None:
            return [], total, True

        rows = (await self.session.execute(
            text(f"""
                SELECT m.id AS memory_id, LEFT(m.content, 120) AS content_preview,
                       {SCOPE_LABEL_COLUMNS}
                FROM memories m
                WHERE {mem_anti}
                ORDER BY m.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )).mappings().all()

        items = [
            {
                "memory_id": str(r["memory_id"]),
                "content_preview": r["content_preview"],
                **scope_labels(r),
            }
            for r in rows
        ]
        return items, total, False

    async def list_obsolete_code_chunks(
        self,
        fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int, bool]:
        active_present = await self._table_exists(
            child_table("code_chunk_embeddings", fingerprint)
        )
        others = await self._non_active_code_chunk_tables(fingerprint)
        if not others:
            return [], 0, not active_present
        total = await self._count_missing_code_chunks(fingerprint)
        union = " UNION ALL ".join(
            f"SELECT repo_id, file_path, symbol_name, line_start, line_end FROM {t}" for t in others
        )
        active = child_table("code_chunk_embeddings", fingerprint)
        not_exists = ""
        if active_present:
            not_exists = f"""
                WHERE NOT EXISTS (
                    SELECT 1 FROM {active} a
                    WHERE a.repo_id = d.repo_id AND a.file_path = d.file_path
                      AND a.line_start IS NOT DISTINCT FROM d.line_start
                      AND a.line_end IS NOT DISTINCT FROM d.line_end
                )
            """
        rows = (await self.session.execute(
            text(f"""
                SELECT DISTINCT d.repo_id, d.file_path, d.symbol_name, d.line_start, d.line_end
                FROM ({union}) d
                {not_exists}
                ORDER BY d.file_path
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )).mappings().all()
        items = [
            {
                "repo_id": str(r["repo_id"]),
                "file_path": r["file_path"],
                "symbol_name": r["symbol_name"],
                "line_start": r["line_start"],
                "line_end": r["line_end"],
            }
            for r in rows
        ]
        return items, total, not active_present

    async def list_obsolete_entities(
        self,
        fingerprint: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int, bool]:
        ent_table = child_table("entity_embeddings", fingerprint)
        ent_anti = await self._anti_join(
            ent_table, f"NOT EXISTS (SELECT 1 FROM {ent_table} ee WHERE ee.entity_id = e.id)"
        )
        total = int((await self.session.execute(
            text(f"SELECT COUNT(*) FROM entities e{_where(ent_anti)}"),
        )).scalar_one())

        if ent_anti is None:
            return [], total, True

        rows = (await self.session.execute(
            text(f"""
                SELECT e.id, e.name, e.entity_type
                FROM entities e
                WHERE {ent_anti}
                ORDER BY e.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )).mappings().all()

        items = [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
            }
            for r in rows
        ]
        return items, total, False

    async def prune_obsolete_cache_entries(self, fingerprint: str) -> int:
        """Drop entity-embedding-cache child tables for retired fingerprints.

        Walks every child of ``entity_embedding_cache`` whose slug does not
        correspond to ``fingerprint``, drops them, and returns the count of
        tables dropped.
        """
        rows = (
            await self.session.execute(
                text(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename LIKE 'entity_embedding_cache__%'
                    """
                )
            )
        ).scalars().all()
        keep = child_table("entity_embedding_cache", fingerprint)
        dropped = 0
        for tbl in rows:
            if tbl == keep:
                continue
            await self.session.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
            dropped += 1
        await self.session.commit()
        return dropped

    # -- backfill -----------------------------------------------------------

    async def reembed_memories(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)

        await self._ensure_partition(llm, current_fingerprint)
        mem_table = child_table("memory_embeddings", current_fingerprint)

        total = (await self.session.execute(
            text(f"""
                SELECT COUNT(*) FROM memories m
                WHERE NOT EXISTS (
                    SELECT 1 FROM {mem_table} me WHERE me.memory_id = m.id
                )
            """),
        )).scalar_one()
        total = int(total)

        await self._broadcast_started(broadcast, batch_id, "memories", total)

        processed = 0
        errors = 0
        last_error: str | None = None
        chunk_size_rows = 100

        while True:
            rows = (await self.session.execute(
                text(f"""
                    SELECT m.id AS memory_id, m.content
                    FROM memories m
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {mem_table} me WHERE me.memory_id = m.id
                    )
                    LIMIT :limit
                """),
                {"limit": chunk_size_rows},
            )).mappings().all()

            if not rows:
                break

            texts = [r["content"] for r in rows]
            try:
                vectors, produced_fp = await llm.embed_batch_chunked(
                    texts, embed_chunk_size, embed_concurrency,
                )
                self._assert_fingerprint(produced_fp, current_fingerprint)
            except Exception as e:
                logger.exception("Re-embed batch failed for memories")
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                await self._broadcast_progress(
                    broadcast, batch_id, "memories",
                    processed + errors, total, processed, errors,
                )
                break

            inserts = [
                {"memory_id": str(r["memory_id"]), "vec": str(vec)}
                for r, vec in zip(rows, vectors)
            ]
            try:
                await self.session.execute(
                    text(f"""
                        INSERT INTO {mem_table} (memory_id, fingerprint, embedding, payload)
                        SELECT v.memory_id::uuid, :fp, v.vec::vector, '{{}}'::jsonb
                        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS v(memory_id text, vec text)
                        ON CONFLICT (memory_id, fingerprint) DO UPDATE
                            SET embedding = EXCLUDED.embedding
                    """),
                    {"fp": current_fingerprint, "rows": json.dumps(inserts)},
                )
                await self.session.commit()
                processed += len(rows)
            except Exception as e:
                logger.exception("Failed to persist re-embedded memories")
                await self.session.rollback()
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                break

            await self._broadcast_progress(
                broadcast, batch_id, "memories",
                processed + errors, total, processed, errors,
            )

        await self._broadcast_done(
            broadcast, batch_id, "memories", total, processed, errors, last_error,
        )
        return {"processed": processed, "errors": errors, "last_error": last_error}

    async def reembed_code_chunks(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        # Cross-fingerprint code-chunk backfill (re-embedding old chunk_content
        # under the active embedder) is not yet implemented. Rather than
        # broadcast a fake success that leaves code search silently degraded,
        # surface the obsolete count and direct the operator to a full reindex,
        # which already rebuilds code embeddings under the active fingerprint.
        total = await self._count_missing_code_chunks(current_fingerprint)
        last_error = (
            "Code-chunk re-embedding across fingerprints is not yet implemented; "
            "run a full repository reindex to rebuild code embeddings under the "
            "active embedder."
        ) if total > 0 else None
        await self._broadcast_started(broadcast, batch_id, "code_chunks", total)
        await self._broadcast_done(
            broadcast, batch_id, "code_chunks", total, 0, total, last_error,
        )
        return {"processed": 0, "errors": total, "last_error": last_error}

    async def reembed_entities(
        self,
        current_fingerprint: str,
        llm,
        batch_id: str,
        broadcast: BroadcastFn | None,
        flags: dict,
    ) -> dict:
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)

        await self._ensure_partition(llm, current_fingerprint)
        ent_table = child_table("entity_embeddings", current_fingerprint)
        cache_table = child_table("entity_embedding_cache", current_fingerprint)

        total = (await self.session.execute(
            text(f"""
                SELECT COUNT(*) FROM entities e
                WHERE NOT EXISTS (
                    SELECT 1 FROM {ent_table} ee WHERE ee.entity_id = e.id
                )
            """),
        )).scalar_one()
        total = int(total)

        await self._broadcast_started(broadcast, batch_id, "entities", total)

        processed = 0
        errors = 0
        last_error: str | None = None
        chunk_size_rows = 100

        while True:
            rows = (await self.session.execute(
                text(f"""
                    SELECT e.id, e.name
                    FROM entities e
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {ent_table} ee WHERE ee.entity_id = e.id
                    )
                    LIMIT :limit
                """),
                {"limit": chunk_size_rows},
            )).mappings().all()

            if not rows:
                break

            texts = [r["name"] for r in rows]
            try:
                vectors, produced_fp = await llm.embed_batch_chunked(
                    texts, embed_chunk_size, embed_concurrency,
                )
                self._assert_fingerprint(produced_fp, current_fingerprint)
            except Exception as e:
                logger.exception("Re-embed batch failed for entities")
                errors += len(rows)
                last_error = f"{type(e).__name__}: {e}"[:500]
                await self._broadcast_progress(
                    broadcast, batch_id, "entities",
                    processed + errors, total, processed, errors,
                )
                break

            inserts = [
                {"id": str(r["id"]), "vec": str(vec)}
                for r, vec in zip(rows, vectors)
            ]
            try:
                await self.session.execute(
                    text(f"""
                        INSERT INTO {ent_table} (entity_id, fingerprint, embedding)
                        SELECT v.id::uuid, :fp, v.vec::vector
                        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS v(id text, vec text)
                        ON CONFLICT (entity_id, fingerprint) DO UPDATE
                            SET embedding = EXCLUDED.embedding
                    """),
                    {"fp": current_fingerprint, "rows": json.dumps(inserts)},
                )

                cache_upserts: dict[str, list[float]] = {}
                for row, vec in zip(rows, vectors):
                    cache_upserts[row["name"].lower()] = vec
                for name_lower, vec in cache_upserts.items():
                    await self.session.execute(
                        text(f"""
                            INSERT INTO {cache_table}
                                (name_lower, fingerprint, embedding, created_at, last_used_at, hit_count)
                            VALUES
                                (:name, :fp, CAST(:vec AS vector), NOW(), NOW(), 1)
                            ON CONFLICT (name_lower, fingerprint) DO UPDATE SET
                                embedding = EXCLUDED.embedding,
                                last_used_at = NOW(),
                                hit_count = {cache_table}.hit_count + 1
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

            await self._broadcast_progress(
                broadcast, batch_id, "entities",
                processed + errors, total, processed, errors,
            )

        await self._broadcast_done(
            broadcast, batch_id, "entities", total, processed, errors, last_error,
        )
        return {"processed": processed, "errors": errors, "last_error": last_error}

    # -- helpers ------------------------------------------------------------

    async def _ensure_partition(self, llm, fingerprint: str) -> None:
        from app.services.embedder_registry import (  # noqa: PLC0415
            EmbedderInfo, embedder_registry, parse_fingerprint,
        )
        if embedder_registry.is_known(fingerprint):
            return
        model_id, dims = parse_fingerprint(fingerprint)
        await embedder_registry.register(
            self.session,
            EmbedderInfo(fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"),
        )

    @staticmethod
    def _assert_fingerprint(produced: str, expected: str) -> None:
        if produced != expected:
            raise RuntimeError(
                f"Re-embed fingerprint mismatch: caller asked for {expected!r}, "
                f"orchestrator produced {produced!r}."
            )

    @staticmethod
    async def _broadcast_started(
        broadcast: BroadcastFn | None, batch_id: str, category: str, total: int,
    ) -> None:
        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": category,
                "current": 0, "total": total, "processed": 0, "errors": 0,
                "state": "started", "error_message": None,
            })

    @staticmethod
    async def _broadcast_progress(
        broadcast: BroadcastFn | None, batch_id: str, category: str,
        current: int, total: int, processed: int, errors: int,
    ) -> None:
        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": category,
                "current": current, "total": total,
                "processed": processed, "errors": errors,
                "state": "progress", "error_message": None,
            })

    @staticmethod
    async def _broadcast_done(
        broadcast: BroadcastFn | None, batch_id: str, category: str,
        total: int, processed: int, errors: int, last_error: str | None,
    ) -> None:
        if broadcast:
            await broadcast("pipeline.reembed_batch.progress", {
                "batch_id": batch_id, "category": category,
                "current": total, "total": total,
                "processed": processed, "errors": errors,
                "state": "done", "error_message": last_error,
            })


async def wait_idle(timeout: float = 30.0) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while reembed_locks._locked and asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.1)
    return not reembed_locks._locked
