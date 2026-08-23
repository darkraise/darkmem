"""The ``block_embeddings`` writer — first writer to T0.13's inert template.

Doc 16 §3 makes block embedding part of the document ingestion variant: parse,
strip-before-rewrite, then embed each block into the per-fingerprint
``block_embeddings__<slug>`` partition. This module is that write, following
the shape ``relation_embeddings.embed_relations`` and
``triple_embeddings.embed_facts`` already established for the sibling
target-new families — a batch embed call, a register-before-insert partition
guarantee, and an upsert keyed on ``(block_id, fingerprint)``.

**Register-before-insert is not advisory.** ``_ensure_partition`` runs before
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

    await _ensure_partition(session, fingerprint)
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
    """The fingerprint a block-partition read may safely key on, resolved
    cheaply (a data probe, never an embed call) — the shape that fits this
    function's one remaining caller, ``document_door.put_document``'s
    ``unchanged`` gap-fill repair.

    Delegated to the same resolver every other family uses, never re-derived:
    ``llm_fingerprint()`` is a pure formatter over static config and can name a
    partition no real embed ever wrote to, so this defers to
    :meth:`PostgresVectorRepository.resolve_read_fingerprint`'s own
    data-probe algorithm exactly as every sibling family does (it checks the
    ``memory_embeddings`` partition, since that is where real embed traffic
    is heaviest on almost every install). Raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved` rather
    than proceeding on an unconfirmed key — the caller here already treats
    that as "nothing to repair yet", not a hard failure.

    **This function briefly probed this family's own ``block_embeddings``
    partition instead of the memory one (T-doc-door.6 review, round 1), and
    that was reverted in round 2** (2026-08-24): a data probe of *any*
    family is structurally biased toward whichever fingerprint already has
    content, which is exactly wrong for a backstop whose job is filling an
    EMPTY partition — see ``block_embedding_refresh._resolve_active_fingerprint``,
    which resolves that job's fingerprint from a real embed call instead,
    the same way retrieval does, rather than from any data probe. That same
    structural bias is still live here, on this narrower question ("does
    this already-filed document have gaps"), and repairing it is out of this
    task's scope — recorded rather than fixed, per the round-2 ruling that
    the "avoid a paid embed call" trade explicitly still stands for this
    caller.
    """
    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


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
