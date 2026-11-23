"""The dependent-caller re-trace debt: persist the overflow, drain it, never
drop it (doc 10 §3, T2).

An incremental reindex re-traces the callers of every changed file because
``_delete_files_data`` drops every edge pointing into a changed file, so a caller
that is not re-traced loses that edge until someone forces a full reindex. The
re-trace is capped so one change to a widely-called utility cannot balloon an
incremental run into a near-full one — and the callers past that cap used to be
logged and forgotten. That failure is silent: code search simply returns fewer
callers, nothing errors, and the staleness lands on exactly the busiest symbols.

So the overflow is persisted to ``repositories.index_debt`` and folded into the
changed set of later runs, a bounded batch at a time, until the queue is empty.
Debt is removed only after the run that re-traced it succeeded.

The stored shape is the observable contract the repos surface reads:

    {"version": 1,
     "files": {"<path>": "<commit sha that made it debt>"},
     "queued": <len(files)>,
     "deferred_total": <lifetime files ever deferred>,
     "drained_total": <lifetime files ever drained>,
     "last_defer": {"at": iso8601, "count": int, "commit": sha} | null,
     "last_drain": {"at": iso8601, "count": int, "commit": sha,
                    "vanished": int} | null}

``queued`` alone cannot distinguish a queue that is draining from one that is
stuck — both look like a number. The two lifetime counters and the two
timestamped last-* records are what make that difference readable at a single
instant, which is what the debt indicator has to show.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEBT_CONFIG_KEY = "code_index_debt"
DEBT_BATCH_FIELD = "drain_batch_size"
DEBT_SHAPE_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_debt() -> dict:
    return {
        "version": DEBT_SHAPE_VERSION,
        "files": {},
        "queued": 0,
        "deferred_total": 0,
        "drained_total": 0,
        "last_defer": None,
        "last_drain": None,
    }


def normalize(value: object) -> dict:
    """Read a stored debt value into the current shape, tolerating anything.

    A debt row that cannot be parsed must not take a reindex down with it: the
    graph is the product, the debt ledger is bookkeeping over it. Unreadable
    bookkeeping degrades to an empty ledger, which the next overflow refills.
    """
    debt = empty_debt()
    if not isinstance(value, dict):
        return debt

    files = value.get("files")
    if isinstance(files, dict):
        debt["files"] = {
            str(path): ("" if sha is None else str(sha))
            for path, sha in files.items()
            if str(path)
        }
    elif isinstance(files, list):
        debt["files"] = {str(path): "" for path in files if str(path)}

    for key in ("deferred_total", "drained_total"):
        raw = value.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            debt[key] = raw

    for key in ("last_defer", "last_drain"):
        raw = value.get(key)
        if isinstance(raw, dict):
            debt[key] = raw

    debt["queued"] = len(debt["files"])
    return debt


def queued_files(debt: dict) -> list[str]:
    """The outstanding files, in a deterministic order.

    Sorted rather than insertion-ordered: jsonb does not preserve key order, so
    an insertion order read back from Postgres would not be the one written and
    successive drain batches could revisit the same files while starving others.
    """
    return sorted(debt.get("files", {}))


def record_overflow(debt: dict, files: list[str], commit: str | None) -> dict:
    """Add re-trace overflow to the queue, deduped.

    A file already in the queue keeps the sha that first made it debt — that is
    the commit whose edges it is missing, and a later run rediscovering the same
    stale caller does not make it any less stale.
    """
    updated = dict(debt)
    queue = dict(debt.get("files", {}))
    added = [f for f in dict.fromkeys(files) if f and f not in queue]
    for path in added:
        queue[path] = commit or ""
    updated["files"] = queue
    updated["queued"] = len(queue)
    if added:
        updated["deferred_total"] = int(debt.get("deferred_total", 0)) + len(added)
        updated["last_defer"] = {
            "at": _now(),
            "count": len(added),
            "commit": commit or "",
        }
    return updated


def record_drain(
    debt: dict, files: list[str], commit: str | None, vanished: int = 0
) -> dict:
    """Remove files a completed run re-traced. Only a success may call this."""
    updated = dict(debt)
    queue = dict(debt.get("files", {}))
    removed = [f for f in dict.fromkeys(files) if f in queue]
    for path in removed:
        queue.pop(path, None)
    updated["files"] = queue
    updated["queued"] = len(queue)
    if removed:
        updated["drained_total"] = int(debt.get("drained_total", 0)) + len(removed)
        updated["last_drain"] = {
            "at": _now(),
            "count": len(removed),
            "commit": commit or "",
            "vanished": vanished,
        }
    return updated


def summarize(value: object) -> dict:
    """The repos-surface projection: counts and progress, without the paths."""
    debt = normalize(value)
    return {
        "queued": debt["queued"],
        "deferred_total": debt["deferred_total"],
        "drained_total": debt["drained_total"],
        "last_defer": debt["last_defer"],
        "last_drain": debt["last_drain"],
    }


async def load(session: AsyncSession, repo_id: UUID) -> dict:
    stored = (await session.execute(
        text("SELECT index_debt FROM repositories WHERE id = CAST(:rid AS uuid)"),
        {"rid": str(repo_id)},
    )).scalar_one_or_none()
    return normalize(stored)


async def save(session: AsyncSession, repo_id: UUID, debt: dict) -> None:
    await session.execute(
        text(
            "UPDATE repositories SET index_debt = CAST(:debt AS jsonb) "
            "WHERE id = CAST(:rid AS uuid)"
        ),
        {"rid": str(repo_id), "debt": json.dumps(debt)},
    )


async def drain_batch_size(session: AsyncSession, default: int) -> int:
    """Files folded into one continuation run, from the ``config`` row.

    Defaults to the re-trace cap: a drain batch that outran the cap would
    reintroduce the balloon the cap exists to prevent.
    """
    from app.models.config import Config

    row = (await session.execute(
        select(Config).where(Config.key == DEBT_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return default
    raw = row.value.get(DEBT_BATCH_FIELD)
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return default


async def journal(
    session: AsyncSession,
    *,
    repo_id: UUID,
    action: str,
    count: int,
    debt: dict,
    commit: str | None,
    vanished: int = 0,
) -> None:
    from app.services.events import record_event

    await record_event(
        session,
        event_type="repo_indexed",
        object_type="repository",
        object_id=repo_id,
        source="code_index",
        payload={
            "action": action,
            "files": count,
            "queued": debt["queued"],
            "deferred_total": debt["deferred_total"],
            "drained_total": debt["drained_total"],
            "commit": commit or "",
            "vanished": vanished,
        },
    )
