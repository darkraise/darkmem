"""The work-log lane: workstreams and their append-only entries.

A coding client's operational state — checkpoints it summarised itself, ledger
chunks, notes to its next session — kept apart from memories so none of it
reaches extraction, memory retrieval or the fact vault
(docs/superpowers/specs/2026-09-23-work-log-lane-design.md §7). Both doors call
this module and hold no logic of their own (invariant 17).

Nothing here commits: the caller owns the transaction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worklog import WorklogEntry, Workstream
from app.services import project_registry
from app.services.events import record_event

__all__ = [
    "AppendResult",
    "DOOR_SOURCE",
    "KINDS",
    "MAX_BODY_CHARS",
    "MAX_ENTRIES_PER_APPEND",
    "MAX_PROPERTIES_BYTES",
    "RESUME_LEDGER_TAIL",
    "RESUME_NOTES_CAP",
    "WorklogJournalWriteFailed",
    "WorklogRejected",
    "WorkstreamNotFound",
    "append",
    "get_workstream",
    "get_workstream_by_id",
    "properties_size",
    "purge_workstream",
    "serialize_entry",
    "serialize_workstream",
    "update_workstream",
]

KINDS = ("checkpoint", "ledger", "note")
MAX_BODY_CHARS = 65_536
# The database bounds properties with pg_column_size(...) <= 16384; the door
# measures encoded JSON text, which is not jsonb's size, so it sits below the
# CHECK. The CHECK stays the guarantee: a merge or a numeric-heavy value that
# still exceeds it surfaces as WorklogRejected, never as a 500.
MAX_PROPERTIES_BYTES = 12_288
MAX_ENTRIES_PER_APPEND = 100
RESUME_LEDGER_TAIL = 20
RESUME_NOTES_CAP = 50
DOOR_SOURCE = "worklog"


class WorkstreamNotFound(LookupError):
    """No workstream under that id or (project, key)."""


class WorklogRejected(ValueError):
    """The database's CHECKs refused the write; nothing of it was kept."""


class WorklogJournalWriteFailed(RuntimeError):
    """The purge journal row is not there, so nothing was deleted.

    Local rather than the vault's `JournalWriteFailed`: this lane stays off
    the vault's modules (spec §7).
    """


@dataclass(frozen=True)
class AppendResult:
    workstream: Workstream
    entry_ids: list[UUID]


def properties_size(value: dict) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


_SELECT_LOCKED = text(
    "SELECT id, state FROM workstreams "
    "WHERE project = CAST(:project AS text) AND key = CAST(:key AS text) FOR UPDATE"
)
_REOPEN = text(
    """
    UPDATE workstreams SET
        state = 'open',
        closed_at = NULL,
        last_entry_at = now(),
        title = COALESCE(CAST(:title AS text), title),
        client = COALESCE(CAST(:client AS text), client),
        properties = properties || CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
    """
)
_INSERT_IF_ABSENT = text(
    """
    INSERT INTO workstreams (id, project, key, title, client, properties)
    VALUES (CAST(:id AS uuid), CAST(:project AS text), CAST(:key AS text),
            CAST(:title AS text), CAST(:client AS text), CAST(:properties AS jsonb))
    ON CONFLICT ON CONSTRAINT ux_workstreams_project_key DO NOTHING
    RETURNING id
    """
)
# Rows journaled inside this transaction carry created_at = now(), so the
# predicate reads back exactly this purge's row and prunes to one partition.
_PURGE_JOURNALED = text(
    """
    SELECT count(*) FROM events
    WHERE event_type = 'workstream_purged' AND object_type = 'workstream'
      AND object_id = CAST(:id AS uuid) AND created_at >= now()
    """
)


async def _lock_or_create(
    session: AsyncSession,
    *,
    project: str,
    key: str,
    title: str | None,
    client: str | None,
    properties: dict | None,
) -> tuple[UUID, str]:
    """The workstream under its row lock, and whether it was opened, reopened or continued.

    Lock first, then decide: the transition is read from the row as locked, so
    a concurrent close is seen rather than raced. The lock is what serialises
    an append against a purge or a retention delete of the same workstream —
    whichever commits second sees the first's result, so no entry lands in a
    deleted parent. An insert that loses a creation race does nothing, and the
    second pass locks the winner's row.
    """
    params = {
        "project": project,
        "key": key,
        "title": title,
        "client": client,
        "properties": json.dumps(properties or {}),
    }
    for _ in range(2):
        found = (await session.execute(_SELECT_LOCKED, params)).mappings().one_or_none()
        if found is not None:
            await session.execute(_REOPEN, {**params, "id": str(found["id"])})
            return found["id"], "reopened" if found["state"] == "closed" else "continued"
        created = (await session.execute(
            _INSERT_IF_ABSENT, {**params, "id": str(uuid4())}
        )).scalar_one_or_none()
        if created is not None:
            return created, "opened"
    raise RuntimeError(f"workstream {project}/{key} could be neither locked nor created")


async def append(
    session: AsyncSession,
    *,
    project: str,
    key: str,
    run_key: str,
    entries: list[dict[str, Any]],
    title: str | None = None,
    client: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> AppendResult:
    """Append 1-100 entries to a workstream, creating or reopening it."""
    if not 1 <= len(entries) <= MAX_ENTRIES_PER_APPEND:
        raise ValueError(
            f"an append carries 1 to {MAX_ENTRIES_PER_APPEND} entries, not {len(entries)}"
        )
    entry_ids = [uuid4() for _ in entries]
    try:
        async with session.begin_nested():
            workstream_id, transition = await _lock_or_create(
                session, project=project, key=key, title=title, client=client,
                properties=properties,
            )
            # One multi-row statement, not executemany: the identity column
            # hands out `seq` in VALUES order, which keeps a ledger in order.
            await session.execute(
                insert(WorklogEntry).values([
                    {
                        "id": entry_id,
                        "workstream_id": workstream_id,
                        "run_key": run_key,
                        "kind": entry["kind"],
                        "body": entry["body"],
                        "properties": entry.get("properties") or {},
                    }
                    for entry_id, entry in zip(entry_ids, entries)
                ])
            )
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
    await project_registry.register(session, project)

    if transition == "opened":
        await record_event(
            session, event_type="workstream_opened", object_type="workstream",
            object_id=workstream_id, project=project, actor=actor,
            api_key_id=api_key_id, payload={"key": key},
        )
    elif transition == "reopened":
        await record_event(
            session, event_type="workstream_reopened", object_type="workstream",
            object_id=workstream_id, project=project, actor=actor,
            api_key_id=api_key_id, payload={"key": key},
        )

    workstream = await session.get(Workstream, workstream_id, populate_existing=True)
    return AppendResult(workstream=workstream, entry_ids=entry_ids)


async def get_workstream(
    session: AsyncSession, *, project: str, key: str, for_update: bool = False
) -> Workstream | None:
    statement = select(Workstream).where(Workstream.project == project, Workstream.key == key)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def get_workstream_by_id(
    session: AsyncSession, workstream_id: UUID, *, for_update: bool = False
) -> Workstream | None:
    statement = select(Workstream).where(Workstream.id == workstream_id)
    if for_update:
        # Without populate_existing an instance already in the identity map
        # keeps its pre-lock attributes, and every decision below would be
        # made on state another transaction has since changed.
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def update_workstream(
    session: AsyncSession,
    workstream_id: UUID,
    *,
    state: str | None = None,
    retain: bool | None = None,
    title: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> Workstream:
    """Move state, retain, title; merge properties. Journals close and reopen."""
    if state is not None and state not in ("open", "closed"):
        raise ValueError(f"state must be 'open' or 'closed', not {state!r}")
    workstream = await get_workstream_by_id(session, workstream_id, for_update=True)
    if workstream is None:
        raise WorkstreamNotFound(str(workstream_id))
    transition = state if state is not None and state != workstream.state else None
    try:
        # The changes are made inside the savepoint on purpose: begin_nested()
        # flushes pending state before it emits SAVEPOINT, so an attribute set
        # above it would hit the CHECK outside the savepoint and abort the
        # caller's whole transaction.
        async with session.begin_nested():
            if transition is not None:
                workstream.state = state
                workstream.closed_at = func.now() if state == "closed" else None
            if retain is not None:
                workstream.retain = retain
            if title is not None:
                workstream.title = title
            if properties:
                workstream.properties = {**(workstream.properties or {}), **properties}
            await session.flush()
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
    if transition == "closed":
        await record_event(
            session, event_type="workstream_closed", object_type="workstream",
            object_id=workstream.id, project=workstream.project, actor=actor,
            api_key_id=api_key_id, payload={"key": workstream.key},
        )
    elif transition == "open":
        await record_event(
            session, event_type="workstream_reopened", object_type="workstream",
            object_id=workstream.id, project=workstream.project, actor=actor,
            api_key_id=api_key_id, payload={"key": workstream.key},
        )
    await session.refresh(workstream)
    return workstream


async def purge_workstream(
    session: AsyncSession,
    workstream_id: UUID,
    *,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> int:
    """Erase a workstream with its entries. Journals first and reads it back, or refuses.

    A purge is irrecoverable and, over MCP, the event's api_key_id is the only
    record of who ran it; failing closed costs a retry where failing open
    loses the audit for good.
    """
    workstream = await get_workstream_by_id(session, workstream_id, for_update=True)
    if workstream is None:
        raise WorkstreamNotFound(str(workstream_id))
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == workstream.id)
    )).scalar_one()
    landed = await record_event(
        session, event_type="workstream_purged", object_type="workstream",
        object_id=workstream.id, project=workstream.project, actor=actor,
        api_key_id=api_key_id, payload={"key": workstream.key, "entries": count},
    )
    journaled = (await session.execute(
        _PURGE_JOURNALED, {"id": str(workstream.id)}
    )).scalar_one()
    if not landed or journaled == 0:
        raise WorklogJournalWriteFailed(
            f"workstream_purged is not journaled for workstream {workstream.id}; "
            "refusing to delete unaudited"
        )
    await session.execute(delete(Workstream).where(Workstream.id == workstream.id))
    session.expunge(workstream)
    return count


def serialize_workstream(workstream: Workstream) -> dict[str, Any]:
    return {
        "id": str(workstream.id),
        "project": workstream.project,
        "key": workstream.key,
        "title": workstream.title,
        "client": workstream.client,
        "state": workstream.state,
        "closed_at": workstream.closed_at.isoformat() if workstream.closed_at else None,
        "retain": workstream.retain,
        "properties": workstream.properties or {},
        "last_entry_at": workstream.last_entry_at.isoformat(),
        "created_at": workstream.created_at.isoformat(),
        "updated_at": workstream.updated_at.isoformat(),
    }


def serialize_entry(entry: WorklogEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "workstream_id": str(entry.workstream_id),
        "seq": entry.seq,
        "run_key": entry.run_key,
        "kind": entry.kind,
        "body": entry.body,
        "properties": entry.properties or {},
        "created_at": entry.created_at.isoformat(),
    }
