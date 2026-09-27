"""The page tree's REST door.

Provides:
  - POST   /api/v1/pages
  - GET    /api/v1/pages
  - GET    /api/v1/pages/trash
  - POST   /api/v1/pages/trash/empty
  - GET    /api/v1/pages/{page_id}
  - PATCH  /api/v1/pages/{page_id}
  - DELETE /api/v1/pages/{page_id}
  - POST   /api/v1/pages/{page_id}/restore
  - POST   /api/v1/pages/{page_id}/blocks
  - POST   /api/v1/pages/{page_id}/blocks/batch
  - PATCH  /api/v1/pages/{page_id}/blocks/{block_id}
  - POST   /api/v1/pages/{page_id}/blocks/{block_id}/move
  - DELETE /api/v1/pages/{page_id}/blocks/{block_id}

REST-only: no MCP tool serves pages. Every `page_door` writer commits itself,
and a refusal leaves the request's transaction for the session dependency to
end, so no handler touches the session after catching one.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_llm
from app.database import get_session
from app.schemas.page import (
    PageBlockBatchInsertRequest,
    PageBlockInsertRequest,
    PageBlockMoveRequest,
    PageBlockUpdateRequest,
    PageCreateRequest,
    PageCreateResponse,
    PageListItem,
    PagePatchRequest,
    PagePatchResponse,
    PageResponse,
    PageRestoreResponse,
    PageTrashEmptyResponse,
    PageTrashItem,
)
from app.services.block_verbs import (
    PAGE_OWNER,
    BlockCycleError,
    BlockTargetUnresolved,
    NewBlock,
    PageBlockIdTaken,
    PageBlockInvalid,
    delete_block,
    insert_block,
    insert_blocks,
    move_block,
    update_block,
)
from app.services.document_door import DocumentTooLarge
from app.services.document_ingest import DocumentHashConflict
from app.services.page_door import (
    PageCycleError,
    PageNotRepresentable,
    PageParentTrashed,
    PageTargetUnresolved,
    PageTooLarge,
    create_page,
    delete_page,
    get_page,
    list_pages,
    list_trash,
    move_page,
    purge_trash,
    rename_page,
    restore_page,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])


def _page_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PageTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, (PageCycleError, PageNotRepresentable, PageTooLarge)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    if isinstance(exc, PageParentTrashed):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise exc


_REFUSALS = (
    PageTargetUnresolved, PageCycleError, PageNotRepresentable, PageTooLarge,
    PageParentTrashed,
)


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


@router.get("/trash", response_model=list[PageTrashItem])
async def list_trash_route(
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[PageTrashItem]:
    """The roots of the project's trashed subtrees, newest first. Declared
    above `/{page_id}` so `trash` is never parsed as a page id."""
    return [PageTrashItem(**row) for row in await list_trash(session, project)]


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
    """Move when `parent_id` is present, then rename when `title` is present.

    Presence is read from `model_fields_set`: a null `parent_id` is a move to
    the root, not an absent field.
    """
    named = body.model_fields_set
    if "after_id" in named and "parent_id" not in named:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "after_id needs parent_id; a reorder is a move naming the current parent",
        )
    if "title" not in named and "parent_id" not in named:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "name at least one of title or parent_id",
        )
    try:
        if "parent_id" in named:
            await move_page(
                session, str(page_id),
                parent_id=_str(body.parent_id),
                after_id=_str(body.after_id),
            )
        if "title" in named:
            await rename_page(session, str(page_id), title=body.title)
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


class PageBlockWriteResponse(BaseModel):
    page_id: str
    block_id: str | None
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int


def _response(result) -> PageBlockWriteResponse:
    return PageBlockWriteResponse(
        page_id=result.owner_id, block_id=result.block_id, outcome=result.outcome,
        content_hash=result.content_hash, blocks_total=result.blocks_total,
        blocks_embedded=result.blocks_embedded,
    )


def _block_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BlockTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, (BlockCycleError, DocumentTooLarge, PageBlockInvalid)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    if isinstance(exc, PageBlockIdTaken):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, DocumentHashConflict):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"page's current content_hash {exc.current_hash}",
        )
    raise exc


_BLOCK_REFUSALS = (BlockTargetUnresolved, BlockCycleError, DocumentTooLarge,
                   DocumentHashConflict, PageBlockInvalid, PageBlockIdTaken)


async def _assert_block_is_in(session, page_id: UUID, block_id: UUID) -> None:
    """The verbs prove a block is some page's; this proves it is the page the
    path names."""
    owner = (await session.execute(
        text("SELECT CAST(page_id AS text) FROM blocks WHERE id = CAST(:id AS uuid)"),
        {"id": str(block_id)},
    )).scalar_one_or_none()
    if owner is None or owner != str(page_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no block {block_id} in page {page_id}",
        )


@router.post(
    "/{page_id}/blocks",
    response_model=PageBlockWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_page_block_route(
    page_id: UUID,
    body: PageBlockInsertRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageBlockWriteResponse:
    """First child of `parent_id` by default, or after `after_block_id` among
    that parent's children."""
    try:
        result = await insert_block(
            session, llm, document_id=str(page_id), type=body.type,
            text=body.text, parent_id=_str(body.parent_id),
            after_block_id=_str(body.after_block_id), properties=body.properties,
            expected_hash=body.expected_hash, block_id=_str(body.block_id),
            owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return _response(result)


class PageBlockBatchWriteResponse(BaseModel):
    page_id: str
    block_ids: list[str]
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int


@router.post(
    "/{page_id}/blocks/batch",
    response_model=PageBlockBatchWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_page_blocks_route(
    page_id: UUID,
    body: PageBlockBatchInsertRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageBlockBatchWriteResponse:
    """Every item in one pass, applied in order: an item may name an earlier
    item's `block_id` as its parent or `after_block_id`, and the first refusal
    writes nothing. A paste of N blocks is one page rewrite, not N."""
    try:
        result = await insert_blocks(
            session, llm, document_id=str(page_id), owner=PAGE_OWNER,
            expected_hash=body.expected_hash,
            blocks=[
                NewBlock(
                    block_id=str(item.block_id), type=item.type, text=item.text,
                    properties=item.properties, parent_id=_str(item.parent_id),
                    after_block_id=_str(item.after_block_id),
                )
                for item in body.blocks
            ],
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return PageBlockBatchWriteResponse(
        page_id=result.owner_id, block_ids=list(result.block_ids),
        outcome=result.outcome, content_hash=result.content_hash,
        blocks_total=result.blocks_total, blocks_embedded=result.blocks_embedded,
    )


@router.patch("/{page_id}/blocks/{block_id}", response_model=PageBlockWriteResponse)
async def update_page_block_route(
    page_id: UUID,
    block_id: UUID,
    body: PageBlockUpdateRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageBlockWriteResponse:
    await _assert_block_is_in(session, page_id, block_id)
    try:
        result = await update_block(
            session, llm, block_id=str(block_id), text=body.text,
            type=body.type, properties=body.properties,
            expected_hash=body.expected_hash, owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return _response(result)


@router.post(
    "/{page_id}/blocks/{block_id}/move", response_model=PageBlockWriteResponse,
)
async def move_page_block_route(
    page_id: UUID,
    block_id: UUID,
    body: PageBlockMoveRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageBlockWriteResponse:
    await _assert_block_is_in(session, page_id, block_id)
    try:
        result = await move_block(
            session, llm, block_id=str(block_id),
            new_parent_id=_str(body.new_parent_id),
            after_block_id=_str(body.after_block_id),
            expected_hash=body.expected_hash, owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return _response(result)


@router.delete("/{page_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page_block_route(
    page_id: UUID,
    block_id: UUID,
    response: Response,
    expected_hash: str | None = Query(
        None, description="Refuse unless the page's content_hash matches."
    ),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> None:
    """The subtree goes with it. `expected_hash` rides the query string because
    a DELETE carries no body here, and the page's new hash rides the
    `X-Content-Hash` header because a 204 carries none either -- without it a
    client chaining preconditions would need a re-read after every delete."""
    await _assert_block_is_in(session, page_id, block_id)
    try:
        result = await delete_block(
            session, llm, block_id=str(block_id), expected_hash=expected_hash,
            owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    response.headers["X-Content-Hash"] = result.content_hash
