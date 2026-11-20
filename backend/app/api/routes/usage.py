"""Token and cost read API.

Four GET shapes over ``llm_usage``: the window total with its breakdowns, a
time series, one subject's calls, and the outliers. Read-only by construction
-- rows are written by the recorder inside the orchestrator and by nothing
else, so there is no POST/PUT/DELETE here and there should never be one.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.models.llm_usage import LLMUsage
from app.repositories.usage_repository import UsageRepository, window_start
from app.services.usage_pricing import (
    DEFAULT_MODEL_PRICES,
    MODEL_PRICES_CONFIG_KEY,
    normalise_price_overrides,
    resolve_rates,
)
from app.services.usage_recorder import price_cache_reset
from app.models.config import Config
from app.schemas.usage import (
    JobUsageResponse,
    JobUsageRow,
    ModelPriceRow,
    ModelPricesResponse,
    ModelPricesUpdate,
    UsageBreakdownRow,
    UsageCallRow,
    UsageOverviewResponse,
    SubjectTotalRow,
    SubjectTotalsRequest,
    SubjectTotalsResponse,
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
    session: AsyncSession = SessionDep,
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
    session: AsyncSession = SessionDep,
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
    session: AsyncSession = SessionDep,
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
        # Only claimed for a subject that actually has calls: asserting it for
        # an empty result would describe work nothing here observed.
        batched_embedding=bool(calls)
        and not any(c.purpose == "embedding" for c in calls),
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


@router.post("/subject-totals", response_model=SubjectTotalsResponse)
async def usage_subject_totals(
    body: SubjectTotalsRequest,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Totals for a page that already knows which subjects it is drawing.

    A POST because the id list is the query and a page draws dozens of rows at
    once; the alternative is one GET per row, which turns a column into a
    connection storm. Capped so a caller cannot ask for the whole table.
    """
    if len(body.subject_ids) > 200:
        raise HTTPException(
            status_code=422, detail="at most 200 subject_ids per request",
        )
    rows = await UsageRepository(session).totals_for_subjects(
        body.subject_type, body.subject_ids,
    )
    return SubjectTotalsResponse(totals=[SubjectTotalRow(**r) for r in rows])


@router.get("/by-job", response_model=JobUsageResponse)
async def usage_by_job(
    window: str = Query(default="30d"),
    project: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """What each job has spent over the window, keyed by job rather than run."""
    rows = await UsageRepository(session).totals_by_job(_start(window), project)
    return JobUsageResponse(jobs=[JobUsageRow(**r) for r in rows])


@router.get("/top", response_model=UsageTopResponse)
async def usage_top(
    window: str = Query(default="30d"),
    by: str = Query(default="cost"),
    subject_type: str | None = None,
    project: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    if by not in _TOP_BY:
        raise HTTPException(status_code=422, detail=f"unrecognised ordering {by!r}")
    rows = await UsageRepository(session).top(
        by, _start(window), project, subject_type, limit,
    )
    return UsageTopResponse(by=by, items=[UsageTopRow(**r) for r in rows])


@router.get("/prices", response_model=ModelPricesResponse)
async def get_model_prices(
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """The effective price table: shipped defaults with the config row merged
    over them, plus every model the operator priced that ships no default."""
    row = (await session.execute(
        select(Config).where(Config.key == MODEL_PRICES_CONFIG_KEY)
    )).scalar_one_or_none()
    overrides = dict(row.value) if row and isinstance(row.value, dict) else {}
    models = sorted(set(DEFAULT_MODEL_PRICES) | set(overrides))
    rows = []
    for model in models:
        rates = resolve_rates(model, overrides)
        if rates is None:
            # A partial override for a model with no shipped default cannot be
            # completed; reporting invented rates would be worse than omitting
            # a row the operator can see is incomplete in their own input.
            continue
        rows.append(ModelPriceRow(
            model=model,
            input_micros_per_mtok=rates.input_micros_per_mtok,
            cached_micros_per_mtok=rates.cached_micros_per_mtok,
            output_micros_per_mtok=rates.output_micros_per_mtok,
            overridden=model in overrides,
        ))
    return ModelPricesResponse(models=rows)


@router.put("/prices", response_model=ModelPricesResponse)
async def put_model_prices(
    body: ModelPricesUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Replace the override layer wholesale, on the config-singleton pattern.

    Rates are validated rather than coerced: an unknown field silently dropped
    leaves an operator looking at a form that accepted their number and did
    nothing with it.
    """
    try:
        clean = normalise_price_overrides(body.prices)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = (await session.execute(
        select(Config).where(Config.key == MODEL_PRICES_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key=MODEL_PRICES_CONFIG_KEY, value=clean))
    else:
        row.value = clean
    await session.commit()
    # The recorder caches this table for a short TTL; a settings form that
    # takes half a minute to mean anything reads as a form that did not work.
    price_cache_reset()
    return await get_model_prices(session=session)
