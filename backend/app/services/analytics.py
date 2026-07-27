import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline_failure import PipelineFailure
from app.models.memory import Memory, Tag, memory_tags
from app.repositories.relational import PostgresAuditRepository
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline: ProcessingPipeline | None = None,
        graph_repo=None,
    ):
        self.session = session
        self.audit_repo = PostgresAuditRepository(session)
        self.pipeline = pipeline
        self.graph_repo = graph_repo

    async def reprocess_all(self) -> dict:
        if not self.pipeline:
            return {"error": "Pipeline not available", "processed": 0}

        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
        result = await self.session.execute(stmt)
        memories = list(result.scalars().all())

        return await self._reprocess_batch(memories)

    async def _reprocess_batch(self, memories: list[Memory]) -> dict:
        batch_entries = [
            {
                "memory_id": m.id,
                "content": m.content,
                "source": m.source,
                "tags": [t.name for t in m.tags],
                "memory_type": m.memory_type,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ]

        statuses = await self.pipeline.process_batch(batch_entries)

        processed = 0
        errors = 0
        for status in statuses:
            mid = status.get("memory_id")
            if status.get("error"):
                errors += 1
            else:
                processed += 1
            try:
                from uuid import UUID
                await self.audit_repo.log("pipeline", UUID(mid) if mid else None, None, status)
            except Exception as e:
                logger.warning("Audit log failed: %s", e)

        return {"processed": processed, "errors": errors, "total": len(memories)}

    async def reprocess_all_stream(self):
        if not self.pipeline:
            yield {"type": "error", "message": "Pipeline not available"}
            return

        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
        result = await self.session.execute(stmt)
        memories = list(result.scalars().all())

        async for event in self._reprocess_batch_stream(memories):
            yield event

    async def _reprocess_batch_stream(self, memories: list[Memory]):
        import asyncio
        from app.services.pipeline import _get_feature_flags

        total = len(memories)
        if total == 0:
            yield {"type": "done", "processed": 0, "errors": 0, "total": 0}
            return

        flags = await _get_feature_flags(self.pipeline.session_factory)
        concurrency = flags.get("pipeline_concurrency", 5)
        semaphore = asyncio.Semaphore(concurrency)

        yield {"type": "start", "total": total}

        processed = 0
        errors = 0
        completed_count = 0
        results_queue: asyncio.Queue = asyncio.Queue()

        async def _process_one(memory: Memory):
            async with semaphore:
                status_label = "ok"
                status = {}
                try:
                    status = await self.pipeline.process_memory(
                        memory_id=memory.id,
                        content=memory.content,
                        source=memory.source,
                        tags=[t.name for t in memory.tags],
                        memory_type=memory.memory_type,
                        created_at=memory.created_at.isoformat(),
                    )
                    if status.get("error"):
                        status_label = "error"
                except Exception as e:
                    status_label = "error"
                    logger.error(f"Reprocess failed for {memory.id}: {e}")
                finally:
                    await results_queue.put((memory.id, status_label, status))

        tasks = [asyncio.create_task(_process_one(m)) for m in memories]

        try:
            while completed_count < total:
                try:
                    memory_id, status_label, status = await asyncio.wait_for(
                        results_queue.get(), timeout=30.0,
                    )
                except asyncio.TimeoutError:
                    # A producer cancelled before its `finally` ran (e.g. the SSE
                    # client disconnected) never puts. If every task has finished,
                    # stop waiting for puts that aren't coming instead of blocking
                    # on results_queue.get() forever.
                    if all(t.done() for t in tasks):
                        break
                    continue
                completed_count += 1
                if status_label == "error":
                    errors += 1
                else:
                    processed += 1

                try:
                    await self.audit_repo.log("pipeline", memory_id, None, status if isinstance(status, dict) else {})
                except Exception as e:
                    logger.warning("Audit log failed: %s", e)

                yield {
                    "type": "progress",
                    "current": completed_count,
                    "total": total,
                    "memory_id": str(memory_id),
                    "status": status_label,
                    "processed": processed,
                    "errors": errors,
                }

            await asyncio.gather(*tasks, return_exceptions=True)
            yield {"type": "done", "processed": processed, "errors": errors, "total": total}
        finally:
            # On normal completion these are all done; on client disconnect
            # (GeneratorExit raised at a yield) cancel the stragglers so they
            # don't keep running detached, draining into a queue nobody reads.
            for t in tasks:
                if not t.done():
                    t.cancel()

    async def get_overview(self, days: int = 7) -> dict:
        # Counts
        memory_count = (await self.session.execute(
            select(func.count()).select_from(Memory).where(Memory.is_archived == False)  # noqa: E712
        )).scalar() or 0
        tag_count = (await self.session.execute(
            select(func.count()).select_from(Tag)
        )).scalar() or 0

        entity_count = None
        rel_count = None
        if self.graph_repo:
            try:
                stats = await self.graph_repo.get_stats()
                entity_count = stats["entity_count"]
                rel_count = stats["relationship_count"]
            except Exception:
                logger.debug("Graph stats unavailable")

        # Activity
        since = date.today() - timedelta(days=days - 1)
        activity_stmt = (
            select(
                func.date(Memory.created_at).label("day"),
                func.count().label("count"),
            )
            .where(Memory.created_at >= since)
            .group_by(func.date(Memory.created_at))
            .order_by(func.date(Memory.created_at))
        )
        activity_rows = (await self.session.execute(activity_stmt)).all()
        activity = [{"date": str(r.day), "count": r.count} for r in activity_rows]

        # Sources breakdown
        source_stmt = (
            select(Memory.source, func.count().label("count"))
            .where(Memory.is_archived == False)  # noqa: E712
            .group_by(Memory.source)
            .order_by(func.count().desc())
        )
        source_rows = (await self.session.execute(source_stmt)).all()
        sources = [{"name": r.source, "count": r.count} for r in source_rows]

        # Top tags
        tag_stmt = (
            select(Tag.name, func.count(memory_tags.c.memory_id).label("count"))
            .outerjoin(memory_tags)
            .group_by(Tag.name)
            .order_by(func.count(memory_tags.c.memory_id).desc())
            .limit(5)
        )
        tag_rows = (await self.session.execute(tag_stmt)).all()
        top_tags = [{"name": r.name, "count": r.count} for r in tag_rows]

        # Recent memories
        mem_stmt = (
            select(Memory)
            .options(selectinload(Memory.tags))
            .where(Memory.is_archived == False)  # noqa: E712
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        mem_rows = (await self.session.execute(mem_stmt)).scalars().all()
        # Deliberately deployment-wide, like every other number on this
        # dashboard, so the rows carry the scope they came from instead of
        # being narrowed: a superseded row is part of what recently happened,
        # and it is honest only while it says so.
        recent_memories = [
            {
                "id": str(m.id),
                "content": m.content,
                "source": m.source,
                "memory_type": m.memory_type,
                "project": m.project,
                "status": m.status,
                "tags": [t.name for t in m.tags],
                "created_at": m.created_at.isoformat(),
            }
            for m in mem_rows
        ]

        # Unresolved pipeline failures are the honest count: pipeline_failures
        # is the per-memory failure substrate (invariant 14), which is a
        # stricter source than counting audit rows that merely carried an
        # error detail. audit_log itself is dropped by the baseline.
        error_stmt = (
            select(func.count())
            .select_from(PipelineFailure)
            .where(PipelineFailure.resolved_at.is_(None))
        )
        recent_errors = (await self.session.execute(error_stmt)).scalar() or 0

        return {
            "counts": {
                "memories": memory_count,
                "tags": tag_count,
                "entities": entity_count,
                "relationships": rel_count,
            },
            "activity": activity,
            "sources": sources,
            "top_tags": top_tags,
            "recent_memories": recent_memories,
            "recent_errors": recent_errors,
        }
