"""The Notion import door.

Provides:
  - POST /api/v1/pages/import/notion

REST-only, like the rest of the page tree. The raw body is the zip: FastAPI's
`UploadFile` spools a whole body before the handler runs, so a ceiling on it
could only ever be checked after the bytes landed. `main.bounds_own_body`
exempts this path from the edge cap for the same reason.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.database import get_session
from app.services.notion_archive import NotionArchiveInvalid, NotionArchiveTooLarge
from app.services.notion_tree import NotionExportInvalid
from app.services.page_import import (
    ImportBusy,
    ImportNoSpace,
    ImportTimedOut,
    ImportTooLarge,
    import_notion_export,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

_PROJECT_EXISTS = text("SELECT 1 FROM projects WHERE name = :name")


class ImportWarningResponse(BaseModel):
    path: str | None
    kind: str
    detail: str


class ImportReportResponse(BaseModel):
    root_page_id: UUID
    pages_created: int
    databases: int
    attachments_stored: int
    attachment_bytes: int
    warnings: list[ImportWarningResponse]
    warnings_omitted: int


@router.post(
    "/import/notion",
    response_model=ImportReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_notion_route(
    request: Request,
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    _read_only=Depends(refuse_when_read_only),
    session: AsyncSession = Depends(get_session),
) -> ImportReportResponse:
    known = (
        await session.execute(_PROJECT_EXISTS, {"name": project})
    ).scalar_one_or_none()
    if known is None:
        # Before a byte is read: a gigabyte must never be accepted for a name
        # that cannot receive it.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"no project named {project!r}",
        )

    declared = request.headers.get("content-length")
    length = int(declared) if declared and declared.isdigit() else None
    actor = getattr(_user, "sub", None)

    try:
        report = await import_notion_export(
            session, project=project, body=request.stream(),
            declared_length=length, actor=actor,
        )
    except ImportBusy as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (ImportTooLarge, NotionArchiveTooLarge) as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except ImportNoSpace as exc:
        raise HTTPException(
            status.HTTP_507_INSUFFICIENT_STORAGE, str(exc)
        ) from exc
    except (NotionArchiveInvalid, NotionExportInvalid, ImportTimedOut) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc

    return ImportReportResponse(
        root_page_id=report.root_page_id,
        pages_created=report.pages_created,
        databases=report.databases,
        attachments_stored=report.attachments_stored,
        attachment_bytes=report.attachment_bytes,
        warnings=[
            ImportWarningResponse(path=w.path, kind=w.kind, detail=w.detail)
            for w in report.warnings
        ],
        warnings_omitted=report.warnings_omitted,
    )
