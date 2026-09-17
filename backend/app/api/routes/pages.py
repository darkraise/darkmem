"""The page tree's REST door.

Provides:
  - POST   /api/v1/pages
  - GET    /api/v1/pages
  - POST   /api/v1/pages/trash/empty
  - GET    /api/v1/pages/{page_id}
  - PATCH  /api/v1/pages/{page_id}
  - DELETE /api/v1/pages/{page_id}
  - POST   /api/v1/pages/{page_id}/restore

REST-only: no MCP tool serves pages. Every `page_door` writer commits itself,
and a refusal leaves the request's transaction for the session dependency to
end, so no handler touches the session after catching one.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_llm
from app.database import get_session
from app.schemas.page import (
    PageCreateRequest,
    PageCreateResponse,
    PageListItem,
    PagePatchRequest,
    PagePatchResponse,
    PageResponse,
    PageRestoreResponse,
    PageTrashEmptyResponse,
)
from app.services.page_door import (
    PageCycleError,
    PageParentTrashed,
    PageTargetUnresolved,
    PageTooLarge,
    create_page,
    delete_page,
    get_page,
    list_pages,
    move_page,
    purge_trash,
    rename_page,
    restore_page,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])


def _page_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PageTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, (PageCycleError, PageTooLarge)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, PageParentTrashed):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise exc


_REFUSALS = (PageTargetUnresolved, PageCycleError, PageTooLarge, PageParentTrashed)


def _str(value: UUID | None) -> str | None:
    return None if value is None else str(value)


@router.post("", response_model=PageCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_page_route(
    body: PageCreateRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageCreateResponse:
    try:
        result = await create_page(
            session, llm,
            project=body.project,
            title=body.title,
            parent_id=_str(body.parent_id),
            after_id=_str(body.after_id),
            content=body.content,
            properties=body.properties,
        )
    except _REFUSALS as exc:
        raise _page_write_error(exc) from exc
    return PageCreateResponse(**vars(result))


@router.get("", response_model=list[PageListItem])
async def list_pages_route(
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[PageListItem]:
    """Every live page in `project`, flat.

    Rows are ordered by `(parent_id, order_index)` with `NULL` parents last,
    so the list carries no parent-before-child guarantee and children of
    different parents interleave; the client nests by `parent_id`.
    """
    return [PageListItem(**row) for row in await list_pages(session, project)]


@router.post("/trash/empty", response_model=PageTrashEmptyResponse)
async def empty_trash_route(
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> PageTrashEmptyResponse:
    return PageTrashEmptyResponse(purged=await purge_trash(session, project))


@router.get("/{page_id}", response_model=PageResponse)
async def get_page_route(
    page_id: UUID,
    include_content: bool = Query(False),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> PageResponse:
    try:
        view = await get_page(session, str(page_id), include_content=include_content)
    except _REFUSALS as exc:
        raise _page_write_error(exc) from exc
    return PageResponse(**vars(view))


@router.patch("/{page_id}", response_model=PagePatchResponse)
async def patch_page_route(
    page_id: UUID,
    body: PagePatchRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> PagePatchResponse:
    """Rename when `title` is present, move when `parent_id` is present.

    Presence is read from `model_fields_set`: a null `parent_id` is a move to
    the root, not an absent field.
    """
    named = body.model_fields_set
    if "after_id" in named and "parent_id" not in named:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "after_id needs parent_id; a reorder is a move naming the current parent",
        )
    if "title" not in named and "parent_id" not in named:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "name at least one of title or parent_id",
        )
    try:
        if "title" in named:
            await rename_page(session, str(page_id), title=body.title)
        if "parent_id" in named:
            await move_page(
                session, str(page_id),
                parent_id=_str(body.parent_id),
                after_id=_str(body.after_id),
            )
    except _REFUSALS as exc:
        raise _page_write_error(exc) from exc
    return PagePatchResponse(id=page_id)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page_route(
    page_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_page(session, str(page_id))
    except _REFUSALS as exc:
        raise _page_write_error(exc) from exc


@router.post("/{page_id}/restore", response_model=PageRestoreResponse)
async def restore_page_route(
    page_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> PageRestoreResponse:
    try:
        restored = await restore_page(session, str(page_id))
    except _REFUSALS as exc:
        raise _page_write_error(exc) from exc
    return PageRestoreResponse(restored=restored)
