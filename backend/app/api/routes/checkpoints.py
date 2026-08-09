"""Session checkpoints over REST (T3.16).

Provides:
  - POST /api/v1/checkpoints                 — save one (201)
  - GET  /api/v1/checkpoints/latest          — the newest for one origin

The MCP half (`checkpoint_save` / `checkpoint_latest`) is the same two verbs
over the same service. Neither door holds logic of its own: invariant 17 asks
for parity, and parity that has to be maintained in two implementations is
parity that lapses on the first change to one of them.

201 rather than 202: the write is synchronous and complete when the response
is written, so there is no queued work for an ack to describe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.checkpoint import CheckpointCreate, CheckpointResponse
from app.services import checkpoints as checkpoint_service

router = APIRouter(prefix="/api/v1/checkpoints", tags=["checkpoints"])


@router.post("", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def save_checkpoint(
    body: CheckpointCreate,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    try:
        steps = body.bounded_steps()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    row = await checkpoint_service.save_checkpoint(
        session,
        origin_key=body.origin_key,
        summary=body.summary,
        next_steps=steps,
        project=body.project,
        actor=getattr(user, "username", None) if user else None,
    )
    await session.commit()
    return checkpoint_service.serialize(row)


@router.get("/latest", response_model=CheckpointResponse)
async def latest_checkpoint(
    origin_key: str = Query(min_length=1),
    project: str = Query(default="default"),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """404 when the run has no checkpoint.

    Not an empty 200: "this run saved nothing" and "this run's note is empty"
    are different answers, and the resume path branches on exactly that —
    a missing checkpoint degrades to the ordinary inject (T3.17), an empty one
    does not.
    """
    row = await checkpoint_service.latest_checkpoint(
        session, origin_key=origin_key, project=project
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No checkpoint for that origin_key")
    return checkpoint_service.serialize(row)
