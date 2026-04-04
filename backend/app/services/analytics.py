import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.memory import Memory
from app.repositories.relational import PostgresAuditRepository
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline: ProcessingPipeline | None = None,
    ):
        self.session = session
        self.audit_repo = PostgresAuditRepository(session)
        self.pipeline = pipeline

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
