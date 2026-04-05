import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
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

    async def reprocess_failed(self) -> dict:
        if not self.pipeline:
            return {"error": "Pipeline not available", "processed": 0}

        stmt = (
            select(AuditLog.memory_id)
            .where(AuditLog.action == "pipeline")
            .where(AuditLog.details["error"].as_string() != "null")
            .where(AuditLog.memory_id.isnot(None))
            .distinct()
        )
        result = await self.session.execute(stmt)
        failed_ids = [r[0] for r in result.all()]

        if not failed_ids:
            return {"processed": 0, "errors": 0, "total": 0}

        memories = []
        for mid in failed_ids:
            mem_result = await self.session.execute(
                select(Memory).options(selectinload(Memory.tags)).where(Memory.id == mid)
            )
            memory = mem_result.scalar_one_or_none()
            if memory and not memory.is_archived:
                memories.append(memory)

        return await self._reprocess_batch(memories)

    async def _reprocess_batch(self, memories: list[Memory]) -> dict:
        processed = 0
        errors = 0
        for memory in memories:
            try:
                status = await self.pipeline.process_memory(
                    memory_id=memory.id,
                    content=memory.content,
                    source=memory.source,
                    tags=[t.name for t in memory.tags],
                    memory_type=memory.memory_type,
                    created_at=memory.created_at.isoformat(),
                )
                await self.audit_repo.log("pipeline", memory.id, None, status)
                if status.get("error"):
                    errors += 1
                else:
                    processed += 1
                logger.info(f"Reprocessed {memory.id}")
            except Exception as e:
                errors += 1
                logger.error(f"Reprocess failed for {memory.id}: {e}")

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

    async def reprocess_failed_stream(self):
        if not self.pipeline:
            yield {"type": "error", "message": "Pipeline not available"}
            return

        stmt = (
            select(AuditLog.memory_id)
            .where(AuditLog.action == "pipeline")
            .where(AuditLog.details["error"].as_string() != "null")
            .where(AuditLog.memory_id.isnot(None))
            .distinct()
        )
        result = await self.session.execute(stmt)
        failed_ids = [r[0] for r in result.all()]

        if not failed_ids:
            yield {"type": "done", "processed": 0, "errors": 0, "total": 0}
            return

        memories = []
        for mid in failed_ids:
            mem_result = await self.session.execute(
                select(Memory).options(selectinload(Memory.tags)).where(Memory.id == mid)
            )
            memory = mem_result.scalar_one_or_none()
            if memory and not memory.is_archived:
                memories.append(memory)

        async for event in self._reprocess_batch_stream(memories):
            yield event

    async def _reprocess_batch_stream(self, memories: list[Memory]):
        total = len(memories)
        if total == 0:
            yield {"type": "done", "processed": 0, "errors": 0, "total": 0}
            return

        processed = 0
        errors = 0
        yield {"type": "start", "total": total}

        for i, memory in enumerate(memories):
            status_label = "ok"
            try:
                status = await self.pipeline.process_memory(
                    memory_id=memory.id,
                    content=memory.content,
                    source=memory.source,
                    tags=[t.name for t in memory.tags],
                    memory_type=memory.memory_type,
                    created_at=memory.created_at.isoformat(),
                )
                await self.audit_repo.log("pipeline", memory.id, None, status)
                if status.get("error"):
                    errors += 1
                    status_label = "error"
                else:
                    processed += 1
                logger.info(f"Reprocessed {memory.id}")
            except Exception as e:
                errors += 1
                status_label = "error"
                logger.error(f"Reprocess failed for {memory.id}: {e}")

            yield {
                "type": "progress",
                "current": i + 1,
                "total": total,
                "memory_id": str(memory.id),
                "status": status_label,
                "processed": processed,
                "errors": errors,
            }

        yield {"type": "done", "processed": processed, "errors": errors, "total": total}

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
        recent_memories = [
            {
                "id": str(m.id),
                "content": m.content,
                "source": m.source,
                "memory_type": m.memory_type,
                "tags": [t.name for t in m.tags],
                "created_at": m.created_at.isoformat(),
            }
            for m in mem_rows
        ]

        # Recent pipeline errors
        error_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "pipeline")
            .where(AuditLog.details["error"].as_string() != "null")
            .where(AuditLog.details["error"].as_string().isnot(None))
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
