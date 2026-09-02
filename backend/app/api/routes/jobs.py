"""Job management API.

Exposes the in-process ``JobRegistry`` over four endpoints:

* ``GET  /api/v1/jobs`` — list every registered job with config + state.
* ``PUT  /api/v1/jobs/{key}`` — update enabled / cron.
* ``POST /api/v1/jobs/{key}/trigger`` — fire the runner immediately.
* ``PUT  /api/v1/jobs/{key}/config`` — update per-job config values.

All routes require auth.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from sqlalchemy import func, select

from app.api.auth import require_auth
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.job_run import JobRun
from app.services.job_registry import FieldDescriptor, JobBusyError

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobItem(BaseModel):
    key: str
    display_name: str
    description: str
    enabled: bool
    cron: str
    min_interval_seconds: int
    default_cron: str
    last_run_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None
    running: bool
    config: dict = {}
    config_schema: list[FieldDescriptor] = []


class JobsResponse(BaseModel):
    jobs: list[JobItem]


class JobUpdate(BaseModel):
    enabled: bool | None = None
    cron: str | None = Field(default=None, min_length=1, max_length=200)


class JobConfigUpdate(BaseModel):
    config: dict


class JobRunItem(BaseModel):
    id: str
    outcome: str
    started_at: str
    duration_seconds: float
    trigger: str
    error: str | None = None
    detail: dict = {}


class JobRunsResponse(BaseModel):
    items: list[JobRunItem]
    total: int
    limit: int
    offset: int


class JobTriggerResponse(BaseModel):
    key: str
    last_status: str | None
    last_error: str | None
    last_run_at: str | None


def _get_registry(request: Request):
    registry = getattr(request.app.state, "job_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="Job registry not initialised")
    return registry


@router.get("", response_model=JobsResponse)
async def list_jobs(request: Request, _user=Depends(require_auth)) -> JobsResponse:
    registry = _get_registry(request)
    items = await registry.list_with_config()
    return JobsResponse(jobs=[JobItem(**item) for item in items])


@router.get("/{key}/runs", response_model=JobRunsResponse)
async def list_job_runs(
    key: str,
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> JobRunsResponse:
    """One job's run history, newest first, server-paginated.

    Reads `job_runs` rather than `events`: run telemetry is prunable
    operational data, and the audit substrate is neither. `total` is the
    unpaginated count so a reader can tell "page 1 of many" from "that is
    everything" — which the previous client-side filter over a shared
    journal could not.
    """
    registry = _get_registry(request)
    if key not in registry._jobs:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")

    total = (await session.execute(
        select(func.count()).select_from(JobRun).where(JobRun.job_key == key)
    )).scalar_one()
    rows = (await session.execute(
        select(JobRun)
        .where(JobRun.job_key == key)
        .order_by(JobRun.started_at.desc(), JobRun.id.desc())
        .limit(limit).offset(offset)
    )).scalars().all()

    return JobRunsResponse(
        items=[
            JobRunItem(
                id=str(r.id),
                outcome=r.outcome,
                started_at=r.started_at.isoformat(),
                duration_seconds=r.duration_seconds,
                trigger=r.trigger,
                error=r.error,
                detail=r.detail or {},
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.put("/{key}", response_model=JobItem)
async def update_job(
    key: str,
    body: JobUpdate,
    request: Request,
    _user=Depends(require_auth),
) -> JobItem:
    registry = _get_registry(request)
    if registry.get(key) is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")
    try:
        await registry.update_config(
            key,
            enabled=body.enabled,
            cron=body.cron,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    items = await registry.list_with_config()
    item = next((i for i in items if i["key"] == key), None)
    if item is None:
        raise HTTPException(status_code=500, detail=f"Job {key!r} disappeared mid-update")
    return JobItem(**item)


@router.put("/{key}/config", response_model=JobItem)
async def update_job_config(
    key: str,
    body: JobConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
) -> JobItem:
    registry = _get_registry(request)
    if registry.get(key) is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")
    try:
        await registry.set_config(key, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    items = await registry.list_with_config()
    item = next((i for i in items if i["key"] == key), None)
    if item is None:
        raise HTTPException(status_code=500, detail=f"Job {key!r} disappeared mid-update")
    return JobItem(**item)


@router.post("/{key}/trigger", response_model=JobTriggerResponse)
async def trigger_job(
    key: str,
    request: Request,
    _user=Depends(require_auth),
) -> JobTriggerResponse:
    # C5 (increment 7): a disarmed scheduler does not disarm this door. The
    # trigger runs the job on demand, and an LLM or egress job spends money
    # client-side of the database before anything the viewer role can refuse.
    if settings.read_only:
        raise HTTPException(
            status_code=403,
            detail="read-only instance: jobs cannot be triggered",
        )
    registry = _get_registry(request)
    job = registry.get(key)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")
    # A scheduled or earlier manual run already holds the per-job lock. Without
    # this 409 the request would block until that run finished (the trigger()
    # call awaits the same lock), so surface the conflict instead of hanging.
    if job.lock.locked():
        raise HTTPException(
            status_code=409,
            detail=f"Job {key!r} is already running",
        )
    # Synchronous by design: the manual "Run" surfaces the run's result, and the
    # per-job lock (shared with the scheduler loop) already prevents a manual and
    # a scheduled run from racing. Long jobs are bounded by the runner's
    # max_run_seconds ceiling. trigger() re-checks the lock and raises
    # JobBusyError if a run slipped in after the pre-check above, so a lost race
    # surfaces as 409 instead of blocking the request.
    try:
        cfg = await registry.trigger(key)
    except JobBusyError:
        raise HTTPException(status_code=409, detail=f"Job {key!r} is already running")
    return JobTriggerResponse(
        key=key,
        last_status=cfg.last_status,
        last_error=cfg.last_error,
        last_run_at=cfg.last_run_at.isoformat() if cfg.last_run_at else None,
    )
