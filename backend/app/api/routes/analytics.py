import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text as sa_text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_analytics_service
from app.database import get_session
from app.models.memory import Memory, Tag
from app.repositories.graph import PostgresGraphRepository
from app.schemas.config import StatsResponse
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
    tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
    sources_result = await session.execute(select(Memory.source).distinct())
    sources = [r[0] for r in sources_result.all()]

    entity_count = None
    rel_count = None
    try:
        graph_repo = PostgresGraphRepository(session)
        stats = await graph_repo.get_stats()
        entity_count = stats["entity_count"]
        rel_count = stats["relationship_count"]
    except SQLAlchemyError:
        # An aborted graph COUNT leaves the session in a failed-transaction
        # state; roll back so the response (and any later reuse of this
        # session) doesn't inherit the poison.
        logger.warning("Graph stats unavailable", exc_info=True)
        await session.rollback()

    return StatsResponse(
        memories=memory_count, tags=tag_count,
        entities=entity_count, relationships=rel_count, sources=sources,
    )


@router.post("/reprocess")
async def reprocess_all_memories(
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    result = await service.reprocess_all()
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


async def _sse_generator(stream):
    async for event in stream:
        yield f"data: {json.dumps(event)}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/reprocess/stream")
async def reprocess_all_stream(
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return StreamingResponse(
        _sse_generator(service.reprocess_all_stream()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/pipeline-logs")
async def get_pipeline_logs(
    limit: int = Query(20, ge=1, le=500),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # audit_log was dropped by the baseline; events is the audit substrate
    # (doc 04 §8.1). This used to query event_type='pipeline', a value
    # outside EVENT_TYPES that nothing ever wrote, so the endpoint returned
    # empty forever. 'extracted' is what process_batch actually journals
    # per memory (pipeline.py), one row per memory per batch with the same
    # status dict the pipeline.* broadcast carries, plus 'outcome'
    # (completed/partial/failed) folded in.
    rows = (await session.execute(
        sa_text(
            "SELECT id, object_id, payload, created_at FROM events "
            "WHERE event_type = 'extracted' ORDER BY created_at DESC LIMIT :limit"
        ),
        {"limit": limit},
    )).all()
    return [
        {
            "id": r.id,
            "memory_id": str(r.object_id) if r.object_id else None,
            "details": r.payload,
            "timestamp": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/overview")
async def get_overview(
    days: int = 7,
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    clamped_days = max(1, min(days, 90))
    return await service.get_overview(clamped_days)
