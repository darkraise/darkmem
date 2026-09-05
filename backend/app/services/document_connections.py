"""Documents nearest this one, by cosine over block vectors (§4).

The sibling of `document_related`, one hop further out: that module asks which
*memories* resemble this document, this asks which other *documents* do.

Everything `document_related` decides still applies -- no LLM call,
max-aggregation over the argmax block pair, no floor, the fingerprint derived
from data, project scoping in SQL -- but the query shape does not, on measured
grounds. An exact same-table self-join (both sides are the same partition) was
shipped first and measured on the live corpus at 166.5s for the largest filed
document, three orders of magnitude past `document_related`'s 89ms, because
here *both* sides of the join scale with block count rather than one side
being a small memory table. That is a real cost, not a tuning miss, and it is
the reason this module runs an ANN probe per block instead: measured on the
same corpus, 494ms typical and 3.4s worst case.

**This surface is therefore approximate where `document_related` is exact.**
`ORDER BY t.embedding <=> m.embedding LIMIT N` per probe is what lets the
planner use the HNSW index; ordering by the derived `score DESC` instead
defeats it and falls back to the same exact scan this module replaced.
`app/database.py` sets `hnsw.ef_search = 100` and `hnsw.iterative_scan =
relaxed_order` connection-wide -- the same tunable `search_blocks` (TH1.06)
already accepts for the block channel, so trading exactness for latency here
is consistent with the rest of the codebase rather than a new risk. The named
cost: a true nearest block can be missed, which can drop a marginal document
out of the results entirely. Wider is more correct and slower; this module
does not tune that trade further than the one measured above.

**No block cap.** An earlier design capped probes per document and ordered by
block count to decide who gets probed at reduced depth; that ordering was
measured to drop the *best* match on exactly the documents where the cap
bound -- one measured case moved 0.843 -> 0.505. The uncapped worst case
(3.4s on the corpus's largest document, affecting a small minority of
documents) is judged worth it against silently returning the wrong answer to
correctly-shaped queries.

**Each probe fetches 10 nearest, not 1**, because the probe is unscoped: it
is not restricted to the *other* documents this call cares about, so a
probe's ten nearest blocks can be entirely the queried document's own blocks
(self-matches) or blocks in a different project. Those rows survive into the
intermediate result and are then correctly dropped by the same project-scope
and self-exclusion predicates `document_related` uses, but a probe that only
ever returned its single nearest neighbour would forfeit any real
cross-document match sitting just past a self-match, undercounting matches
disproportionately on documents whose blocks closely resemble each other.

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

# Nearest per probe, not the single nearest -- the probe is unscoped (see the
# module docstring), so a self-match or a foreign-project match can occupy
# the top slot without leaving room for the cross-document match this surface
# exists to find.
_PROBE_LIMIT = 10


def _connections_sql(blocks_table: str) -> str:
    """Interpolated, not bound: a table identifier from `child_table` over a
    fingerprint read out of `embedders`, never from a caller."""
    return f"""
        WITH mine AS (
            SELECT b.id AS block_id, b.text AS block_text, be.embedding AS embedding
            FROM {blocks_table} be
            JOIN blocks b ON b.id = be.block_id
            WHERE b.document_id = CAST(:document_id AS uuid)
        ),
        hits AS (
            SELECT m.block_id, m.block_text,
                   p.document_id, p.other_block_id, p.other_block_text, p.score
            FROM mine m
            CROSS JOIN LATERAL (
                SELECT tb.document_id                    AS document_id,
                       tb.id                              AS other_block_id,
                       tb.text                             AS other_block_text,
                       1 - (t.embedding <=> m.embedding)   AS score
                FROM {blocks_table} t
                JOIN blocks tb ON tb.id = t.block_id
                ORDER BY t.embedding <=> m.embedding
                LIMIT {_PROBE_LIMIT}
            ) p
        ),
        best AS (
            SELECT DISTINCT ON (hits.document_id)
                   hits.document_id, hits.score, hits.block_id, hits.block_text,
                   hits.other_block_id, hits.other_block_text
            FROM hits
            ORDER BY hits.document_id, hits.score DESC
        )
        SELECT other.id::text            AS document_id,
               other.title                AS title,
               best.score                 AS score,
               best.block_id::text        AS block_id,
               best.block_text            AS block_text,
               best.other_block_id::text  AS other_block_id,
               best.other_block_text      AS other_block_text
        FROM best
        JOIN documents other ON other.id = best.document_id
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
