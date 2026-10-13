"""The progress board's REST door (spec 2026-10-13 §2.2).

Provides:
  - GET    /api/v1/board/records
  - PATCH  /api/v1/board/registers/{document_id}/rows/{number}
  - GET    /api/v1/board/views
  - POST   /api/v1/board/views
  - PATCH  /api/v1/board/views/{view_id}
  - DELETE /api/v1/board/views/{view_id}

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused.
Refusals raise `BoardRefusal`, which `app.main` answers with `error.code` set
to the refusal's reason.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import TokenPayload, require_auth
from app.database import get_session
from app.schemas.board import (
    BoardRecordsResponse,
    BoardView,
    BoardViewCreateRequest,
    BoardViewUpdateRequest,
    RegisterRowEditRequest,
    RegisterRowEditResponse,
)
from app.services.board import board_version, load_board
from app.services.board_edit import edit_register_row
from app.services.board_views import create_view, delete_view, list_views, update_view

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


@router.get("/views", response_model=list[BoardView])
async def list_views_route(
    project: str = Query(..., min_length=1),
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[BoardView]:
    """The two built-in views, then the project's saved views by (position, name)."""
    return [BoardView(**view) for view in await list_views(session, project)]


@router.post("/views", response_model=BoardView, status_code=status.HTTP_201_CREATED)
async def create_view_route(
    body: BoardViewCreateRequest,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> BoardView:
    return BoardView(**await create_view(
        session, project=body.project, name=body.name,
        definition=body.definition, position=body.position,
    ))


@router.patch("/views/{view_id}", response_model=BoardView)
async def update_view_route(
    view_id: str,
    body: BoardViewUpdateRequest,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> BoardView:
    # An explicit null changes nothing: every column it could name is NOT NULL.
    changes = {
        field: getattr(body, field)
        for field in body.model_fields_set
        if getattr(body, field) is not None
    }
    return BoardView(**await update_view(session, view_id, changes=changes))


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_view_route(
    view_id: str,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_view(session, view_id)
