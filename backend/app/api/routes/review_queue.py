"""The review queue read surface (doc 08 §6, T2.22).

Provides:
  - GET /api/v1/review-queue/facts    — list open (disputed / under-sourced) facts
  - GET /api/v1/review-queue/articles — list open (ungrounded) articles
  - GET /api/v1/review-queue/counts   — cheap totals for both arms

Read-only by design: ``review_state`` has no writer on this surface. See
``app/services/review_queue.py`` for why, and for the ordering seam T2.24
fills in.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.review_queue import (
    ReviewQueueArticleListResponse,
    ReviewQueueCountsResponse,
    ReviewQueueFactListResponse,
)
from app.services import review_queue as review_queue_service

router = APIRouter(prefix="/api/v1/review-queue", tags=["review-queue"])


@router.get("/facts", response_model=ReviewQueueFactListResponse)
async def list_facts(
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await review_queue_service.list_open_facts(
        session, project=project, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/articles", response_model=ReviewQueueArticleListResponse)
async def list_articles(
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await review_queue_service.list_open_articles(
        session, project=project, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/counts", response_model=ReviewQueueCountsResponse)
async def counts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return await review_queue_service.counts(session)
