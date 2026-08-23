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

**Fingerprint resolution is block-family-aware, not merely reused as-is**
(T-doc-door.6 review, 2026-08-24). ``resolve_read_fingerprint`` is the one
shared resolver every embedding family wraps
(:meth:`~app.repositories.vector.PostgresVectorRepository.resolve_read_fingerprint`),
and this module never re-derives its walk-the-live-fingerprints algorithm —
but the resolver's own "does this candidate actually hold data" check now
takes a ``parent_table`` argument, and ``block_embeddings.resolve_read_fingerprint``
passes ``"block_embeddings"``. An earlier version of that wrapper always
checked the ``memory_embeddings`` partition, which is wrong in both
directions on an install whose block and memory traffic diverge: it could
report the configured fingerprint as empty-and-unconfirmed while a different,
already-registered fingerprint held every real block vector (this sweep would
never converge, forever re-embedding the whole corpus), or it could report a
stale sibling fingerprint whose *block* partition happened to already be
complete while the true current fingerprint was still missing rows (this
sweep would report 0 and look converged while retrieval, which derives its
fingerprint from a real ``embed()`` call, searched an empty partition — a
document filed and never found, with no symptom, which is exactly the class
of bug this whole job exists to close). Probing the block partition removes
both directions for the case a real block-family fingerprint holds real data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import EmbedderFingerprintUnresolved
from app.services.block_embeddings import (
    PARENT_TABLE,
    _ensure_partition,
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
    "RefreshOutcome",
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


@dataclass(frozen=True)
class RefreshOutcome:
    embedded: int
    fingerprint: str | None
    # Whether this run's own fetch came back under the batch limit — i.e.
    # this run saw the entire backlog and cleared it, rather than merely
    # clearing one page of a larger one. Derived for free from the row count
    # this run already fetched; deliberately NOT a `COUNT(*)` of what remains
    # — that would force a full-table scan on every tick regardless of
    # whether anything is missing, which is strictly worse than the
    # unavoidable full scan this exact arm already pays once convergence is
    # reached (a known, separately-tracked cost, not one to compound here).
    converged: bool


async def refresh_block_embeddings(
    session: AsyncSession, llm, *, batch: int = DEFAULT_BATCH
) -> RefreshOutcome:
    """Embed up to `batch` blocks lacking a vector under the active embedder.

    The fingerprint is resolved **by data** through `resolve_read_fingerprint`
    — the same resolver every other embedding family wraps, asked here about
    the block family specifically (see module docstring) — never spending an
    embed call just to learn it, and never re-derived here.

    Residual risk, honestly stated rather than papered over: the resolver's
    "prefer the fingerprint that already has data" strategy can still, in
    principle, return a stale live sibling fingerprint if two fingerprints
    share one ``model_id`` (a real rotation still in flight, or two model
    generations both still registered) AND the true current fingerprint's
    block partition holds *zero* rows so far — e.g. every inline embed since
    the rotation has failed. That state is genuinely ambiguous from data
    alone, the same way a fresh, correctly configured install is
    indistinguishable from a wrong one with nothing embedded yet
    (invariant 14's own accepted gap). A misconfigured embedding
    ``dimensions`` value is NOT part of this risk: ``LLMOrchestrator._check_dims``
    refuses any embed whose real length disagrees with the configured one, so
    a wrong-dims install dies at the embed call inside `embed_blocks`, never
    reaching the comparison below.

    Raises ``RuntimeError`` when the fingerprint `embed_blocks` actually
    writes under disagrees with the one resolved above — that should be
    unreachable given the block-aware probe, so surfacing it as a failed run
    (visible in `job_runs.last_error`) is correct: silently absorbing it would
    re-spend up to `batch` embed calls against a paid embedder every tick,
    forever, with only a log line to show for it.
    """
    if batch <= 0:
        return RefreshOutcome(embedded=0, fingerprint=None, converged=True)

    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info("block_embedding_refresh: no fingerprint holds data yet")
        return RefreshOutcome(embedded=0, fingerprint=None, converged=True)

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    rows = (await session.execute(
        text(_MISSING_SQL.format(table=table)),
        {"fp": fingerprint, "limit": batch},
    )).mappings().all()
    block_ids = [row["block_id"] for row in rows]
    converged = len(block_ids) < batch
    if not block_ids:
        return RefreshOutcome(embedded=0, fingerprint=fingerprint, converged=True)

    result = await embed_blocks(session, llm, block_ids=block_ids)
    if result is None:
        await session.commit()
        return RefreshOutcome(embedded=0, fingerprint=fingerprint, converged=converged)

    await session.commit()

    if result.fingerprint != fingerprint:
        raise RuntimeError(
            f"block_embedding_refresh: resolved fingerprint {fingerprint!r} "
            f"but the embed call wrote under {result.fingerprint!r} instead "
            "— resolve_read_fingerprint returned a live sibling fingerprint "
            "rather than the one blocks are actually embedded under. This "
            "should be unreachable after the block-aware data probe; refusing "
            "rather than re-spending embed calls against the wrong partition "
            "every tick."
        )

    return RefreshOutcome(
        embedded=result.written, fingerprint=result.fingerprint, converged=converged,
    )
