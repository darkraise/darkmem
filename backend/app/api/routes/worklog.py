"""The work-log lane over REST (spec 2026-09-23 §2).

Every route declares `require_scope`, so a `dmk_` key reaches the verbs its
scope names and a login session reaches all of them. The MCP tools are the
same verbs over the same service; neither door holds logic of its own.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import Principal, require_scope
from app.api.mcp.client_identity import ORIGIN_HEADER, resolve_client_source
from app.database import get_session
from app.schemas.worklog import (
    Kind,
    State,
    WorklogAppendRequest,
    WorklogAppendResponse,
    WorklogEntryListResponse,
    WorklogResumeResponse,
    WorkstreamListResponse,
    WorkstreamOut,
    WorkstreamUpdateRequest,
)
from app.services import worklog
from app.services.checkpoints import resolve_checkpoint_origin

router = APIRouter(prefix="/api/v1/worklog", tags=["worklog"])

# Module-level for the reason `routes/repos.py:31` records: an inline
# require_scope(...) builds a fresh dependency per import, which
# `app.dependency_overrides` cannot address.
_require_capture = require_scope("capture")
_require_read = require_scope("read")
_require_admin = require_scope("admin")


@router.post("/entries", response_model=WorklogAppendResponse, status_code=status.HTTP_201_CREATED)
async def append_entries(
    body: WorklogAppendRequest,
    request: Request,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
):
    source = resolve_client_source(None, headers=request.headers, fallback=worklog.DOOR_SOURCE)
    try:
        run_key = resolve_checkpoint_origin(
            body.run_key or request.headers.get(ORIGIN_HEADER),
            source=source,
            project=body.project,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        result = await worklog.append(
            session,
            project=body.project,
            key=body.workstream,
            run_key=run_key,
            entries=[entry.model_dump() for entry in body.entries],
            title=body.title,
            client=body.client,
            properties=body.properties,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
            expected_last_seq=body.expected_last_seq,
        )
    except worklog.WorklogSeqConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except worklog.WorklogRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = {
        "workstream": worklog.serialize_workstream(result.workstream),
        "entry_ids": [str(entry_id) for entry_id in result.entry_ids],
        "last_seq": result.last_seq,
    }
    await session.commit()
    return payload


@router.get("/resume", response_model=WorklogResumeResponse)
async def resume(
    project: str = Query(min_length=1),
    workstream: str = Query(min_length=1),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    answer = await worklog.resume(session, project=project, key=workstream)
    if answer is None:
        raise HTTPException(status_code=404, detail="No workstream with that key in that project")
    return answer


@router.get("/workstreams", response_model=WorkstreamListResponse)
async def list_workstreams(
    project: str = Query(min_length=1),
    state: State | None = Query(default=None),
    before: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await worklog.list_workstreams(
            session, project=project, state=state, before=before, limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/workstreams/{workstream_id}/entries", response_model=WorklogEntryListResponse)
async def list_entries(
    workstream_id: UUID,
    kind: Kind | None = Query(default=None),
    since: datetime | None = Query(default=None),
    after: int | None = Query(default=None, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    if await worklog.get_workstream_by_id(session, workstream_id) is None:
        raise HTTPException(status_code=404, detail="No such workstream")
    return await worklog.list_entries(
        session, workstream_id=workstream_id, kind=kind, since=since, after=after, limit=limit
    )


@router.patch("/workstreams/{workstream_id}", response_model=WorkstreamOut)
async def update_workstream(
    workstream_id: UUID,
    body: WorkstreamUpdateRequest,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
):
    try:
        workstream = await worklog.update_workstream(
            session,
            workstream_id,
            state=body.state,
            retain=body.retain,
            title=body.title,
            properties=body.properties,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
        )
    except worklog.WorkstreamNotFound as error:
        raise HTTPException(status_code=404, detail="No such workstream") from error
    except worklog.WorklogRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = worklog.serialize_workstream(workstream)
    await session.commit()
    return payload


@router.delete("/workstreams/{workstream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_workstream(
    workstream_id: UUID,
    principal: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        await worklog.purge_workstream(
            session, workstream_id, actor=principal.actor, api_key_id=principal.api_key_id
        )
    except worklog.WorkstreamNotFound as error:
        raise HTTPException(status_code=404, detail="No such workstream") from error
    except worklog.WorklogJournalWriteFailed as error:
        await session.rollback()
        raise HTTPException(status_code=503, detail=str(error)) from error
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
