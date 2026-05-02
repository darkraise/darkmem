"""Job management API.

Exposes the in-process ``JobRegistry`` over three endpoints:

* ``GET  /api/v1/jobs`` — list every registered job with config + state.
* ``PUT  /api/v1/jobs/{key}`` — update enabled / interval_seconds.
* ``POST /api/v1/jobs/{key}/trigger`` — fire the runner immediately.

All routes require auth.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import require_auth

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobItem(BaseModel):
    key: str
    display_name: str
    description: str
    enabled: bool
    interval_seconds: int
    min_interval_seconds: int
    default_interval_seconds: int
    last_run_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None
    running: bool


class JobsResponse(BaseModel):
    jobs: list[JobItem]


class JobUpdate(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=1)


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
            interval_seconds=body.interval_seconds,
        )
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
    registry = _get_registry(request)
    if registry.get(key) is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")
    cfg = await registry.trigger(key)
    return JobTriggerResponse(
        key=key,
        last_status=cfg.last_status,
        last_error=cfg.last_error,
        last_run_at=cfg.last_run_at.isoformat() if cfg.last_run_at else None,
    )
