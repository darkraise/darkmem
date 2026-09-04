"""Memories related to a document, through the entities its lift minted (§6.2).

The sibling of `document_connections`, one hop short of it. That module asks
which other *documents* share entities with this one; this asks which
*memories* assert the same entities, which is the maintenance question: the
document says something, and these are the memory rows that also say it.

Every constraint `document_connections` states for itself holds here for the
same reasons, and they are repeated rather than referenced because a reader
arriving at this module needs them:

- **No LLM call.** The moment a relatedness feature writes prose about what a
  document and a memory have in common it has become unbadged synthesis, which
  doc 09 owns properly, with grounding and a ladder. A test pins the absence.
- **No new table.** `entities.memory_ids` is the GIN-indexed array Phase 5
  already maintains; this reads it.
- **It never touches the block channel.** The path is document → lifted
  propositions (ordinary memories, by provenance) → entities → memories. No
  block row crosses into ranking and no fact is minted, so
  `test_block_retrieval.py`'s scans are untouched.
- **Shared-entity count is evidence, not a score.** Rows are ordered by how
  many entities are shared and nothing normalises that into a similarity
  number, which would read as a measurement nobody made.

An **unlifted** document is not an empty result. `lifted` on the envelope says
which it is, so the surface can offer the lift rather than rendering an empty
list that looks like "nothing relates to this".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.proposition_lift import PROVENANCE_KEY

logger = logging.getLogger(__name__)

__all__ = ["RelatedMemory", "RelatedMemories", "related_memories_for_document"]


@dataclass(frozen=True)
class RelatedMemory:
    memory_id: str
    content: str
    memory_type: str | None
    status: str
    source: str | None
    shared_entities: tuple[str, ...]

    @property
    def shared_count(self) -> int:
        return len(self.shared_entities)


@dataclass(frozen=True)
class RelatedMemories:
    """`lifted` distinguishes "nothing relates" from "nothing to relate to"."""

    document_id: str
    lifted: bool
    items: tuple[RelatedMemory, ...]


# Read bottom-up:
#   `mine`   — the memories this document's lift minted, by provenance;
#   the join — entities asserted by one of those AND by some other memory.
# The other memory is excluded from `mine` so a document is never reported as
# related to its own lift, which would be every row and no information.
_RELATED_SQL = text(
    """
    WITH mine AS (
        SELECT id FROM memories
        WHERE metadata -> :key ->> 'document_id' = :document_id
    )
    SELECT m.id::text                  AS memory_id,
           m.content                   AS content,
           m.memory_type               AS memory_type,
           m.status                    AS status,
           m.source                    AS source,
           array_agg(DISTINCT e.name)  AS shared
    FROM entities e
    JOIN mine ON e.memory_ids @> ARRAY[mine.id]
    JOIN memories m
      ON e.memory_ids @> ARRAY[m.id]
     AND m.id NOT IN (SELECT id FROM mine)
    WHERE m.project = :project
    GROUP BY m.id, m.content, m.memory_type, m.status, m.source
    ORDER BY count(DISTINCT e.name) DESC, m.id
    LIMIT :limit
    """
)

_LIFT_COUNT_SQL = text(
    """
    SELECT count(*) FROM memories
    WHERE metadata -> :key ->> 'document_id' = :document_id
    """
)

_PROJECT_SQL = text("SELECT project FROM documents WHERE id = CAST(:id AS uuid)")


async def related_memories_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> RelatedMemories:
    """Which memories assert what this document's lift asserted.

    Scoped to the document's own project in SQL, for the reason
    `connections_for_document` gives: a cross-project result would breach the
    isolation boundary doc 18 §8 calls a security one, in the surface whose
    whole purpose is to surface rows the reader had not thought of.
    """
    key = str(document_id)
    project = (await session.execute(
        _PROJECT_SQL, {"id": key}
    )).scalar_one_or_none()
    if project is None:
        return RelatedMemories(document_id=key, lifted=False, items=())

    lifted = (await session.execute(
        _LIFT_COUNT_SQL, {"key": PROVENANCE_KEY, "document_id": key}
    )).scalar_one() > 0
    if not lifted:
        return RelatedMemories(document_id=key, lifted=False, items=())

    rows = (await session.execute(
        _RELATED_SQL,
        {
            "key": PROVENANCE_KEY,
            "document_id": key,
            "project": project,
            "limit": limit,
        },
    )).mappings().all()

    return RelatedMemories(
        document_id=key,
        lifted=True,
        items=tuple(
            RelatedMemory(
                memory_id=row["memory_id"],
                content=row["content"],
                memory_type=row["memory_type"],
                status=row["status"],
                source=row["source"],
                shared_entities=tuple(sorted(row["shared"] or ())),
            )
            for row in rows
        ),
    )
