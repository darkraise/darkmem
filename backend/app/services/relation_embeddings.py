"""The ``relation_embeddings`` writer and its Tier-C refresh (doc 07 §4, T2.49).

The dual-level retrieval channel's global arm ranks over relation vectors
rather than memory vectors: a query about "what replaced Redis" matches the
*edge* `redis REPLACED_BY valkey` even when no single memory's text says it
that way. This module writes those vectors. The channel that spends them is
T2.49's sibling work in the retrieval path; what lands here is the artefact
and the job that keeps it current, which is the half doc 07 §4 assigns to the
artefact-refresh job rather than to Phase 5.

**Off the hot path, never inside Phase 5** (doc 07 §4, invariant 15). Writing
a relation vector during ingest would put an extra embed round-trip on every
capture, for a signal retrieval does not read until its flag is on.

**One fingerprint per read and per write** (invariant 2), and the mechanism is
the *table*, not a predicate. Every statement resolves its table through
`child_table(PARENT_TABLE, fingerprint)`, so a row under another fingerprint is
not merely filtered out — it is in a different table and unreachable. The
`fingerprint = :fp` clauses that also appear are redundant by construction and
kept only because the column is part of the primary key; removing them changes
no result, and a mutation drill confirms it. What must never be "simplified" is
the table resolution: hardcode one child table and every read silently answers
about the wrong embedder.

**The row's text is derived, not stored, and that is why the refresh has two
arms.** A relation embeds as ``"<source name> <rel_type> <target name>"``, and
the partition has no column holding that string — so nothing on disk can tell
you that an entity was renamed under an already-embedded relation, leaving a
vector that describes text no longer produced by the same row. The *missing*
arm is exact (a `LEFT JOIN` finds every relation with no vector under this
fingerprint). The *rotation* arm is the backstop that makes renames converge:
it re-embeds the oldest slice of already-embedded rows, so a drifted vector is
corrected within one full rotation rather than never. This is the same
exact-arm-plus-slow-arm shape `verification_recompute` carries, and for the
same reason — an exact arm cannot see a change that leaves no trace.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

PARENT_TABLE = "relation_embeddings"

RELATION_EMBEDDING_JOB_KEY = "relation_embedding_refresh"

DEFAULT_EMBED_CHUNK = 20
DEFAULT_EMBED_CONCURRENCY = 1
DEFAULT_MISSING_BATCH = 200
DEFAULT_ROTATION_BATCH = 50

RELATION_EMBEDDING_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="missing_batch", label="New Relations Per Run",
        default=DEFAULT_MISSING_BATCH, min=0, max=5_000,
        help=(
            "Relations with no vector under the active fingerprint embedded "
            "per run. This arm is exact: it drains to zero and stays there."
        ),
    ),
    FieldDescriptor(
        key="rotation_batch", label="Re-embedded Per Run",
        default=DEFAULT_ROTATION_BATCH, min=0, max=5_000,
        help=(
            "Already-embedded relations refreshed per run, oldest first. The "
            "backstop for an entity renamed under an embedded relation, which "
            "leaves no trace the exact arm could find. 0 disables it."
        ),
    ),
    FieldDescriptor(
        key="embed_chunk", label="Embed Chunk Size",
        default=DEFAULT_EMBED_CHUNK, min=1, max=200,
        help="Texts per embedder call.",
    ),
]


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


@dataclass
class RefreshOutcome:
    missing_written: int = 0
    rotated: int = 0
    fingerprint: str | None = None

    @property
    def total(self) -> int:
        return self.missing_written + self.rotated


# The embedded text, assembled in SQL so the ordering, the join and the text
# are one statement — a Python-side assembly would need a second round trip per
# batch and could silently pair a vector with the wrong row's id.
_RELATION_TEXTS = """
    SELECT CAST(r.id AS text) AS relation_id,
           s.name || ' ' || r.rel_type || ' ' || t.name AS phrase
    FROM entity_relations r
    JOIN entities s ON s.id = r.source_entity_id
    JOIN entities t ON t.id = r.target_entity_id
    WHERE r.id = ANY(CAST(:ids AS uuid[]))
    ORDER BY r.id
"""


def _missing_sql(table: str) -> str:
    return f"""
        SELECT CAST(r.id AS text) AS relation_id
        FROM entity_relations r
        LEFT JOIN {table} e
               ON e.relation_id = r.id
              AND e.fingerprint = CAST(:fp AS text)
        WHERE e.relation_id IS NULL
        ORDER BY r.created_at, r.id
        LIMIT CAST(:limit AS int)
    """


def _rotation_sql(table: str) -> str:
    return f"""
        SELECT CAST(e.relation_id AS text) AS relation_id
        FROM {table} e
        WHERE e.fingerprint = CAST(:fp AS text)
        ORDER BY e.created_at, e.relation_id
        LIMIT CAST(:limit AS int)
    """


async def embed_relations(
    session: AsyncSession,
    llm,
    *,
    relation_ids: Sequence[str],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed ``"src rel_type tgt"`` for each relation into the active partition.

    ``None`` means nothing was embedded — an empty request, or ids that name no
    surviving relation — and therefore that no fingerprint was measured. It is
    not a failure: a caller draining a work set legitimately finds it empty.

    Re-embedding refreshes the vector and leaves ``created_at`` at the first
    write, so the column records when the relation entered the partition. The
    rotation arm depends on that: ordering by a last-touched timestamp would
    make the rotation re-read whatever it just wrote and never advance.

    **This may commit the caller's transaction**, for the reason
    `triple_embeddings.embed_facts` records: first contact with an unknown
    fingerprint runs the child-table DDL through `embedder_registry.register`,
    which commits on this session.
    """
    ids = [str(rid) for rid in relation_ids]
    if not ids:
        return None

    rows = (await session.execute(text(_RELATION_TEXTS), {"ids": ids})).mappings().all()
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["phrase"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"relation_embeddings: the embedder returned {len(vectors)} vectors "
            f"for {len(rows)} relations; refusing to write vectors under ids "
            "they may not belong to"
        )

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (relation_id, fingerprint, embedding)
                VALUES (CAST(:rid AS uuid), CAST(:fp AS text),
                        CAST(:embedding AS vector))
                ON CONFLICT (relation_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "rid": row["relation_id"],
                "fp": fingerprint,
                "embedding": str(list(vector)),
            },
        )

    return WriteResult(fingerprint=fingerprint, written=len(rows))


async def _ensure_partition(session: AsyncSession, fingerprint: str) -> None:
    from app.services.embedder_registry import (  # noqa: PLC0415
        EmbedderInfo, embedder_registry, parse_fingerprint,
    )
    if embedder_registry.is_known(fingerprint):
        return
    model_id, dims = parse_fingerprint(fingerprint)
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"),
    )


async def resolve_read_fingerprint(session: AsyncSession, llm) -> str:
    """The fingerprint a partition read may safely key on.

    Delegated, never re-derived. ``llm_fingerprint()`` is a pure formatter over
    static config and can name a partition no embed ever wrote to — the ``|0``
    sentinel under unset dimensions, or a syntactically valid but permanently
    empty table under a wrong positive one (T2.68, T2.83). Here that failure
    would be especially quiet: the missing-vector arm would find *every*
    relation missing under a phantom fingerprint, re-embed the whole graph into
    a table nothing reads, and report a healthy row count every run. Raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved` rather than
    proceeding on an unconfirmed key.
    """
    from app.repositories.vector import PostgresVectorRepository  # noqa: PLC0415

    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


async def relations_missing_vectors(
    session: AsyncSession, fingerprint: str, limit: int
) -> list[str]:
    """Relations with no vector under this fingerprint, oldest first.

    Keyed on one fingerprint on both sides of the join: a relation embedded
    under a *previous* embedder is missing under the current one, and must be
    re-embedded rather than counted as covered (invariant 2).
    """
    if limit <= 0:
        return []
    table = child_table(PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(_missing_sql(table)), {"fp": fingerprint, "limit": limit},
    )
    return [row[0] for row in rows]


async def relations_to_rotate(
    session: AsyncSession, fingerprint: str, limit: int
) -> list[str]:
    """The oldest already-embedded slice, for the drift backstop."""
    if limit <= 0:
        return []
    table = child_table(PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(_rotation_sql(table)), {"fp": fingerprint, "limit": limit},
    )
    return [row[0] for row in rows]


async def refresh_relation_embeddings(
    session: AsyncSession,
    llm,
    *,
    missing_batch: int = DEFAULT_MISSING_BATCH,
    rotation_batch: int = DEFAULT_ROTATION_BATCH,
    chunk_size: int = DEFAULT_EMBED_CHUNK,
) -> RefreshOutcome:
    """One tick of both arms.

    The exact arm runs first and the rotation arm is skipped when it wrote
    anything: while a backlog of never-embedded relations exists, spending the
    run's budget re-embedding rows that already have vectors would starve the
    arm that has actual coverage to add.

    The fingerprint is resolved **by data** through
    :func:`resolve_read_fingerprint`, never from static config. An install
    where nothing has been embedded yet has no fingerprint to key on, and this
    returns an empty outcome rather than inventing one — the arms have nothing
    to cover until a real embed exists.
    """
    from app.repositories.vector import (  # noqa: PLC0415
        EmbedderFingerprintUnresolved,
    )

    outcome = RefreshOutcome()
    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info(
            "relation_embedding_refresh: no fingerprint holds data yet; "
            "nothing to refresh"
        )
        return outcome
    await _ensure_partition(session, fingerprint)
    outcome.fingerprint = fingerprint

    missing = await relations_missing_vectors(session, fingerprint, missing_batch)
    if missing:
        written = await embed_relations(
            session, llm, relation_ids=missing, chunk_size=chunk_size,
        )
        outcome.missing_written = written.written if written else 0
        return outcome

    rotating = await relations_to_rotate(session, fingerprint, rotation_batch)
    if rotating:
        written = await embed_relations(
            session, llm, relation_ids=rotating, chunk_size=chunk_size,
        )
        outcome.rotated = written.written if written else 0

    return outcome
