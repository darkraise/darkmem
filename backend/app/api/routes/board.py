"""The progress board's REST door (spec 2026-10-13 §2.2).

Provides:
  - GET    /api/v1/board/records
  - PATCH  /api/v1/board/registers/{document_id}/rows/{number}

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused.
Refusals raise `BoardRefusal`, which `app.main` answers with `error.code` set
to the refusal's reason.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import TokenPayload, require_auth
from app.database import get_session
from app.schemas.board import (
    BoardRecordsResponse,
    RegisterRowEditRequest,
    RegisterRowEditResponse,
)
from app.services.board import board_version, load_board
from app.services.board_edit import edit_register_row

router = APIRouter(prefix="/api/v1/board", tags=["board"])

# Revalidate on every read: the browser sends If-None-Match by itself and a
# 304 costs two aggregates instead of a parse of every register and plan.
_CACHE_CONTROL = "private, no-cache"


def _matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    tags = [tag.strip() for tag in header.split(",")]
    return "*" in tags or etag in tags or etag.removeprefix("W/") in tags


@router.get("/records", response_model=BoardRecordsResponse)
async def board_records_route(
    request: Request,
    response: Response,
    project: str = Query(..., min_length=1),
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every register row and plan task of `project`, derived on read."""
    etag = f'W/"{await board_version(session, project)}"'
    headers = {"ETag": etag, "Cache-Control": _CACHE_CONTROL}
    if _matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return BoardRecordsResponse(**await load_board(session, project))


@router.patch(
    "/registers/{document_id}/rows/{number}", response_model=RegisterRowEditResponse,
)
async def edit_register_row_route(
    document_id: UUID,
    number: int,
    body: RegisterRowEditRequest,
    user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> RegisterRowEditResponse:
    """Edit one register row's state, note or assigned, as a document revision."""
    changes = {
        column: value
        for column, value in (("state", body.state), ("note", body.note), ("assigned", body.assigned))
        if value is not None
    }
    result = await edit_register_row(
        session,
        document_id=str(document_id),
        number=number,
        expected_hash=body.expected_hash,
        changes=changes,
        actor=user.sub,
    )
    return RegisterRowEditResponse(**result)
