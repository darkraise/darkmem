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
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    before: dict
    after: dict
    detail: dict
    undone: bool = False
    undone_at: datetime | None = None
    undone_by: str | None = None
    undo_batch_id: str | None = None
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
           ) AS projects
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
            },
        )

    views: list[DreamActionView] = []
    for row in rows:
        payload = row["payload"] or {}
        undo = undone_by_action.get(str(row["event_id"]))
        views.append(
            DreamActionView(
                event_id=int(row["event_id"]),
                created_at=row["created_at"],
                action=str(payload.get("action") or ""),
                object_id=row["object_id"],
                project=row["project"],
                detector=payload.get("detector"),
                before=payload.get("before") or {},
                after=payload.get("after") or {},
                detail=action_detail(payload),
                undone=undo is not None,
                undone_at=undo["at"] if undo else None,
                undone_by=undo["by"] if undo else None,
                undo_batch_id=undo["batch"] if undo else None,
            )
        )
    return views


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
