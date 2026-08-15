"""SQL for `documents` and `blocks` — the tables T0.13 landed inert (TH1.02).

Doc 16 §2 fixes document identity as the partial ``UNIQUE (project, uri)
WHERE uri IS NOT NULL``: re-filing the same source resolves to the existing
row instead of minting a duplicate, while uri-less sources (an ad-hoc note)
are identified by their id and coexist under the partial predicate. Both
halves are the database's, not this module's — :func:`upsert_by_uri` reaches
the constraint through ``ON CONFLICT (project, uri) WHERE uri IS NOT NULL``
so a caller that raced the resolving SELECT lands on the existing row rather
than on an IntegrityError.

Blocks are written strip-before-rewrite by ``document_id`` (doc 16 §3,
invariant 8 generalised): every id is minted fresh on each write, so nothing
durable may key on a block id across ingests. That churn is deliberate and it
is also what makes "no block rewrite" observable — a re-ingest that did any
work leaves a different set of block ids behind.

Block ids are minted here rather than server-side because ``parent_id`` points
into the same batch: the tree is resolved in one pass and the whole set goes
down as one statement.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "BlockRow",
    "DocumentRow",
    "insert_blocks",
    "resolve_by_id",
    "resolve_by_uri",
    "strip_blocks",
    "update_document",
    "upsert_by_uri",
]


@dataclass(frozen=True)
class DocumentRow:
    id: UUID
    project: str
    uri: str | None
    content_hash: str | None


@dataclass(frozen=True)
class BlockRow:
    """One block as the writer takes it — ids resolved, tree already flattened."""

    id: UUID
    parent_id: UUID | None
    order_index: int
    type: str
    text: str
    properties: dict | None
    char_span: tuple[int, int] | None


_RESOLVE_BY_URI = text(
    "SELECT id, project, uri, content_hash FROM documents "
    "WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text)"
)

_RESOLVE_BY_ID = text(
    "SELECT id, project, uri, content_hash FROM documents "
    "WHERE id = CAST(:id AS uuid)"
)

_UPSERT_BY_URI = text(
    """
    INSERT INTO documents (id, project, uri, title, source_type, content_hash, properties)
    VALUES (CAST(:id AS uuid), CAST(:project AS text), CAST(:uri AS text),
            CAST(:title AS text), CAST(:source_type AS text),
            CAST(:content_hash AS text), CAST(:properties AS jsonb))
    ON CONFLICT (project, uri) WHERE uri IS NOT NULL DO UPDATE SET
        title = EXCLUDED.title,
        source_type = EXCLUDED.source_type,
        content_hash = EXCLUDED.content_hash,
        properties = EXCLUDED.properties
    RETURNING id
    """
)

_UPDATE_DOCUMENT = text(
    """
    UPDATE documents SET
        title = CAST(:title AS text),
        source_type = CAST(:source_type AS text),
        content_hash = CAST(:content_hash AS text),
        properties = CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
    """
)

_STRIP_BLOCKS = text("DELETE FROM blocks WHERE document_id = CAST(:document_id AS uuid)")

_INSERT_BLOCK = text(
    """
    INSERT INTO blocks (id, document_id, parent_id, order_index, type, text,
                        properties, char_span)
    VALUES (CAST(:id AS uuid), CAST(:document_id AS uuid), CAST(:parent_id AS uuid),
            CAST(:order_index AS integer), CAST(:type AS text), CAST(:text AS text),
            CAST(:properties AS jsonb), CAST(CAST(:char_span AS text) AS int4range))
    """
)


def _row(mapping) -> DocumentRow:
    return DocumentRow(
        id=mapping["id"],
        project=mapping["project"],
        uri=mapping["uri"],
        content_hash=mapping["content_hash"],
    )


async def resolve_by_uri(
    session: AsyncSession, *, project: str, uri: str
) -> DocumentRow | None:
    mapping = (
        await session.execute(_RESOLVE_BY_URI, {"project": project, "uri": uri})
    ).mappings().first()
    return None if mapping is None else _row(mapping)


async def resolve_by_id(session: AsyncSession, document_id: UUID) -> DocumentRow | None:
    mapping = (
        await session.execute(_RESOLVE_BY_ID, {"id": str(document_id)})
    ).mappings().first()
    return None if mapping is None else _row(mapping)


async def upsert_by_uri(
    session: AsyncSession,
    *,
    document_id: UUID,
    project: str,
    uri: str | None,
    title: str | None,
    source_type: str | None,
    content_hash: str,
    properties: dict | None,
) -> UUID:
    """Insert the row, or fold onto the one that already owns `(project, uri)`.

    Returns the surviving id, which differs from `document_id` exactly when
    something else filed this uri between the caller's resolve and this write.
    A NULL `uri` never conflicts — the unique index is partial — so uri-less
    documents always insert.
    """
    return (
        await session.execute(
            _UPSERT_BY_URI,
            {
                "id": str(document_id),
                "project": project,
                "uri": uri,
                "title": title,
                "source_type": source_type,
                "content_hash": content_hash,
                "properties": None if properties is None else json.dumps(properties),
            },
        )
    ).scalar_one()


async def update_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    title: str | None,
    source_type: str | None,
    content_hash: str,
    properties: dict | None,
) -> None:
    await session.execute(
        _UPDATE_DOCUMENT,
        {
            "id": str(document_id),
            "title": title,
            "source_type": source_type,
            "content_hash": content_hash,
            "properties": None if properties is None else json.dumps(properties),
        },
    )


async def strip_blocks(session: AsyncSession, document_id: UUID) -> int:
    """Delete every block of `document_id`. The `parent_id` CASCADE takes the
    subtree and the `block_embeddings__<slug>` FK CASCADE takes the vectors."""
    result = await session.execute(_STRIP_BLOCKS, {"document_id": str(document_id)})
    return result.rowcount or 0


async def insert_blocks(
    session: AsyncSession, document_id: UUID, rows: Sequence[BlockRow]
) -> None:
    if not rows:
        return
    await session.execute(
        _INSERT_BLOCK,
        [
            {
                "id": str(row.id),
                "document_id": str(document_id),
                "parent_id": None if row.parent_id is None else str(row.parent_id),
                "order_index": row.order_index,
                "type": row.type,
                "text": row.text,
                "properties": None if row.properties is None else json.dumps(row.properties),
                "char_span": _span_literal(row.char_span),
            }
            for row in rows
        ],
    )


def _span_literal(span: tuple[int, int] | None) -> str | None:
    """Postgres `int4range` half-open literal.

    Half-open because character offsets are: a block spanning characters 3
    through 9 is `[3,10)`, and two adjacent blocks must not both claim the
    boundary offset or a containment test for a cited span answers twice.
    """
    if span is None:
        return None
    start, end = span
    if end < start:
        raise ValueError(f"char_span end {end} precedes start {start}")
    return f"[{start},{end})"
