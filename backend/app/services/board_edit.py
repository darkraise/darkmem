"""The board's one write: a register row edit filed as a document put (spec 2026-10-13 §2.2).

Outside `board` on purpose: filing goes through `document_door`, whose import
closure carries memory models, and `board` sits inside the work-log wall.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import (
    EDITABLE_COLUMNS,
    REGISTER_PREFIX,
    REGISTER_STATES,
    BoardRefusal,
    RowEditRefused,
    is_blank_note,
    parse_register,
    rewrite_register_row,
)
from app.services.document_door import BLOCK_FIRST, DocumentIsBlockFirst, put_document
from app.services.document_ingest import DocumentHashConflict

_REFUSAL_STATUS = {"not_found": 404}

_DOCUMENT = text(
    "SELECT project, uri, content, content_hash, "
    "       properties->>'ingest_direction' AS direction "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)


def _hash_conflict(current_hash: str | None) -> BoardRefusal:
    return BoardRefusal(
        409, "hash_conflict",
        "this register changed since it was loaded; reload it and try again",
        current_hash=current_hash,
    )


def _block_first() -> BoardRefusal:
    return BoardRefusal(
        409, "block_first",
        "this register was converted to block-first and its content is owned by "
        "the block verbs; delete and re-file it to edit it from the board",
    )


async def edit_register_row(
    session: AsyncSession,
    *,
    document_id: str,
    number: int,
    expected_hash: str,
    changes: dict[str, str],
    actor: str,
) -> dict[str, Any]:
    """Rewrite one row and file the register; answers the row and the new hash.

    The put takes the row lock and compares `expected_hash` inside its own
    UPDATE, so a racing writer meets a conflict rather than an overwrite. Like
    the REST door and the mirror's own put, it passes no `properties` (spec
    2026-10-13 decision 8), and it embeds nothing (§2.4).
    """
    # The rewrite raises a plain ValueError on an unknown column, which would
    # otherwise escape as an unmapped error indistinguishable from a refusal's
    # base class; a caller naming one has a bug, not a refusable edit.
    unknown = set(changes) - EDITABLE_COLUMNS
    if unknown:
        raise TypeError(f"not an editable column: {sorted(unknown)}")
    if not changes:
        raise BoardRefusal(422, "no_change", "name at least one of state, note or assigned")
    document = (await session.execute(_DOCUMENT, {"id": document_id})).first()
    if (
        document is None
        or document.uri is None
        or not document.uri.startswith(REGISTER_PREFIX)
        or not document.uri.endswith(".md")
    ):
        raise BoardRefusal(404, "not_found", f"no register with id {document_id}")
    if document.direction == BLOCK_FIRST:
        raise _block_first()
    if document.content_hash != expected_hash:
        raise _hash_conflict(document.content_hash)
    try:
        updated = rewrite_register_row(document.content or "", number, changes)
    except RowEditRefused as exc:
        raise BoardRefusal(_REFUSAL_STATUS.get(exc.reason, 422), exc.reason, str(exc)) from exc
    try:
        result = await put_document(
            session, None,
            project=document.project, uri=document.uri, content=updated,
            actor=actor, source="api", expected_hash=expected_hash, embed_inline=False,
        )
    except DocumentHashConflict as exc:
        raise _hash_conflict(exc.current_hash) from exc
    except DocumentIsBlockFirst as exc:
        raise _block_first() from exc
    row = next(r for r in parse_register(updated).rows if r.number == number)
    return {
        "document_id": result.document_id,
        "content_hash": result.content_hash,
        "row": {
            "number": row.number,
            "item": row.item,
            "assigned": row.assigned,
            "acceptance": row.acceptance,
            "state": row.state if row.state in REGISTER_STATES else "unrecognised",
            "raw_state": row.state,
            "note": row.note,
            "note_blank": is_blank_note(row.note),
            "line": row.line,
        },
    }
