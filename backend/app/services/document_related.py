"""Memories nearest a document, by cosine over vectors both sides carry (§3).

The sibling of `document_connections`, one hop short of it: that module asks
which other *documents* resemble this one, this asks which *memories* do, which
is the maintenance question.

**No LLM call, at query time or ever.** Both sides are already embedded — the
blocks by the document pipeline, the memories by the ordinary one — so this is
a join, not a retrieval. The moment a relatedness feature writes prose about
what a document and a memory have in common it has become unbadged synthesis,
which doc 09 owns properly, with grounding and a ladder. A test pins the
absence.

**Max, not mean.** One row per memory, scored by its single best-matching
block. A large document is heterogeneous and a mean dilutes every real match
into noise, ranking the memory that matches one paragraph perfectly below one
vaguely near everything. The `LATERAL` carries the argmax block out with the
score, which is what lets the surface show the passage rather than only the
number.

**No floor.** Measured across all 475 filed documents the score distribution is
continuous -- p50 0.503, p90 0.612, p99 0.750, no seam -- and both error kinds
straddle any cut: at 0.724 a 28-character list item is noise, at 0.673 two
blocks make the same claim. A max over N blocks is also an order statistic, so
a fixed floor would encode "longer documents are more related". The surface
returns the nearest N with the score and the passage, and the reader judges.

**This is a scan, and the cost model is stated rather than implied.** It is
O(document blocks x project memories) and uses no index: the project predicate
defeats the HNSW path, and forcing the index yields a post-scan filter with no
over-fetch to compensate. Measured on the corpus's largest document (1,132
blocks against the `darkmem` project's 20 memories = 22,640 distance
computations): 89 ms. Correction, 2026-09-05: the multiplier was stated as 50
memories, which is the *corpus-wide* memory count across all eight projects;
the query is project-scoped and that document's project holds 20 (verified
against the live database on 2026-09-05). The measurement was of the real
scoped query -- only the arithmetic beside it was unscoped.

What keeps that viable is the owner's
ruling that documents are never extracted into memories -- a corpus that does
not absorb a hundred thousand machine-extracted propositions is a corpus small
enough to scan. The threshold to revisit is the project's *memory* count.
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

__all__ = ["RelatedMemory", "RelatedMemories", "related_memories_for_document"]


@dataclass(frozen=True)
class RelatedMemory:
    memory_id: str
    content: str
    memory_type: str | None
    status: str
    source: str | None
    project: str
    score: float
    block_id: str
    block_text: str
    span_start: int | None
    span_end: int | None


@dataclass(frozen=True)
class RelatedMemories:
    """Four states, and `comparable_memories` is what separates two of them.

    `comparable_memories` counts the project's memories **at any fingerprint**,
    so it is independent of `embedded` and is answered even when no comparison
    could be made. That independence is the whole point, and it was not true
    until 2026-09-05: the count used to be read out of the shared partition
    the fingerprint resolved to, so a project with no embedded memory reported
    `embedded=False, comparable_memories=0` and the two states below collapsed
    into one on the wire. A zero-memory project then rendered "still being
    embedded" forever, since nothing will ever embed a memory that does not
    exist.

    - `comparable_memories = 0` -- the project holds no memory, so there is
      nothing to compare against and nothing will change that but capturing
      one. A reader must test this **before** `embedded`.
    - `comparable_memories > 0` with `embedded` false -- memories exist but no
      live fingerprint holds vectors for both this document and them yet.
    - `embedded` true with empty `items` -- the comparison ran and returned
      nothing.
    - `embedded` true with items -- the nearest N, with scores.
    """

    document_id: str
    embedded: bool
    comparable_memories: int
    items: tuple[RelatedMemory, ...]


_DOCUMENT_SQL = text(
    "SELECT project FROM documents WHERE id = CAST(:id AS uuid)"
)


def _related_sql(memories_table: str, blocks_table: str) -> str:
    """Interpolated, not bound: these are table identifiers, which no driver
    parameterises. Both come from `child_table` over a fingerprint read out of
    `embedders`, never from a caller."""
    return f"""
        SELECT m.id::text          AS memory_id,
               m.content           AS content,
               m.memory_type       AS memory_type,
               m.status            AS status,
               m.source            AS source,
               m.project           AS project,
               best.score          AS score,
               best.block_id::text AS block_id,
               best.block_text     AS block_text,
               lower(best.span)    AS span_start,
               upper(best.span)    AS span_end
        FROM memories m
        JOIN LATERAL (
            SELECT b.id        AS block_id,
                   b.text      AS block_text,
                   b.char_span AS span,
                   1 - (me.embedding <=> be.embedding) AS score
            FROM {memories_table} me
            JOIN {blocks_table} be ON true
            JOIN blocks b ON b.id = be.block_id
            WHERE me.memory_id = m.id
              AND b.document_id = CAST(:document_id AS uuid)
            ORDER BY score DESC
            LIMIT 1
        ) best ON true
        WHERE m.project = :project
        ORDER BY best.score DESC, m.id
        LIMIT :limit
    """


# Fingerprint-independent on purpose: this answers "does the project hold
# anything to compare against", which is a question about the corpus, not
# about what has been embedded. Counting inside the shared partition instead
# made the zero-memory and not-yet-embedded states indistinguishable.
_COMPARABLE_SQL = text("SELECT count(*) FROM memories WHERE project = :project")


async def related_memories_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> RelatedMemories:
    """Which memories are nearest this document, and which passage matched.

    Scoped to the document's own project in SQL, for the reason
    `connections_for_document` gives: a cross-project result would breach the
    isolation boundary doc 18 §8 calls a security one, in the surface whose
    whole purpose is to surface rows the reader had not thought of. Filtering
    the returned page instead would silently under-fill it.
    """
    key = str(document_id)
    project = (await session.execute(
        _DOCUMENT_SQL, {"id": key}
    )).scalar_one_or_none()
    if project is None:
        return RelatedMemories(
            document_id=key, embedded=False, comparable_memories=0, items=(),
        )

    comparable = int(await session.scalar(
        _COMPARABLE_SQL, {"project": project},
    ) or 0)

    fingerprint = await resolve_shared_fingerprint(
        session, document_id=key, project=project, counterpart="memory",
    )
    if fingerprint is None:
        return RelatedMemories(
            document_id=key,
            embedded=False,
            comparable_memories=comparable,
            items=(),
        )

    memories_table = child_table("memory_embeddings", fingerprint)
    blocks_table = child_table("block_embeddings", fingerprint)

    rows = (await session.execute(
        text(_related_sql(memories_table, blocks_table)),
        {"document_id": key, "project": project, "limit": limit},
    )).mappings().all()

    return RelatedMemories(
        document_id=key,
        embedded=True,
        comparable_memories=comparable,
        items=tuple(
            RelatedMemory(
                memory_id=row["memory_id"],
                content=row["content"],
                memory_type=row["memory_type"],
                status=row["status"],
                source=row["source"],
                project=row["project"],
                score=float(row["score"]),
                block_id=row["block_id"],
                block_text=row["block_text"],
                span_start=row["span_start"],
                span_end=row["span_end"],
            )
            for row in rows
        ),
    )
