import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth, require_auth_for_stream
from app.api.deps import (
    AnalyticsServiceDep,
    get_analytics_service_for_stream,
    refuse_when_read_only,
)
from app.database import SessionDep
from app.schemas.config import StatsResponse
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _user=Depends(require_auth),
    service: AnalyticsService = AnalyticsServiceDep,
):
    stats = await service.get_stats()
    return StatsResponse(**stats)


@router.post("/reprocess")
async def reprocess_all_memories(
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    service: AnalyticsService = AnalyticsServiceDep,
):
    result = await service.reprocess_all()
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


async def _sse_generator(stream, session: AsyncSession):
    async for event in stream:
        # Each failure row lands as it is reported, and no read transaction
        # stays open across a run that can last minutes.
        await session.commit()
        yield f"data: {json.dumps(event)}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/reprocess/stream")
async def reprocess_all_stream(
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth_for_stream),
    service: AnalyticsService = Depends(get_analytics_service_for_stream),
) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(service.reprocess_all_stream(), service.session),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/pipeline-logs")
async def get_pipeline_logs(
    limit: int = Query(20, ge=1, le=500),
    project: str | None = Query(None, description="Only runs of memories in this project."),
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
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
            "WHERE event_type = 'extracted' "
            # The pipeline journals each run under its memory's project, so the
            # header scope filters here as it does on the dashboard's feed.
            "AND (CAST(:project AS text) IS NULL OR project = CAST(:project AS text)) "
            "ORDER BY created_at DESC LIMIT :limit"
        ),
        {"limit": limit, "project": project},
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
    service: AnalyticsService = AnalyticsServiceDep,
):
    clamped_days = max(1, min(days, 90))
    return await service.get_overview(clamped_days)
