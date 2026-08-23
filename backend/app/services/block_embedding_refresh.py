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
vector under the active fingerprint, embed them, converge to zero. Tier C,
and deliberately not a dreaming-family member: contract 6 fixes that family
at six, and this is an artefact refresh in the same class as
``ppr_snapshot`` and ``relation_embedding_refresh`` — off the hot path, never
reachable from capture or retrieval (invariant 15), and it never decides
*when* inline embedding runs; it only cleans up after it.

**Fingerprint resolution is a real embed call, not a data probe — and that
took two review rounds to land on** (T-doc-door.6 review, 2026-08-24).

Round 1 pointed ``resolve_read_fingerprint``'s "does this candidate hold
data" check at the block family's own partition instead of the memory one it
was hardcoded to, on the reasoning that an install can carry real block
traffic with none on the memory side. That closed the direction where the
sweep never converges, but reopened the OTHER headline case in this module's
own second bullet above: an embedder rotation. Walk it — a dims rotation on
one ``model_id`` leaves ``F_old`` holding every existing block; config moves
to ``F_new``; nothing has re-filed a document since, so ``F_new``'s own block
partition is empty. A data probe of *any* family — block included — prefers
whichever candidate already has rows, so it hands back ``F_old``, the anti-
join finds nothing missing there, and the sweep reports ``converged=True``
while retrieval (which derives its fingerprint from a real ``embed()`` call,
same as this module now does) reads ``F_new`` and finds nothing. Silent at
every log level, for the exact document-unfindable failure this whole job
exists to close.

**The structural fix is what changed, not just which partition gets
checked.** A backstop *writer*, whose entire purpose is filling an EMPTY
partition, cannot resolve its target by asking "which live fingerprint holds
data" — that question is biased toward the wrong answer by construction, on
every family, not only the block one. So this module resolves its fingerprint
the same way ``BlockQueryService.search`` resolves the one it searches under:
a real embed call, ``block_embeddings.resolve_active_fingerprint``. This
reverses this job's own original "never spend an embed call to learn a
fingerprint" instruction for exactly this one call site — one embed call per
scheduled run buys a correctness property (sweep and search targeting the
same partition) that no read-only probe, on any family, can guarantee.

**Round 3 found the identical bias in a second caller**
(T-doc-door.6 review, 2026-08-24): ``document_door.put_document``'s
``unchanged`` gap-fill repair push had the same chicken-and-egg — it called
the memory-probe ``block_embeddings.resolve_read_fingerprint`` to find which
blocks of one document still need embedding, so after a rotation it would
look at the stale, already-complete partition and report nothing to repair.
It now resolves from ``resolve_active_fingerprint`` too, so the shared helper
lives in ``block_embeddings.py`` rather than being duplicated here — both
callers import it from there. ``block_embeddings.resolve_read_fingerprint``
(the data probe) is unchanged in shape and stays exported for a caller that
only needs *some* already-populated partition, not one that must fill gaps;
neither of this family's two known callers is that shape today.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import (
    PARENT_TABLE, ensure_partition, embed_blocks, resolve_active_fingerprint,
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

    The fingerprint is resolved from one real embed call
    (`block_embeddings.resolve_active_fingerprint`), the same way
    `BlockQueryService.search` resolves the fingerprint it reads under — see
    the module docstring for why a data probe cannot do this job correctly,
    on any family.

    Raises ``RuntimeError`` when the fingerprint `embed_blocks` actually
    writes the batch under disagrees with the one the probe call resolved.
    With both calls now real embeds, this should only ever fire if the
    active embedder's configuration changes mid-run (a race, not a resolver
    defect) — surfacing it as a failed run (visible in `job_runs.last_error`)
    is still correct: silently absorbing it would let the batch's vectors
    land under a fingerprint this run never verified converges.
    """
    if batch <= 0:
        return RefreshOutcome(embedded=0, fingerprint=None, converged=True)

    fingerprint = await resolve_active_fingerprint(llm)

    await ensure_partition(session, fingerprint)
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
            f"block_embedding_refresh: the probe resolved fingerprint "
            f"{fingerprint!r} but the batch embed call wrote under "
            f"{result.fingerprint!r} instead — the active embedder's "
            "configuration changed between the two calls within this one "
            "run. Refusing rather than reporting a batch as converged under "
            "a fingerprint this run never actually verified."
        )

    return RefreshOutcome(
        embedded=result.written, fingerprint=result.fingerprint, converged=converged,
    )
