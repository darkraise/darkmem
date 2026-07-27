"""The append-only events writer and the journaling convention (T1.07).

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
"""
from __future__ import annotations

import json
import logging
import uuid

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
