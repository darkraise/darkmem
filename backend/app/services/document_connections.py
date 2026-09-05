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
the reason this module runs an ANN probe per block instead.

**Measured cost of the statement actually shipped** (three runs each, with
`app/database.py`'s own connection settings applied -- `hnsw.ef_search =
100`, `hnsw.iterative_scan = relaxed_order`; a number measured without them,
e.g. in a bare `psql` session that never issued those `SET`s, is not this
surface's number, since pgvector 0.8.2 registers those GUCs lazily and
silently falls back to its 40/off defaults until something sets them):
320-623ms on a 282-block document, 2,739-3,964ms on the corpus's 1,132-block
outlier (`E2-truth-core`). A narrower query -- projecting only ids and score,
not the full block-pair evidence this statement actually returns -- measures
faster than the statement above only on the large document (2,085ms vs.
2,739-3,964ms unfiltered); on the 282-block document it is in fact slower
(785ms vs. 320-623ms) -- 785ms is a single reading, not a three-run range, but
it sits 26% above the top of the shipped statement's 320-623ms range, which is
a real gap rather than noise at that size. Correction, 2026-09-05: an earlier
version of this paragraph called the narrower query faster without that
qualifier, which held for the 1,132-block document and did not for the
282-block one. Filtered numbers
(586ms / 2,173ms, after the document-exclusion predicate below existed) are a
comparison of what adding that predicate costs on top of the narrower
projection, not a second measurement of this surface's own number.

**This surface is therefore approximate where `document_related` is exact,
in the same way the rest of the block channel already is.** `search_blocks`
(TH1.06) runs its own ANN probe under the same connection-wide `ef_search` /
`iterative_scan` setting -- it does not itself configure or accept either
one, both live only in `app/database.py` -- so this module is not taking on a
new kind of risk, it is the second caller of a trade the codebase already
made once. `ORDER BY t.embedding <=> m.embedding LIMIT N` per probe is what
lets the planner use the HNSW index; ordering by the derived `score DESC`
instead defeats it and falls back to the same exact scan this module
replaced. The named cost: `ef_search=100` can still miss the true nearest
block, which can drop a marginal document out of the results entirely. Wider
is more correct and slower; this module does not tune that trade further
than the one measured above.

**No block cap.** An earlier design capped probes per document and ordered by
block count to decide who gets probed at reduced depth; that ordering was
measured to drop the *best* match on exactly the documents where the cap
bound -- one measured case moved 0.843 -> 0.505. The uncapped worst case
(measured above) is judged worth it against silently returning the wrong
answer to correctly-shaped queries.

**The LATERAL excludes the queried document's own blocks**
(`tb.document_id <> :document_id`), because leaving them in wastes probe
slots on matches the outer `WHERE` was always going to discard anyway: a
document full of near-duplicate blocks (repeated headings, short list items)
can fill all ten slots with its own text before a single cross-document
candidate is considered, silently returning no connections for exactly the
documents most likely to need finding one. Because `iterative_scan =
relaxed_order` really is on for every application connection, adding this
predicate inside the LATERAL does not turn the ANN probe into a post-filter
over ten raw candidates -- the index scan itself keeps expanding until it has
ten survivors -- so on the narrower-projection comparison above it cost
nothing measurable (785ms unfiltered vs 586ms filtered on the 282-block
document; 2,085ms vs 2,173ms, within noise, on the 1,132-block one). The
outer query also excludes the queried document (`other.id <>
:document_id`), which is now redundant with the LATERAL's own exclusion --
kept as a second, independent layer rather than removed; see the comment
beside it.

**Each probe still fetches 10 nearest, not 1, and a truncation risk remains
even with the document exclusion**: the probe is not scoped to the calling
document's own project, so all ten slots can still be consumed by another
*project's* blocks -- correctly dropped by the outer `other.project =
:project` predicate, but at the cost of returning nothing for a real
same-project match that happened to rank behind ten foreign-project
near-duplicates. `search_blocks`'s own remedy for exactly this shape is its
over-fetch multiplier (`SEMANTIC_FETCH_MULTIPLIER`,
`block_embeddings.py:302-333`): its project predicate sits *inside* the same
ANN statement's `WHERE`, evaluated as a post-scan filter over the raw HNSW
candidate stream, so its `LIMIT` asks for `limit * multiplier` rows to
compensate for however many of those candidates the project filter is going
to discard, then the caller slices the survivors back down to `limit`
afterward. This module does not adopt that pattern because the measured cost
above does not warrant it yet, but it is the documented next lever if a
corpus with heavier cross-project density ever needs it.

**Cold-cache cost is not yet measured under the app's own settings.** An
earlier 12.2s / 1.3-1.4s cold-vs-warm pair was measured in a bare `psql`
session before the `ef_search` / `iterative_scan` correction above landed --
the exact basis this docstring's own first paragraph says is not this
surface's number -- so it is not repeated here as a comparable figure.
`block_embeddings__qwen3_embedding_0_6b_1024` is ~665MB (doc CLAUDE.md,
backup sizing note), so a cold-cache cost is a real question whenever that
partition is evicted -- a nightly backup dump reading through it or
`block_embedding_refresh` rewriting it, not only a process restart -- it has
simply not been measured yet with the settings this surface actually runs
under.

The former basis was `entities.memory_ids` over the memories a lift minted.
Nothing is lifted any more, so that walk would return an empty list forever.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_similarity import resolve_shared_fingerprint
from app.services.embedder_registry import child_table

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

# Nearest per probe, not the single nearest -- the probe excludes the
# queried document's own blocks but is not scoped to its project (see the
# module docstring), so a foreign-project match can still occupy a slot
# without leaving room for the cross-document match this surface exists to
# find.
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
                WHERE tb.document_id <> CAST(:document_id AS uuid)
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
          -- Deliberately redundant with the LATERAL's own document exclusion above -- a second layer, not dead weight.
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
