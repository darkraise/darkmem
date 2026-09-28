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
import logging
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp.client_identity import UNKNOWN_ORIGIN_PREFIX, resolve_origin_key
from app.config import settings
from app.models.worklog import WorklogEntry, Workstream
from app.services import project_registry
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.rank_fusion import RankedList, fusion_fetch_depth, rrf_fuse
from app.services.worklog_embeddings import PARENT_TABLE as EMBEDDING_PARENT

logger = logging.getLogger(__name__)

__all__ = [
    "AppendResult",
    "DOOR_SOURCE",
    "KINDS",
    "MAX_BODY_CHARS",
    "MAX_ENTRIES_PER_APPEND",
    "MAX_PROPERTIES_BYTES",
    "MAX_QUERY_CHARS",
    "MAX_SEARCH_LIMIT",
    "RESUME_LEDGER_TAIL",
    "RESUME_NOTES_CAP",
    "SEARCH_ARMS",
    "SEARCH_DEFAULT_LIMIT",
    "UndeclaredRun",
    "WorklogJournalWriteFailed",
    "WorklogRejected",
    "WorklogSeqConflict",
    "WorkstreamNotFound",
    "append",
    "expire_next",
    "get_workstream",
    "get_workstream_by_id",
    "list_entries",
    "list_workstreams",
    "properties_size",
    "purge_workstream",
    "resolve_run_key",
    "resume",
    "search",
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
SEARCH_ARMS = ("keyword", "semantic")
SEARCH_DEFAULT_LIMIT = 20
MAX_SEARCH_LIMIT = 100
MAX_QUERY_CHARS = 2_000


class UndeclaredRun(ValueError):
    """An append arrived with no declared agent-run identity."""


def resolve_run_key(declared, *, source: str, project: str) -> str:
    """The run's key by doc 05 §2.1's derivation, or a refusal.

    The derivation is capture's own `resolve_origin_key`, so the sanitising,
    the length bound and the prefix have one owner. Its fallback is not
    inherited: capture merges an undeclared origin into one
    `unknown:<source>:<project>` bucket, which is safe for a key that counts
    corroboration and wrong for one that looks work up, because two runs
    sharing it would each resume the other's work as their own.
    """
    if not isinstance(declared, str) or not declared.strip():
        raise UndeclaredRun(
            "a work-log entry needs a declared agent-run identity: send "
            "`run_key`, or the X-Darkmem-Origin header the client mints at "
            "process boot. Undeclared runs are refused rather than merged into "
            "one bucket the way undeclared captures are: two runs sharing a key "
            "would each resume the other's work as their own."
        )
    resolved = resolve_origin_key(declared, None, source=source, project=project)
    # Unreachable while `declared` is non-empty, but asserted rather than
    # assumed: the failure it guards is silent.
    if resolved.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:"):
        raise UndeclaredRun(
            f"origin resolution produced the merge-to-one bucket {resolved!r}; "
            "refusing to file work under a key every unattributed run shares"
        )
    # `_sanitize_origin` drops separators and unprintables, so ":::" or a lone
    # zero-width space reduces to the bare "<source>:", one key every such run
    # would share.
    if resolved == f"{source}:":
        raise UndeclaredRun(
            f"the declared agent-run identity {declared!r} contains nothing that "
            f"survives sanitisation, so it resolves to the bare {resolved!r}. "
            "Send an identity with at least one printable, non-separator character."
        )
    return resolved


class WorkstreamNotFound(LookupError):
    """No workstream under that id or (project, key)."""


class WorklogRejected(ValueError):
    """The database's CHECKs refused the write; nothing of it was kept."""


class WorklogSeqConflict(Exception):
    """expected_last_seq did not name the newest entry of its kind; nothing was kept."""

    def __init__(self, kind: str, expected: int, current: int) -> None:
        super().__init__(
            f"expected the newest {kind} entry to be seq {expected}, but it is {current}"
        )
        self.kind = kind
        self.expected = expected
        self.current = current


class WorklogJournalWriteFailed(RuntimeError):
    """The purge journal row is not there, so nothing was deleted.

    Local rather than the vault's `JournalWriteFailed`: this lane stays off
    the vault's modules (spec §7).
    """


@dataclass(frozen=True)
class AppendResult:
    workstream: Workstream
    entry_ids: list[UUID]
    last_seq: int


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
# predicate reads back exactly this purge's row and prunes to the current
# month's partition and any later ones.
_PURGE_JOURNALED = text(
    """
    SELECT count(*) FROM events
    WHERE event_type = 'workstream_purged' AND object_type = 'workstream'
      AND object_id = CAST(:id AS uuid) AND created_at >= now()
    """
)
# SKIP LOCKED: a workstream an append holds is being reopened, so the sweep
# passes it by rather than queueing behind the append and deleting nothing.
_NEXT_EXPIRED = text(
    """
    SELECT id FROM workstreams
    WHERE state = 'closed' AND NOT retain
      AND closed_at < now() - make_interval(days => CAST(:days AS integer))
    ORDER BY closed_at, id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
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
    a concurrent close is seen rather than raced. The lock is what keeps an
    entry out of a deleted parent: an append behind a purge or a retention
    sweep waits for its commit and then recreates the workstream, a purge
    behind an append waits for it, and the sweep skips a row an append holds
    (FOR UPDATE SKIP LOCKED). An insert that loses a creation race does
    nothing, and the second pass locks the winner's row.
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
    expected_last_seq: int | None = None,
) -> AppendResult:
    """Append 1-100 entries to a workstream, creating or reopening it; optionally a compare-and-set."""
    if not 1 <= len(entries) <= MAX_ENTRIES_PER_APPEND:
        raise ValueError(
            f"an append carries 1 to {MAX_ENTRIES_PER_APPEND} entries, not {len(entries)}"
        )
    kinds = {entry["kind"] for entry in entries}
    if expected_last_seq is not None and len(kinds) != 1:
        raise ValueError("expected_last_seq needs every entry of the append to share one kind")
    entry_ids = [uuid4() for _ in entries]
    try:
        async with session.begin_nested():
            workstream_id, transition = await _lock_or_create(
                session, project=project, key=key, title=title, client=client,
                properties=properties,
            )
            # Checked under the row lock and inside the savepoint: a mismatch
            # unwinds the creation or reopen above along with everything else.
            if expected_last_seq is not None:
                (kind,) = kinds
                current = (await session.execute(
                    select(func.coalesce(func.max(WorklogEntry.seq), 0)).where(
                        WorklogEntry.workstream_id == workstream_id,
                        WorklogEntry.kind == kind,
                    )
                )).scalar_one()
                if current != expected_last_seq:
                    raise WorklogSeqConflict(kind, expected_last_seq, current)
            # One multi-row statement, not executemany: the identity column
            # hands out `seq` in VALUES order, which keeps a ledger in order.
            seqs = (await session.execute(
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
                ]).returning(WorklogEntry.seq)
            )).scalars().all()
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
    return AppendResult(workstream=workstream, entry_ids=entry_ids, last_seq=max(seqs))


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


async def _journal_then_delete(
    session: AsyncSession,
    workstream: Workstream,
    *,
    actor: str | None,
    api_key_id: UUID | None,
    extra: dict[str, Any] | None = None,
) -> int:
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == workstream.id)
    )).scalar_one()
    landed = await record_event(
        session, event_type="workstream_purged", object_type="workstream",
        object_id=workstream.id, project=workstream.project, actor=actor,
        api_key_id=api_key_id,
        payload={"key": workstream.key, "entries": count, **(extra or {})},
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
    return await _journal_then_delete(session, workstream, actor=actor, api_key_id=api_key_id)


async def expire_next(
    session: AsyncSession, *, retention_days: int, actor: str | None = None
) -> int | None:
    """Erase the longest-closed workstream past retention; None when none is eligible.

    Open and retained workstreams are never eligible, however old (spec §6).
    The erase keeps the purge verb's journal-first contract, and the caller
    commits one workstream at a time.
    """
    found = (await session.execute(
        _NEXT_EXPIRED, {"days": retention_days}
    )).scalar_one_or_none()
    if found is None:
        return None
    workstream = await get_workstream_by_id(session, found, for_update=True)
    # _NEXT_EXPIRED already holds this row's lock, so it cannot have gone.
    assert workstream is not None
    return await _journal_then_delete(
        session, workstream, actor=actor, api_key_id=None,
        extra={"retention_days": retention_days},
    )


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


def _cursor(workstream: Workstream) -> str:
    return f"{workstream.created_at.isoformat()}|{workstream.id}"


def _parse_cursor(value: str) -> tuple[datetime, UUID]:
    stamp, _, ident = value.partition("|")
    try:
        return datetime.fromisoformat(stamp), UUID(ident)
    except ValueError as error:
        raise ValueError(f"not a workstream cursor: {value!r}") from error


_ENTRY_FIELDS = ("id", "workstream_id", "seq", "run_key", "kind", "body", "properties", "created_at")
_ENTRY_COLUMNS = ", ".join(_ENTRY_FIELDS)
# One statement on purpose: under READ COMMITTED every statement takes its own
# snapshot, so reading the workstream and its entries separately could pair one
# append's properties with another's checkpoint. Neither SET TRANSACTION (the
# REST session has already queried during auth) nor FOR SHARE (refused to the
# read-only worker's SELECT-only role) is available to widen the snapshot.
_RESUME = text(
    f"""
    SELECT w.id, w.project, w.key, w.title, w.client, w.state, w.closed_at,
           w.retain, w.properties, w.last_entry_at, w.created_at, w.updated_at,
           e.id AS e_id, e.workstream_id AS e_workstream_id, e.seq AS e_seq,
           e.run_key AS e_run_key, e.kind AS e_kind, e.body AS e_body,
           e.properties AS e_properties, e.created_at AS e_created_at
    FROM workstreams w
    LEFT JOIN LATERAL (
        (SELECT {_ENTRY_COLUMNS} FROM worklog_entries
         WHERE workstream_id = w.id AND kind = 'checkpoint'
         ORDER BY seq DESC LIMIT 1)
        UNION ALL
        (SELECT {_ENTRY_COLUMNS} FROM worklog_entries
         WHERE workstream_id = w.id AND kind = 'note'
         ORDER BY seq DESC LIMIT CAST(:notes_limit AS integer))
        UNION ALL
        (SELECT {_ENTRY_COLUMNS} FROM worklog_entries
         WHERE workstream_id = w.id AND kind = 'ledger'
         ORDER BY seq DESC LIMIT CAST(:ledger_limit AS integer))
    ) e ON true
    WHERE w.project = CAST(:project AS text) AND w.key = CAST(:key AS text)
    """
)


def _entry_from_row(row: Any) -> SimpleNamespace:
    return SimpleNamespace(**{
        name: getattr(row, f"e_{name}")
        for name in _ENTRY_FIELDS
    })


async def resume(session: AsyncSession, *, project: str, key: str) -> dict[str, Any] | None:
    """What a new session loads: the latest checkpoint, notes, the ledger tail."""
    rows = (await session.execute(_RESUME, {
        "project": project,
        "key": key,
        "notes_limit": RESUME_NOTES_CAP + 1,
        "ledger_limit": RESUME_LEDGER_TAIL,
    })).all()
    if not rows:
        return None
    # UNION ALL promises no order across its branches, so order here.
    entries = sorted(
        (_entry_from_row(row) for row in rows if row.e_id is not None),
        key=lambda entry: entry.seq,
    )
    checkpoints = [e for e in entries if e.kind == "checkpoint"]
    notes = [e for e in entries if e.kind == "note"]
    ledger = [e for e in entries if e.kind == "ledger"]
    return {
        "workstream": serialize_workstream(rows[0]),
        "checkpoint": serialize_entry(checkpoints[-1]) if checkpoints else None,
        "notes": [serialize_entry(n) for n in notes[-RESUME_NOTES_CAP:]],
        "notes_truncated": len(notes) > RESUME_NOTES_CAP,
        "ledger": [serialize_entry(e) for e in ledger],
    }


async def list_workstreams(
    session: AsyncSession,
    *,
    project: str,
    state: str | None = None,
    before: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Newest-created first, keyset-paged on the immutable (created_at, id).

    Not last_entry_at: an append moves that, and a page boundary on a moving
    key skips or repeats workstreams between pages.
    """
    if state is not None and state not in ("open", "closed"):
        raise ValueError(f"state must be 'open' or 'closed', not {state!r}")
    conditions = [Workstream.project == project]
    if state is not None:
        conditions.append(Workstream.state == state)
    if before is not None:
        stamp, ident = _parse_cursor(before)
        conditions.append(or_(
            Workstream.created_at < stamp,
            and_(Workstream.created_at == stamp, Workstream.id < ident),
        ))
    rows = (await session.execute(
        select(Workstream)
        .where(*conditions)
        .order_by(Workstream.created_at.desc(), Workstream.id.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_workstream(w) for w in rows],
        "next_before": _cursor(rows[-1]) if len(rows) == limit else None,
    }


async def list_entries(
    session: AsyncSession,
    *,
    workstream_id: UUID,
    kind: str | None = None,
    since: datetime | None = None,
    after: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Entries oldest first, paged forward on `seq`; `since` keeps created_at >= since."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    conditions = [WorklogEntry.workstream_id == workstream_id]
    if kind is not None:
        conditions.append(WorklogEntry.kind == kind)
    if since is not None:
        conditions.append(WorklogEntry.created_at >= since)
    if after is not None:
        conditions.append(WorklogEntry.seq > after)
    rows = (await session.execute(
        select(WorklogEntry).where(*conditions).order_by(WorklogEntry.seq).limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_entry(e) for e in rows],
        "next_after": rows[-1].seq if len(rows) == limit else None,
    }


_HIT_COLUMNS = ", ".join([*(f"e.{name}" for name in _ENTRY_FIELDS), "w.key AS workstream_key"])
_KEYWORD_SEARCH = """
    SELECT {columns}
    FROM worklog_entries e
    JOIN workstreams w ON w.id = e.workstream_id
    CROSS JOIN plainto_tsquery('english', CAST(:query AS text)) q
    WHERE w.project = CAST(:project AS text) AND e.search_vector @@ q{filters}
    ORDER BY ts_rank(e.search_vector, q) DESC, e.seq DESC
    LIMIT CAST(:depth AS integer)
"""
# Exact cosine distance over one project's vectors, reached through the
# project btree index: the family has no HNSW index
# (embedder_registry._EXACT_SCAN_PARENTS).
_SEMANTIC_SEARCH = """
    SELECT {columns}
    FROM {table} v
    JOIN worklog_entries e ON e.id = v.entry_id
    JOIN workstreams w ON w.id = e.workstream_id
    WHERE v.project = CAST(:project AS text)
      AND w.project = CAST(:project AS text)
      AND v.fingerprint = CAST(:fp AS text){filters}
    ORDER BY v.embedding <=> CAST(:vec AS vector), e.seq DESC
    LIMIT CAST(:depth AS integer)
"""


async def search(
    session: AsyncSession,
    llm,
    *,
    project: str,
    query: str,
    workstream: str | None = None,
    kind: str | None = None,
    limit: int = SEARCH_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """One project's entries matching `query` by words, by meaning or both, fused by RRF.

    The keyword arm ranks the whole body; the semantic arm ranks the vectors
    of each body's first worklog_embeddings.EMBED_CHARS characters. It is
    skipped, with semantic_ran false, when there is no orchestrator, the
    instance is read-only (a backup worker makes no external call) or the
    query embed fails, and the keyword arm answers alone. Each hit names the arms that found it.
    """
    if not query.strip():
        raise ValueError("query must contain a non-space character")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query is longer than {MAX_QUERY_CHARS} characters")
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    if not 1 <= limit <= MAX_SEARCH_LIMIT:
        raise ValueError(f"limit must be 1 to {MAX_SEARCH_LIMIT}, not {limit}")

    scope: dict[str, Any] = {"project": project, "depth": fusion_fetch_depth(limit)}
    filters = ""
    if workstream is not None:
        filters += " AND w.key = CAST(:workstream AS text)"
        scope["workstream"] = workstream
    if kind is not None:
        filters += " AND e.kind = CAST(:kind AS text)"
        scope["kind"] = kind

    # Embed before the first query, so a session nothing has used yet holds
    # no connection, idle in a transaction, while the embedder answers.
    embedded = None
    if llm is not None and not settings.read_only:
        try:
            embedded = await llm.embed(query)
        except Exception as error:  # noqa: BLE001 - the keyword arm still answers
            logger.warning("worklog.search: the query embed failed; keyword arm only: %s", error)

    keyword = (await session.execute(
        text(_KEYWORD_SEARCH.format(columns=_HIT_COLUMNS, filters=filters)),
        {**scope, "query": query},
    )).mappings().all()

    semantic: list = []
    semantic_ran = embedded is not None
    if embedded is not None:
        vector, fingerprint = embedded
        table = child_table(EMBEDDING_PARENT, fingerprint)
        # No child table means nothing is embedded under this fingerprint
        # yet: an empty arm, not a fault.
        exists = (await session.execute(
            text("SELECT to_regclass(:name)"), {"name": table},
        )).scalar_one_or_none()
        if exists is not None:
            semantic = (await session.execute(
                text(_SEMANTIC_SEARCH.format(columns=_HIT_COLUMNS, table=table, filters=filters)),
                {**scope, "vec": str(list(vector)), "fp": fingerprint},
            )).mappings().all()

    rows = {str(row["id"]): row for row in (*keyword, *semantic)}
    found_by = {
        "keyword": {str(row["id"]) for row in keyword},
        "semantic": {str(row["id"]) for row in semantic},
    }
    fused = rrf_fuse(
        [
            RankedList("keyword", [{"id": str(row["id"])} for row in keyword], 1.0),
            RankedList("semantic", [{"id": str(row["id"])} for row in semantic], 1.0),
        ],
        limit,
    )
    items = []
    for hit in fused:
        row = rows[hit["id"]]
        items.append({
            "entry": serialize_entry(SimpleNamespace(**{name: row[name] for name in _ENTRY_FIELDS})),
            "workstream": row["workstream_key"],
            "rrf_score": hit["rrf_score"],
            "arms": [arm for arm in SEARCH_ARMS if hit["id"] in found_by[arm]],
        })
    return {"items": items, "semantic_ran": semantic_ran}
