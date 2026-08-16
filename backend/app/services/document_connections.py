"""Cross-document connections, emergent from the shared graph (TH1.15, §6).

**No new analysis engine, and that is the decision rather than a constraint.**
Two documents are connected because their lifted propositions minted entities
in the *same* graph — the one Phase 4 already dedups and Phase 5 already
writes. There is no new table, no new job family, no traversal of its own and
no model call: this module is a read over `entities.memory_ids` and the
provenance the lift already stored.

**A multi-document write-up is an article, and articles are doc 09's.** This
returns which documents share which entities and nothing more. The moment a
"connections" feature generates prose about several documents it has become
unbadged synthesis reading blocks, which doc 16 §6 puts out of scope and doc 09
already owns properly — with grounding, citations and a ladder. So the module
makes no LLM call at all, and a test pins that rather than trusting the
sentence.

**Shared entity count is evidence, not a score.** The rows come back ordered by
how many entities two documents have in common, because that is the only
ordering the underlying data supports honestly. Nothing here weights, decays or
normalises it into a similarity number, which would read as a measurement
nobody made.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.proposition_lift import PROVENANCE_KEY

logger = logging.getLogger(__name__)

__all__ = ["DocumentConnection", "connections_for_document"]


@dataclass(frozen=True)
class DocumentConnection:
    document_id: str
    title: str | None
    shared_entities: tuple[str, ...]

    @property
    def shared_count(self) -> int:
        return len(self.shared_entities)


# One statement, over tables that already exist. Read bottom-up:
#   `mine`   — the memories this document's lift minted, by provenance;
#   `theirs` — every other lifted memory, with the document it came from;
#   the join — entities asserted by both, which is the connection.
# `entities.memory_ids` is the existing GIN-indexed array Phase 5 maintains;
# nothing here writes it, and nothing here needs a traversal.
_CONNECTIONS_SQL = text(
    """
    WITH mine AS (
        SELECT id FROM memories
        WHERE metadata -> :key ->> 'document_id' = :document_id
    ),
    theirs AS (
        SELECT id, metadata -> :key ->> 'document_id' AS document_id
        FROM memories
        WHERE metadata -> :key ->> 'document_id' IS NOT NULL
          AND metadata -> :key ->> 'document_id' <> :document_id
          AND project = :project
    )
    SELECT theirs.document_id AS document_id,
           d.title            AS title,
           array_agg(DISTINCT e.name) AS shared
    FROM entities e
    JOIN mine   ON e.memory_ids @> ARRAY[mine.id]
    JOIN theirs ON e.memory_ids @> ARRAY[theirs.id]
    JOIN documents d ON d.id = CAST(theirs.document_id AS uuid)
    GROUP BY theirs.document_id, d.title
    ORDER BY count(DISTINCT e.name) DESC, theirs.document_id
    LIMIT :limit
    """
)

_PROJECT_SQL = text(
    "SELECT project FROM documents WHERE id = CAST(:id AS uuid)"
)


async def connections_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> list[DocumentConnection]:
    """Which other documents share entities with this one.

    Scoped to the document's own project in SQL. A connection across projects
    would cross the isolation boundary doc 18 §8 calls a security one — and it
    would do it in the surface whose whole purpose is to suggest things a
    reader has not thought of, which is the worst place to leak.
    """
    project = (await session.execute(
        _PROJECT_SQL, {"id": str(document_id)}
    )).scalar_one_or_none()
    if project is None:
        return []

    rows = (await session.execute(
        _CONNECTIONS_SQL,
        {
            "key": PROVENANCE_KEY,
            "document_id": str(document_id),
            "project": project,
            "limit": limit,
        },
    )).mappings().all()

    return [
        DocumentConnection(
            document_id=row["document_id"],
            title=row["title"],
            shared_entities=tuple(sorted(row["shared"] or ())),
        )
        for row in rows
    ]
