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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.mcp.client_identity import ORIGIN_HEADER, resolve_client_source
from app.database import get_session
from app.schemas.checkpoint import CheckpointCreate, CheckpointResponse
from app.services import checkpoints as checkpoint_service

router = APIRouter(prefix="/api/v1/checkpoints", tags=["checkpoints"])


@router.post("", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def save_checkpoint(
    body: CheckpointCreate,
    request: Request,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Resolved through doc 05 §2.1's derivation, exactly as capture resolves
    # it, so a run declaring one identity *and one client* to both doors lands
    # on one key. Both halves are load-bearing: the derivation is shared, and
    # each door must feed it the source its own transport declares. A door
    # passing a constant here puts its checkpoints in a key space the other
    # door cannot read.
    source = resolve_client_source(
        None, headers=request.headers, fallback=checkpoint_service.DOOR_SOURCE
    )
    try:
        steps = body.bounded_steps()
        origin_key = checkpoint_service.resolve_checkpoint_origin(
            body.origin_key or request.headers.get(ORIGIN_HEADER),
            source=source,
            project=body.project,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    row = await checkpoint_service.save_checkpoint(
        session,
        origin_key=origin_key,
        summary=body.summary,
        next_steps=steps,
        project=body.project,
        actor=user.sub,
    )
    await session.commit()
    return checkpoint_service.serialize(row)


@router.get("/latest", response_model=CheckpointResponse)
async def latest_checkpoint(
    request: Request,
    origin_key: str | None = Query(default=None),
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
    # Resolved on the read too, or the door could never find what the write
    # stored: the client declares the same raw identity both times and the
    # server derives the same key. The header is honoured on the read for the
    # same reason it is on the write -- a client that mints its run id once at
    # boot and sends it as a header would otherwise be able to save a
    # checkpoint it could never fetch.
    source = resolve_client_source(
        None, headers=request.headers, fallback=checkpoint_service.DOOR_SOURCE
    )
    try:
        resolved = checkpoint_service.resolve_checkpoint_origin(
            origin_key or request.headers.get(ORIGIN_HEADER),
            source=source,
            project=project,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    row = await checkpoint_service.latest_checkpoint(
        session, origin_key=resolved, project=project
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No checkpoint for that origin_key")
    return checkpoint_service.serialize(row)
