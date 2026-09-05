"""Documents nearest this one, by cosine over block vectors (§4).

The sibling of `document_related`, one hop further out: that module asks which
*memories* resemble this document, this asks which other *documents* do.

Everything `document_related` decides applies here and for the same reasons --
no LLM call, max-aggregation over the argmax block pair, no floor, the
fingerprint derived from data, project scoping in SQL -- with one difference
that makes this the cheaper of the two: both sides are the *same* partition, so
this is a same-table join.

The former basis was `entities.memory_ids` over the memories a lift minted.
Nothing is lifted any more, so that walk would return an empty list forever.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_similarity import resolve_shared_fingerprint
from app.services.embedder_registry import child_table

logger = logging.getLogger(__name__)

__all__ = [
    "DocumentConnection", "DocumentConnections", "connections_for_document",
]


@dataclass(frozen=True)
class DocumentConnection:
    document_id: str
    title: str | None
    score: float
    block_id: str
    block_text: str
    other_block_id: str
    other_block_text: str


@dataclass(frozen=True)
class DocumentConnections:
    document_id: str
    embedded: bool
    comparable_documents: int
    items: tuple[DocumentConnection, ...]


_DOCUMENT_SQL = text(
    "SELECT project FROM documents WHERE id = CAST(:id AS uuid)"
)


def _connections_sql(blocks_table: str) -> str:
    """Interpolated, not bound: a table identifier from `child_table` over a
    fingerprint read out of `embedders`, never from a caller."""
    return f"""
        SELECT other.id::text      AS document_id,
               other.title         AS title,
               best.score          AS score,
               best.block_id::text AS block_id,
               best.block_text     AS block_text,
               best.other_block_id::text AS other_block_id,
               best.other_block_text     AS other_block_text
        FROM documents other
        JOIN LATERAL (
            SELECT mine_b.id    AS block_id,
                   mine_b.text  AS block_text,
                   their_b.id   AS other_block_id,
                   their_b.text AS other_block_text,
                   1 - (mine.embedding <=> theirs.embedding) AS score
            FROM {blocks_table} mine
            JOIN blocks mine_b ON mine_b.id = mine.block_id
            JOIN {blocks_table} theirs ON true
            JOIN blocks their_b ON their_b.id = theirs.block_id
            WHERE mine_b.document_id = CAST(:document_id AS uuid)
              AND their_b.document_id = other.id
            ORDER BY score DESC
            LIMIT 1
        ) best ON true
        WHERE other.project = :project
          AND other.id <> CAST(:document_id AS uuid)
        ORDER BY best.score DESC, other.id
        LIMIT :limit
    """


def _comparable_sql() -> str:
    return (
        "SELECT count(*) FROM documents "
        "WHERE project = :project AND id <> CAST(:document_id AS uuid)"
    )


async def connections_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> DocumentConnections:
    """Which other documents are nearest this one, and which passages matched.

    Scoped to the document's own project in SQL. A connection across projects
    would cross the isolation boundary doc 18 §8 calls a security one — and it
    would do it in the surface whose whole purpose is to suggest things a
    reader has not thought of, which is the worst place to leak.
    """
    key = str(document_id)
    project = (await session.execute(
        _DOCUMENT_SQL, {"id": key}
    )).scalar_one_or_none()
    if project is None:
        return DocumentConnections(
            document_id=key, embedded=False, comparable_documents=0, items=(),
        )

    fingerprint = await resolve_shared_fingerprint(
        session, document_id=key, project=project, counterpart="block",
    )
    if fingerprint is None:
        return DocumentConnections(
            document_id=key, embedded=False, comparable_documents=0, items=(),
        )

    blocks_table = child_table("block_embeddings", fingerprint)

    comparable = await session.scalar(
        text(_comparable_sql()), {"project": project, "document_id": key},
    )

    rows = (await session.execute(
        text(_connections_sql(blocks_table)),
        {"document_id": key, "project": project, "limit": limit},
    )).mappings().all()

    return DocumentConnections(
        document_id=key,
        embedded=True,
        comparable_documents=int(comparable or 0),
        items=tuple(
            DocumentConnection(
                document_id=row["document_id"],
                title=row["title"],
                score=float(row["score"]),
                block_id=row["block_id"],
                block_text=row["block_text"],
                other_block_id=row["other_block_id"],
                other_block_text=row["other_block_text"],
            )
            for row in rows
        ),
    )
