"""/api/v1/pipeline — aggregator + system metrics."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.services import pipeline_aggregator, system_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("")
async def get_pipeline(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return await pipeline_aggregator.build_pipeline_state(session)


@router.get("/metrics")
async def get_metrics(_user=Depends(require_auth)):
    return system_metrics.snapshot()
