"""The Tier-C verification recompute — the drain side of doc 08 §4.3's
enqueue-for-verification hook, plus the slow reconciliation arm that closes
T2.10's I-4 finding.

``recompute_fact`` (``verification_ladder.py``) is the per-fact primitive and
the sole journaller of verification transitions; it is finished and out of
scope here. This module owns only *which* facts get called with it and *when*
— the drain, never the decision.

**Two arms, cooperating under one job.**

The **fast arm** (``_drain_sources_changed``) drains ``sources_changed``
events — emitted by ``fact_lift`` (birth), ``fact_provenance`` (a memory
withdrawn), the Tier-C citation re-verifier (a code citation going stale or
resolving again) and the repository entity merge's fact fold (sources moved
onto the surviving fact) whenever a fact's evidence actually changed —
past a watermark,
dedups the affected ``fact_id``s, and calls ``recompute_fact`` on each. This
is the doc 08 §4.3 path and is O(evidence churn), not O(vault size).

The citation re-verifier is named in words rather than by its module
basename on purpose: ``tests/test_citation_reverifier.py`` scans every file
under ``app/`` for that basename against an allowlist of its wiring, prose
included, so spelling it here would either red the build or buy this module
an allowlist entry it has no reason to hold.

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

**The watermark is a ``(created_at, id)`` tuple, not a bare timestamp — and
that tuple compare fixes exactly one hazard, not two.** Within one
transaction ``now()`` is constant (T2.06's finding, load-bearing here too),
so two ``sources_changed`` events written by the same transaction share one
``created_at``. A bare ``created_at > watermark`` compare processes the
first such row, advances the watermark to that shared timestamp, and then
silently drops every sibling row with the identical timestamp on every later
run — 0 rows found instead of 1. The tuple compare —
``created_at >= :wm_ts AND (created_at > :wm_ts OR id > :wm_id)`` — closes
exactly this: **same-transaction ties**, where two rows share one
``created_at`` because they were written by the same transaction. The first
conjunct is redundant with the second by pure logic but is not redundant to
the planner: it is a plain comparison on the partition key (``events`` is
RANGE-partitioned by month), so partition pruning sees it directly rather
than having to reason through the OR.

**It does not fix cross-transaction commit-order skew, which is a distinct
hazard the tuple compare cannot touch.** ``created_at`` is transaction
*start* time, not commit time, so `(created_at, id)` ordering is not
commit-ordered across different transactions. Two producers, A and B: A
begins first (so its event's ``created_at`` sorts earlier) but commits
*last*; B begins later but commits *first*. If a drain tick runs in the
window after B's commit but before A's, it sees B's row (already committed,
MVCC-visible) but not A's (not yet committed) — and advances the watermark
past B's timestamp. Because A's ``created_at`` is *earlier* than B's, A's
row now sits **behind** the watermark forever: the next drain's
``created_at >= :wm_ts`` excludes it permanently, with no error and no
retry, since the watermark only ever moves forward. This is a genuine,
mechanically-demonstrable gap distinct from the same-transaction tie the
tuple compare targets, and an earlier revision of this docstring overstated
the tuple compare as closing both.

The consequence is bounded and in the sanctioned undercount direction (a
dropped promotion delays, it never fabricates one), and it is caught for
that specific fact by the slow arm's next pass regardless — but it quietly
promotes the slow arm's rotation period from a rare-corruption backstop to a
load-bearing bound for *ordinary* concurrent operation, since ``fact_lift``
ticks and the withdrawal emits overlap by construction, not only under
failure. **Hardening: the fast arm never reads an event newer than
``moment - _COMMIT_SKEW_MARGIN`` (5s)**, so a drain never advances the
watermark past a timestamp an in-flight, earlier-started transaction might
still land behind. The read is also capped just before the start of the
oldest open transaction in the database, which closes the gap for a
producer that takes longer than the margin to go from ``BEGIN`` to
``COMMIT`` (a lift batch waiting out its memory-lock budget, a pipeline
batch holding its memory locks to the batch commit). What each of the
four producers actually does in one transaction, since the bound rests on
the count and not on the intent:

- ``fact_lift`` and ``fact_provenance`` write single-digit rows per savepoint.
- the entity merge's fact fold moves one pair's sources and writes one event
  for the keeper inside that pair's savepoint.
- the **citation re-verifier is the one whose transaction scales with a
  configurable knob**, and an earlier revision of this paragraph got its
  quantity wrong by naming "one row per stale citation" — it issues one
  ``UPDATE`` per *candidate*, plus an event per citation whose staleness
  changed, so the row count is its ``batch_size``: ``500`` by default and up
  to ``MAX_REVERIFY_BATCH`` (5000) if an operator raises it.

None of the four makes an LLM call on this path, which is what keeps all of
them in the same order of magnitude as their row counts. **The margin is
established for the three fixed-size producers and for the re-verifier at
its default batch; it is not established at the re-verifier's configured
maximum**, where a transaction ten times longer is plainly closer to five
seconds than one at the default. That is a bound to measure before raising
``batch_size`` on a real corpus, not a reason to distrust today's default.
A producer that ever became slower than the margin would reopen the gap, at
which point the margin is the number to raise, not the mechanism to abandon.

**The margin compares two clocks, and today that is safe only because they
are the same clock.** ``moment`` is ``datetime.now(timezone.utc)`` in the
*application* process (or, for a replay/test, a caller-supplied stand-in for
it); ``created_at`` is computed by *PostgreSQL's* own clock. On today's
single-host deployment the app and the database share one system clock, so
the two are never meaningfully skewed. A split deployment — the app and the
database on separate hosts — would change that silently: any clock drift
between the two hosts eats directly into the margin's headroom (or, in the
adversarial direction, could invert it), with no error and no symptom,
because nothing here ever compares the two clocks against each other. This
is worth stating plainly rather than leaving implicit, so whoever changes
the deployment topology knows to re-examine it rather than trusting that a
constant tuned for one deployment shape still means the same thing on
another.

The slow arm's cursor carries the identical same-transaction-tie hazard —
``fact_lift`` can mint several facts inside one transaction, so
``knowledge_triples.created_at`` can tie the same way — and uses the same
tuple-compare shape, with ``id`` (a ``uuid``) as the tiebreak instead of a
bigint. It has no analogous commit-skew hazard of its own: it reads
``knowledge_triples`` directly rather than an events queue, and a fact row
becomes visible to it exactly when its own inserting transaction commits, no
different fact's commit ordering involved.

**Slow-arm coverage.** The cursor rotates over every non-``confirmed`` fact
ordered by ``(created_at, id)``, advancing past whatever slice it just
scanned; when a scan returns fewer rows than the slice size the walk has
reached the end of the table and the cursor resets to the beginning next
time it runs. That guarantees every fact is eventually revisited without ever
re-scanning the same head on every pass, at a cost bounded by the slice size
per run. ``confirmed`` facts are excluded from the slice because
``decide()`` always holds them (T2.05); scanning them would only spend
budget on a guaranteed no-op.

**One recompute per fact per tick, and it is load-bearing rather than a
saving.** When the slow arm is due it can slice over a fact the fast arm
already recomputed moments earlier in the same tick — always, on any vault
smaller than the slice size — so the slow arm skips whatever the fast arm just
did (``DrainOutcome.recomputed_ids`` in, ``facts_skipped_fresh`` out). Both
looks run in the same session and the same transaction, so the second one
reads exactly the state the first one wrote and cannot possibly observe
anything new. Before T2.46 that made it merely wasteful: a lock, a read and a
no-op write per duplicated fact. With demotion hysteresis it is a correctness
bug, because the grace window is counted in recompute cycles: a fact would
burn two cycles on one tick, and at the shipped grace of 1 the whole window
would collapse into the tick that opened it — the hysteresis silently not
applying, exactly on the ticks the slow arm happens to be due. The skip is
what makes "a cycle" mean "an opportunity for the fact to have been
re-corroborated" rather than "a call".

This does not weaken the backstop. The slow arm exists to reach facts the fast
arm *missed*; a fact the fast arm just recomputed is by definition not one of
them, and the cursor still advances over it, so the rotation period is
unchanged.

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

**Isolation is per-fact, not per-tick — a batch of many wedged facts can
still exhaust the tick.** ``_set_local_lock_timeout`` (M-2) bounds any *one*
fact's lock wait to ``_LOCK_TIMEOUT_MS`` (5s), but that bound is per fact,
not per run: roughly 24 or more concurrently-wedged facts in a single batch
would still sum past the job's own ``max_run_seconds`` (120s) ceiling and
reproduce the exact zero-progress rollback M-2 exists to prevent for the
single-poisonous-fact case (every lock in the batch failing after its own
5s still adds up to more than 120s of wall time before the batch finishes).
This is recorded as a known, accepted limit — pathological in practice (it
needs dozens of rows genuinely wedged at once, not one), and closing it
would mean either a much smaller per-fact timeout (trading false-positive
failures on ordinary contention for batch-level safety) or the bounded
in-state retry list the T2.09 report already declined to build for
unrelated reasons. Neither is undertaken here; this paragraph is the
record, not a task.

**Both arms re-check liveness under the per-fact lock, not just at
selection time (N-1).** ``fact_provenance``'s withdrawal sweep
(``_withdraw``, ``fact_provenance.py``) emits ``sources_changed``
*unconditionally* for every source row it withdraws, including the source
whose withdrawal just expired the fact inline — doc 08 §3.3's own contract
is "expires inline ... **then enqueues**", not "expires inline instead of
enqueuing". So the fast arm can reach a fact expired only moments earlier
through a perfectly legitimate, correctly-emitted event; this is not a
producer bug and not something either arm can route around by reading
events more carefully. ``recompute_fact`` has no opinion about ``expired_at``
at all — it only ever touches the verification axis, by the belief/
verification split ``knowledge_triples.py`` documents — so left unguarded it
will happily compute and journal a transition (a demote, typically) on a row
nothing is served from any more, landing in the same ``verified`` stream
G-C's metrics read live transitions from. ``_still_live`` closes this on
**both** arms: called inside each per-fact savepoint, under the same
``FOR UPDATE`` lock ``recompute_fact`` will immediately re-acquire on the
same row, so there is no window between the check and the decision for the
fact to be expired out from under it. The slow arm's own
``expired_at IS NULL`` slice filter is a cheap pre-filter that keeps
obviously-dead rows out of the slice entirely (and bounds the rotation
period by live fact count); ``_still_live`` is what actually closes the
race between that filter's read and the row's eventual lock, which the
filter alone cannot do.

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
from app.services.ladder_config import LadderConfig, get_ladder_config
from app.services.verification_ladder import get_demote_grace_cycles, recompute_fact

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

# Commit-skew hardening (I-1). The fast arm never reads (and therefore never
# advances the watermark past) an event newer than `moment - margin`, so an
# earlier-started, later-committing producer transaction always has this much
# headroom to land before the watermark could pass it. Not an operator knob:
# it protects a correctness property, not a cost/latency tradeoff, so it is a
# module constant rather than a RECOMPUTE_CONFIG_SCHEMA field.
_COMMIT_SKEW_MARGIN = timedelta(seconds=5)

# Lock-wait hardening (M-2). Scoped inside each per-fact SAVEPOINT via
# `SET LOCAL`, so it reverts automatically on that savepoint's rollback and
# never leaks into a sibling fact's attempt. Converts a wedged FOR UPDATE
# wait -- which would otherwise block until the whole tick's
# max_run_seconds cancellation, voiding every fact processed that tick,
# watermark included -- into an ordinary per-fact failure the ambient
# try/except settles alone, the same as any other poisonous fact.
_LOCK_TIMEOUT_MS = 5000


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


async def _set_local_lock_timeout(session: AsyncSession) -> None:
    """Bound the FOR UPDATE wait inside the caller's current SAVEPOINT (M-2).

    Without it, a wedged row lock blocks until the whole tick's
    `max_run_seconds` cancels the *entire* runner coroutine, which rolls back
    everything the tick had done, watermark advance included, making zero
    progress rather than settling the one blocked fact alone. With it, the
    lock acquisition itself fails after `_LOCK_TIMEOUT_MS` with an ordinary
    `lock_not_available` error, which the ambient per-fact try/except settles
    the same way as any other poisonous fact.

    **`SET LOCAL`'s actual PostgreSQL scoping, precisely** (get this wrong and
    the reasoning above is wrong too): it reverts on a subtransaction
    *rollback* -- `ROLLBACK TO SAVEPOINT`, which is what an exception
    unwinding `session.begin_nested()` issues -- but it does **not** revert
    on a successful `RELEASE SAVEPOINT`; it persists into whatever comes
    after in the same outer transaction, and only fully expires at that
    transaction's own end. So this call, made once per fact right after
    `begin_nested()`, is not "scoped to exactly one fact" on the happy path
    the way a first read suggests -- a successful fact's 5s timeout quietly
    carries forward into the next fact's savepoint too. That is harmless
    here specifically because every fact's savepoint calls this again
    unconditionally, so the value in effect for any given fact is always
    this call's own, whether it was already 5s from a sibling's successful
    run or the session default beforehand. What the rollback-only reversion
    *does* guarantee, and the property that actually matters, is that a
    poisonous fact's own failed savepoint cannot leave some *other*, more
    exotic session-level state change behind for its siblings -- rollback
    undoes it, same as everything else that fact's savepoint touched. A
    value literal rather than a bind parameter: `SET` does not accept the
    usual parameter placeholder, and the value is a fixed internal constant,
    never caller-supplied input.
    """
    await session.execute(text(f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT_MS}ms'"))


async def _still_live(session: AsyncSession, fact_id: str) -> bool:
    """Is this fact still un-expired? N-1's fix, shared by both arms.

    Read under `FOR UPDATE`, inside the caller's own savepoint -- the same
    lock `recompute_fact` will immediately re-acquire on the same row a
    moment later, so there is no window between this check and the decision
    it gates for the fact to be expired out from under it. A plain SELECT
    beforehand would leave exactly that window open.

    A **missing** row (the fact deleted outright, not merely expired) is
    treated as live here on purpose: `recompute_fact` already handles that
    case gracefully on its own (a "missing" hold that writes nothing, per
    its own docstring), so this only has to gate the one state
    `recompute_fact` has no opinion about at all -- `expired_at`, the belief
    axis, which `set_verification_status` never touches. See the module
    docstring's "Both arms re-check liveness" paragraph (N-1) for why a
    fact can reach this call already dead through a perfectly ordinary,
    correctly-emitted event.
    """
    result = await session.execute(
        text(
            "SELECT expired_at FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid) FOR UPDATE"
        ),
        {"id": str(fact_id)},
    )
    row = result.first()
    return row is None or row[0] is None


# ── the fast arm: drain sources_changed ────────────────────────────────

# The tuple compare, spelled as two conjuncts rather than a Postgres row
# constructor: `created_at >= :wm_ts` is what lets the planner prune
# partitions on the range-partitioned events table directly; the OR clause
# is what makes same-transaction ties (identical created_at, distinct id)
# unmissable. Removing the OR clause and its `id` half is exactly the T2.06
# same-transaction bug reintroduced -- see the module docstring and
# tests/test_verification_recompute.py's mutation proof.
#
# `created_at <= :safe_until` is the I-1 commit-skew margin: it caps how
# recent a row this drain will even look at, so the watermark this tick
# advances to can never land past a still-in-flight, earlier-started
# producer transaction. See the module docstring's commit-order-skew
# paragraph for the mechanical scenario this closes.
# An event's created_at is its transaction's start, so no uncommitted event
# is older than the oldest open transaction in this database. Capping the read
# there means neither a read row nor an idle advance can pass one, however long
# a producer holds its locks (a lift batch's lock waits, a pipeline batch held
# to its commit). A long unrelated transaction (a pg_dump) only delays the
# drain. Sessions of other roles report a NULL xact_start and are not counted;
# every producer connects as the app's own role.
_OLDEST_OPEN_TRANSACTION = text("""
    SELECT min(xact_start)
    FROM pg_stat_activity
    WHERE datname = current_database()
      AND pid <> pg_backend_pid()
      AND xact_start IS NOT NULL
""")

# pg_stat_activity is a snapshot taken at its first read in a transaction;
# without clearing it, a tick in a long transaction reads stale backends.
_CLEAR_STATS_SNAPSHOT = text("SELECT pg_stat_clear_snapshot()")

_MICROSECOND = timedelta(microseconds=1)

# A cap from a transaction this old is reported: request, flush and stream
# transactions end well inside it, so one that binds this long is a real hold.
_HOLD_REPORT_AFTER = timedelta(minutes=5)

_DRAIN_EVENTS = text("""
    SELECT id, created_at, payload
    FROM events
    WHERE event_type = 'sources_changed'
      AND object_type = 'fact'
      AND created_at >= CAST(:wm_ts AS timestamptz)
      AND (created_at > CAST(:wm_ts AS timestamptz) OR id > CAST(:wm_id AS bigint))
      AND created_at <= CAST(:safe_until AS timestamptz)
    ORDER BY created_at, id
    LIMIT CAST(:batch AS integer)
""")


@dataclass(frozen=True)
class DrainOutcome:
    events_scanned: int = 0
    facts_touched: int = 0
    facts_recomputed: int = 0
    facts_failed: int = 0
    facts_skipped_expired: int = 0
    transitions: int = 0
    # Which facts this arm recomputed, so the slow arm can decline to recompute
    # them again inside the same tick. See `run_recompute`.
    recomputed_ids: frozenset[str] = frozenset()
    # The start of a long-open transaction the drain was held behind, if any.
    held_since: datetime | None = None


@dataclass(frozen=True)
class _LadderInputs:
    """The ladder's config rows, read once per tick for every fact it touches."""

    config: LadderConfig
    grace_cycles: int


async def _drain_sources_changed(
    session: AsyncSession,
    state: _State,
    *,
    batch_size: int,
    moment: datetime,
    ladder: _LadderInputs,
) -> tuple[DrainOutcome, _State]:
    wm_ts = state.watermark_created_at or _EPOCH
    wm_id = state.watermark_id if state.watermark_id is not None else -1
    safe_until = moment - _COMMIT_SKEW_MARGIN
    await session.execute(_CLEAR_STATS_SNAPSHOT)
    oldest_open = (await session.execute(_OLDEST_OPEN_TRANSACTION)).scalar_one()
    held_since = None
    if oldest_open is not None:
        if (
            oldest_open - _MICROSECOND < safe_until
            and moment - oldest_open >= _HOLD_REPORT_AFTER
        ):
            held_since = oldest_open
        safe_until = min(safe_until, oldest_open - _MICROSECOND)
    result = await session.execute(
        _DRAIN_EVENTS,
        {"wm_ts": wm_ts, "wm_id": wm_id, "batch": batch_size, "safe_until": safe_until},
    )
    rows = result.mappings().all()
    if len(rows) < batch_size and (
        state.watermark_created_at is None or safe_until > state.watermark_created_at
    ):
        # A short read saw every event up to `safe_until`, so the watermark can
        # stand there: otherwise an idle drain re-scans every monthly partition
        # from the last event onward on every tick. Its id half is the last
        # row read at exactly that instant, so none is read twice. It only
        # moves forward: a clock stepped back must not re-expose drained rows.
        idle_state = replace(
            state,
            watermark_created_at=safe_until,
            watermark_id=max(
                (int(row["id"]) for row in rows if row["created_at"] == safe_until),
                default=-1,
            ),
        )
    else:
        idle_state = None
    if not rows:
        return DrainOutcome(held_since=held_since), idle_state or state

    fact_ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        payload = row["payload"] or {}
        fact_id = payload.get("fact_id")
        if fact_id and fact_id not in seen:
            seen.add(fact_id)
            fact_ids.append(fact_id)

    recomputed = failed = transitions = skipped_expired = 0
    recomputed_ids: set[str] = set()
    for fact_id in fact_ids:
        try:
            async with session.begin_nested():
                await _set_local_lock_timeout(session)
                if not await _still_live(session, fact_id):
                    skipped_expired += 1
                    continue
                decision = await recompute_fact(
                    session, fact_id, config=ladder.config, grace_cycles=ladder.grace_cycles,
                )
        except Exception:
            failed += 1
            logger.exception(
                "verification_recompute: fast-arm recompute failed for fact %s",
                fact_id,
            )
            continue
        recomputed += 1
        recomputed_ids.add(str(fact_id))
        if decision.outcome != "hold":
            transitions += 1

    last = rows[-1]
    new_state = idle_state or replace(
        state,
        watermark_created_at=last["created_at"],
        watermark_id=int(last["id"]),
    )
    outcome = DrainOutcome(
        events_scanned=len(rows),
        facts_touched=len(fact_ids),
        facts_recomputed=recomputed,
        facts_failed=failed,
        facts_skipped_expired=skipped_expired,
        transitions=transitions,
        recomputed_ids=frozenset(recomputed_ids),
        held_since=held_since,
    )
    return outcome, new_state


# ── the slow arm: reconcile from fact_sources directly ─────────────────

# confirmed is excluded: decide() always holds it (T2.05, the machine's
# ceiling), so recomputing it can only ever be a wasted lock-and-read.
#
# expired_at IS NULL is I-2's fix: expiry lives on the belief axis
# (`KnowledgeTripleRepository.expire`, never touches verification_status).
# An expired fact is dead, not merely unsourced, and it must not be
# recomputed. Without this filter a corroborated-but-expired fact with zero
# surviving sources gets "demoted" by the slow arm, journaling a `verified`
# row with outcome=demote that is indistinguishable in payload from a live
# demotion, in the exact stream T2.51/T2.40 count. Excluding dead facts also
# bounds the rotation period by *live* fact count rather than historical
# count, since a dead row can never be walked past -- it simply never enters
# the slice again.
#
# This is a pre-filter, not the whole guarantee: `_still_live` (below,
# called inside the per-fact savepoint on BOTH arms) is what actually closes
# the race between this SELECT and the row's eventual FOR UPDATE lock,
# because a fact can die in the gap between the two. It is also, on its own,
# the ONLY thing standing between the fast arm and a fact that just died --
# `fact_provenance`'s withdrawal sweep emits `sources_changed`
# unconditionally, including for the source whose withdrawal is what just
# expired the fact (doc 08 3.3: "expires inline ... then enqueues"), so the
# fast arm reaches freshly-dead facts through ordinary, correctly-emitted
# events, not merely through this slice's own read-write race. See the
# module docstring's "Both arms re-check liveness" paragraph (N-1).
#
# invalid_at (window-closed but still live, i.e. superseded-by-a-newer-
# belief history) is deliberately NOT excluded, on a ruling made here: a
# window-closed row stays in the LIVE_PREDICATE set
# (`knowledge_triples.py`'s `expired_at IS NULL`) and doc 08 says invalidation
# is a re-save on a retained row, never a delete -- it can still answer
# "what did we believe as of X". Its `fact_sources` can still shrink after
# its window closes: `fact_provenance`'s withdrawal sweep matches on
# `fact_id` alone, with no `invalid_at`/`expired_at` filter, and both
# producers already treat such a row as reachable (the fast arm recomputes
# whatever fact_id an event names, window-closed or not). Excluding it here
# would make the two arms disagree about which facts are "in scope" for
# recompute, which is a worse inconsistency than the small extra cost of
# reconciling a row that can only ever demote, never promote (fact_lift only
# adds sources to the *open* row for a triple_key, never a window-closed
# one).
_SLOW_ARM_SLICE = text("""
    SELECT id, created_at
    FROM knowledge_triples
    WHERE verification_status != 'confirmed'
      AND expired_at IS NULL
      AND created_at >= CAST(:cur_ts AS timestamptz)
      AND (created_at > CAST(:cur_ts AS timestamptz) OR id > CAST(:cur_id AS uuid))
    ORDER BY created_at, id
    LIMIT CAST(:batch AS integer)
""")


@dataclass(frozen=True)
class ReconcileOutcome:
    facts_scanned: int = 0
    facts_healed: int = 0
    facts_skipped_expired: int = 0
    facts_skipped_fresh: int = 0
    wrapped: bool = False


async def _reconcile_from_fact_sources(
    session: AsyncSession,
    state: _State,
    *,
    batch_size: int,
    ladder: _LadderInputs,
    already_recomputed: frozenset[str] = frozenset(),
) -> tuple[ReconcileOutcome, _State]:
    cur_ts = state.slow_cursor_created_at or _EPOCH
    cur_id = state.slow_cursor_id or _NIL_UUID
    result = await session.execute(
        _SLOW_ARM_SLICE, {"cur_ts": cur_ts, "cur_id": cur_id, "batch": batch_size}
    )
    rows = result.mappings().all()

    healed = skipped_expired = skipped_fresh = 0
    for row in rows:
        fact_id = str(row["id"])
        if fact_id in already_recomputed:
            skipped_fresh += 1
            continue
        try:
            async with session.begin_nested():
                await _set_local_lock_timeout(session)
                if not await _still_live(session, fact_id):
                    skipped_expired += 1
                    continue
                decision = await recompute_fact(
                    session, fact_id, config=ladder.config, grace_cycles=ladder.grace_cycles,
                )
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
        facts_scanned=len(rows), facts_healed=healed,
        facts_skipped_expired=skipped_expired, facts_skipped_fresh=skipped_fresh,
        wrapped=wrapped,
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

    Does not commit -- transaction control is the caller's. ``now`` is a seam
    for tests that need to force or suppress the slow arm without sleeping
    real wall-clock time.
    """
    moment = now or datetime.now(timezone.utc)
    state = await _load_state(session)

    ladder = _LadderInputs(
        config=await get_ladder_config(session),
        grace_cycles=await get_demote_grace_cycles(session),
    )
    drain_outcome, state = await _drain_sources_changed(
        session, state, batch_size=batch_size, moment=moment, ladder=ladder,
    )

    due = (
        state.slow_arm_last_run_at is None
        or (moment - state.slow_arm_last_run_at)
        >= timedelta(seconds=slow_arm_interval_seconds)
    )
    if due:
        reconcile_outcome, state = await _reconcile_from_fact_sources(
            session,
            state,
            batch_size=slow_arm_batch_size,
            ladder=ladder,
            already_recomputed=drain_outcome.recomputed_ids,
        )
        state = replace(state, slow_arm_last_run_at=moment)
    else:
        reconcile_outcome = ReconcileOutcome()

    await _save_state(session, state)
    return RecomputeOutcome(
        drain=drain_outcome, reconcile=reconcile_outcome, slow_arm_ran=due,
    )
