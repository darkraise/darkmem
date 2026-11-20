"""Pipeline failures API routes.

Provides:
  - GET  /api/v1/pipeline-failures — list unresolved failures
  - GET  /api/v1/pipeline-failures/counts — counts by pipeline
  - GET  /api/v1/pipeline-failures/{id} — get one
  - POST /api/v1/pipeline-failures/{id}/retry — async single retry
  - POST /api/v1/pipeline-failures/retry-all — async bulk retry
  - DELETE /api/v1/pipeline-failures/{id} — forget a failure
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.api.websocket import event_manager
from app.utils.background import spawn
from app.database import async_session_factory, get_session
from app.services.pipeline import load_pipeline_entry
from app.services.pipeline_failures import (
    PipelineFailureService,
    RETRY_HANDLERS,
    retry_locks,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline-failures", tags=["pipeline-failures"])


@router.get("")
async def list_failures(
    entity_type: str | None = None,
    pipeline_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    items, total = await svc.list_unresolved(
        entity_type=entity_type, pipeline_name=pipeline_name,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/counts")
async def counts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    return await svc.counts_by_pipeline()


@router.get("/{failure_id}")
async def get_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    return failure


@router.post("/{failure_id}/retry", status_code=202)
async def retry_failure(
    failure_id: UUID,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    failure = await svc.get(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    if failure["resolved_at"] is not None:
        return {"accepted": True, "failure_id": str(failure_id), "note": "already resolved"}

    handler = RETRY_HANDLERS.get(failure["pipeline_name"])
    if not handler:
        raise HTTPException(
            status_code=503,
            detail=f"No retry handler registered for pipeline {failure['pipeline_name']!r}",
        )

    if not retry_locks.try_acquire(failure_id):
        raise HTTPException(status_code=409, detail="Failure is already retrying")

    async def _run():
        try:
            await handler(UUID(failure["entity_id"]))
        except Exception as e:
            logger.exception("Retry handler failed for failure_id=%s", failure_id)
            try:
                async with async_session_factory() as s:
                    manual_svc = PipelineFailureService(s, broadcast=event_manager.broadcast)
                    await manual_svc.record(
                        entity_type=failure["entity_type"],
                        entity_id=UUID(failure["entity_id"]),
                        pipeline_name=failure["pipeline_name"],
                        failed_step=failure["failed_step"],
                        error_message=f"Retry handler raised: {e}",
                    )
                    await s.commit()
            except Exception:
                logger.exception("Failed to record retry exception")
        finally:
            retry_locks.release(failure_id)

    spawn(_run(), name="retry-failure")
    return {"accepted": True, "failure_id": str(failure_id)}


@router.post("/retry-all", status_code=202)
async def retry_all(
    entity_type: str | None = None,
    pipeline_name: str | None = None,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    svc = PipelineFailureService(session)
    failures, total = await svc.list_unresolved(
        entity_type=entity_type, pipeline_name=pipeline_name, limit=1000,
    )
    batch_id = str(uuid4())

    if total == 0:
        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": 0, "total": 0,
            "processed": 0, "errors": 0,
            "entity_type": None, "entity_id": None, "state": "done",
        })
        return {"accepted": True, "batch_id": batch_id, "total": 0}

    pipeline_obj = getattr(request.app.state, "pipeline", None) if request else None

    async def _run_bulk():
        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": 0, "total": total,
            "processed": 0, "errors": 0,
            "entity_type": None, "entity_id": None, "state": "started",
        })

        processed = 0
        errors = 0

        # Memory bulk path — use process_batch for full batching benefit
        if pipeline_name == "memory_ingest" and pipeline_obj is not None:
            entries_with_failures: list[tuple[dict, dict]] = []
            for f in failures:
                fid = UUID(f["id"])
                if not retry_locks.try_acquire(fid):
                    continue
                try:
                    entry = await load_pipeline_entry(
                        async_session_factory, UUID(f["entity_id"]),
                    )
                except Exception:
                    logger.exception("Failed to build memory entry for %s", f["entity_id"])
                    retry_locks.release(fid)
                    continue
                if entry is None:
                    retry_locks.release(fid)
                    continue
                entries_with_failures.append((f, entry))

            try:
                results = await pipeline_obj.process_batch([e for _, e in entries_with_failures])
                for (f, _), result in zip(entries_with_failures, results):
                    processed += 1
                    if isinstance(result, dict) and result.get("error"):
                        errors += 1
                    await event_manager.broadcast("pipeline.retry_batch.progress", {
                        "batch_id": batch_id, "current": processed, "total": total,
                        "processed": processed, "errors": errors,
                        "entity_type": f["entity_type"], "entity_id": f["entity_id"],
                        "state": "progress",
                    })
            except Exception:
                logger.exception("Bulk memory retry failed")
                # process_batch raised before the per-entry zip loop ran, so none
                # of THIS chunk is in `processed` yet; count the whole chunk as
                # attempted-and-errored (cumulative across chunks).
                errors += len(entries_with_failures)
                processed += len(entries_with_failures)
            finally:
                for f, _ in entries_with_failures:
                    retry_locks.release(UUID(f["id"]))
        else:
            # Sequential fallback: run the handler per failure
            for f in failures:
                fid = UUID(f["id"])
                if not retry_locks.try_acquire(fid):
                    continue
                try:
                    handler = RETRY_HANDLERS.get(f["pipeline_name"])
                    if handler:
                        await handler(UUID(f["entity_id"]))
                        processed += 1
                    else:
                        errors += 1
                        logger.warning("No retry handler for %s", f["pipeline_name"])
                except Exception:
                    logger.exception("Retry handler failed in bulk")
                    errors += 1
                finally:
                    retry_locks.release(fid)
                    await event_manager.broadcast("pipeline.retry_batch.progress", {
                        "batch_id": batch_id, "current": processed + errors, "total": total,
                        "processed": processed, "errors": errors,
                        "entity_type": f["entity_type"], "entity_id": f["entity_id"],
                        "state": "progress",
                    })

        await event_manager.broadcast("pipeline.retry_batch.progress", {
            "batch_id": batch_id, "current": total, "total": total,
            "processed": processed, "errors": errors,
            "entity_type": None, "entity_id": None, "state": "done",
        })

    spawn(_run_bulk(), name="retry-bulk")
    return {"accepted": True, "batch_id": batch_id, "total": total}


@router.delete("/{failure_id}", status_code=204)
async def forget_failure(
    failure_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    svc = PipelineFailureService(session, broadcast=event_manager.broadcast)
    deleted = await svc.forget_by_id(failure_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Failure not found")
