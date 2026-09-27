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
    "DocumentIsBlockFirst",
    "DocumentRow",
    "insert_blocks",
    "insert_revision",
    "latest_revision_hash",
    "resolve_by_id",
    "resolve_by_uri",
    "strip_blocks",
    "update_document",
    "upsert_by_uri",
]


class DocumentIsBlockFirst(ValueError):
    """put refused: this document is owned by the block verbs (spec §8.2).

    A content push over an editing session is a silent overwrite -- the put
    would strip every block the editor placed and rewrite the content it was
    serialising from.

    It lives in the repository because that is where the statement carrying
    one of the two refusals lives, and because this module names no service:
    ``document_ingest`` imports it, so an exception defined over there and
    raised here would close an import cycle. ``document_door`` re-exports it
    for the two doors.
    """


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

# The `ON CONFLICT ... WHERE` arm guards the one put path this statement is
# on: a caller whose resolve found nothing, and whose INSERT then collides
# with a block-first row another lane freed and refiled. `put_document`'s own
# locked pre-check is the guard for the ordinary path, where an existing row
# is written through `_UPDATE_DOCUMENT` and this statement never runs, so
# neither guard subsumes the other.
_UPSERT_BY_URI = text(
    """
    INSERT INTO documents (id, project, uri, title, source_type, content_hash,
                           content, properties)
    VALUES (CAST(:id AS uuid), CAST(:project AS text), CAST(:uri AS text),
            CAST(:title AS text), CAST(:source_type AS text),
            CAST(:content_hash AS text), CAST(:content AS text),
            CAST(:properties AS jsonb))
    ON CONFLICT (project, uri) WHERE uri IS NOT NULL DO UPDATE SET
        title = EXCLUDED.title,
        source_type = EXCLUDED.source_type,
        content_hash = EXCLUDED.content_hash,
        content = EXCLUDED.content,
        properties = EXCLUDED.properties
    WHERE documents.properties->>'ingest_direction' IS DISTINCT FROM 'blocks'
    RETURNING id
    """
)

# The `expected_hash` arm is review finding M1's whole point and must stay IN
# this statement: a read-then-compare in Python passes for both of two racing
# lanes and the second still clobbers the first. Inside the UPDATE, the loser
# blocks on the winner's row lock, re-evaluates the predicate against the
# committed row, and matches zero rows -- which the caller must treat as the
# conflict. A NULL expected_hash disables the arm, which is last-writer-wins,
# the pre-CAS behaviour every existing caller relies on.
_UPDATE_DOCUMENT = text(
    """
    UPDATE documents SET
        title = CAST(:title AS text),
        source_type = CAST(:source_type AS text),
        content_hash = CAST(:content_hash AS text),
        content = CAST(:content AS text),
        properties = CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
      AND (CAST(:expected_hash AS text) IS NULL
           OR content_hash = CAST(:expected_hash AS text))
    """
)

_STRIP_BLOCKS = text("DELETE FROM blocks WHERE document_id = CAST(:document_id AS uuid)")

# `clock_timestamp()`, not the column's `now()` default: two puts on one
# document serialise on its row lock, so the later writer can hold the earlier
# transaction start, and revisions order by `created_at`.
_INSERT_REVISION = text(
    "INSERT INTO document_revisions "
    "(id, document_id, content, content_hash, actor, api_key_id, created_at) "
    "VALUES (CAST(:id AS uuid), CAST(:document_id AS uuid), CAST(:content AS text), "
    "CAST(:content_hash AS text), CAST(:actor AS text), CAST(:api_key_id AS uuid), "
    "clock_timestamp())"
)

_LATEST_REVISION_HASH = text(
    "SELECT content_hash FROM document_revisions "
    "WHERE document_id = CAST(:document_id AS uuid) "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)

# The `char_span` bind is cast twice on purpose. A single `CAST(:char_span AS
# int4range)` — which is the form doc 16 §2 names — makes asyncpg infer the
# parameter as int4range and then refuse the string: "list, tuple or Range
# object expected (got type <class 'str'>)". Casting through `text` first pins
# the parameter to a type asyncpg can send and lets Postgres parse the literal,
# which is what keeps the bound convention (`[lo,hi)`) explicit in one place
# rather than delegated to a driver default.
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
    # Defaulted so a caller that predates the round-trip column still
    # compiles: the bytes-source path stores NULL for the same reason, and a
    # required eighth keyword would break callers that have no text to give.
    content: str | None = None,
) -> UUID:
    """Insert the row, or fold onto the one that already owns `(project, uri)`.

    Returns the surviving id, which differs from `document_id` exactly when
    something else filed this uri between the caller's resolve and this write.
    A NULL `uri` never conflicts — the unique index is partial — so uri-less
    documents always insert.

    Raises `DocumentIsBlockFirst` when the row it would fold onto is owned by
    the block verbs.
    """
    resolved = (
        await session.execute(
            _UPSERT_BY_URI,
            {
                "id": str(document_id),
                "project": project,
                "uri": uri,
                "title": title,
                "source_type": source_type,
                "content_hash": content_hash,
                "content": content,
                "properties": None if properties is None else json.dumps(properties),
            },
        )
    ).scalar_one_or_none()
    if resolved is None:
        # The conflict target existed and the predicate excluded it: the row at
        # this uri is block-first. A non-conflicting INSERT returns its own row,
        # so zero rows means this and nothing else.
        raise DocumentIsBlockFirst(
            f"the document at uri {uri!r} in project {project!r} is "
            "block-first: its content is owned by the block verbs."
        )
    return resolved


async def update_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    title: str | None,
    source_type: str | None,
    content_hash: str,
    properties: dict | None,
    content: str | None = None,
    expected_hash: str | None = None,
) -> int:
    """Write the document row; return how many rows the write matched.

    Zero with an ``expected_hash`` means the precondition failed -- the row's
    ``content_hash`` is not what the caller asserted, or the row is gone. Zero
    without one means the row is gone. This module only reports the count; what
    either case means is the caller's decision.
    """
    result = await session.execute(
        _UPDATE_DOCUMENT,
        {
            "id": str(document_id),
            "title": title,
            "source_type": source_type,
            "content_hash": content_hash,
            "content": content,
            "properties": None if properties is None else json.dumps(properties),
            "expected_hash": expected_hash,
        },
    )
    return result.rowcount


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


async def insert_revision(
    session: AsyncSession,
    *,
    revision_id: UUID,
    document_id: UUID,
    content: str,
    content_hash: str,
    actor: str | None,
    api_key_id: UUID | None,
) -> None:
    await session.execute(
        _INSERT_REVISION,
        {
            "id": str(revision_id),
            "document_id": str(document_id),
            "content": content,
            "content_hash": content_hash,
            "actor": actor,
            "api_key_id": None if api_key_id is None else str(api_key_id),
        },
    )


async def latest_revision_hash(session: AsyncSession, document_id: UUID) -> str | None:
    return (await session.execute(
        _LATEST_REVISION_HASH, {"document_id": str(document_id)}
    )).scalar_one_or_none()


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
