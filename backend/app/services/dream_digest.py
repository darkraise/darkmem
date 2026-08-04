"""The dream digest: one consolidation cycle, read back from its journal.

Doc 08 §7, doc 13 §6.3. The dreaming pass writes one uniform ``consolidated``
event per action carrying its own before/after; this module groups that stream
by ``payload.cycle_id`` and, within a cycle, by the object each action touched.

**Actions inside a cycle are ordered by ``(created_at, id)`` — journal order,
which is application order — and never regrouped by action kind.** A cycle
where a duplicate pair outranked a subsume pair legitimately shows an
``associate`` against a memory followed by the ``subsume`` that retired it.
That is what happened, and a digest that reordered or hid it would be
describing a cycle that did not occur.

Every query is bounded by ``created_at``. ``events`` is RANGE-partitioned by
month, so the bound is what prunes the read to the relevant children rather
than a nicety — and it is why no index is added for a surface that is, by the
pass's own fan-out limits, at most fifty rows a night.

``detector`` filters the stream so a future producer emitting ``consolidated``
rows of its own does not silently appear in this digest wearing an action name
this module has no inverse for.

**A human curation batch (T2.23's hygiene queue) journals through this same
stream, and the projection says so.** Its bulk actions reuse the dreaming
pass's journal shape (same ``event_type``, same ``detector="dedup"``, so
``dream_undo`` can invert them) but carry an extra ``payload.origin`` key and a
real ``actor``, which memory_dream's own actions never set. ``detector`` is
what a *detector* found; a human clicking "supersede" or "confirm" is not one,
so an action carrying ``origin`` never renders ``detector`` — rendering
``"dedup"`` for a human-initiated prune would be a false provenance claim,
not a detail. ``origin`` and ``actor`` are projected instead, at both the
per-action (``DreamActionView``) and per-cycle (``DreamCycleSummary``) level —
a cycle is homogeneous in origin by construction, since a human bulk-action
request and an automated dreaming tick never share a ``cycle_id``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import dream_journal as journal

# How far back the digest looks when the caller names no window. Independent of
# `dream_undo_retention`: an action stays *readable* long after it stops being
# undoable, and the digest renders the honest blocked reason rather than hiding
# the row.
DEFAULT_DIGEST_WINDOW_DAYS = 30

MAX_CYCLE_LIMIT = 200


@dataclass(frozen=True)
class DreamActionView:
    event_id: int
    created_at: datetime
    action: str
    object_id: str
    project: str | None
    detector: str | None
    origin: str | None
    actor: str | None
    before: dict
    after: dict
    detail: dict
    undone: bool = False
    undone_at: datetime | None = None
    undone_by: str | None = None
    undo_batch_id: str | None = None
    # Reconstructed from the `undone` event's own payload (`dream_undo._journal_undo`
    # writes both lists there), never re-stored on this row — the journal already
    # carries the one place this information exists. Empty for an action that has
    # not been undone; the invert functions never produce an empty `restored` for
    # one that has.
    restored: tuple[str, ...] = ()
    not_restored: tuple[str, ...] = ()
    undoable: bool = False
    undo_blocked_reason: str | None = None


@dataclass(frozen=True)
class DreamObjectGroup:
    object_id: str
    project: str | None
    actions: list[DreamActionView] = field(default_factory=list)


@dataclass(frozen=True)
class DreamCycleSummary:
    cycle_id: str
    started_at: datetime
    ended_at: datetime
    projects: list[str]
    total: int
    counts: dict[str, int]
    undone_count: int
    # None means an automated dreaming tick; a value (e.g. "hygiene_queue")
    # names the human surface that ran the batch. Homogeneous within a cycle
    # by construction — see the module docstring.
    origin: str | None = None


@dataclass(frozen=True)
class DreamCycleDigest:
    cycle_id: str
    started_at: datetime
    ended_at: datetime
    counts: dict[str, int]
    undone_count: int
    objects: list[DreamObjectGroup]


def _window(
    since: datetime | None, until: datetime | None, *, now: datetime | None = None
) -> tuple[datetime, datetime]:
    resolved_now = now or datetime.now(timezone.utc)
    return (
        since or resolved_now - timedelta(days=DEFAULT_DIGEST_WINDOW_DAYS),
        until or resolved_now,
    )


_CYCLES = text("""
    SELECT payload ->> 'cycle_id' AS cycle_id,
           min(created_at) AS started_at,
           max(created_at) AS ended_at,
           count(*) AS total,
           count(*) FILTER (WHERE payload ->> 'action' = 'subsume') AS subsume,
           count(*) FILTER (WHERE payload ->> 'action' = 'associate') AS associate,
           count(*) FILTER (WHERE payload ->> 'action' = 'refine') AS refine,
           COALESCE(
               array_agg(DISTINCT project) FILTER (WHERE project IS NOT NULL),
               CAST(ARRAY[] AS text[])
           ) AS projects,
           -- Homogeneous within a cycle by construction (a human bulk-action
           -- request and an automated tick never share a cycle_id), so any
           -- aggregate agrees; MIN is the cheapest that ignores NULLs.
           min(payload ->> 'origin') AS origin
    FROM events
    WHERE event_type = CAST(:event_type AS text)
      AND object_type = CAST(:object_type AS text)
      AND payload ->> 'detector' = CAST(:detector AS text)
      AND payload ->> 'cycle_id' IS NOT NULL
      AND created_at >= CAST(:since AS timestamptz)
      AND created_at <= CAST(:until AS timestamptz)
      AND (CAST(:project AS text) IS NULL OR project = CAST(:project AS text))
    GROUP BY payload ->> 'cycle_id'
    ORDER BY min(created_at) DESC
    LIMIT CAST(:limit AS int) OFFSET CAST(:offset AS int)
""")

_CYCLE_TOTAL = text("""
    SELECT count(DISTINCT payload ->> 'cycle_id') AS total
    FROM events
    WHERE event_type = CAST(:event_type AS text)
      AND object_type = CAST(:object_type AS text)
      AND payload ->> 'detector' = CAST(:detector AS text)
      AND payload ->> 'cycle_id' IS NOT NULL
      AND created_at >= CAST(:since AS timestamptz)
      AND created_at <= CAST(:until AS timestamptz)
      AND (CAST(:project AS text) IS NULL OR project = CAST(:project AS text))
""")

# An undo can only ever follow its action, so the lower bound alone prunes; the
# digest window's upper bound must NOT apply here or an undo performed today
# would be invisible on a cycle read with an `until` of yesterday, and the
# digest would offer an undo button for an action already undone.
_UNDONE_BY_CYCLE = text("""
    SELECT payload ->> 'cycle_id' AS cycle_id, count(*) AS undone
    FROM events
    WHERE event_type = CAST(:undone_type AS text)
      AND created_at >= CAST(:since AS timestamptz)
      AND payload ->> 'cycle_id' = ANY(CAST(:cycle_ids AS text[]))
    GROUP BY payload ->> 'cycle_id'
""")

_CYCLE_ACTIONS = text("""
    SELECT id AS event_id,
           created_at,
           CAST(object_id AS text) AS object_id,
           project,
           actor,
           payload
    FROM events
    WHERE event_type = CAST(:event_type AS text)
      AND object_type = CAST(:object_type AS text)
      AND payload ->> 'detector' = CAST(:detector AS text)
      AND payload ->> 'cycle_id' = CAST(:cycle_id AS text)
      AND created_at >= CAST(:since AS timestamptz)
      AND created_at <= CAST(:until AS timestamptz)
    ORDER BY created_at, id
""")

_UNDONE_FOR_ACTIONS = text("""
    SELECT created_at,
           actor,
           payload
    FROM events
    WHERE event_type = CAST(:undone_type AS text)
      AND created_at >= CAST(:since AS timestamptz)
      AND payload ->> 'undoes_event_id' = ANY(CAST(:event_ids AS text[]))
    ORDER BY created_at, id
""")


def _stream_params(*, since: datetime, until: datetime) -> dict:
    return {
        "event_type": journal.EVENT_TYPE,
        "object_type": journal.OBJECT_TYPE,
        "detector": journal.DETECTOR,
        "since": since,
        "until": until,
    }


def action_detail(payload: dict) -> dict:
    """The per-action extras a rendered digest shows beside before/after."""
    action = payload.get("action")
    if action == journal.ACTION_REFINE:
        return {"fields": list(payload.get("fields") or ())}
    detail = {
        "pair": payload.get("pair"),
        "verdict": payload.get("verdict"),
        "score": payload.get("score"),
    }
    if action == journal.ACTION_ASSOCIATE:
        detail["created"] = bool(payload.get("created"))
    return detail


async def list_cycles(
    session: AsyncSession,
    *,
    project: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> tuple[list[DreamCycleSummary], int]:
    resolved_since, resolved_until = _window(since, until, now=now)
    params = _stream_params(since=resolved_since, until=resolved_until)
    params["project"] = project

    total = (
        await session.execute(_CYCLE_TOTAL, params)
    ).scalar_one()

    rows = (
        await session.execute(
            _CYCLES,
            {**params, "limit": max(1, min(limit, MAX_CYCLE_LIMIT)), "offset": max(0, offset)},
        )
    ).mappings().all()
    if not rows:
        return [], int(total)

    undone = {
        row["cycle_id"]: int(row["undone"])
        for row in (
            await session.execute(
                _UNDONE_BY_CYCLE,
                {
                    "undone_type": journal.UNDONE_EVENT_TYPE,
                    "since": resolved_since,
                    "cycle_ids": [row["cycle_id"] for row in rows],
                },
            )
        ).mappings()
    }

    return [
        DreamCycleSummary(
            cycle_id=row["cycle_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            projects=sorted(row["projects"] or ()),
            total=int(row["total"]),
            counts={
                journal.ACTION_SUBSUME: int(row["subsume"]),
                journal.ACTION_ASSOCIATE: int(row["associate"]),
                journal.ACTION_REFINE: int(row["refine"]),
            },
            undone_count=undone.get(row["cycle_id"], 0),
            origin=row["origin"],
        )
        for row in rows
    ], int(total)


async def read_cycle_actions(
    session: AsyncSession,
    cycle_id: str,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    now: datetime | None = None,
) -> list[DreamActionView]:
    """One cycle's actions in journal order, each carrying its undo status.

    Undoability is not decided here — that needs the live rows, and it is the
    same pure predicate the door re-runs under its locks (see
    :mod:`app.services.dream_undo`). This returns the journal half.
    """
    resolved_since, resolved_until = _window(since, until, now=now)
    rows = (
        await session.execute(
            _CYCLE_ACTIONS,
            {
                **_stream_params(since=resolved_since, until=resolved_until),
                "cycle_id": cycle_id,
            },
        )
    ).mappings().all()
    if not rows:
        return []

    undone_by_action: dict[str, dict] = {}
    for row in (
        await session.execute(
            _UNDONE_FOR_ACTIONS,
            {
                "undone_type": journal.UNDONE_EVENT_TYPE,
                "since": resolved_since,
                "event_ids": [str(row["event_id"]) for row in rows],
            },
        )
    ).mappings():
        payload = row["payload"] or {}
        undone_by_action.setdefault(
            str(payload.get("undoes_event_id")),
            {
                "at": row["created_at"],
                "by": row["actor"],
                "batch": payload.get("undo_batch_id"),
                "restored": payload.get("restored") or [],
                "not_restored": payload.get("not_restored") or [],
            },
        )

    views: list[DreamActionView] = []
    for row in rows:
        payload = row["payload"] or {}
        undo = undone_by_action.get(str(row["event_id"]))
        origin = payload.get("origin")
        views.append(
            DreamActionView(
                event_id=int(row["event_id"]),
                created_at=row["created_at"],
                action=str(payload.get("action") or ""),
                object_id=row["object_id"],
                project=row["project"],
                # `detector` names what a *detector* found. An action carrying
                # `origin` came from a human curation surface, not a detector,
                # so rendering the payload's literal "dedup" (kept only for
                # dream_undo's resolve() to match on) would be a false
                # provenance claim.
                detector=payload.get("detector") if not origin else None,
                origin=origin,
                actor=row["actor"],
                before=payload.get("before") or {},
                after=payload.get("after") or {},
                detail=action_detail(payload),
                undone=undo is not None,
                undone_at=undo["at"] if undo else None,
                undone_by=undo["by"] if undo else None,
                undo_batch_id=undo["batch"] if undo else None,
                restored=tuple(undo["restored"]) if undo else (),
                not_restored=tuple(undo["not_restored"]) if undo else (),
            )
        )
    return views


async def annotate_undoability(
    session: AsyncSession,
    actions: list[DreamActionView],
    *,
    now: datetime | None = None,
) -> list[DreamActionView]:
    """Fill each view's ``undoable`` / ``undo_blocked_reason``, advisory only.

    Computed with no locks, from the same pure predicate the door re-runs under
    its locks — the same function object, so the advisory and authoritative
    answers cannot drift into disagreement about *why*. They can still disagree
    about *whether*, because the live row may move between this render and the
    request; that is what the door's 409 is for, and it is why T2.38 must
    re-fetch on a 409 rather than trusting its last render.
    """
    # Imported here rather than at module scope: the undo service reads this
    # module's window constant, and the digest reads its predicate.
    from app.services import dream_undo

    if not actions:
        return actions
    resolved_now = now or datetime.now(timezone.utc)
    retention = await dream_undo.read_retention(session)

    resolved = [
        dream_undo.ResolvedAction(
            event_id=view.event_id,
            created_at=view.created_at,
            object_id=view.object_id,
            project=view.project,
            payload={
                "action": view.action,
                "before": view.before,
                "after": view.after,
                "created": view.detail.get("created"),
                "fields": view.detail.get("fields"),
            },
        )
        for view in actions
    ]
    live = await dream_undo._read_live(
        session, dream_undo.lock_plan(resolved), lock=False
    )

    annotated: list[DreamActionView] = []
    for view, action in zip(actions, resolved):
        reason = dream_undo.blocking_reason(
            action,
            live=live[dream_undo.live_key(action)],
            already_undone=view.undone,
            now=resolved_now,
            retention=retention,
        )
        annotated.append(
            replace(view, undoable=reason is None, undo_blocked_reason=reason)
        )
    return annotated


def group_by_object(actions: list[DreamActionView]) -> list[DreamObjectGroup]:
    """One group per object, ordered by its first action, actions in journal
    order within it. Both orderings come from the input sequence, which the
    query already sorted by ``(created_at, id)``."""
    groups: dict[str, DreamObjectGroup] = {}
    for view in actions:
        group = groups.get(view.object_id)
        if group is None:
            group = DreamObjectGroup(object_id=view.object_id, project=view.project)
            groups[view.object_id] = group
        group.actions.append(view)
    return list(groups.values())


def digest_of(cycle_id: str, actions: list[DreamActionView]) -> DreamCycleDigest:
    counts = {
        journal.ACTION_SUBSUME: 0,
        journal.ACTION_ASSOCIATE: 0,
        journal.ACTION_REFINE: 0,
    }
    for view in actions:
        if view.action in counts:
            counts[view.action] += 1
    return DreamCycleDigest(
        cycle_id=cycle_id,
        started_at=actions[0].created_at,
        ended_at=actions[-1].created_at,
        counts=counts,
        undone_count=sum(1 for view in actions if view.undone),
        objects=group_by_object(actions),
    )
