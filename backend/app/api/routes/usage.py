"""Token and cost read API.

Four GET shapes over ``llm_usage``: the window total with its breakdowns, a
time series, one subject's calls, and the outliers. Read-only by construction
-- rows are written by the recorder inside the orchestrator and by nothing
else, so there is no POST/PUT/DELETE here and there should never be one.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.models.llm_usage import LLMUsage
from app.repositories.usage_repository import UsageRepository, window_start
from app.schemas.usage import (
    UsageBreakdownRow,
    UsageCallRow,
    UsageOverviewResponse,
    UsageSeriesBucket,
    UsageSeriesResponse,
    UsageSubjectResponse,
    UsageTopResponse,
    UsageTopRow,
)

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])

_BUCKETS = {"hour", "day", "week", "month"}
_TOP_BY = {"cost", "calls", "duration"}


def _start(window: str) -> datetime | None:
    try:
        return window_start(window)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/overview", response_model=UsageOverviewResponse)
async def usage_overview(
    window: str = Query(default="30d"),
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    start = _start(window)
    repo = UsageRepository(session)
    totals = await repo.totals(start, project)
    return UsageOverviewResponse(
        window_start=start,
        window_end=datetime.now(timezone.utc),
        unpriced_models=await repo.unpriced_models(start, project),
        by_purpose=[
            UsageBreakdownRow(**r)
            for r in await repo.breakdown(LLMUsage.purpose, start, project)
        ],
        by_model=[
            UsageBreakdownRow(**r)
            for r in await repo.breakdown(LLMUsage.model, start, project)
        ],
        by_subject_type=[
            UsageBreakdownRow(**r)
            for r in await repo.breakdown(LLMUsage.subject_type, start, project)
        ],
        **totals,
    )


@router.get("/series", response_model=UsageSeriesResponse)
async def usage_series(
    window: str = Query(default="30d"),
    bucket: str = Query(default="day"),
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    if bucket not in _BUCKETS:
        raise HTTPException(status_code=422, detail=f"unrecognised bucket {bucket!r}")
    rows = await UsageRepository(session).series(bucket, _start(window), project)
    return UsageSeriesResponse(
        bucket=bucket, buckets=[UsageSeriesBucket(**r) for r in rows],
    )


@router.get("/by-subject/{subject_type}/{subject_id}", response_model=UsageSubjectResponse)
async def usage_by_subject(
    subject_type: str,
    subject_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    repo = UsageRepository(session)
    calls = await repo.subject_calls(subject_type, subject_id, limit)
    totals = await repo.subject_totals(subject_type, subject_id)
    return UsageSubjectResponse(
        subject_type=subject_type,
        subject_id=subject_id,
        # A memory's content and entity-name embeds are paid for by the batch it
        # arrived in. Reporting the memory's own embedding cost as zero would be
        # as wrong as inventing a share of the batch's, so the panel says which.
        batched_embedding=not any(c.purpose == "embedding" for c in calls),
        calls=[
            UsageCallRow(
                id=str(c.id),
                occurred_at=c.occurred_at,
                purpose=c.purpose,
                model=c.model,
                provider=c.provider,
                api_kind=c.api_kind,
                subject_type=c.subject_type,
                subject_id=c.subject_id,
                project=c.project,
                prompt_tokens=c.prompt_tokens,
                cached_tokens=c.cached_tokens,
                completion_tokens=c.completion_tokens,
                reasoning_tokens=c.reasoning_tokens,
                tokens_measured=c.tokens_measured,
                cost_micros=c.cost_micros,
                ok=c.ok,
                error_kind=c.error_kind,
                duration_ms=c.duration_ms,
                merged_classification=bool(
                    (c.usage_raw or {}).get("merged_classification")
                ),
            )
            for c in calls
        ],
        **totals,
    )


@router.get("/top", response_model=UsageTopResponse)
async def usage_top(
    window: str = Query(default="30d"),
    by: str = Query(default="cost"),
    subject_type: str | None = None,
    project: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    if by not in _TOP_BY:
        raise HTTPException(status_code=422, detail=f"unrecognised ordering {by!r}")
    rows = await UsageRepository(session).top(
        by, _start(window), project, subject_type, limit,
    )
    return UsageTopResponse(by=by, items=[UsageTopRow(**r) for r in rows])
