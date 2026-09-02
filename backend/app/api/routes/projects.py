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

    Derived, never a registry -- a project exists here because a memory, a
    document or a checkpoint carries it, and stops existing when the last of
    them is deleted. Widened 2026-08-31 (spec §2.1, review M2): grouping
    ``memories.project`` alone made a document-only project -- exactly what
    the corpus import creates -- invisible to its own scope picker.
    """

    name: str
    memory_count: int
    document_count: int
    checkpoint_count: int
    last_checkpoint_at: datetime | None
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
    ),
    m AS (SELECT project, count(*) AS n FROM memories GROUP BY project),
    d AS (SELECT project, count(*) AS n FROM documents GROUP BY project),
    c AS (SELECT project, count(*) AS n, max(created_at) AS latest
          FROM session_checkpoints GROUP BY project),
    e AS (SELECT project,
                 max((created_at AT TIME ZONE 'UTC')::date) AS latest_day
          FROM events GROUP BY project)
    SELECT names.project AS name,
           COALESCE(m.n, 0) AS memory_count,
           COALESCE(d.n, 0) AS document_count,
           COALESCE(c.n, 0) AS checkpoint_count,
           c.latest AS last_checkpoint_at,
           e.latest_day AS last_event_day
    FROM names
    LEFT JOIN m ON m.project = names.project
    LEFT JOIN d ON d.project = names.project
    LEFT JOIN c ON c.project = names.project
    LEFT JOIN e ON e.project = names.project
    WHERE names.project IS NOT NULL AND names.project <> ''
    ORDER BY COALESCE(m.n, 0) + COALESCE(d.n, 0) + COALESCE(c.n, 0) DESC,
             names.project ASC
    """
)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every distinct project across memories, documents and checkpoints,
    busiest first.

    Counts every row rather than only the active ones: this drives a *scope*
    picker, and a project holding nothing but superseded rows is still a
    scope worth being able to switch into.

    The `events` CTE reuses `ix_events_day`'s expression verbatim. Simplifying
    it to `created_at::date` de-indexes it and changes what a day means.
    """
    rows = (await session.execute(_UNION_SQL)).mappings().all()
    return [ProjectSummary(**dict(row)) for row in rows]
