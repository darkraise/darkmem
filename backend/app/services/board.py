"""The progress board: a projection of registers, plans and ledgers (spec 2026-10-13).

Nothing is stored. Every read derives the records from `documents.content` and
`worklog_entries`, so a board can never disagree with the files it shows. It
reads `documents`, never `blocks`, and imports neither the memory pipeline nor
any vault module (§2.1; `tests/test_board_service.py` holds the memberships).
Register edits live in `board_edit`, outside the work-log wall, because they
file through `document_door`.
"""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import (
    LEDGER_STATES,
    PLAN_PREFIX,
    REGISTER_PREFIX,
    REGISTER_STATES,
    cell_uri,
    is_blank_note,
    parse_plan,
    parse_register,
)

# `document_door.BLOCK_FIRST`, restated: importing the door would carry its
# memory-model imports inside the work-log wall (`tests/test_worklog_wall.py`).
# `tests/test_board_service.py` asserts the two stay equal.
BLOCK_FIRST = "blocks"
# Bumped when the records' shape changes, so a browser holding an old ETag
# refetches after a deploy instead of revalidating into the old shape.
BOARD_FORMAT = "1"

# A ledger line past the body limit arrives as consecutive pieces; this bounds
# how far back a blocked reason looks for them (16 x 65,536 characters).
MAX_REASON_PIECES = 16

_CORPUS_WHERE = (
    "project = CAST(:project AS text) "
    "AND (starts_with(uri, CAST(:registers AS text)) OR starts_with(uri, CAST(:plans AS text))) "
    "AND right(uri, 3) = '.md'"
)

_CORPUS = text(
    "SELECT CAST(id AS text) AS id, uri, title, content, content_hash, "
    "       properties->>'ingest_direction' AS direction "
    f"FROM documents WHERE {_CORPUS_WHERE} ORDER BY uri"
)

_WORKSTREAMS = text(
    "SELECT CAST(id AS text) AS id, key, state, last_entry_at, "
    "       properties->>'plan_uri' AS plan_uri, properties->>'spec_uri' AS spec_uri "
    "FROM workstreams "
    "WHERE project = CAST(:project AS text) AND properties->>'plan_uri' IS NOT NULL"
)

# An integer `task` or NULL. Nested CASEs, because only a CASE orders
# evaluation: the cast must never run on a string such as "3a".
_TASK = (
    "CASE WHEN jsonb_typeof(e.properties->'task') = 'number' THEN "
    "CASE WHEN CAST(e.properties->>'task' AS numeric) "
    "        = floor(CAST(e.properties->>'task' AS numeric)) "
    "THEN CAST(e.properties->>'task' AS numeric) END END"
)

_STATES = text(
    f"""
    WITH t AS (
        SELECT e.workstream_id, e.seq, e.body, e.properties, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[]))
          AND e.kind = 'ledger'
          AND e.properties->>'state' IS NOT NULL
    )
    SELECT DISTINCT ON (workstream_id, task)
           CAST(workstream_id AS text) AS workstream_id, task, seq, body, properties
    FROM t WHERE task IS NOT NULL
    ORDER BY workstream_id, task, seq DESC
    """
)

_ACTIVITY = text(
    f"""
    WITH t AS (
        SELECT e.workstream_id, e.seq, e.created_at,
               e.properties->>'commit' AS commit, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[]))
    )
    SELECT CAST(workstream_id AS text) AS workstream_id, task,
           (array_agg(created_at ORDER BY seq DESC))[1] AS last_activity,
           (array_agg(commit ORDER BY seq DESC) FILTER (WHERE commit IS NOT NULL))[1] AS commit
    FROM t WHERE task IS NOT NULL
    GROUP BY workstream_id, task
    """
)

_LEDGER_TASKS = text(
    f"""
    SELECT DISTINCT CAST(workstream_id AS text) AS workstream_id, task
    FROM (
        SELECT e.workstream_id, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[])) AND e.kind = 'ledger'
    ) t
    WHERE task IS NOT NULL
    """
)

_PRECEDING = text(
    "SELECT body, properties FROM worklog_entries "
    "WHERE workstream_id = CAST(:workstream_id AS uuid) AND kind = 'ledger' "
    "AND seq < :seq ORDER BY seq DESC LIMIT :limit"
)

_VERSION_DOCUMENTS = text(
    "SELECT count(*) AS n, max(updated_at) AS at, "
    "       md5(string_agg(coalesce(content_hash, ''), ',' ORDER BY id)) AS hashes "
    f"FROM documents WHERE {_CORPUS_WHERE}"
)

_VERSION_LOG = text(
    "SELECT (SELECT count(*) FROM workstreams WHERE project = CAST(:project AS text)) AS n, "
    "       (SELECT max(updated_at) FROM workstreams WHERE project = CAST(:project AS text)) AS at, "
    "       (SELECT max(e.seq) FROM worklog_entries e JOIN workstreams w ON w.id = e.workstream_id "
    "        WHERE w.project = CAST(:project AS text)) AS seq"
)


def _corpus_params(project: str) -> dict[str, str]:
    return {"project": project, "registers": REGISTER_PREFIX, "plans": PLAN_PREFIX}


async def board_version(session: AsyncSession, project: str) -> str:
    """A fingerprint of everything the board reads, from aggregates only.

    It never reads `content`: a 304 must cost two index-backed aggregates,
    not the parse it saves.
    """
    documents = (await session.execute(_VERSION_DOCUMENTS, _corpus_params(project))).one()
    log = (await session.execute(_VERSION_LOG, {"project": project})).one()
    material = repr((BOARD_FORMAT, tuple(documents), tuple(log)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _choose(candidates: list[Any]) -> Any | None:
    """Open over closed, then the newest `last_entry_at`, then the larger id."""
    if not candidates:
        return None
    return max(candidates, key=lambda w: (w.state == "open", w.last_entry_at, w.id))


async def _blocked_reason(session: AsyncSession, workstream_id: str, entry: Any) -> str:
    """The blocking entry's body, preceded by the earlier pieces of its line."""
    pieces = [entry.body]
    rows = await session.execute(
        _PRECEDING,
        {"workstream_id": workstream_id, "seq": entry.seq, "limit": MAX_REASON_PIECES},
    )
    for row in rows:
        if row.properties != entry.properties or row.body.endswith("\n"):
            break
        pieces.insert(0, row.body)
    return "".join(pieces)


def _register_record(document: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "document_id": document.id,
        "uri": document.uri,
        "title": document.title,
        "covers": None,
        "content_hash": document.content_hash,
        "block_first": document.direction == BLOCK_FIRST,
        "rows": [],
        "malformed": [],
        "error": None,
    }
    if document.content is None:
        record["error"] = "this register has no stored text to read"
        return record
    try:
        parsed = parse_register(document.content)
    except Exception as exc:  # one source's failure must not blank the board (§5)
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["title"] = parsed.title or document.title
    record["covers"] = parsed.covers
    record["rows"] = [
        {
            "number": row.number,
            "item": row.item,
            "assigned": row.assigned,
            "acceptance": row.acceptance,
            "state": row.state if row.state in REGISTER_STATES else "unrecognised",
            "raw_state": row.state,
            "note": row.note,
            "note_blank": is_blank_note(row.note),
            "line": row.line,
            "plan_uri": None,
            "plan_progress": None,
        }
        for row in parsed.rows
    ]
    record["malformed"] = [
        {"line": m.line, "text": m.text, "reason": m.reason} for m in parsed.malformed
    ]
    return record


async def load_board(session: AsyncSession, project: str) -> dict[str, Any]:
    """Every register row and plan task of `project`, derived on read (§1)."""
    documents = (await session.execute(_CORPUS, _corpus_params(project))).all()
    registers = [d for d in documents if d.uri.startswith(REGISTER_PREFIX)]
    plan_documents = [d for d in documents if d.uri.startswith(PLAN_PREFIX)]

    by_plan: dict[str, list[Any]] = {}
    for workstream in (await session.execute(_WORKSTREAMS, {"project": project})).all():
        by_plan.setdefault(workstream.plan_uri, []).append(workstream)
    chosen = {uri: _choose(by_plan.get(uri, [])) for uri in (d.uri for d in plan_documents)}
    ids = sorted({w.id for w in chosen.values() if w is not None})

    states: dict[tuple[str, int], Any] = {}
    activity: dict[tuple[str, int], Any] = {}
    ledger_tasks: dict[str, set[int]] = {}
    if ids:
        for row in (await session.execute(_STATES, {"ids": ids})).all():
            states[(row.workstream_id, int(row.task))] = row
        for row in (await session.execute(_ACTIVITY, {"ids": ids})).all():
            activity[(row.workstream_id, int(row.task))] = row
        for row in (await session.execute(_LEDGER_TASKS, {"ids": ids})).all():
            ledger_tasks.setdefault(row.workstream_id, set()).add(int(row.task))

    plans: list[dict[str, Any]] = []
    for document in plan_documents:
        workstream = chosen[document.uri]
        record: dict[str, Any] = {
            "document_id": document.id,
            "uri": document.uri,
            "title": document.title,
            "content_hash": document.content_hash,
            "workstream": None,
            "other_workstreams": max(len(by_plan.get(document.uri, [])) - 1, 0),
            "spec_uri": None,
            "untracked": None,
            "tasks": [],
            "orphans": [],
            "error": None,
        }
        if workstream is not None:
            record["workstream"] = {
                "id": workstream.id, "key": workstream.key, "state": workstream.state,
            }
            record["spec_uri"] = workstream.spec_uri
        if workstream is None:
            record["untracked"] = "no_workstream"
        elif workstream.id not in ledger_tasks:
            record["untracked"] = "no_properties"
        plans.append(record)
        if document.content is None:
            record["error"] = "this plan has no stored text to read"
            continue
        try:
            parsed = parse_plan(document.content)
        except Exception as exc:  # one source's failure must not blank the board (§5)
            record["error"] = f"{type(exc).__name__}: {exc}"
            continue
        record["title"] = parsed.title or document.title
        counts: dict[int, int] = {}
        for task in parsed.tasks:
            counts[task.number] = counts.get(task.number, 0) + 1
        for task in parsed.tasks:
            record["tasks"].append(
                await _task_record(session, task, workstream, record["untracked"],
                                   states, activity, counts[task.number] > 1)
            )
        if workstream is not None:
            headings = set(counts)
            record["orphans"] = sorted(ledger_tasks.get(workstream.id, set()) - headings)

    progress = {
        plan["uri"]: {
            "done": sum(1 for t in plan["tasks"] if t["state"] == "done"),
            "total": len(plan["tasks"]),
            "untracked": plan["untracked"],
        }
        for plan in plans
        if plan["error"] is None
    }
    register_records = [_register_record(d) for d in registers]
    for register in register_records:
        for row in register["rows"]:
            uri = cell_uri(row["assigned"])
            if uri in progress:
                row["plan_uri"] = uri
                row["plan_progress"] = progress[uri]
    return {"project": project, "registers": register_records, "plans": plans}


async def _task_record(session, task, workstream, untracked, states, activity, shared):
    record: dict[str, Any] = {
        "number": task.number,
        "label": task.label,
        "title": task.title,
        "line": task.line,
        "state": "untracked" if untracked else "todo",
        "raw_state": None,
        "untracked": untracked,
        "shared_number": shared,
        "blocked_reason": None,
        "commit": None,
        "last_activity": None,
        "steps": [{"checked": s.checked, "text": s.text} for s in task.steps],
    }
    if workstream is None:
        return record
    key = (workstream.id, task.number)
    seen = activity.get(key)
    if seen is not None:
        record["commit"] = seen.commit
        record["last_activity"] = seen.last_activity
    if untracked:
        return record
    entry = states.get(key)
    if entry is None:
        return record
    raw = entry.properties.get("state")
    record["raw_state"] = raw if isinstance(raw, str) else str(raw)
    record["state"] = raw if raw in LEDGER_STATES else "unrecognised"
    if record["state"] == "blocked":
        record["blocked_reason"] = await _blocked_reason(session, workstream.id, entry)
    return record
