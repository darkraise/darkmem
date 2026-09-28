from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectSummary(BaseModel):
    """A project any corpus actually contains.

    Derived for every ordinary project -- one exists here because a memory, a
    document, a checkpoint, a workstream or a page carries it, and stops
    existing when the last of them is deleted. Widened 2026-08-31 (spec §2.1,
    review M2): grouping ``memories.project`` alone made a document-only
    project -- exactly what the corpus import creates -- invisible to its own
    scope picker.

    One exception, and it is the reason this endpoint reads the ``projects``
    registry at all: a ``kind='personal'`` row is served even holding nothing.
    The notes workspace's scope has to be selectable *before* anything has been
    filed into it, so deriving it from its own contents would make it
    unreachable exactly when it is empty.
    """

    name: str
    kind: str = "project"
    memory_count: int
    document_count: int
    checkpoint_count: int
    page_count: int
    last_checkpoint_at: datetime | None
    workstream_count: int
    open_workstream_count: int
    last_worklog_at: datetime | None
    # Day granularity on purpose: `ix_events_day` indexes the UTC-day
    # expression and nothing indexes (project, created_at); a timestamp here
    # would be a full scan of every monthly events partition.
    last_event_day: date | None


_UNION_SQL = text(
    """
    WITH names AS (
        SELECT project FROM memories
        UNION
        SELECT project FROM documents
        UNION
        SELECT project FROM session_checkpoints
        UNION
        SELECT project FROM workstreams
        UNION
        SELECT project FROM pages WHERE deleted_at IS NULL
        UNION
        -- A registered personal space appears even holding nothing: it is the
        -- notes workspace's own scope, not a project that happens to exist.
        SELECT name FROM projects WHERE kind = 'personal'
    ),
    m AS (SELECT project, count(*) AS n FROM memories GROUP BY project),
    d AS (SELECT project, count(*) AS n FROM documents GROUP BY project),
    c AS (SELECT project, count(*) AS n, max(created_at) AS latest
          FROM session_checkpoints GROUP BY project),
    w AS (SELECT project, count(*) AS n,
                 count(*) FILTER (WHERE state = 'open') AS open_n,
                 max(last_entry_at) AS latest
          FROM workstreams GROUP BY project),
    pg AS (SELECT project, count(*) AS n FROM pages
           WHERE deleted_at IS NULL GROUP BY project),
    e AS (SELECT project,
                 max((created_at AT TIME ZONE 'UTC')::date) AS latest_day
          FROM events GROUP BY project)
    SELECT names.project AS name,
           COALESCE(p.kind, 'project') AS kind,
           COALESCE(m.n, 0) AS memory_count,
           COALESCE(d.n, 0) AS document_count,
           COALESCE(c.n, 0) AS checkpoint_count,
           COALESCE(pg.n, 0) AS page_count,
           c.latest AS last_checkpoint_at,
           COALESCE(w.n, 0) AS workstream_count,
           COALESCE(w.open_n, 0) AS open_workstream_count,
           w.latest AS last_worklog_at,
           e.latest_day AS last_event_day
    FROM names
    LEFT JOIN m ON m.project = names.project
    LEFT JOIN d ON d.project = names.project
    LEFT JOIN c ON c.project = names.project
    LEFT JOIN w ON w.project = names.project
    LEFT JOIN pg ON pg.project = names.project
    LEFT JOIN e ON e.project = names.project
    LEFT JOIN projects p ON p.name = names.project
    WHERE names.project IS NOT NULL AND names.project <> ''
    ORDER BY COALESCE(m.n, 0) + COALESCE(d.n, 0) + COALESCE(c.n, 0)
             + COALESCE(w.n, 0) + COALESCE(pg.n, 0) DESC,
             names.project ASC
    """
)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every distinct project across memories, documents, checkpoints,
    workstreams and pages, busiest first.

    Counts every row rather than only the active ones: this drives a *scope*
    picker, and a project holding nothing but superseded rows is still a
    scope worth being able to switch into.

    The `events` CTE reuses `ix_events_day`'s expression verbatim. Simplifying
    it to `created_at::date` de-indexes it and changes what a day means.
    """
    rows = (await session.execute(_UNION_SQL)).mappings().all()
    return [ProjectSummary(**dict(row)) for row in rows]
