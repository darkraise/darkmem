"""The review queue read surface (doc 08 §6, T2.22).

Provides:
  - GET /api/v1/review-queue/facts    — list open (disputed / under-sourced) facts
  - GET /api/v1/review-queue/articles — list open (ungrounded) articles
  - GET /api/v1/review-queue/counts   — cheap totals for both arms
  - POST /api/v1/review-queue/facts/{fact_id}/reject — the one action door

``review_state`` still has no writer on this surface (T2.62 owns its sole,
derived one). See ``app/services/review_queue.py`` for why, and for the
ordering seam T2.24 fills in.

The reject door (T2.63) is the exception to "read-only", and it is an
adjudication verb rather than a queue control: it withdraws belief and journals
a ``human_verdict`` event, touching neither ``verification_status`` nor
``review_state``. It accepts any fact id, queued or not, because doc 17
§5.1's audit counts *corroborated* facts a human later rejected and a
corroborated fact has no opener firing on it — see
``app/services/human_adjudication.py``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.review_queue import (
    ReviewQueueArticleListResponse,
    ReviewQueueCountsResponse,
    ReviewQueueFactListResponse,
    ReviewQueueRejectRequest,
)
from app.services import human_adjudication, review_queue as review_queue_service

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
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return await review_queue_service.counts(session, project=project)


@router.post("/facts/{fact_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_fact(
    fact_id: UUID,
    body: ReviewQueueRejectRequest | None = None,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Record a human rejection of a fact and withdraw belief in it.

    204 rather than a row echo: the verdict's durable record is the journal
    entry, and returning the post-rejection fact would invite a caller to read
    a status this door deliberately does not change.
    """
    try:
        await human_adjudication.reject_fact(
            session,
            fact_id,
            actor=user.sub,
            note=body.note if body else None,
        )
    except human_adjudication.FactNotFound:
        raise HTTPException(status_code=404, detail="Fact not found")
    await session.commit()
