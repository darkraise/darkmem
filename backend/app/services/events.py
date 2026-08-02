"""The append-only events writer, the journaling convention (T1.07), and the
read API over the durable substrate (T1.08).

Doc 04 §8.1 makes ``events`` the sole audit substrate from day one.
``record_event`` is the one helper every subsystem journals through —
capture, extraction/pipeline outcomes, supersession, auth, and setup all
route the same shape through here (doc 05 §2.3) — so payload conventions
stay uniform and the append-only/partition mechanics live in exactly one
place.

``EVENT_TYPES`` / ``OBJECT_TYPES`` are the closed vocabularies doc 04 §8.1
names, kept here rather than in ``app.taxonomy`` deliberately: that module's
four vocabularies (doc 06 §3) normalise *LLM-emitted* strings, so an unknown
value must be rewritten to a safe fallback (``concept``, ``RELATED_TO``, ...)
or a hallucinated type would land on disk. ``event_type``/``object_type`` are
never LLM output — every call site is a literal string written by this
codebase — so there is nothing to rewrite; an unrecognised value is a
programming error, not untrusted input, and the correct response is a loud
warning (so it surfaces in review/CI logs) rather than a silent substitution
that would quietly misfile the row. That asymmetry is why these vocabularies
live beside their one writer instead of joining taxonomy.py's LLM-facing set
— the same reasoning that already keeps ``TECH_TYPES`` in ``app.services.relations``
beside the graph code that reads it rather than in taxonomy.py.

``list_events``/``calendar_counts``/``object_timeline`` back the doc 12 §7
read API. Each builds its WHERE clause (and the calendar's GROUP BY) so the
project/object/date predicates ride the query Postgres actually executes,
never a post-fetch Python filter — that is what lets the two doc 04 §8.1
indexes carry the read: ``ix_events_object`` for the timeline,
``ix_events_day`` for the calendar. The calendar bucket expression,
``(created_at AT TIME ZONE 'UTC')::date``, must match the index expression
verbatim — a bare ``created_at::date`` is only STABLE (it resolves against
the session ``TimeZone`` GUC), so it neither matches the IMMUTABLE index
expression nor means the same UTC day to every viewer.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Doc 04 §8.1's list is explicitly non-exhaustive ("..."); this is the subset
# named there plus the values T1.07's call sites (capture, extraction,
# supersession, pipeline outcomes) actually emit. Widening it is
# taxonomy-first, same discipline as app.taxonomy: land the value here before
# any emitter ships it.
EVENT_TYPES: list[str] = [
    "created",
    "superseded",
    "deprecated",
    "expired",
    "invalidated",
    "extracted",
    "consolidated",
    "verified",
    "sources_changed",
    "document_filed",
    "repo_registered",
    "repo_synced",
    "repo_indexed",
    "inject",
    "inject_curbed",
    "setup_completed",
    "auth_lockout",
    "repo_hint_rejected",
    "buffer_requeued",
    "buffer_discarded",
    "maintenance_run",
    "human_verdict",
    "pin_decision",
    "undone",
]

OBJECT_TYPES: list[str] = [
    "memory",
    "entity",
    "relation",
    "fact",
    "article",
    "topic",
    "document",
    "repository",
    "system",
]

_EVENT_TYPE_SET = frozenset(EVENT_TYPES)
_OBJECT_TYPE_SET = frozenset(OBJECT_TYPES)

_INSERT = text(
    "INSERT INTO events "
    "(event_type, object_type, object_id, project, actor, api_key_id, source, payload) "
    "VALUES (:event_type, :object_type, CAST(:object_id AS uuid), :project, "
    ":actor, CAST(:api_key_id AS uuid), :source, CAST(:payload AS jsonb))"
)


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    object_type: str,
    object_id: uuid.UUID | None = None,
    project: str | None = None,
    actor: str | None = None,
    api_key_id: uuid.UUID | None = None,
    source: str | None = None,
    payload: dict | None = None,
) -> None:
    """Append one row to the durable events journal.

    Never raises. Journaling is a side-channel to the operation it records —
    a capture, an extraction pass, a supersession flip — so a broken
    partition, a bad payload, or any other journal-side failure must degrade
    loudly (logged here) without failing the caller. The insert runs inside
    its own SAVEPOINT so a real DB-level failure (a constraint violation, a
    missing partition) rolls back only the journal write, leaving the
    caller's own transaction exactly as usable as if this call had never
    happened.
    """
    if event_type not in _EVENT_TYPE_SET:
        logger.warning(
            "events: event_type %r is outside the doc 04 §8.1 closed vocabulary",
            event_type,
        )
    if object_type not in _OBJECT_TYPE_SET:
        logger.warning(
            "events: object_type %r is outside the doc 04 §8.1 closed vocabulary",
            object_type,
        )

    try:
        # asyncpg cannot infer the uuid and jsonb parameter types here, so
        # each is cast explicitly (invariant 10).
        async with session.begin_nested():
            await session.execute(
                _INSERT,
                {
                    "event_type": event_type,
                    "object_type": object_type,
                    "object_id": str(object_id) if object_id else None,
                    "project": project,
                    "actor": actor,
                    "api_key_id": str(api_key_id) if api_key_id else None,
                    "source": source,
                    "payload": json.dumps(payload or {}, default=str),
                },
            )
    except Exception:
        logger.error(
            "events: failed to journal event_type=%r object_type=%r object_id=%s",
            event_type, object_type, object_id,
            exc_info=True,
        )


async def record_maintenance_run(
    session_factory,
    *,
    operation: str,
    outcome: str,
    detail: dict | None = None,
) -> None:
    """Journal one Settings -> Maintenance / Jobs -> cleanup operation run.

    The one writer for the ``maintenance_run`` event type, shared by
    ``job_runners.py``'s cleanup runners and ``reembed.py``'s background
    tasks, so the two call sites can never drift into their own vocabulary
    or payload shape (T1.63 ruling 2). Runs through a fresh, independently
    committed session — mirroring ``auth.py``'s ``_record_audit`` — because
    a background task's own session may already be closed, rolled back, or
    mid-exception by the time the outcome is known.
    """
    try:
        async with session_factory() as session:
            await record_event(
                session,
                event_type="maintenance_run",
                object_type="system",
                payload={"operation": operation, "outcome": outcome, "detail": detail or {}},
            )
            await session.commit()
    except Exception:
        # record_event itself never raises; a failure here is the fresh
        # session/commit machinery around it (a DB blip). Journaling is a
        # side-channel to the operation it records (same rule as
        # record_event's own docstring) — it must never take the operation
        # down with it.
        logger.error(
            "events: failed to journal maintenance_run operation=%r outcome=%r",
            operation, outcome, exc_info=True,
        )


# Months kept ahead of the current one. A RANGE-partitioned parent rejects every
# insert that lands outside a child, so running out of partitions does not
# degrade the journal — it stops it, and takes the write that was being journaled
# with it.
_MONTHS_AHEAD = 1

_ENSURE_PARTITIONS = text(
    "SELECT events_ensure_partition("
    "    (date_trunc('month', now() AT TIME ZONE 'UTC')"
    "     + (make_interval(months => g))::interval)::date) AS child "
    "FROM generate_series(0, :months_ahead) AS g"
)


async def reconcile_event_partitions(session: AsyncSession) -> list[str]:
    """Ensure the current and next monthly `events` children exist, and return
    their names.

    Idempotent, and deliberately not boot-only: a process that boots in January
    and is still running in March would have exhausted the two partitions the
    baseline created, so the same reconcile also runs as an arm on
    ``pipeline_failure_cleanup``. The per-child TRUNCATE guard is attached by
    ``events_ensure_partition`` itself — the parent's truncate trigger does not
    cascade to children, so a partition created without it would be truncatable.
    """
    rows = await session.execute(_ENSURE_PARTITIONS, {"months_ahead": _MONTHS_AHEAD})
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Read API (T1.08, doc 12 §7) — three shapes over the durable substrate.
# `events` is never written through the API (§8.1: forbid-triggers, no
# POST/PUT/DELETE here), so every route this module backs is a GET.
# ---------------------------------------------------------------------------

_EVENT_COLUMNS = (
    "id, created_at, event_type, object_type, object_id, "
    "project, actor, api_key_id, source, payload"
)


async def list_events(
    session: AsyncSession,
    *,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    project: str | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Filtered, paginated event list — newest first.

    Every predicate lands in the SQL WHERE clause (never a post-fetch Python
    filter), so `project` isolation and the other filters ride the same
    query the partition-pruning and `ix_events_object` planner sees.
    """
    where_parts: list[str] = []
    params: dict = {"limit": limit, "offset": offset}
    if object_type:
        where_parts.append("object_type = :object_type")
        params["object_type"] = object_type
    if object_id is not None:
        where_parts.append("object_id = CAST(:object_id AS uuid)")
        params["object_id"] = str(object_id)
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    if event_type:
        where_parts.append("event_type = :event_type")
        params["event_type"] = event_type
    if since is not None:
        where_parts.append("created_at >= :since")
        params["since"] = since
    if until is not None:
        where_parts.append("created_at <= :until")
        params["until"] = until
    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

    items_sql = (
        f"SELECT {_EVENT_COLUMNS} FROM events "
        f"WHERE {where_sql} "
        "ORDER BY created_at DESC, id DESC "
        "LIMIT :limit OFFSET :offset"
    )
    result = await session.execute(text(items_sql), params)
    items = [dict(row) for row in result.mappings().all()]

    count_sql = f"SELECT COUNT(*) FROM events WHERE {where_sql}"
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()

    return items, int(total)


async def calendar_counts(
    session: AsyncSession,
    *,
    project: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict]:
    """Per-UTC-day event counts for the contribution heatmap.

    The GROUP BY expression is `(created_at AT TIME ZONE 'UTC')::date`,
    byte-for-byte the `ix_events_day` index expression — a bare
    `created_at::date` would still group correctly today but would silently
    change which day a row belongs to under a non-UTC session `TimeZone` GUC,
    since that cast is only STABLE (doc 04 §8.1).
    """
    where_parts: list[str] = []
    params: dict = {}
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    if since is not None:
        where_parts.append("created_at >= :since")
        params["since"] = since
    if until is not None:
        where_parts.append("created_at <= :until")
        params["until"] = until
    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

    sql = (
        "SELECT (created_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS count "
        "FROM events "
        f"WHERE {where_sql} "
        "GROUP BY (created_at AT TIME ZONE 'UTC')::date "
        "ORDER BY day"
    )
    result = await session.execute(text(sql), params)
    return [{"day": row["day"], "count": int(row["count"])} for row in result.mappings().all()]


async def object_timeline(
    session: AsyncSession,
    *,
    object_type: str,
    object_id: uuid.UUID,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """One object's full history, oldest-to-newest.

    `object_type = ... AND object_id = ...` are the two leading columns of
    `ix_events_object`, and the ASC order matches the index's own
    `created_at` order exactly, so the planner needs no extra sort.

    Accepted limitation (doc 04 §8.1): bigint-keyed code-graph objects carry
    their key in `payload`, not `object_id`, so their timelines are not
    reachable through this index-backed shape.
    """
    where_parts = ["object_type = :object_type", "object_id = CAST(:object_id AS uuid)"]
    params: dict = {
        "object_type": object_type,
        "object_id": str(object_id),
        "limit": limit,
        "offset": offset,
    }
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    where_sql = " AND ".join(where_parts)

    items_sql = (
        f"SELECT {_EVENT_COLUMNS} FROM events "
        f"WHERE {where_sql} "
        "ORDER BY created_at ASC, id ASC "
        "LIMIT :limit OFFSET :offset"
    )
    result = await session.execute(text(items_sql), params)
    items = [dict(row) for row in result.mappings().all()]

    count_sql = f"SELECT COUNT(*) FROM events WHERE {where_sql}"
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()

    return items, int(total)
