"""The append-only events writer.

Doc 04 §8.1 makes ``events`` the sole audit substrate from day one; this is
the narrow writer T0.12c needs to keep the security audit trail alive after
``audit_log`` is dropped. T1.07 owns the general journaling convention and
the rest of the event vocabulary.
"""
from __future__ import annotations

import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    # asyncpg cannot infer the uuid and jsonb parameter types here, so each is
    # cast explicitly (invariant 10).
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
            "payload": json.dumps(payload or {}),
        },
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
