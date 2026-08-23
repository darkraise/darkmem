"""Backstop for the document door's inline embed (spec 2026-08-23, T-doc-door.6).

``put_document`` embeds every filed block inline, right after the filing
commits (``app.services.document_door``). That covers the common path but
cannot cover three shapes of drift, all of which leave a document that exists
and is unfindable with no symptom:

- an embed call that failed *after* the filing already committed;
- an embedder rotation, which strands every existing block's vector in a dead
  partition while the active fingerprint's partition holds nothing for it;
- a document filed before this door shipped at all.

This module is the exact-arm sweep that closes all three: find blocks with no
vector under the active fingerprint, embed them, converge to zero. It is Tier
C — off the hot path, never reachable from capture or retrieval (invariant
15) — and it never decides *when* inline embedding runs; it only cleans up
after it.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import EmbedderFingerprintUnresolved
from app.services.block_embeddings import (
    PARENT_TABLE,
    embed_blocks,
    resolve_read_fingerprint,
)
from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

__all__ = [
    "BLOCK_EMBEDDING_CONFIG_SCHEMA",
    "BLOCK_EMBEDDING_CRON",
    "BLOCK_EMBEDDING_JOB_KEY",
    "BLOCK_EMBEDDING_MAX_RUN_SECONDS",
    "BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS",
    "refresh_block_embeddings",
]

BLOCK_EMBEDDING_JOB_KEY = "block_embedding_refresh"
BLOCK_EMBEDDING_CRON = "35 * * * *"
BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS = 300
BLOCK_EMBEDDING_MAX_RUN_SECONDS = 900

DEFAULT_BATCH = 500

BLOCK_EMBEDDING_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch",
        label="Blocks per run",
        default=DEFAULT_BATCH,
        min=0,
        max=5_000,
        help=(
            "Blocks embedded per run. Each one spends an embedding call, so "
            "0 disables the sweep."
        ),
    ),
]

_MISSING_SQL = """
    SELECT CAST(b.id AS text) AS block_id
    FROM blocks b
    LEFT JOIN {table} e
           ON e.block_id = b.id
          AND e.fingerprint = CAST(:fp AS text)
    WHERE e.block_id IS NULL
    ORDER BY b.id
    LIMIT CAST(:limit AS int)
"""


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


async def refresh_block_embeddings(
    session: AsyncSession, llm, *, batch: int = DEFAULT_BATCH
) -> int:
    """Embed up to `batch` blocks lacking a vector under the active embedder.

    Returns the number of blocks embedded. The fingerprint is resolved **by
    data** through `resolve_read_fingerprint` — the same resolver every other
    embedding family wraps — never spending an embed call just to learn it,
    and never re-derived here.

    Known hazard, inherited rather than introduced by this job: the resolver
    checks for real data only in the ``memory_embeddings`` partition
    (`PostgresVectorRepository._partition_has_data`). On an install with block
    traffic but literally no memory traffic, under a misconfigured embedding
    ``dimensions`` value, the resolver can fall through to its "fresh,
    correctly configured deployment" branch and hand back the *wrong,
    empty* fingerprint even though a *different* live fingerprint already
    holds every block's real vector. This job cannot safely correct that
    without re-deriving the resolver's own family-scoped logic (which
    conflicts with reusing it as one shared implementation across every
    embedding family, and duplicated logic is exactly what leaves families
    silently answering different questions). Instead this job detects and
    surfaces the symptom: if the fingerprint an embed call actually reports
    differs from the one the resolver handed back, that is direct evidence of
    the hazard, and it is logged loudly rather than silently retried forever.
    """
    if batch <= 0:
        return 0

    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info("block_embedding_refresh: no fingerprint holds data yet")
        return 0

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    rows = (await session.execute(
        text(_MISSING_SQL.format(table=table)),
        {"fp": fingerprint, "limit": batch},
    )).mappings().all()
    block_ids = [row["block_id"] for row in rows]
    if not block_ids:
        return 0

    result = await embed_blocks(session, llm, block_ids=block_ids)
    if result is None:
        await session.commit()
        return 0

    if result.fingerprint != fingerprint:
        logger.warning(
            "block_embedding_refresh: resolved fingerprint %r but the embed "
            "call actually reported %r — the embedding purpose's "
            "'dimensions' config likely disagrees with the real embedder, "
            "and this run will not converge until it is corrected",
            fingerprint, result.fingerprint,
        )

    await session.commit()
    return result.written
