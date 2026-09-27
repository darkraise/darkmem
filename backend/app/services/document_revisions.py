"""A document's revisions, newest first: every content a filing wrote.

The writer is `document_ingest`'s filing body; this module only reads, and
both doors call it (`GET /api/v1/documents/{id}/revisions` and its
`/{revision_id}` read, and the MCP `document_revisions` tool). A page carries
no content because one revision can be a megabyte; a caller fetches the
revision it wants by id and computes any diff itself. Neither function
confirms the document exists: the doors resolve it first, through
`document_door.resolve_document_target`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["DEFAULT_LIMIT", "MAX_LIMIT", "get_revision", "list_revisions"]

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

_CURSOR = text(
    "SELECT created_at, id FROM document_revisions "
    "WHERE id = CAST(:id AS uuid) AND document_id = CAST(:document_id AS uuid)"
)

_PAGE = text(
    """
    SELECT CAST(id AS text) AS id, content_hash, actor,
           CAST(api_key_id AS text) AS api_key_id, created_at
    FROM document_revisions
    WHERE document_id = CAST(:document_id AS uuid)
      AND (CAST(:before_at AS timestamptz) IS NULL
           OR (created_at, id) < (CAST(:before_at AS timestamptz), CAST(:before_id AS uuid)))
    ORDER BY created_at DESC, id DESC
    LIMIT CAST(:limit AS integer)
    """
)

_ONE = text(
    """
    SELECT CAST(id AS text) AS id, content_hash, actor,
           CAST(api_key_id AS text) AS api_key_id, created_at, content
    FROM document_revisions
    WHERE id = CAST(:id AS uuid) AND document_id = CAST(:document_id AS uuid)
    """
)


def _serialize(row) -> dict[str, Any]:
    out = dict(row)
    out["created_at"] = row["created_at"].isoformat()
    return out


def _uuid(value: UUID | str, name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValueError(f"{name} is not a revision id: {value!r}") from error


async def list_revisions(
    session: AsyncSession,
    *,
    document_id: UUID | str,
    before: UUID | str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """One page of revisions without content, newest first.

    `before` is the last revision of the previous page (its `next_before`).
    Raises `ValueError` for a limit outside 1-`MAX_LIMIT`, or for a `before`
    that names no revision of this document.
    """
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, not {limit}")
    before_at = before_id = None
    if before is not None:
        cursor = (await session.execute(
            _CURSOR,
            {"id": str(_uuid(before, "before")), "document_id": str(document_id)},
        )).first()
        if cursor is None:
            raise ValueError(f"before names no revision of this document: {before}")
        before_at, before_id = cursor.created_at, str(cursor.id)
    rows = (await session.execute(
        _PAGE,
        {
            "document_id": str(document_id),
            "before_at": before_at,
            "before_id": before_id,
            "limit": limit + 1,
        },
    )).mappings().all()
    items = [_serialize(row) for row in rows[:limit]]
    return {
        "document_id": str(document_id),
        "items": items,
        "next_before": items[-1]["id"] if len(rows) > limit else None,
    }


async def get_revision(
    session: AsyncSession, *, document_id: UUID | str, revision_id: UUID | str
) -> dict[str, Any] | None:
    """One revision with its content, or `None` when it is not this document's."""
    row = (await session.execute(
        _ONE,
        {"id": str(_uuid(revision_id, "revision_id")), "document_id": str(document_id)},
    )).mappings().first()
    if row is None:
        return None
    return {"document_id": str(document_id), **_serialize(row)}
