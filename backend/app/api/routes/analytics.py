import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import require_auth
from app.database import get_session
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag
from app.schemas.config import StatsResponse
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
    tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
    sources_result = await session.execute(select(Memory.source).distinct())
    sources = [r[0] for r in sources_result.all()]

    entity_count = None
    rel_count = None
    graph_repo = getattr(request.app.state, "graph_repo", None) if request else None
    if graph_repo:
        try:
            stats = await graph_repo.get_stats()
            entity_count = stats["entity_count"]
            rel_count = stats["relationship_count"]
        except Exception:
            pass

    return StatsResponse(
        memories=memory_count, tags=tag_count,
        entities=entity_count, relationships=rel_count, sources=sources,
    )


@router.post("/reprocess")
async def reprocess_all_memories(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    pipeline: ProcessingPipeline | None = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        return {"error": "Pipeline not available", "processed": 0}

    stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
    result = await session.execute(stmt)
    memories = result.scalars().all()

    from app.repositories.relational import PostgresAuditRepository
    audit = PostgresAuditRepository(session)

    processed = 0
    errors = 0
    for memory in memories:
        try:
            status = await pipeline.process_memory(
                memory_id=memory.id,
                content=memory.content,
                source=memory.source,
                tags=[t.name for t in memory.tags],
                memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            )
            await audit.log("pipeline", memory.id, None, status)
            if status.get("error"):
                errors += 1
            else:
                processed += 1
            logger.info(f"Reprocessed {memory.id}")
        except Exception as e:
            errors += 1
            logger.error(f"Reprocess failed for {memory.id}: {e}")

    await session.commit()
    return {"processed": processed, "errors": errors, "total": len(memories)}


@router.post("/reprocess-failed")
async def reprocess_failed_memories(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    pipeline: ProcessingPipeline | None = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        return {"error": "Pipeline not available", "processed": 0}

    # Find memory_ids with errors in pipeline logs
    stmt = (
        select(AuditLog.memory_id)
        .where(AuditLog.action == "pipeline")
        .where(AuditLog.details["error"].as_string() != "null")
        .where(AuditLog.memory_id.isnot(None))
        .distinct()
    )
    result = await session.execute(stmt)
    failed_ids = [r[0] for r in result.all()]

    if not failed_ids:
        return {"processed": 0, "errors": 0, "total": 0}

    processed = 0
    errors = 0
    for mid in failed_ids:
        mem_result = await session.execute(
            select(Memory).options(selectinload(Memory.tags)).where(Memory.id == mid)
        )
        memory = mem_result.scalar_one_or_none()
        if not memory or memory.is_archived:
            continue
        try:
            status = await pipeline.process_memory(
                memory_id=memory.id, content=memory.content, source=memory.source,
                tags=[t.name for t in memory.tags], memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            )
            from app.repositories.relational import PostgresAuditRepository
            audit = PostgresAuditRepository(session)
            await audit.log("pipeline", memory.id, None, status)
            processed += 1
        except Exception as e:
            errors += 1
            logger.error(f"Retry failed for {memory.id}: {e}")

    await session.commit()
    return {"processed": processed, "errors": errors, "total": len(failed_ids)}


@router.get("/pipeline-logs")
async def get_pipeline_logs(
    limit: int = 20,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "pipeline")
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "memory_id": str(log.memory_id) if log.memory_id else None,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
