"""Undo for the dreaming pass's actions — per action and per batch (doc 08 §7).

**There is no per-action code path.** A single-action undo is a batch of one
through :func:`undo`, so the usual way a partial undo appears — a batch that
"reuses" a single path by calling it N times with per-call error handling —
has nowhere to live. That is the strongest of the four layers behind "partial
undo is not representable"; the others are a result type with no field that
could carry a per-item outcome, a module owning no savepoint and swallowing no
exception, and a validate-everything-under-the-locks-before-writing-anything
sequence. A source scan (``tests/test_dream_undo.py``) fails the build on all
five shapes rather than trusting review to notice them.

**Three outcomes, and only one of them guarantees nothing was written.**

===========================  ==============================================
Returns ``UndoBatch``        every named action restored, uncommitted; commit
Raises ``UndoRefused``       nothing written — validation completed before any
                             write, so the session is clean and still usable
Raises anything else         restores may already be in the session; **the
                             caller must roll back**
===========================  ==============================================

The last row is not a caveat, it is the contract. This module structurally
cannot clean up after itself: the scan that forbids the savepoint forbids the
rollback too.

**One side effect outlives the call**, and an in-process caller should know
it: `undo()` issues `SET LOCAL lock_timeout`, which is scoped to the
*transaction*, not to this function. A caller that keeps working on the same
transaction afterwards inherits that timeout on every later statement until it
commits or rolls back. Harmless for the HTTP door, whose transaction ends with
the request; worth knowing for a bulk caller doing more work on the same
session. The HTTP door inherits the obligation from its request-scoped
session dependency, which is exactly why the gap is invisible from this lane's
own route tests — an in-process caller inherits nothing, and a bulk loop
catching broadly per item and continuing on one session would commit a
partial, unjournalled undo.

**Undoability is a compare-and-swap against the live row**, not the ``events``
watermark doc 08 §7 names. §7's own parenthetical states the property — *"the
before-state the undo would restore is then no longer current"* — and both the
watermark and "a newer consolidation change" are narrower proxies for it in the
same sentence. The widening matters concretely: a human's triage write on a
near-duplicate block is not a consolidation event, so a watermark would report
the associate action still undoable and its row-delete arm would take the
triage with it. Widening a safety guard this way can only ever decline to act.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories import memory_relations as edges
from app.repositories.relational import PostgresMemoryRepository
from app.services import dream_journal as journal
from app.services.events import record_event
from app.utils.ids import new_id

# ── the retention window ─────────────────────────────────────────────────

# A standalone `config` row rather than a knob on any job: an undo window is not
# a property of the pass that produced the actions, and the pass's own schema is
# the operator surface for the pass.
RETENTION_CONFIG_KEY = "dream_undo_retention"
DEFAULT_RETENTION_DAYS = 14

# How far back an *unresolved* id is chased before it is called unknown. The
# normal resolve is bounded by the retention window, which is what keeps the
# by-id lookup pruned to one or two monthly children; this second, rarer query
# runs only for ids that window did not find, so an action just past its window
# reports the honest `retention_elapsed` instead of vanishing into "no such
# action".
STALE_LOOKBACK_DAYS = 365

_LOCK_TIMEOUT_MS = 5000

# ── blocking reasons, in fixed precedence order ──────────────────────────

REASON_ALREADY_UNDONE = "already_undone"
REASON_RETENTION_ELAPSED = "retention_elapsed"
REASON_OBJECT_MISSING = "object_missing"
# An action kind this door has no inverse for. Distinct from `state_changed`
# on purpose: the state may be pristine, and saying it changed would send an
# operator looking for a write that never happened. Doc 08 §7 lists seven
# reversible action kinds and today's producer ships three, so the fourth
# arrives with a producer rather than with a corruption.
REASON_UNSUPPORTED_ACTION = "unsupported_action"
REASON_STATE_CHANGED = "state_changed"

BLOCKING_REASONS: tuple[str, ...] = (
    REASON_ALREADY_UNDONE,
    REASON_RETENTION_ELAPSED,
    REASON_OBJECT_MISSING,
    REASON_UNSUPPORTED_ACTION,
    REASON_STATE_CHANGED,
)

_LEGAL_STATUSES = frozenset({"active", "superseded", "deprecated"})


# ── "exact prior state", with its exclusions named ───────────────────────


@dataclass(frozen=True)
class Exclusion:
    """One entry of the plan's D2 exclusion table, in code.

    An undo restores exact prior state when, for every field the action wrote,
    the post-undo value equals the journalled ``before`` value, and the undo
    writes no field the action did not write — *except* these. Saying "exact"
    while the implementation has sanctioned exclusions is the kind of clause
    that reads as a lie later, so each one is named, typed, and reported on the
    result.
    """

    key: str
    field: str
    actions: frozenset[str]
    kind: str


NOT_RESTORABLE = "not_restorable"
BY_DESIGN = "by_design"

_ALL_ACTIONS = frozenset(
    {journal.ACTION_SUBSUME, journal.ACTION_ASSOCIATE, journal.ACTION_REFINE}
)

EXCLUSIONS: tuple[Exclusion, ...] = (
    Exclusion(
        "E1", "updated_at",
        frozenset({journal.ACTION_SUBSUME, journal.ACTION_REFINE}),
        NOT_RESTORABLE,
    ),
    Exclusion(
        "E2", "metadata.dream.refine",
        frozenset({journal.ACTION_REFINE}), BY_DESIGN,
    ),
    Exclusion("E3", "events", _ALL_ACTIONS, BY_DESIGN),
    Exclusion(
        "E4", "orphan_tags", frozenset({journal.ACTION_REFINE}), NOT_RESTORABLE,
    ),
    Exclusion(
        "E5", "memory_relations_row",
        frozenset({journal.ACTION_ASSOCIATE}), BY_DESIGN,
    ),
    # The one exclusion T2.13 introduces rather than inherits: the inverse
    # *adds* the suppression tombstone, which was not in the prior state. Named
    # loudly so a reader who finds an unexplained metadata key on a restored
    # memory meets it here first.
    Exclusion(
        "E6", "metadata.dream.undone_subsume",
        frozenset({journal.ACTION_SUBSUME}), BY_DESIGN,
    ),
)

EXCLUSIONS_BY_FIELD: dict[str, Exclusion] = {item.field: item for item in EXCLUSIONS}


# ── the result types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class UndoneAction:
    """One restored action.

    **No field here can carry a per-item outcome** — no ``applied``, no
    ``skipped``, no ``error``. A caller wanting to report a partial undo would
    have to add one first, and the source scan fails when one appears. Same
    idiom as ``RefineVerdict`` having no field that could carry content.
    """

    event_id: int
    action: str
    object_id: str
    restored: tuple[str, ...]
    not_restored: tuple[str, ...]


@dataclass(frozen=True)
class UndoBatch:
    undo_batch_id: str
    undone: tuple[UndoneAction, ...]


@dataclass(frozen=True)
class BlockedAction:
    event_id: int
    action: str
    reason: str


class UndoRefused(Exception):
    """Validation declined before anything was written.

    The one raise whose contract is that the session is clean: a caller may
    report it and carry on without rolling back.
    """

    def __init__(self, blocked: tuple[BlockedAction, ...]):
        self.blocked = blocked
        super().__init__(
            "; ".join(f"{item.event_id}: {item.reason}" for item in blocked)
            or "undo refused"
        )


class UndoActionNotFound(UndoRefused):
    """An event id names no dream action this door can invert.

    Deliberately a subclass: it happens at resolution, before any write, so it
    carries exactly ``UndoRefused``'s guarantee and a caller that handles the
    parent is already correct.
    """

    def __init__(self, event_ids: tuple[int, ...]):
        self.missing_event_ids = event_ids
        super().__init__(())


class UndoNotJournalled(RuntimeError):
    """The journal readback came up short.

    ``record_event`` degrades loudly and never raises, which is correct for a
    side-channel and wrong for a Done-when clause: an undo whose journal
    silently failed *is* an erasure. Raising here makes an unjournalled undo
    unreachable rather than merely unlikely — and, like every raise other than
    ``UndoRefused``, it leaves restores in the session for the caller to roll
    back.
    """


class UndoIncomplete(RuntimeError):
    """Fewer actions were restored than were named. Unreachable by
    construction; the assertion is what makes a short result *unreturnable*
    rather than merely unproduced."""


# ── the journal read ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResolvedAction:
    event_id: int
    created_at: datetime
    object_id: str
    project: str | None
    payload: dict

    @property
    def action(self) -> str:
        return str(self.payload.get("action") or "")

    @property
    def before(self) -> dict:
        return self.payload.get("before") or {}

    @property
    def after(self) -> dict:
        return self.payload.get("after") or {}


@dataclass(frozen=True)
class LiveState:
    """The object as it is right now, read under the batch's locks."""

    exists: bool
    memory: dict | None = None
    edge: dict | None = None


_RESOLVE = text("""
    SELECT id AS event_id,
           created_at,
           CAST(object_id AS text) AS object_id,
           project,
           payload
    FROM events
    WHERE event_type = CAST(:event_type AS text)
      AND object_type = CAST(:object_type AS text)
      AND payload ->> 'detector' = CAST(:detector AS text)
      AND id = ANY(CAST(:event_ids AS bigint[]))
      AND created_at >= CAST(:floor AS timestamptz)
""")

_ALREADY_UNDONE = text("""
    SELECT DISTINCT payload ->> 'undoes_event_id' AS undoes
    FROM events
    WHERE event_type = CAST(:undone_type AS text)
      AND created_at >= CAST(:floor AS timestamptz)
      AND payload ->> 'undoes_event_id' = ANY(CAST(:event_ids AS text[]))
""")

# `tag_names` rides the read for the same reason it rides the producer's: the
# compare-and-swap must see the state as of the lock, not as of a render some
# minutes earlier. The digest reads the identical projection without the lock,
# so its advisory answer is computed from the same inputs as the door's.
_MEMORY_STATE_SQL = """
    SELECT m.status::text AS status,
           m.content,
           m.project,
           m.summary,
           m.metadata,
           CAST(m.superseded_by AS text) AS superseded_by,
           COALESCE(
               ARRAY(
                   SELECT t.name FROM memory_tags mt
                   JOIN tags t ON t.id = mt.tag_id
                   WHERE mt.memory_id = m.id
                   ORDER BY t.name
               ),
               CAST(ARRAY[] AS text[])
           ) AS tag_names
    FROM memories m
    WHERE m.id = CAST(:memory_id AS uuid)
"""

_LOCK_MEMORY = text(f"{_MEMORY_STATE_SQL}    FOR UPDATE")
_READ_MEMORY = text(_MEMORY_STATE_SQL)

_READ_CONTENT = text(
    "SELECT content FROM memories WHERE id = CAST(:memory_id AS uuid)"
)

_LOCK_EDGE = text("""
    SELECT 1 FROM memory_relations
     WHERE id = CAST(:id AS uuid)
     FOR UPDATE
""")

# One statement, and the suppression tombstone rides it for the same reason the
# producer's refine marker rides the summary write: a tombstone can never record
# an undo that did not land.
#
# **Three nested `jsonb_set`, and two is silent data loss.** `create_if_missing`
# creates only the *final* path element, so level 1 must materialise `dream` and
# level 2 must materialise `undone_subsume` before level 3 has a container to
# write the counterpart key into. Measured on this deployment's PostgreSQL
# 17.10: the two-level form drops the block even on a row that already carries a
# `dream` key, because `undone_subsume` beneath it does not exist — so a test
# written only against a previously-refined memory would not catch it either.
_RESTORE_STATUS = text("""
    UPDATE memories
       SET status = CAST(:status AS memory_status),
           superseded_by = CAST(:superseded_by AS uuid),
           metadata = jsonb_set(
               jsonb_set(
                   jsonb_set(
                       COALESCE(metadata, CAST('{}' AS jsonb)),
                       '{dream}',
                       COALESCE(metadata -> 'dream', CAST('{}' AS jsonb)),
                       true
                   ),
                   '{dream,undone_subsume}',
                   COALESCE(
                       metadata -> 'dream' -> 'undone_subsume',
                       CAST('{}' AS jsonb)
                   ),
                   true
               ),
               CAST(:tombstone_path AS text[]),
               CAST(:tombstone AS jsonb),
               true
           )
     WHERE id = CAST(:memory_id AS uuid)
    RETURNING CAST(id AS text) AS id
""")

# Bounded by real wall-clock rather than the caller's injected `now`: the row
# lands at the server's `now()` whatever the caller believes the time to be, and
# the bound is what prunes this read to one or two monthly children.
_READBACK = text("""
    SELECT count(*) AS journalled
    FROM events
    WHERE event_type = CAST(:undone_type AS text)
      AND created_at >= CAST(:floor AS timestamptz)
      AND payload ->> 'undo_batch_id' = CAST(:undo_batch_id AS text)
""")

_RESTORE_SUMMARY = text("""
    UPDATE memories
       SET summary = :summary
     WHERE id = CAST(:memory_id AS uuid)
    RETURNING CAST(id AS text) AS id
""")


async def read_retention(session: AsyncSession) -> timedelta:
    """The undo window, degrading to the default rather than taking the door
    down. A malformed operator edit is bookkeeping gone wrong, not grounds for
    refusing every undo in the system."""
    row = (
        await session.execute(
            select(Config).where(Config.key == RETENTION_CONFIG_KEY)
        )
    ).scalar_one_or_none()
    days = DEFAULT_RETENTION_DAYS
    if row is not None and isinstance(row.value, dict):
        raw = row.value.get("days")
        if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
            days = raw
    return timedelta(days=days)


def edge_triple(action: ResolvedAction) -> tuple[str, str, str]:
    edge = action.after.get("edge") or {}
    return (
        str(edge.get("source") or ""),
        str(edge.get("target") or ""),
        str(edge.get("rel_type") or ""),
    )


def lock_plan(actions: list[ResolvedAction]) -> list[tuple[str, tuple]]:
    """The deterministic global lock order: every ``memories`` row first,
    sorted by id, then every ``memory_relations`` row sorted by its triple.

    Pure, so the ordering can be asserted directly rather than through the
    absence of a deadlock, which is untestable. Two concurrent batches
    therefore cannot deadlock on the rows this module locks — *qualified*,
    because the refine inverse's ``set_tags`` inserts tag rows in the restored
    order, which is outside this plan. Two batches restoring overlapping new
    tag names can in principle deadlock there; the consequence is a
    whole-transaction abort, so atomicity is intact and only the claim needed
    narrowing.
    """
    memories = sorted(
        {
            action.object_id
            for action in actions
            if action.action in (journal.ACTION_SUBSUME, journal.ACTION_REFINE)
        }
    )
    relations = sorted(
        {
            edge_triple(action)
            for action in actions
            if action.action == journal.ACTION_ASSOCIATE
        }
    )
    return [("memory", (identifier,)) for identifier in memories] + [
        ("edge", triple) for triple in relations
    ]


def _memory_state(row: dict | None) -> LiveState:
    return LiveState(exists=row is not None, memory=row)


async def _read_live(
    session: AsyncSession, plan: list[tuple[str, tuple]], *, lock: bool
) -> dict[tuple, LiveState]:
    live: dict[tuple, LiveState] = {}
    for kind, key in plan:
        if kind == "memory":
            statement = _LOCK_MEMORY if lock else _READ_MEMORY
            row = (
                await session.execute(statement, {"memory_id": key[0]})
            ).mappings().first()
            live[(kind, key)] = _memory_state(dict(row) if row else None)
        else:
            source, target, rel_type = key
            edge = await edges.get_edge(
                session,
                source_memory_id=source,
                target_memory_id=target,
                rel_type=rel_type,
            )
            if edge is not None and lock:
                # Located by the triple, then locked by id and re-read: the
                # normalisation the triple needs lives behind `get_edge`, and
                # a row that vanished between the two reads comes back as
                # `object_missing` rather than as a lock on nothing.
                await session.execute(_LOCK_EDGE, {"id": edge["id"]})
                edge = await edges.get_edge(
                    session,
                    source_memory_id=source,
                    target_memory_id=target,
                    rel_type=rel_type,
                )
            live[(kind, key)] = LiveState(exists=edge is not None, edge=edge)
    return live


def live_key(action: ResolvedAction) -> tuple[str, tuple]:
    if action.action == journal.ACTION_ASSOCIATE:
        return ("edge", edge_triple(action))
    return ("memory", (action.object_id,))


# ── the compare-and-swap, shared by the digest and the door ──────────────


def _subsume_unchanged(action: ResolvedAction, live: LiveState) -> bool:
    row = live.memory or {}
    after = action.after
    return (
        row.get("status") == after.get("status")
        and row.get("superseded_by") == after.get("superseded_by")
    )


def _associate_unchanged(action: ResolvedAction, live: LiveState) -> bool:
    journalled = (
        (action.after.get("edge") or {}).get("properties") or {}
    ).get(journal.NEAR_DUPLICATE_PASS)
    return edges.pass_block_of(live.edge, journal.NEAR_DUPLICATE_PASS) == journalled


def _refine_unchanged(action: ResolvedAction, live: LiveState) -> bool:
    row = live.memory or {}
    after = action.after
    live_tags = sorted(row.get("tag_names") or ())
    after_tags = sorted(after.get("tags") or ())
    return (
        row.get("summary") == after.get("summary")
        and live_tags == after_tags
        and journal.refine_marker_of(row.get("metadata"))
        == after.get("metadata_dream_refine")
    )


_UNCHANGED = {
    journal.ACTION_SUBSUME: _subsume_unchanged,
    journal.ACTION_ASSOCIATE: _associate_unchanged,
    journal.ACTION_REFINE: _refine_unchanged,
}


def blocking_reason(
    action: ResolvedAction,
    *,
    live: LiveState,
    already_undone: bool,
    now: datetime,
    retention: timedelta,
) -> str | None:
    """The one predicate, called from the digest's advisory read and from the
    door's authoritative one, so the two answers cannot drift.

    Precedence is fixed and tested: an action that is both already undone and
    out of window reports ``already_undone``, because that is the fact an
    operator needs first.
    """
    if already_undone:
        return REASON_ALREADY_UNDONE
    if now - action.created_at > retention:
        return REASON_RETENTION_ELAPSED
    if not live.exists:
        return REASON_OBJECT_MISSING
    comparator = _UNCHANGED.get(action.action)
    if comparator is None:
        return REASON_UNSUPPORTED_ACTION
    if not comparator(action, live):
        return REASON_STATE_CHANGED
    return None


# ── the three inverses ───────────────────────────────────────────────────


async def _invert_subsume(
    session: AsyncSession,
    action: ResolvedAction,
    live: LiveState,
    *,
    undo_batch_id: str,
) -> UndoneAction:
    before = action.before
    status = before.get("status")
    if status not in _LEGAL_STATUSES:
        raise ValueError(
            f"the journalled before-status {status!r} is outside the memory "
            "status enum; refusing to restore a value the lifecycle cannot hold"
        )
    counterpart = str((action.payload.get("pair") or {}).get("newer") or "")
    # Unlocked, and deliberately so. The subsume payload journals no shas, so
    # this read is the counterpart sha's only source; if the counterpart's
    # content moves between here and the commit the recorded sha is stale and
    # the tombstone lapses **early**, re-proposing the pair — which is the
    # behaviour with no tombstone at all. The race can only ever fail toward
    # not suppressing, never toward suppressing a supersession it should not,
    # so a second lock contending with the dreaming pass's write phase is not
    # worth buying.
    counterpart_content = (
        await session.execute(_READ_CONTENT, {"memory_id": counterpart})
    ).scalar_one_or_none() if counterpart else None

    tombstone = {
        "at": datetime.now(timezone.utc).isoformat(),
        "undo_batch_id": undo_batch_id,
        "cycle_id": action.payload.get("cycle_id"),
        "content_sha": journal.content_sha((live.memory or {}).get("content") or ""),
        "counterpart_content_sha": (
            journal.content_sha(counterpart_content)
            if counterpart_content is not None else None
        ),
    }
    # One statement, because `chk_superseded_has_pointer` is evaluated once per
    # row per statement: the intermediate state in which the status has moved
    # and the pointer has not is not merely unlikely, it has no existence for
    # the constraint to observe.
    await session.execute(
        _RESTORE_STATUS,
        {
            "memory_id": action.object_id,
            "status": status,
            "superseded_by": before.get("superseded_by"),
            "tombstone_path": [*journal.SUBSUME_TOMBSTONE_PATH, counterpart],
            "tombstone": json.dumps(tombstone),
        },
    )
    return UndoneAction(
        event_id=action.event_id,
        action=action.action,
        object_id=action.object_id,
        restored=("status", "superseded_by"),
        not_restored=("updated_at", "events", "metadata.dream.undone_subsume"),
    )


async def _invert_associate(
    session: AsyncSession,
    action: ResolvedAction,
    live: LiveState,
    *,
    undo_batch_id: str,
) -> UndoneAction:
    source, target, rel_type = edge_triple(action)
    prior = action.before.get("edge")
    not_restored: list[str] = ["events"]

    if isinstance(prior, dict):
        # The block existed before this action overwrote it, whatever `created`
        # says: restore it through the same nested pass-keyed write, never a
        # whole-object assignment.
        await edges.write_pass_block(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
            pass_key=journal.NEAR_DUPLICATE_PASS,
            block=prior,
        )
        return UndoneAction(
            event_id=action.event_id,
            action=action.action,
            object_id=action.object_id,
            restored=("edge",),
            not_restored=tuple(not_restored),
        )

    exclusive = await edges.clear_pass_block(
        session,
        source_memory_id=source,
        target_memory_id=target,
        rel_type=rel_type,
        pass_key=journal.NEAR_DUPLICATE_PASS,
    )
    if action.payload.get("created") and exclusive:
        await edges.delete_edge(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
        )
    elif action.payload.get("created"):
        # Prior state was "no row", but a sibling pass has claimed it since.
        # Restoring "no row" would destroy another actor's edge, so the row
        # survives carrying only what is not mine, and the result says so.
        not_restored.append("memory_relations_row")
    return UndoneAction(
        event_id=action.event_id,
        action=action.action,
        object_id=action.object_id,
        restored=("edge",),
        not_restored=tuple(not_restored),
    )


async def _invert_refine(
    session: AsyncSession,
    action: ResolvedAction,
    live: LiveState,
    *,
    undo_batch_id: str,
) -> UndoneAction:
    fields = tuple(action.payload.get("fields") or ())
    if not fields:
        raise ValueError(
            "a refine action journalled no changed field; a no-op that reports "
            "success is indistinguishable from a completed undo"
        )
    before = action.before
    restored: list[str] = []
    if "summary" in fields:
        # The marker is deliberately absent from this statement (E2): on a
        # first refine the before-value is absent, so restoring it would clear
        # the marker and the next cycle would re-apply the refine, silently
        # reversing the undo.
        await session.execute(
            _RESTORE_SUMMARY,
            {"memory_id": action.object_id, "summary": before.get("summary")},
        )
        restored.append("summary")
    if "tags" in fields:
        await PostgresMemoryRepository(session).set_tags(
            UUID(action.object_id), list(before.get("tags") or ())
        )
        restored.append("tags")

    not_restored = ["events", "metadata.dream.refine"]
    if "summary" in restored:
        not_restored.append("updated_at")
    if "tags" in restored:
        not_restored.append("orphan_tags")
    return UndoneAction(
        event_id=action.event_id,
        action=action.action,
        object_id=action.object_id,
        restored=tuple(restored),
        not_restored=tuple(not_restored),
    )


_INVERSES = {
    journal.ACTION_SUBSUME: _invert_subsume,
    journal.ACTION_ASSOCIATE: _invert_associate,
    journal.ACTION_REFINE: _invert_refine,
}


# ── the batch ────────────────────────────────────────────────────────────


async def resolve(
    session: AsyncSession,
    event_ids: list[int],
    *,
    now: datetime,
    retention: timedelta,
) -> list[ResolvedAction]:
    """Every named id as a dream action, in journal order.

    The normal read is bounded by the retention window, which is what prunes
    the by-id lookup to one or two monthly children — ``events``'s primary key
    is composite, so a bare ``WHERE id = :id`` scans every child. Ids that
    window misses are chased once over a wider bound, so an action just past
    its window can still be reported as ``retention_elapsed`` rather than
    disappearing.
    """
    params = {
        "event_type": journal.EVENT_TYPE,
        "object_type": journal.OBJECT_TYPE,
        "detector": journal.DETECTOR,
        "event_ids": event_ids,
    }
    rows = (
        await session.execute(
            _RESOLVE, {**params, "floor": now - retention}
        )
    ).mappings().all()
    found = {int(row["event_id"]) for row in rows}
    if len(found) != len(set(event_ids)):
        rows = list(rows) + [
            row
            for row in (
                await session.execute(
                    _RESOLVE,
                    {
                        **params,
                        "event_ids": [
                            identifier
                            for identifier in set(event_ids)
                            if identifier not in found
                        ],
                        "floor": now - timedelta(days=STALE_LOOKBACK_DAYS),
                    },
                )
            ).mappings()
        ]

    resolved = [
        ResolvedAction(
            event_id=int(row["event_id"]),
            created_at=row["created_at"],
            object_id=row["object_id"],
            project=row["project"],
            payload=row["payload"] or {},
        )
        for row in rows
    ]
    missing = tuple(
        sorted(set(event_ids) - {action.event_id for action in resolved})
    )
    if missing:
        raise UndoActionNotFound(missing)
    resolved.sort(key=lambda action: (action.created_at, action.event_id))
    return resolved


async def already_undone_ids(
    session: AsyncSession, actions: list[ResolvedAction], *, now: datetime
) -> set[int]:
    rows = (
        await session.execute(
            _ALREADY_UNDONE,
            {
                "undone_type": journal.UNDONE_EVENT_TYPE,
                "floor": min(action.created_at for action in actions),
                "event_ids": [str(action.event_id) for action in actions],
            },
        )
    ).mappings().all()
    return {int(row["undoes"]) for row in rows if row["undoes"]}


async def _journal_undo(
    session: AsyncSession,
    *,
    action: ResolvedAction,
    restored: UndoneAction,
    undo_batch_id: str,
    actor: str,
) -> None:
    """One row per undone action, never one per batch.

    **``before`` and ``after`` are in the undo's own frame**, not the original
    action's: an undo *is* an action, and every payload in this journal means
    "what this row's transition moved from and to". So the undo's ``before`` is
    the action's ``after``, and its ``after`` is the action's ``before``.
    Stated explicitly because writing it the other way round produces a journal
    that reads plausibly and is exactly backwards.

    ``object_type`` stays ``memory`` so one memory's timeline carries the
    action and its reversal through the existing index.
    """
    await record_event(
        session,
        event_type=journal.UNDONE_EVENT_TYPE,
        object_type=journal.OBJECT_TYPE,
        object_id=UUID(action.object_id),
        project=action.project,
        actor=actor,
        payload={
            "action": action.action,
            "undoes_event_id": action.event_id,
            "undo_batch_id": undo_batch_id,
            "cycle_id": action.payload.get("cycle_id"),
            "before": action.after,
            "after": action.before,
            "restored": list(restored.restored),
            "not_restored": list(restored.not_restored),
        },
    )


async def undo(
    session: AsyncSession,
    *,
    event_ids: list[int],
    actor: str,
    now: datetime | None = None,
) -> UndoBatch:
    """Restore every named action, or write nothing.

    Takes the caller's session, opens no transaction and commits nothing. See
    the module docstring for the three outcomes and the caller obligation the
    third one carries — it is a contract, not a docstring courtesy.
    """
    if not event_ids:
        raise UndoActionNotFound(())
    resolved_now = now or datetime.now(timezone.utc)
    retention = await read_retention(session)

    # A wedged row lock aborts the whole batch with nothing written rather than
    # hanging an HTTP request. This serves atomicity rather than threatening it.
    await session.execute(text(f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT_MS}ms'"))

    actions = await resolve(
        session, list(event_ids), now=resolved_now, retention=retention
    )
    plan = lock_plan(actions)
    live = await _read_live(session, plan, lock=True)
    undone_already = await already_undone_ids(session, actions, now=resolved_now)

    blocked: list[BlockedAction] = []
    for action in actions:
        reason = blocking_reason(
            action,
            live=live[live_key(action)],
            already_undone=action.event_id in undone_already,
            now=resolved_now,
            retention=retention,
        )
        if reason is not None:
            blocked.append(
                BlockedAction(
                    event_id=action.event_id, action=action.action, reason=reason
                )
            )
    if blocked:
        # Nothing has been written at this point, and that is the property that
        # makes this raise safe for a caller to report and carry on from.
        raise UndoRefused(tuple(blocked))

    # LIFO. The three inverses touch disjoint state so no order is required
    # today; it is specified because it is the natural inverse of a sequence
    # and the right default the day two action kinds do interact.
    undo_batch_id = str(new_id())
    undone: list[UndoneAction] = []
    for action in reversed(actions):
        restored = await _INVERSES[action.action](
            session, action, live[live_key(action)], undo_batch_id=undo_batch_id,
        )
        # Only a real restore counts as one. An inverse that returns anything
        # else has reported nothing, and the completeness check below is what
        # makes a short result *unreturnable* rather than merely unproduced —
        # a tuple shorter than the request carries no forbidden field and is
        # invisible to a scan looking for one.
        if isinstance(restored, UndoneAction):
            undone.append(restored)

    if len(undone) != len(actions):
        raise UndoIncomplete(
            f"{len(undone)} of {len(actions)} actions restored; a batch that "
            "cannot be completed must not be returned as one that was"
        )

    by_event = {action.event_id: action for action in actions}
    for restored_action in undone:
        await _journal_undo(
            session,
            action=by_event[restored_action.event_id],
            restored=restored_action,
            undo_batch_id=undo_batch_id,
            actor=actor,
        )

    journalled = (
        await session.execute(
            _READBACK,
            {
                "undone_type": journal.UNDONE_EVENT_TYPE,
                "floor": datetime.now(timezone.utc) - timedelta(days=1),
                "undo_batch_id": undo_batch_id,
            },
        )
    ).scalar_one()
    if journalled != len(undone):
        raise UndoNotJournalled(
            f"{journalled} of {len(undone)} undo rows reached the journal; an "
            "undo that could not be journalled does not happen"
        )

    return UndoBatch(
        undo_batch_id=undo_batch_id, undone=tuple(reversed(undone))
    )
