"""The Tier-C verification recompute — the drain side of doc 08 §4.3's
enqueue-for-verification hook, plus the slow reconciliation arm that closes
T2.10's I-4 finding.

``recompute_fact`` (``verification_ladder.py``) is the per-fact primitive and
the sole journaller of verification transitions; it is finished and out of
scope here. This module owns only *which* facts get called with it and *when*
— the drain, never the decision.

**Two arms, cooperating under one job.**

The **fast arm** (``_drain_sources_changed``) drains ``sources_changed``
events — emitted by ``fact_lift`` (birth) and ``fact_provenance``
(withdrawal) whenever a fact's evidence actually changed — past a watermark,
dedups the affected ``fact_id``s, and calls ``recompute_fact`` on each. This
is the doc 08 §4.3 path and is O(evidence churn), not O(vault size).

The **slow arm** (``_reconcile_from_fact_sources``) is the backstop
``record_event`` makes necessary. ``record_event`` degrades loudly but never
raises into its caller (``app/services/events.py``); combined with
events-as-queue, a swallowed ``sources_changed`` emit leaves a fact holding
promotable evidence forever with **no event to drain** — nothing about the
fast arm can ever notice, because the missing input is the event itself. The
slow arm closes that hole by ignoring events entirely: on a cadence far
slower than the fast arm's tick, it walks a bounded, rotating slice of
``knowledge_triples`` directly and recomputes each one from ``fact_sources``.
Any fact whose recomputed decision differs from its stored status is proof
the fast arm missed it — for *any* reason, not only a swallowed emit; a fact
whose per-fact recompute raised on the fast arm's watermark-advancing pass
(see below) is healed by the exact same mechanism.

**Watermark and cursor are internal bookkeeping, not operator config.** Both
live in their own ``config`` row (``_STATE_CONFIG_KEY``), deliberately
outside ``job:verification_recompute``'s ``config`` dict:
``JobRegistry.set_config`` validates every write against
``RECOMPUTE_CONFIG_SCHEMA`` (type, min/max, unknown keys rejected) and is the
operator-facing surface reached from ``PUT /api/v1/jobs/{key}/config`` — a
watermark is not a tunable int an operator should be able to set to an
arbitrary value through that path, and trying to route it through
``cfg.config`` would either be rejected by the schema or, if forced into the
schema to make it pass, become editable there. A dedicated row sidesteps both
traps named in the brief: it is written directly through
``JobRegistry``-independent SQL, never through ``set_config``, so nothing
merges over it and nothing validates it as a tunable.

**The watermark is a ``(created_at, id)`` tuple, not a bare timestamp.**
Within one transaction ``now()`` is constant (T2.06's finding, load-bearing
here too), so two ``sources_changed`` events written by the same transaction
share one ``created_at``. A bare ``created_at > watermark`` compare processes
the first such row, advances the watermark to that shared timestamp, and
then silently drops every sibling row with the identical timestamp on every
later run — 0 rows found instead of 1. The fix is the same row-comparison
T2.06 needed: ``created_at >= :wm_ts AND (created_at > :wm_ts OR id >
:wm_id)``. The first conjunct is redundant with the second by pure logic but
is not redundant to the planner: it is a plain comparison on the partition
key (``events`` is RANGE-partitioned by month), so partition pruning sees it
directly rather than having to reason through the OR.

The slow arm's cursor carries the identical hazard — ``fact_lift`` can mint
several facts inside one transaction, so ``knowledge_triples.created_at`` can
tie the same way — and uses the same tuple-compare shape, with ``id`` (a
``uuid``) as the tiebreak instead of a bigint.

**Slow-arm coverage.** The cursor rotates over every non-``confirmed`` fact
ordered by ``(created_at, id)``, advancing past whatever slice it just
scanned; when a scan returns fewer rows than the slice size the walk has
reached the end of the table and the cursor resets to the beginning next
time it runs. That guarantees every fact is eventually revisited without ever
re-scanning the same head on every pass, at a cost bounded by the slice size
per run. ``confirmed`` facts are excluded from the slice because
``decide()`` always holds them (T2.05); scanning them would only spend
budget on a guaranteed no-op.

**Slow-arm cadence.** It only runs when ``slow_arm_interval_seconds`` has
elapsed since its last run, checked against a persisted
``slow_arm_last_run_at`` — never on every tick. Running it every tick would
make the watermark pointless, since the slow arm would then re-derive
whatever the fast arm just drained on the very same cycle. The default is
600s (5x the job's 2-minute cron) so it fires roughly every fifth tick.

**Per-fact isolation, not batch-atomic.** Each fact — on both arms — is
recomputed inside its own ``session.begin_nested()`` savepoint, so a
poisonous fact settles alone: its exception is logged and counted, and every
other fact in the batch still gets recomputed. This mirrors the
``buffer_flush`` job's row-at-a-time retry precedent (``CLAUDE.md``,
"Capture is buffered") over a batch-abort. The fast arm's watermark still
advances past a failed fact's event — holding it back would let one
permanently-poisonous fact stall the whole queue forever — and the slow arm
is what re-visits that fact later regardless of the reason it was missed,
which is why the two arms are a genuine pair rather than one primary path
with a redundant mirror.

**Volume consequence, named as the brief asks.** ``set_verification_status``
journals a *contradiction-blocked* hold on purpose, once per call, even when
the status does not change (see its docstring, ``knowledge_triples.py``) —
it is the durable record that a standing dispute is still disputed. Every
fast-arm event on a disputed fact re-adjudicates it, and every slow-arm pass
that happens to slice over a disputed fact does too, so a long-lived dispute
accumulates one ``verified`` event per drain pass that touches it — from
*both* arms now, not just the fast one. That is intentional (it is the
evidence T2.11's contradiction scan needs), but it means the slow arm's
default cadence directly sets a floor on that volume: every
``slow_arm_interval_seconds`` a standing dispute inside the current slice
gets one more row, on top of whatever the fast arm already produced.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.job_registry import FieldDescriptor
from app.services.verification_ladder import recompute_fact

logger = logging.getLogger(__name__)

# ── config (operator-facing, validated by JobRegistry.set_config) ─────────

# batch_size keeps the T2.08 placeholder's key, default (100) and ceiling
# (2000) verbatim -- set_config merges and never drops a persisted key, so an
# operator who already tuned the placeholder's batch_size keeps a value that
# still means the same thing (events drained per tick) rather than being
# silently orphaned by this schema swap.
DEFAULT_FAST_BATCH = 100
MAX_FAST_BATCH = 2000

DEFAULT_SLOW_BATCH = 200
MAX_SLOW_BATCH = 2000

DEFAULT_SLOW_ARM_INTERVAL_SECONDS = 600
MIN_SLOW_ARM_INTERVAL_SECONDS = 60
MAX_SLOW_ARM_INTERVAL_SECONDS = 86400

RECOMPUTE_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size", label="Batch Size",
        default=DEFAULT_FAST_BATCH, min=1, max=MAX_FAST_BATCH,
        help=(
            "sources_changed events drained per run, past the watermark. "
            "Carried over from the T2.08 placeholder schema (same key, "
            "default and bounds) so a value an operator already persisted "
            "keeps its meaning across this swap."
        ),
    ),
    FieldDescriptor(
        key="slow_arm_batch_size", label="Slow Arm Slice Size",
        default=DEFAULT_SLOW_BATCH, min=1, max=MAX_SLOW_BATCH,
        help=(
            "Facts scanned per slow-arm pass, reconciled directly from "
            "fact_sources rather than from sources_changed. This is the "
            "backstop for a swallowed emit (T2.10 finding I-4); its cursor "
            "rotates over every non-confirmed fact so coverage is "
            "eventually total."
        ),
    ),
    FieldDescriptor(
        key="slow_arm_interval_seconds", label="Slow Arm Interval (s)",
        default=DEFAULT_SLOW_ARM_INTERVAL_SECONDS,
        min=MIN_SLOW_ARM_INTERVAL_SECONDS, max=MAX_SLOW_ARM_INTERVAL_SECONDS,
        help=(
            "Minimum wall-clock gap between slow-arm passes. It is a "
            "backstop, not a co-equal path with the fast drain, so it must "
            "run far less often than every tick or the watermark buys "
            "nothing."
        ),
    ),
]

# Internal bookkeeping only -- never read or written through
# JobRegistry.set_config / load_config. See the module docstring for why.
_STATE_CONFIG_KEY = "verification_recompute_state"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_NIL_UUID = "00000000-0000-0000-0000-000000000000"


# ── persisted state ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class _State:
    watermark_created_at: datetime | None = None
    watermark_id: int | None = None
    slow_arm_last_run_at: datetime | None = None
    slow_cursor_created_at: datetime | None = None
    slow_cursor_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "watermark_created_at": _iso(self.watermark_created_at),
            "watermark_id": self.watermark_id,
            "slow_arm_last_run_at": _iso(self.slow_arm_last_run_at),
            "slow_cursor_created_at": _iso(self.slow_cursor_created_at),
            "slow_cursor_id": self.slow_cursor_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "_State":
        return cls(
            watermark_created_at=_parse_dt(data.get("watermark_created_at")),
            watermark_id=data.get("watermark_id"),
            slow_arm_last_run_at=_parse_dt(data.get("slow_arm_last_run_at")),
            slow_cursor_created_at=_parse_dt(data.get("slow_cursor_created_at")),
            slow_cursor_id=data.get("slow_cursor_id"),
        )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _load_state(session: AsyncSession) -> _State:
    row = (
        await session.execute(select(Config).where(Config.key == _STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return _State()
    return _State.from_dict(row.value)


async def _save_state(session: AsyncSession, state: _State) -> None:
    row = (
        await session.execute(select(Config).where(Config.key == _STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key=_STATE_CONFIG_KEY, value=state.to_dict()))
    else:
        row.value = state.to_dict()


# ── the fast arm: drain sources_changed ────────────────────────────────

# The tuple compare, spelled as two conjuncts rather than a Postgres row
# constructor: `created_at >= :wm_ts` is what lets the planner prune
# partitions on the range-partitioned events table directly; the OR clause
# is what makes same-transaction ties (identical created_at, distinct id)
# unmissable. Removing the OR clause and its `id` half is exactly the T2.06
# same-transaction bug reintroduced -- see the module docstring and
# tests/test_verification_recompute.py's mutation proof.
_DRAIN_EVENTS = text("""
    SELECT id, created_at, payload
    FROM events
    WHERE event_type = 'sources_changed'
      AND object_type = 'fact'
      AND created_at >= CAST(:wm_ts AS timestamptz)
      AND (created_at > CAST(:wm_ts AS timestamptz) OR id > CAST(:wm_id AS bigint))
    ORDER BY created_at, id
    LIMIT CAST(:batch AS integer)
""")


@dataclass(frozen=True)
class DrainOutcome:
    events_scanned: int = 0
    facts_touched: int = 0
    facts_recomputed: int = 0
    facts_failed: int = 0
    transitions: int = 0


async def _drain_sources_changed(
    session: AsyncSession, state: _State, *, batch_size: int
) -> tuple[DrainOutcome, _State]:
    wm_ts = state.watermark_created_at or _EPOCH
    wm_id = state.watermark_id if state.watermark_id is not None else -1
    result = await session.execute(
        _DRAIN_EVENTS, {"wm_ts": wm_ts, "wm_id": wm_id, "batch": batch_size}
    )
    rows = result.mappings().all()
    if not rows:
        return DrainOutcome(), state

    fact_ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        payload = row["payload"] or {}
        fact_id = payload.get("fact_id")
        if fact_id and fact_id not in seen:
            seen.add(fact_id)
            fact_ids.append(fact_id)

    recomputed = failed = transitions = 0
    for fact_id in fact_ids:
        try:
            async with session.begin_nested():
                decision = await recompute_fact(session, fact_id)
        except Exception:
            failed += 1
            logger.exception(
                "verification_recompute: fast-arm recompute failed for fact %s",
                fact_id,
            )
            continue
        recomputed += 1
        if decision.outcome != "hold":
            transitions += 1

    last = rows[-1]
    new_state = replace(
        state,
        watermark_created_at=last["created_at"],
        watermark_id=int(last["id"]),
    )
    outcome = DrainOutcome(
        events_scanned=len(rows),
        facts_touched=len(fact_ids),
        facts_recomputed=recomputed,
        facts_failed=failed,
        transitions=transitions,
    )
    return outcome, new_state


# ── the slow arm: reconcile from fact_sources directly ─────────────────

# confirmed is excluded: decide() always holds it (T2.05, the machine's
# ceiling), so recomputing it can only ever be a wasted lock-and-read.
_SLOW_ARM_SLICE = text("""
    SELECT id, created_at
    FROM knowledge_triples
    WHERE verification_status != 'confirmed'
      AND created_at >= CAST(:cur_ts AS timestamptz)
      AND (created_at > CAST(:cur_ts AS timestamptz) OR id > CAST(:cur_id AS uuid))
    ORDER BY created_at, id
    LIMIT CAST(:batch AS integer)
""")


@dataclass(frozen=True)
class ReconcileOutcome:
    facts_scanned: int = 0
    facts_healed: int = 0
    wrapped: bool = False


async def _reconcile_from_fact_sources(
    session: AsyncSession, state: _State, *, batch_size: int
) -> tuple[ReconcileOutcome, _State]:
    cur_ts = state.slow_cursor_created_at or _EPOCH
    cur_id = state.slow_cursor_id or _NIL_UUID
    result = await session.execute(
        _SLOW_ARM_SLICE, {"cur_ts": cur_ts, "cur_id": cur_id, "batch": batch_size}
    )
    rows = result.mappings().all()

    healed = 0
    for row in rows:
        fact_id = str(row["id"])
        try:
            async with session.begin_nested():
                decision = await recompute_fact(session, fact_id)
        except Exception:
            logger.exception(
                "verification_recompute: slow-arm recompute failed for fact %s",
                fact_id,
            )
            continue
        if decision.outcome != "hold":
            healed += 1

    wrapped = len(rows) < batch_size
    if wrapped:
        new_state = replace(
            state, slow_cursor_created_at=None, slow_cursor_id=None
        )
    else:
        last = rows[-1]
        new_state = replace(
            state,
            slow_cursor_created_at=last["created_at"],
            slow_cursor_id=str(last["id"]),
        )
    outcome = ReconcileOutcome(
        facts_scanned=len(rows), facts_healed=healed, wrapped=wrapped
    )
    return outcome, new_state


# ── the tick ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RecomputeOutcome:
    drain: DrainOutcome
    reconcile: ReconcileOutcome
    slow_arm_ran: bool


async def run_recompute(
    session: AsyncSession,
    *,
    batch_size: int = DEFAULT_FAST_BATCH,
    slow_arm_batch_size: int = DEFAULT_SLOW_BATCH,
    slow_arm_interval_seconds: int = DEFAULT_SLOW_ARM_INTERVAL_SECONDS,
    now: datetime | None = None,
) -> RecomputeOutcome:
    """One recompute tick: the fast drain, then the slow arm if it is due.

    Does not commit -- transaction control is the caller's, matching
    ``run_lift``'s contract. ``now`` is a seam for tests that need to force
    or suppress the slow arm without sleeping real wall-clock time.
    """
    moment = now or datetime.now(timezone.utc)
    state = await _load_state(session)

    drain_outcome, state = await _drain_sources_changed(
        session, state, batch_size=batch_size
    )

    due = (
        state.slow_arm_last_run_at is None
        or (moment - state.slow_arm_last_run_at)
        >= timedelta(seconds=slow_arm_interval_seconds)
    )
    if due:
        reconcile_outcome, state = await _reconcile_from_fact_sources(
            session, state, batch_size=slow_arm_batch_size
        )
        state = replace(state, slow_arm_last_run_at=moment)
    else:
        reconcile_outcome = ReconcileOutcome()

    await _save_state(session, state)
    return RecomputeOutcome(
        drain=drain_outcome, reconcile=reconcile_outcome, slow_arm_ran=due
    )
