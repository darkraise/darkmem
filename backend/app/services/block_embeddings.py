"""The ``block_embeddings`` writer — first writer to T0.13's inert template.

Doc 16 §3 makes block embedding part of the document ingestion variant: parse,
strip-before-rewrite, then embed each block into the per-fingerprint
``block_embeddings__<slug>`` partition. This module is that write, following
the shape ``relation_embeddings.embed_relations`` and
``triple_embeddings.embed_facts`` already established for the sibling
target-new families — a batch embed call, a register-before-insert partition
guarantee, and an upsert keyed on ``(block_id, fingerprint)``.

**Register-before-insert is not advisory.** ``ensure_registered`` runs before
the first statement that names the child table; skip it and the insert fails
outright with an undefined-relation error rather than silently landing
somewhere else, because the table does not exist until the registry creates
it. What must never be "simplified" away is the ordering: the register call
has to complete (and commit — see below) before any ``INSERT`` reaches the
table it creates.

**Naming goes through ``child_table(parent, fingerprint)`` only**
(invariant 2). ``PARENT_TABLE`` and ``PAGE_PARENT_TABLE`` are the only string
literals naming these families; every table reference in this module resolves
through one of them, never through an inline f-string of the parent name.

**Two families, one writer.** A block belongs to a document or to a page, and
the two own separate partition families: the document family carries one HNSW
index per child that every document ANN read filters the owner *after*, so a
growing notes corpus sharing it would starve document search of candidates.
``embed_blocks`` therefore takes the family to write as ``parent``,
defaulting to the document one. The read side (``search_blocks``) is
document-only and takes no ``parent``: it joins ``documents``, and page
retrieval has no door yet.

**No cross-fingerprint comparison.** Every statement here scopes to one
resolved fingerprint's own child table — a different fingerprint is a
different, unrelated table, not a filtered subset of this one, so there is no
predicate that could leak a comparison across two partitions even by mistake.

**This module does not decide *when* a block gets embedded.** ``embed_blocks``
takes the ids to embed and embeds exactly those; nothing here re-derives a
missing-vectors work set or hooks into ``file_document`` / ``block_pipeline``.
Wiring this into the ingestion hot path (or a refresh job, if that turns out
to be the right shape) is downstream work, not this task's.

**This may commit the caller's transaction**, for the same reason
``triple_embeddings.embed_facts`` and ``relation_embeddings.embed_relations``
both record: first contact with an unknown fingerprint runs the child-table
DDL through ``embedder_registry.ensure_registered``, which commits on this session so
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

from app.repositories.vector import SEMANTIC_FETCH_MULTIPLIER
from app.services.embedder_registry import child_table, ensure_registered

logger = logging.getLogger(__name__)

PARENT_TABLE = "block_embeddings"
PAGE_PARENT_TABLE = "page_embeddings"

DEFAULT_EMBED_CHUNK = 32
DEFAULT_EMBED_CONCURRENCY = 2
# Rows per vector INSERT; the arrays are bound as two parameters, so this
# bounds one statement's payload rather than its parameter count.
INSERT_CHUNK = 500


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


_BLOCK_TEXTS = """
    SELECT CAST(id AS text) AS block_id, text, document_id, page_id
    FROM blocks
    WHERE id = ANY(CAST(:ids AS uuid[]))
    ORDER BY id
"""


async def embed_blocks(
    session: AsyncSession,
    llm,
    *,
    block_ids: Sequence[str],
    parent: str = PARENT_TABLE,
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

    Results for deleted or changed blocks are skipped. Current text is read
    under the owner's mutation lock after the provider returns, and that lock
    remains held through the vector write and the caller's commit.

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

    await ensure_registered(session, fingerprint)
    await _lock_owners(session, rows)
    current = {
        row["block_id"]: row["text"]
        for row in (await session.execute(text(_BLOCK_TEXTS), {"ids": ids})).mappings()
    }
    fresh = [
        (row["block_id"], str(list(vector)))
        for row, vector in zip(rows, vectors)
        if current.get(row["block_id"]) == row["text"]
    ]
    await write_vectors(session, child_table(parent, fingerprint), fingerprint, fresh)
    return WriteResult(fingerprint=fingerprint, written=len(fresh))


async def write_vectors(
    session: AsyncSession, table: str, fingerprint: str,
    pairs: Sequence[tuple[str, str]],
) -> None:
    """Upsert ``(block_id, vector text)`` pairs into ``table``, a few
    statements per call however many blocks a document holds."""
    for start in range(0, len(pairs), INSERT_CHUNK):
        chunk = pairs[start:start + INSERT_CHUNK]
        await session.execute(
            text(f"""
                INSERT INTO {table} (block_id, fingerprint, embedding)
                SELECT t.block_id, CAST(:fp AS text), CAST(t.embedding AS vector)
                FROM unnest(CAST(:ids AS uuid[]), CAST(:embeddings AS text[]))
                     AS t(block_id, embedding)
                ON CONFLICT (block_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "fp": fingerprint,
                "ids": [block_id for block_id, _ in chunk],
                "embeddings": [embedding for _, embedding in chunk],
            },
        )


async def document_vectors_by_text(
    session: AsyncSession, document_id, fingerprint: str,
) -> dict[str, str]:
    """A document's vectors under ``fingerprint`` keyed by block text, read
    before a re-file strips the blocks they cascade with. Empty when the
    partition does not exist yet."""
    table = child_table(PARENT_TABLE, fingerprint)
    exists = (await session.execute(
        text("SELECT to_regclass(:name)"), {"name": table},
    )).scalar_one_or_none()
    if exists is None:
        return {}
    rows = await session.execute(text(f"""
        SELECT DISTINCT ON (b.text) b.text, e.embedding::text AS embedding
        FROM blocks b JOIN {table} e ON e.block_id = b.id
        WHERE b.document_id = CAST(:id AS uuid)
        ORDER BY b.text, b.id
    """), {"id": str(document_id)})
    return {row.text: row.embedding for row in rows}


async def carry_document_vectors(
    session: AsyncSession, document_id, fingerprint: str, by_text: dict[str, str],
) -> int:
    """Give each newly filed block whose text is unchanged the vector that
    text already had, so a re-file embeds only the blocks that changed."""
    if not by_text:
        return 0
    rows = await session.execute(text(
        "SELECT CAST(id AS text) AS id, text FROM blocks "
        "WHERE document_id = CAST(:id AS uuid) ORDER BY id"
    ), {"id": str(document_id)})
    pairs = [(row.id, by_text[row.text]) for row in rows if row.text in by_text]
    await write_vectors(session, child_table(PARENT_TABLE, fingerprint), fingerprint, pairs)
    return len(pairs)


async def _lock_owners(session: AsyncSession, rows) -> None:
    """Keep freshness checks and vector writes under the content writer's locks.

    Page tree locks precede owner rows, including multi-page sweeps, so a
    trash purge cannot take the same owners in the opposite order. Registration
    must finish first because it may commit the current transaction.
    """
    from app.services.page_door import _LOCK_ROOT, root_lock_key

    page_ids = sorted({str(row["page_id"]) for row in rows if row["page_id"] is not None})
    document_ids = sorted({str(row["document_id"]) for row in rows if row["document_id"] is not None})
    if page_ids:
        projects = (await session.execute(text(
            "SELECT DISTINCT project FROM pages WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY project"
        ), {"ids": page_ids})).scalars().all()
        for project in projects:
            await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})
    for table, owner_ids in (("documents", document_ids), ("pages", page_ids)):
        if owner_ids:
            await session.execute(text(
                f"SELECT id FROM {table} WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id FOR UPDATE"
            ), {"ids": owner_ids})


# Never written anywhere and never compared against real block text — its
# only job is to make the active embedder name the fingerprint it would
# currently produce, the same role a real search query plays in
# `BlockQueryService.search`.
_ACTIVE_FINGERPRINT_PROBE_TEXT = "darkmem block_embeddings active-fingerprint probe"


async def active_fingerprint(llm) -> str:
    """The fingerprint the active embedder writes under. A configured width
    names it exactly, since an embed returning any other width is refused, so
    no call is spent; without one, a real embed call names it."""
    try:
        configured = llm.llm_fingerprint()
    except (AttributeError, KeyError):
        configured = None
    if configured and not configured.endswith("|0"):
        return configured
    return await resolve_active_fingerprint(llm)


async def resolve_active_fingerprint(llm) -> str:
    """The fingerprint the active embedder produces right now, established
    the same way retrieval does (`BlockQueryService.search`, which embeds the
    query and reads whatever fingerprint that produced): a real embed call,
    never a data probe.

    **This exists because a data probe cannot correctly serve a caller whose
    job is to fill an EMPTY partition** (T-doc-door.6 review, rounds 2-3,
    2026-08-24). "Which live fingerprint holds data" is answered correctly by
    :meth:`PostgresVectorRepository.resolve_read_fingerprint` for a caller
    that only needs *some* already-populated partition — every sibling
    family's own resolver callers are that shape. But `block_embedding_refresh`'s corpus-wide sweep and
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
    :meth:`PostgresVectorRepository.resolve_read_fingerprint` does — this never raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved`.

    **The cost is one embed call per caller-defined unit of work, always —
    never skipped, even when there is nothing to repair** (T-doc-door.6
    review, round 4, 2026-08-24). For `block_embedding_refresh`'s sweep that
    unit is one scheduled run (at most once every
    ``BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS``), so the cost is bounded and
    small. `document_door.put_document` reaches it through
    :func:`active_fingerprint`, so it pays one call per filing only when the
    embedding purpose configures no width.
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
