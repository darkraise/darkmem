"""`GET /api/v1/knowledge/overview` — the REST twin of `memory_overview`.

Doc 12 §3 pairs the tool with this route, and invariant 17 makes the pairing
mean something: both doors call `app.services.memory_overview.get_overview`
and neither computes anything of its own, so the map selection, the single
reduce, the cache and the declared drops cannot drift apart between them.

Read-only. Nothing here generates a community report — the reports are
precomputed off the hot path by T2.19's Tier-C generator, and a topic without
one is reported as `pending`/`skipped`/`failed`, never filled in on a read
(doc 09 §3.3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import lease_llm
from app.api.auth import require_auth
from app.database import SessionDep
from app.schemas.overview import OverviewResponse
from app.services.memory_overview import OverviewUnavailable, get_overview

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/overview", response_model=OverviewResponse)
async def project_overview(
    request: Request,
    project: str = "default",
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    llm = getattr(request.app.state, "llm", None)
    with lease_llm(llm):
        try:
            result = await get_overview(session, llm, project)
        except OverviewUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return result.to_dict()
