import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_analytics_service
from app.database import get_session
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag
from app.schemas.config import StatsResponse
from app.services.analytics import AnalyticsService

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
            logger.debug("Graph stats unavailable")

    return StatsResponse(
        memories=memory_count, tags=tag_count,
        entities=entity_count, relationships=rel_count, sources=sources,
    )


@router.post("/reprocess")
async def reprocess_all_memories(
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.reprocess_all()


@router.post("/reprocess-failed")
async def reprocess_failed_memories(
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.reprocess_failed()


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
