"""The `memory_buffer` read and triage API (T1.13b, doc 05 §3.1, doc 13 §6.1).

Two GETs over the state the Tier-B flush produces — a filtered list and the
per-state counts — plus the two actions that make a poison row actionable:
requeue it to `pending` with a clean ladder, or discard it. Both journal to
`events`, so a row that leaves the buffer by a human decision leaves a record
behind it.

**REST single door, no MCP twin**, the same reason the `events` read surface
carries (doc 12 §7): this is an operator's view of the ingest tier's own
plumbing — claim leases, attempt counts, worker identities — not an agent
capability. An agent has no use for another agent's stalled claim, and exposing
a delete over buffered captures to the MCP door would put an unauthenticated
local surface in front of the triage queue. Recorded here for T1.42d's parity
audit; if a monitor client ever needs it over MCP, the tools call
`app.services.buffer_monitor` rather than growing a second implementation.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_memory_service
from app.database import get_session
from app.schemas.buffer import (
    BufferListResponse,
    BufferRowResponse,
    BufferStatsResponse,
)
from app.services import buffer_monitor
from app.services.buffer_monitor import BufferState
from app.services.memory import MemoryService

router = APIRouter(prefix="/api/v1/memory-buffer", tags=["memory-buffer"])


@router.get("", response_model=BufferListResponse)
async def list_buffer_rows(
    state: BufferState | None = None,
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    rows, total, _ = await buffer_monitor.list_rows(
        session, state=state, project=project, limit=limit, offset=offset,
    )
    return BufferListResponse(
        items=[BufferRowResponse(**row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=BufferStatsResponse)
async def buffer_stats(
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return BufferStatsResponse(**await buffer_monitor.stats(session, project=project))


@router.post("/{buffer_id}/requeue", response_model=BufferRowResponse)
async def requeue_buffer_row(
    buffer_id: UUID,
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    try:
        row = await buffer_monitor.requeue(session, buffer_id, project=project)
    except buffer_monitor.BufferRowNotFound:
        raise HTTPException(status_code=404, detail="Buffer row not found")
    except buffer_monitor.BufferRowNotActionable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"only a poison row can be requeued; this one is {exc}",
        )
    await session.commit()
    return BufferRowResponse(**row)


@router.delete("/{buffer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_buffer_row(
    buffer_id: UUID,
    project: str | None = None,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Discard a poison row, and the memory its replay materialised.

    `X-Memory-Deleted` says whether that memory existed and was deleted with
    the row.
    """
    try:
        memory_deleted = await buffer_monitor.discard(
            session, buffer_id, memory_service, project=project, actor=user.sub,
        )
    except buffer_monitor.BufferRowNotFound:
        raise HTTPException(status_code=404, detail="Buffer row not found")
    except buffer_monitor.BufferRowNotActionable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"only a poison row can be discarded; this one is {exc}",
        )
    await session.commit()
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"X-Memory-Deleted": "true" if memory_deleted else "false"},
    )
