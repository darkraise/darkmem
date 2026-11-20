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

**One arm and one budget per owner.** A block belongs to a document or to a page, and
each owner has its own partition family and its own per-tick allowance. One
shared budget over an unscoped query would let a notes corpus consume the
whole allowance and push document embedding behind it by one tick per 500
page blocks — a document regression caused by writing notes. Both arms run in
one job body over one resolved fingerprint, so the probe embed call is spent
once per run rather than once per owner.

Work-log entries are a third arm on a third budget, ``worklog_batch``. Appends
never embed inline, so this sweep is the only writer of
``worklog_embeddings__<slug>``, and an agent's ledger cannot delay a document
any more than a note can.

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

**One block the embedder rejects must not starve the ones behind it.** The
fetch below is ``ORDER BY b.id``, so a failing batch is the *same* failing
batch on every subsequent tick; a run that simply raised would be loud in
``job_runs.last_error`` and would still never sweep anything. So a failed
batch is bisected (:func:`_embed_bisecting`) until each rejected row stands
alone, and the rejected ids are kept in the ``config`` row
``block_embedding_refresh_state`` and left out of the next
``POISON_SKIP_TICKS`` runs, so a backlog behind one bad block costs a few
calls once rather than a failed batch on every tick.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import (
    PAGE_PARENT_TABLE, PARENT_TABLE, embed_blocks, resolve_active_fingerprint,
)
from app.services.embedder_registry import child_table, ensure_registered
from app.services.job_registry import FieldDescriptor
from app.services.worklog_embeddings import (
    MISSING_SQL as WORKLOG_MISSING_SQL,
    PARENT_TABLE as WORKLOG_PARENT_TABLE,
    embed_entries,
)

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
DEFAULT_PAGE_BATCH = 500
DEFAULT_WORKLOG_BATCH = 500
STATE_KEY = "block_embedding_refresh_state"
POISON_SKIP_TICKS = 6

BLOCK_EMBEDDING_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch",
        label="Document blocks per run",
        default=DEFAULT_BATCH,
        min=0,
        max=5_000,
        help=(
            "Document blocks embedded per run. Each one spends an embedding "
            "call, so 0 disables the document sweep."
        ),
    ),
    # A separate number rather than a share of the one above: the two arms
    # exist so neither owner's backlog can delay the other's, and a single
    # budget split at runtime still couples them — the split itself would be
    # the coupling, and `FieldDescriptor.default` is an int, so a split could
    # not be configured anyway.
    FieldDescriptor(
        key="page_batch",
        label="Page blocks per run",
        default=DEFAULT_PAGE_BATCH,
        min=0,
        max=5_000,
        help=(
            "Page blocks embedded per run, budgeted independently of the "
            "document sweep. 0 disables the page sweep."
        ),
    ),
    FieldDescriptor(
        key="worklog_batch",
        label="Work-log entries per run",
        default=DEFAULT_WORKLOG_BATCH,
        min=0,
        max=5_000,
        help=(
            "Work-log entries embedded per run, budgeted independently of "
            "both block sweeps. 0 disables the work-log sweep."
        ),
    ),
]


_MISSING_SQL = """
    SELECT CAST(b.id AS text) AS block_id
    FROM blocks b
    LEFT JOIN {table} e
           ON e.block_id = b.id
          AND e.fingerprint = CAST(:fp AS text)
    WHERE e.block_id IS NULL AND b.{owner} IS NOT NULL
    ORDER BY b.id
    LIMIT CAST(:limit AS int)
"""


@dataclass(frozen=True)
class _Arm:
    """One owner's sweep: the partition family it fills, the anti-join that
    lists its rows with no vector (one text column; formatted with ``table``
    and, for blocks, ``owner``), and the writer that embeds a list of them."""
    parent: str
    missing_sql: str
    embed: Callable[[AsyncSession, Any, list[str]], Awaitable[Any]]
    owner_column: str | None = None


def _block_writer(parent: str) -> Callable[[AsyncSession, Any, list[str]], Awaitable[Any]]:
    async def write(session: AsyncSession, llm, ids: list[str]):
        return await embed_blocks(session, llm, block_ids=ids, parent=parent)
    return write


async def _write_entries(session: AsyncSession, llm, ids: list[str]):
    return await embed_entries(session, llm, entry_ids=ids)


# Separate arms rather than one unscoped sweep: page blocks and work-log
# entries are repaired on their own budgets, because sharing the document one
# would let a notes corpus or an agent's ledger consume the whole per-tick
# allowance and delay document embedding.
_DOCUMENT_ARM = _Arm(
    parent=PARENT_TABLE, missing_sql=_MISSING_SQL,
    embed=_block_writer(PARENT_TABLE), owner_column="document_id",
)
_PAGE_ARM = _Arm(
    parent=PAGE_PARENT_TABLE, missing_sql=_MISSING_SQL,
    embed=_block_writer(PAGE_PARENT_TABLE), owner_column="page_id",
)
_WORKLOG_ARM = _Arm(
    parent=WORKLOG_PARENT_TABLE, missing_sql=WORKLOG_MISSING_SQL, embed=_write_entries,
)


@dataclass(frozen=True)
class RefreshOutcome:
    embedded: int
    fingerprint: str | None
    # Rows the bisection isolated and could not embed. They stay in the
    # backlog, skipped for `POISON_SKIP_TICKS` runs, so a run that reports
    # any is never `converged`.
    failed: int
    # Whether this run's own fetch came back under the batch limit — i.e.
    # this run saw the entire backlog and cleared it, rather than merely
    # clearing one page of a larger one. Derived for free from the row count
    # this run already fetched; deliberately NOT a `COUNT(*)` of what remains
    # — that would force a full-table scan on every tick regardless of
    # whether anything is missing, which is strictly worse than the
    # unavoidable full scan this exact arm already pays once convergence is
    # reached (a known, separately-tracked cost, not one to compound here).
    converged: bool


# How many split attempts may fail, with none yet succeeding, before the
# bisection gives up and re-raises. An embedder that is down fails every half;
# one poison row leaves the other half of the first split embeddable, so a
# success arrives first.
_OUTAGE_PROBE = 3


async def _embed_bisecting(
    session: AsyncSession, llm, row_ids: list[str], batch_error: Exception,
    *, arm: _Arm,
) -> tuple[int, str | None, list[str]]:
    """Split `row_ids` in halves after the batch call failed, until each
    rejected row stands alone.

    Halves are tried a level at a time, so one poison row among n costs about
    2·log2(n) calls and an outage costs `_OUTAGE_PROBE` calls past the batch.
    Each attempt runs in its own SAVEPOINT, so a row that fails mid-insert
    rolls back only its own half.

    Re-raises `batch_error` — never a per-half one — when nothing could be
    embedded at all, so the run's `last_error` names the failure an operator
    would recognise rather than an artefact of the retry.
    """
    embedded = 0
    fingerprint: str | None = None
    rejected: list[str] = []
    level = [row_ids]
    failures = 0

    while level:
        failing: list[list[str]] = []
        for current in level:
            if len(current) == 1:
                rejected.append(current[0])
                continue
            middle = len(current) // 2
            for half in (current[:middle], current[middle:]):
                try:
                    async with session.begin_nested():
                        result = await arm.embed(session, llm, half)
                except Exception:
                    failures += 1
                    if embedded == 0 and failures >= _OUTAGE_PROBE:
                        raise batch_error from None
                    failing.append(half)
                    continue
                if result is not None:
                    embedded += result.written
                    fingerprint = result.fingerprint
        level = failing

    if embedded == 0 and rejected:
        raise batch_error from None

    if rejected:
        logger.warning(
            "block_embedding_refresh: %d of %d %s row(s) could not be embedded "
            "and are skipped for %d runs; the rest of the batch was written. "
            "Ids: %s",
            len(rejected), len(row_ids), arm.parent, POISON_SKIP_TICKS,
            ", ".join(rejected),
        )
    return embedded, fingerprint, rejected


async def _load_state(session: AsyncSession) -> tuple[int, dict[str, int]]:
    value = (await session.execute(
        text("SELECT value FROM config WHERE key = :key"), {"key": STATE_KEY},
    )).scalar_one_or_none() or {}
    return int(value.get("tick", 0)), dict(value.get("skip", {}))


async def _save_state(session: AsyncSession, tick: int, skip: dict[str, int]) -> None:
    await session.execute(text("""
        INSERT INTO config (key, value) VALUES (:key, CAST(:value AS jsonb))
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """), {"key": STATE_KEY, "value": json.dumps({"tick": tick, "skip": skip})})
    await session.commit()


async def refresh_block_embeddings(
    session: AsyncSession,
    llm,
    *,
    batch: int = DEFAULT_BATCH,
    page_batch: int = DEFAULT_PAGE_BATCH,
    worklog_batch: int = DEFAULT_WORKLOG_BATCH,
) -> RefreshOutcome:
    """Sweep every owner's missing vectors, each on its own budget.

    Documents first, then pages, then work-log entries, in one run over one
    resolved fingerprint — arms rather than jobs, because the fingerprint
    probe is an embed call and a second registered job would spend a second
    one per tick for nothing. The returned outcome sums the arms; `converged`
    holds only if every arm did.

    Raises out of whichever arm failed, so a document-side failure leaves the
    page arm unrun. That is the right way round: the document sweep is the
    one whose starvation this job exists to prevent, and a failure loud in
    `job_runs.last_error` is retried on the next tick.
    """
    if batch <= 0 and page_batch <= 0 and worklog_batch <= 0:
        return RefreshOutcome(
            embedded=0, fingerprint=None, failed=0, converged=True,
        )

    fingerprint = await resolve_active_fingerprint(llm)
    last_tick, recorded = await _load_state(session)
    tick = last_tick + 1
    skip = {row_id: until for row_id, until in recorded.items() if until >= tick}

    embedded = 0
    failed = 0
    converged = True
    for arm, arm_batch in (
        (_DOCUMENT_ARM, batch), (_PAGE_ARM, page_batch), (_WORKLOG_ARM, worklog_batch),
    ):
        outcome, rejected = await _refresh_arm(
            session, llm, fingerprint, arm=arm, batch=arm_batch, skip=skip,
        )
        for row_id in rejected:
            skip[row_id] = tick + POISON_SKIP_TICKS
        await _save_state(session, tick, skip)
        embedded += outcome.embedded
        failed += outcome.failed
        converged = converged and outcome.converged

    return RefreshOutcome(
        embedded=embedded,
        fingerprint=fingerprint,
        failed=failed,
        converged=converged,
    )


async def _refresh_arm(
    session: AsyncSession, llm, fingerprint: str, *, arm: _Arm, batch: int,
    skip: dict[str, int],
) -> tuple[RefreshOutcome, list[str]]:
    """Embed up to `batch` of `arm`'s rows lacking a vector under `fingerprint`.

    The fingerprint is the caller's, resolved from one real embed call
    (`block_embeddings.resolve_active_fingerprint`), the same way
    `BlockQueryService.search` resolves the fingerprint it reads under — see
    the module docstring for why a data probe cannot do this job correctly,
    on any family.

    A batch the embedder rejects is bisected (:func:`_embed_bisecting`)
    rather than failing the run: without that, one unembeddable block starves
    every block behind it forever, because the fetch order is deterministic
    and the same batch comes back every tick. Ids in `skip` are left out of
    the work set; the rejected ids are returned for the caller to record.

    Raises ``RuntimeError`` when the fingerprint `embed_blocks` actually
    writes the batch under disagrees with the one the probe call resolved.
    With both calls now real embeds, this should only ever fire if the
    active embedder's configuration changes mid-run (a race, not a resolver
    defect) — surfacing it as a failed run (visible in `job_runs.last_error`)
    is still correct: silently absorbing it would let the batch's vectors
    land under a fingerprint this run never verified converges.
    """
    if batch <= 0:
        return RefreshOutcome(
            embedded=0, fingerprint=fingerprint, failed=0, converged=True,
        ), []

    await ensure_registered(session, fingerprint)
    table = child_table(arm.parent, fingerprint)
    limit = batch + len(skip)
    fetched = list((await session.execute(
        text(arm.missing_sql.format(table=table, owner=arm.owner_column)),
        {"fp": fingerprint, "limit": limit},
    )).scalars().all())
    row_ids = [row_id for row_id in fetched if row_id not in skip][:batch]
    # A skipped row is still missing, so a backlog holding one is not cleared.
    converged = len(fetched) < limit and len(row_ids) == len(fetched)
    if not row_ids:
        return RefreshOutcome(
            embedded=0, fingerprint=fingerprint, failed=0, converged=converged,
        ), []

    failed: list[str] = []
    # The SAVEPOINT is what makes the retry below possible: a batch that fails
    # inside its inserts leaves the transaction aborted, and the bisection
    # could not run a single statement in it.
    try:
        async with session.begin_nested():
            result = await arm.embed(session, llm, row_ids)
    except Exception as batch_error:  # noqa: BLE001 - re-raised unless isolable
        embedded, written_fingerprint, failed = await _embed_bisecting(
            session, llm, row_ids, batch_error, arm=arm,
        )
        await session.commit()
    else:
        await session.commit()
        if result is None:
            return RefreshOutcome(
                embedded=0, fingerprint=fingerprint, failed=0, converged=converged,
            ), []
        embedded, written_fingerprint = result.written, result.fingerprint

    # None only where every isolated id named a block that vanished mid-run,
    # so nothing was written and there is no fingerprint to disagree with.
    if written_fingerprint is not None and written_fingerprint != fingerprint:
        raise RuntimeError(
            f"block_embedding_refresh: the probe resolved fingerprint "
            f"{fingerprint!r} but the batch embed call wrote under "
            f"{written_fingerprint!r} instead — the active embedder's "
            "configuration changed between the two calls within this one "
            "run. Refusing rather than reporting a batch as converged under "
            "a fingerprint this run never actually verified."
        )

    if converged and embedded < len(row_ids):
        remaining = (await session.execute(
            text(arm.missing_sql.format(table=table, owner=arm.owner_column)),
            {"fp": fingerprint, "limit": 1},
        )).first()
        converged = remaining is None

    return RefreshOutcome(
        embedded=embedded,
        fingerprint=fingerprint,
        failed=len(failed),
        # A block this run could not embed is still missing, so a run that
        # left any behind has not seen the backlog cleared however short its
        # own fetch came back.
        converged=converged and not failed,
    ), failed
