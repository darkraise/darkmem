"""Events read API (T1.08).

Three GET shapes over the durable, append-only `events` table (doc 04 §8.1,
doc 12 §7): a filtered list, a per-UTC-day calendar, and a per-object
timeline. `events` is append-only and journaled only by services through
`record_event` — there is no POST/PUT/DELETE here, and per doc 12 §7 there
never will be (single-door REST, no MCP twin: an observability surface for
the human curator, not an agent capability).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.event_log import (
    EventCalendarResponse,
    EventListResponse,
    EventTimelineResponse,
)
from app.services.events import calendar_counts, list_events, object_timeline

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def get_events(
    object_type: str | None = None,
    object_id: UUID | None = None,
    project: str | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_events(
        session,
        object_type=object_type,
        object_id=object_id,
        project=project,
        event_type=event_type,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}


@router.get("/calendar", response_model=EventCalendarResponse)
async def get_events_calendar(
    project: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    buckets = await calendar_counts(session, project=project, since=since, until=until)
    return {"buckets": buckets}


@router.get("/timeline", response_model=EventTimelineResponse)
async def get_events_timeline(
    object_type: str,
    object_id: UUID,
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await object_timeline(
        session,
        object_type=object_type,
        object_id=object_id,
        project=project,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}
