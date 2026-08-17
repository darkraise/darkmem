"""Re-derive a filed research run's evidence (T3.28's trigger half).

**What the operator asked for, and what the box can honestly do.** The owner's
2026-08-16 ruling settled the shape as "the trigger surface re-runs the subject
of a previously filed research run" — the one option needing no gatherer in the
tree, because the evidence was gathered by an MCP caller on the original run.
Implementing it exposed that "re-run" cannot mean *re-file*:

- The `research_run` journal stores no finding text on purpose (doc 05's
  write-time minimisation, and the text is already durable on the memory rows),
  so the only evidence a re-run can reach is the memories the run filed.
- A memory that was deleted is therefore unrecoverable — the journal keeps at
  most a truncated preview, and re-filing from a preview would file corrupted
  evidence under a real origin.
- A memory that survives already carries that finding's exact content and
  origin key, so re-filing it writes a duplicate row asserting the same claim
  under the same origin. Corroboration counts `DISTINCT origin_key`, so the
  duplicate adds no evidence — only a row.

So a re-file is either impossible or inert, and this module does the operation
that is neither: it feeds the run's surviving memories back through the
pipeline, which is the idempotent re-extraction path (Phase 5 strips a memory's
prior graph contributions inside savepoint B before writing the new set). The
subject is re-derived under the current taxonomy, extractor and dedup, and no
origin, count or row is created or moved.

**It never imports the loop, and that is the point.** Invariant 15's scan
forbids `app.services.auto_research` anywhere under `app/`; T3.27 bought one
scoped exemption for the MCP door because that door genuinely files evidence.
Re-derivation files nothing, so it needs no exemption and takes none — the
research constant it needs to recognise a researched row lives beside the
config row instead (`research_config.RESEARCH_SOURCE`).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.models.memory import Memory
from app.services.research_config import RESEARCH_SOURCE

RESEARCH_RUN_EVENT = "research_run"

__all__ = [
    "RESEARCH_RUN_EVENT",
    "ResearchRunSummary",
    "RerunOutcome",
    "RerunRefused",
    "list_research_runs",
    "load_research_run",
    "rerun_research_run",
]


class RerunRefused(Exception):
    """The run cannot be re-derived, and nothing was written.

    A distinct type rather than a bare `ValueError` so the route can answer 404
    or 409 without string-matching, and so an in-process caller can tell "this
    request was refused" from "the pipeline failed partway".
    """


@dataclass(frozen=True)
class ResearchRunSummary:
    """One filed run, as the operator surface lists it.

    `occurred_at` is not decoration: `events` has a composite
    `PRIMARY KEY (id, created_at)` and is RANGE-partitioned by month, so a bare
    `WHERE id = :id` scans every monthly child. The list hands back the bound
    the re-run then passes in, which is the same discipline T2.13's undo path
    established for the first by-id consumer of this table.
    """

    event_id: int
    occurred_at: datetime
    run_id: str | None
    subject: str
    project: str
    filed: int
    memory_ids: tuple[uuid.UUID, ...]
    live: int


@dataclass(frozen=True)
class RerunOutcome:
    event_id: int
    subject: str
    project: str
    #: Memory ids the original run filed, as journalled.
    filed: int
    #: Of those, how many still exist. Re-derivation reaches no others, and the
    #: difference is reported rather than silently absorbed — a run whose rows
    #: were deleted re-derives less than it filed, and the operator should see
    #: that rather than read a clean "reprocessed" line.
    reprocessed: int
    missing: int
    errors: int


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _summary_from_row(row: dict, live_ids: set[uuid.UUID]) -> ResearchRunSummary:
    payload = row.get("payload") or {}
    memory_ids = tuple(
        parsed for parsed in (_as_uuid(m) for m in payload.get("memory_ids") or ())
        if parsed is not None
    )
    return ResearchRunSummary(
        event_id=row["id"],
        occurred_at=row["created_at"],
        run_id=payload.get("run_id"),
        subject=payload.get("subject") or "",
        project=row.get("project") or payload.get("project") or "",
        # The journalled count, never `len(memory_ids)`: they agree today, and
        # if they ever stop the journal is the record of what the run did.
        filed=int(payload.get("filed") or 0),
        memory_ids=memory_ids,
        live=sum(1 for m in memory_ids if m in live_ids),
    )


async def _live_research_ids(
    session: AsyncSession, memory_ids: tuple[uuid.UUID, ...]
) -> set[uuid.UUID]:
    """Which of these ids are live rows this loop actually filed.

    The `source` predicate is a guard, not a filter. `memory_ids` comes out of
    a journal payload, and ids are reused by nothing — but a re-derivation that
    trusted the payload alone would reprocess whatever now sits at that id if
    one were ever recycled or hand-written. Re-extraction is idempotent, so the
    blast radius is small; asserting the row is a researched capture keeps it
    zero.
    """
    if not memory_ids:
        return set()
    rows = await session.execute(
        select(Memory.id).where(
            Memory.id.in_(memory_ids), Memory.source == RESEARCH_SOURCE
        )
    )
    return set(rows.scalars().all())


async def list_research_runs(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> tuple[list[ResearchRunSummary], int]:
    """Filed research runs, newest first, each with its live-row count."""
    from app.services.events import list_events

    rows, total = await list_events(
        session, event_type=RESEARCH_RUN_EVENT, limit=limit, offset=offset
    )
    every_id = tuple(
        {m for row in rows for m in _summary_from_row(row, set()).memory_ids}
    )
    live_ids = await _live_research_ids(session, every_id)
    return [_summary_from_row(row, live_ids) for row in rows], total


async def load_research_run(
    session: AsyncSession, *, event_id: int, occurred_at: datetime
) -> ResearchRunSummary:
    """One run, addressed by its composite key.

    Refuses an event of another type rather than reading its payload: every
    `events` row has a `payload`, most have no `memory_ids`, and one that did
    would be reprocessed as if it were a research run.
    """
    row = (await session.execute(
        text(
            "SELECT id, created_at, event_type, project, payload FROM events "
            "WHERE id = CAST(:id AS bigint) AND created_at = :occurred_at"
        ),
        {"id": event_id, "occurred_at": occurred_at},
    )).mappings().first()
    if row is None:
        raise RerunRefused(
            f"no event {event_id} at {occurred_at.isoformat()} — the re-run "
            "carries the timestamp the listing gave it, and a wrong one prunes "
            "to the wrong partition rather than scanning every month"
        )
    if row["event_type"] != RESEARCH_RUN_EVENT:
        raise RerunRefused(
            f"event {event_id} is a {row['event_type']!r}, not a "
            f"{RESEARCH_RUN_EVENT!r}"
        )
    summary = _summary_from_row(dict(row), set())
    live_ids = await _live_research_ids(session, summary.memory_ids)
    return _summary_from_row(dict(row), live_ids)


async def rerun_research_run(
    session: AsyncSession,
    *,
    event_id: int,
    occurred_at: datetime,
    reprocess,
) -> RerunOutcome:
    """Re-derive everything the run's surviving evidence supports.

    ``reprocess`` is the re-extraction callable — ``AnalyticsService`` owns the
    pipeline wiring and the audit write, and passing it in keeps this module
    free of both, so a test can drive the whole refusal surface without a
    pipeline.

    A run with no surviving memory is **refused**, not reported as a successful
    re-derivation of nothing: "re-ran, 0 processed" and "there is nothing left
    of this run" are different facts, and only the second is true.
    """
    summary = await load_research_run(
        session, event_id=event_id, occurred_at=occurred_at
    )
    if summary.live == 0:
        raise RerunRefused(
            f"none of the {summary.filed} memories run {event_id} filed is "
            "still live, so there is no evidence left to re-derive. The journal "
            "records what it filed but never the finding text, so a deleted "
            "researched memory cannot be restored from it"
        )

    live_ids = await _live_research_ids(session, summary.memory_ids)
    result = await reprocess(sorted(live_ids, key=str))
    return RerunOutcome(
        event_id=summary.event_id,
        subject=summary.subject,
        project=summary.project,
        filed=summary.filed,
        reprocessed=int(result.get("processed", 0)),
        missing=len(summary.memory_ids) - len(live_ids),
        errors=int(result.get("errors", 0)),
    )
