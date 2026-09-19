"""Page attachments over REST.

Provides:
  - POST /api/v1/pages/{page_id}/attachments
  - GET  /api/v1/pages/attachments/{attachment_id}

REST-only, like the page tree. The upload body is the raw file, not a
multipart form: FastAPI's `UploadFile` spools the whole body before the
handler runs, so a cap on it could only ever be checked after the bytes
landed. The request's own Content-Type is ignored -- a browser sends the
file's type, and the stored type is sniffed from the bytes.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.config import settings
from app.database import get_session
from app.services.page_attachments import (
    AttachmentTooLarge,
    attachment_path,
    clean_filename,
    get_attachment,
    serving_headers,
    store_upload,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

_LIVE_PAGE_PROJECT = text(
    "SELECT project FROM pages WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL"
)


class AttachmentResponse(BaseModel):
    id: UUID
    url: str
    filename: str
    content_type: str
    size_bytes: int


def _too_large() -> HTTPException:
    return HTTPException(
        status.HTTP_413_CONTENT_TOO_LARGE,
        f"attachment exceeds {settings.attachment_max_bytes} bytes",
    )


@router.post(
    "/{page_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment_route(
    page_id: UUID,
    request: Request,
    x_filename: str | None = Header(default=None),
    _user=Depends(require_auth),
    _read_only=Depends(refuse_when_read_only),
    session: AsyncSession = Depends(get_session),
) -> AttachmentResponse:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > settings.attachment_max_bytes:
        raise _too_large()
    project = (
        await session.execute(_LIVE_PAGE_PROJECT, {"id": str(page_id)})
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no live page with id {page_id}")
    try:
        stored = await store_upload(
            session,
            page_id=page_id,
            project=project,
            filename=clean_filename(x_filename),
            chunks=request.stream(),
            max_bytes=settings.attachment_max_bytes,
        )
    except AttachmentTooLarge as exc:
        raise _too_large() from exc
    return AttachmentResponse(
        id=stored.id, url=stored.url, filename=stored.filename,
        content_type=stored.content_type, size_bytes=stored.size_bytes,
    )


@router.get("/attachments/{attachment_id}", response_class=FileResponse)
async def get_attachment_route(
    attachment_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    row = await get_attachment(session, attachment_id)
    path = attachment_path(attachment_id)
    if row is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no attachment with id {attachment_id}")
    return FileResponse(path, media_type=row.content_type, headers=serving_headers(row))
