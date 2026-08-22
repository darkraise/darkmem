from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_session
from app.models.memory import Memory

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectSummary(BaseModel):
    """A project the corpus actually contains.

    `project` is a free-text column with no table of its own — a project comes
    into existence by being written to a memory and stops existing when the
    last of them is deleted. So this is derived, never a registry, and a scope
    the operator has in mind but has not captured into yet will legitimately be
    absent from it.
    """

    name: str
    memory_count: int


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every distinct `memories.project`, busiest first.

    Counts every row rather than only the active ones: this drives a *scope*
    picker, and a project holding nothing but superseded rows is still a scope
    worth being able to switch into — hiding it would make those rows
    unreachable from the UI.
    """
    rows = (
        await session.execute(
            select(Memory.project, func.count().label("memory_count"))
            .group_by(Memory.project)
            .order_by(func.count().desc(), Memory.project.asc())
        )
    ).all()
    return [
        ProjectSummary(name=name, memory_count=count)
        for name, count in rows
        if name
    ]
