"""The ``block_embeddings`` writer — first writer to T0.13's inert template.

Doc 16 §3 makes block embedding part of the document ingestion variant: parse,
strip-before-rewrite, then embed each block into the per-fingerprint
``block_embeddings__<slug>`` partition. This module is that write, following
the shape ``relation_embeddings.embed_relations`` and
``triple_embeddings.embed_facts`` already established for the sibling
target-new families — a batch embed call, a register-before-insert partition
guarantee, and an upsert keyed on ``(block_id, fingerprint)``.

**Register-before-insert is not advisory.** ``ensure_partition`` runs before
the first statement that names the child table; skip it and the insert fails
outright with an undefined-relation error rather than silently landing
somewhere else, because the table does not exist until the registry creates
it. What must never be "simplified" away is the ordering: the register call
has to complete (and commit — see below) before any ``INSERT`` reaches the
table it creates.

**Naming goes through ``child_table(PARENT_TABLE, fingerprint)`` only**
(invariant 2). ``PARENT_TABLE`` is the one string literal naming this family;
every table reference in this module resolves through it, never through an
inline f-string of the parent name.

**No cross-fingerprint comparison.** Every statement here scopes to one
resolved fingerprint's own child table — a different fingerprint is a
different, unrelated table, not a filtered subset of this one, so there is no
predicate that could leak a comparison across two partitions even by mistake.
``block_vectors`` reads back exactly the fingerprint it was given and nothing
else, which is what a caller building a same-fingerprint ANN probe (TH1.06)
needs and all it needs.

**This module does not decide *when* a block gets embedded.** ``embed_blocks``
takes the ids to embed and embeds exactly those; nothing here re-derives a
missing-vectors work set or hooks into ``file_document`` / ``block_pipeline``.
Wiring this into the ingestion hot path (or a refresh job, if that turns out
to be the right shape) is downstream work, not this task's.

**This may commit the caller's transaction**, for the same reason
``triple_embeddings.embed_facts`` and ``relation_embeddings.embed_relations``
both record: first contact with an unknown fingerprint runs the child-table
DDL through ``embedder_registry.register``, which commits on this session so
the partition's inline ``REFERENCES blocks`` FK can take a lock that would
otherwise conflict with row locks the caller already holds on its own
uncommitted block inserts. A caller that needs the surrounding work to stay
rollback-able must embed after it commits, not before.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import SEMANTIC_FETCH_MULTIPLIER, PostgresVectorRepository
from app.services.embedder_registry import child_table

logger = logging.getLogger(__name__)

PARENT_TABLE = "block_embeddings"

DEFAULT_EMBED_CHUNK = 32
DEFAULT_EMBED_CONCURRENCY = 2


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


_BLOCK_TEXTS = """
    SELECT CAST(id AS text) AS block_id, text
    FROM blocks
    WHERE id = ANY(CAST(:ids AS uuid[]))
    ORDER BY id
"""


async def embed_blocks(
    session: AsyncSession,
    llm,
    *,
    block_ids: Sequence[str],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed each block's ``text`` into the active partition.

    ``None`` means nothing was embedded — an empty request, or ids that name
    no surviving block (a re-ingest may have stripped them since the caller
    listed them) — and therefore that no fingerprint was measured. It is not a
    failure: a caller draining a work set legitimately finds it empty.

    Re-embedding an already-embedded block refreshes its vector and leaves
    ``created_at`` at the first write, matching the sibling writers' contract:
    the column records when the block entered the partition, not when it was
    last touched.

    Blocks whose ``text`` is empty are embedded like any other row — an empty
    string is a legitimate embedder input, and a writer silently skipping it
    would leave a retrievable block with no vector and no record of why.
    """
    ids = [str(block_id) for block_id in block_ids]
    if not ids:
        return None

    rows = (await session.execute(text(_BLOCK_TEXTS), {"ids": ids})).mappings().all()
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["text"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"block_embeddings: the embedder returned {len(vectors)} vectors "
            f"for {len(rows)} blocks; refusing to write vectors under ids "
            "they may not belong to"
        )

    await ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (block_id, fingerprint, embedding)
                VALUES (CAST(:bid AS uuid), CAST(:fp AS text), CAST(:embedding AS vector))
                ON CONFLICT (block_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "bid": row["block_id"],
                "fp": fingerprint,
                "embedding": str(list(vector)),
            },
        )

    return WriteResult(fingerprint=fingerprint, written=len(rows))


async def ensure_partition(session: AsyncSession, fingerprint: str) -> None:
    """Idempotently register `fingerprint` and create its per-family child
    tables if they do not already exist.

    **Exported (no leading underscore) because it is part of this family's
    contract, not merely an internal implementation detail** (T-doc-door.6
    review, round 4, 2026-08-24): both `document_door.put_document`'s
    ``unchanged`` repair and `block_embedding_refresh`'s sweep must guarantee
    a fingerprint resolved from a real embed call — which, unlike a
    data-probe result, is not guaranteed to already be registered — has a
    child table before they run their own anti-join read against it,
    *before* either of them reaches `embed_blocks` (which already calls this
    internally on the write side). Two family-external callers needing the
    same guarantee is what promotes a helper from private to part of the
    contract; sibling families' own `_ensure_partition` copies
    (`relation_embeddings.py`, `triple_embeddings.py`, `entity_anchoring.py`)
    stay private and un-shared, because nothing outside each of those
    modules needs to reach for one directly.
    """
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
    """A cheap, data-probe fingerprint resolution for this family — never an
    embed call.

    Delegated to the same resolver every other family uses, never re-derived:
    ``llm_fingerprint()`` is a pure formatter over static config and can name a
    partition no real embed ever wrote to, so this defers to
    :meth:`PostgresVectorRepository.resolve_read_fingerprint`'s own
    data-probe algorithm exactly as every sibling family does (it checks the
    ``memory_embeddings`` partition, since that is where real embed traffic
    is heaviest on almost every install). Raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved` rather
    than proceeding on an unconfirmed key.

    **Neither of this family's two callers use this anymore** (T-doc-door.6
    review, round 3, 2026-08-24): both `block_embedding_refresh`'s sweep and
    `document_door.put_document`'s ``unchanged`` gap-fill repair resolve from
    :func:`resolve_active_fingerprint` instead, because both exist to fill a
    partition that may be EMPTY, which is exactly the case any data probe —
    of any family — is biased against finding (see
    :func:`resolve_active_fingerprint`'s docstring). This function is kept
    for a caller that only needs "some live, already-populated fingerprint
    for this family" and can accept a data probe's bias, the same shape
    every sibling family's own callers use — no such caller exists in this
    family today. A future caller of that shape should use this rather than
    re-deriving it; a caller whose job is to fill gaps should use
    :func:`resolve_active_fingerprint`.
    """
    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


# Never written anywhere and never compared against real block text — its
# only job is to make the active embedder name the fingerprint it would
# currently produce, the same role a real search query plays in
# `BlockQueryService.search`.
_ACTIVE_FINGERPRINT_PROBE_TEXT = "darkmem block_embeddings active-fingerprint probe"


async def resolve_active_fingerprint(llm) -> str:
    """The fingerprint the active embedder produces right now, established
    the same way retrieval does (`BlockQueryService.search`, which embeds the
    query and reads whatever fingerprint that produced): a real embed call,
    never a data probe.

    **This exists because a data probe cannot correctly serve a caller whose
    job is to fill an EMPTY partition** (T-doc-door.6 review, rounds 2-3,
    2026-08-24). "Which live fingerprint holds data" is answered correctly by
    :func:`resolve_read_fingerprint` for a caller that only needs *some*
    already-populated partition — every sibling family's own resolver callers
    are that shape. But `block_embedding_refresh`'s corpus-wide sweep and
    `document_door.put_document`'s single-document ``unchanged`` repair are
    both the opposite shape: their entire purpose is finding and filling the
    gaps in a partition that may hold nothing at all for the fingerprint that
    actually matters (the one the active embedder produces right now, which
    is the one retrieval will read). A data probe of ANY family, asked "which
    live fingerprint has data", is structurally biased toward a stale
    sibling over the correct-but-still-empty one — concretely, after an
    embedder rotation, the round-2 review's headline case. Both callers
    resolve here instead, so the fingerprint they act on is always the one a
    real query would land on too.

    A real embed always yields a real fingerprint, so there is no
    "unconfirmed"/bootstrap case to guard against the way
    :func:`resolve_read_fingerprint` does — this never raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved`.

    **The cost is one embed call per caller-defined unit of work, always —
    never skipped, even when there is nothing to repair** (T-doc-door.6
    review, round 4, 2026-08-24). For `block_embedding_refresh`'s sweep that
    unit is one scheduled run (at most once every
    ``BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS``), so the cost is bounded and
    small. For `document_door.put_document`'s ``unchanged`` repair the unit
    is one write-door request: every re-push of an already-fully-embedded,
    unchanged document now spends one embed call it would not have spent
    before this function existed, where it previously spent a cheap database
    probe instead. A caller re-pushing N unchanged documents in a pass pays N
    embed calls, unconditionally. That is the traded-away cost this function
    is named for taking on, not a side effect to discover later.
    """
    _, fingerprint = await llm.embed(_ACTIVE_FINGERPRINT_PROBE_TEXT)
    return fingerprint


async def search_blocks(
    session: AsyncSession,
    *,
    vector: Sequence[float],
    fingerprint: str,
    project: str,
    limit: int = 20,
    document_id: str | None = None,
) -> list[dict]:
    """One ANN probe over ``fingerprint``'s partition, scoped in SQL (TH1.06).

    **Every scope predicate is in this statement, never applied in Python
    afterwards** (T1.29a–c). The partition carries no ``project`` column — it
    cannot, since a block's project belongs to its document — so scoping means
    joining ``blocks`` and ``documents`` and filtering there. Filtering the
    returned page instead would silently under-fill it: rows from other
    projects would consume the LIMIT and then be discarded.

    That join makes the predicate a **post-scan filter** over the HNSW
    candidate stream, exactly as T1.29a records for the semantic channel, so
    what compensates is the fetch multiplier, not an index plan. The project
    predicate is never absent, so the probe always over-fetches and trims —
    and it borrows `SEMANTIC_FETCH_MULTIPLIER` rather than declaring its own,
    because two copies of one tuning constant drift apart in exactly the way
    the RRF constant already did.

    ``char_span`` is decomposed here rather than handed out as a range type:
    the caller needs two integers to slice the source, and asyncpg would give
    it a driver object nothing downstream speaks.
    """
    table = child_table(PARENT_TABLE, fingerprint)

    # An install that has never embedded a block has no child table, and that
    # is an empty corpus rather than a fault: the probe must answer "nothing
    # matched", not raise UndefinedTable at whoever asked. Checked explicitly
    # rather than caught, so a genuine query failure against a table that DOES
    # exist still raises — swallowing the exception would make the two
    # indistinguishable, which is the failure this channel's one-arm rule is
    # about (TH1.08 found this; the channel's own tests all seeded first).
    exists = (await session.execute(
        text("SELECT to_regclass(:name)"), {"name": table},
    )).scalar_one_or_none()
    if exists is None:
        return []

    params: dict = {
        "vec": str(list(vector)),
        "project": project,
        "limit": limit * SEMANTIC_FETCH_MULTIPLIER,
    }
    filters = ""
    if document_id is not None:
        filters = " AND d.id = CAST(:document_id AS uuid)"
        params["document_id"] = str(document_id)

    result = await session.execute(
        text(f"""
            SELECT CAST(b.id AS text)          AS block_id,
                   CAST(d.id AS text)          AS document_id,
                   d.project                   AS project,
                   d.uri                       AS uri,
                   b.type                      AS type,
                   b.text                      AS text,
                   b.order_index               AS order_index,
                   lower(b.char_span)          AS span_start,
                   upper(b.char_span)          AS span_end,
                   1 - (e.embedding <=> CAST(:vec AS vector)) AS score
            FROM {table} e
            JOIN blocks b    ON b.id = e.block_id
            JOIN documents d ON d.id = b.document_id
            WHERE d.project = :project {filters}
            ORDER BY e.embedding <=> CAST(:vec AS vector)
            LIMIT :limit
        """),
        params,
    )
    return [dict(mapping) for mapping in result.mappings()][:limit]


async def block_vectors(
    session: AsyncSession, *, fingerprint: str, block_ids: Sequence[str],
) -> dict[str, list[float]]:
    """Each block's vector from ``fingerprint``'s own partition, in one read.

    Never falls back to another fingerprint: a cross-fingerprint cosine has no
    defined meaning, so a block with no row under this fingerprint is simply
    absent from the result rather than probed somewhere else.
    """
    ids = [str(block_id) for block_id in block_ids]
    if not ids:
        return {}
    table = child_table(PARENT_TABLE, fingerprint)
    result = await session.execute(
        text(
            f"SELECT CAST(block_id AS text) AS block_id, embedding::text AS embedding_text "
            f"FROM {table} WHERE block_id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": ids},
    )
    return {
        mapping["block_id"]: [float(v) for v in mapping["embedding_text"].strip("[]").split(",")]
        for mapping in result.mappings()
    }
