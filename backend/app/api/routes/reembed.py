"""Re-embed API routes.

After the per-fingerprint redesign these endpoints are a missing-fingerprint
backfill: they look for memories/entities/code chunks whose vector for the
active embedder partition does not yet exist, and produce one.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.websocket import event_manager
from app.utils.background import spawn
from app.database import async_session_factory, get_session
from app.services.reembed import ReembedService, reembed_locks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reembed", tags=["reembed"])


async def _get_flags() -> dict:
    """Fetch feature flags in a fresh session (for background tasks)."""
    from app.services.pipeline import _get_feature_flags
    return await _get_feature_flags(async_session_factory)


def _resolve_fingerprint(request: Request) -> str:
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None or pipeline.llm is None:
        raise HTTPException(503, "Pipeline not initialized")
    return pipeline.llm.llm_fingerprint()


@router.get("/obsolete-counts")
async def get_obsolete_counts(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None or pipeline.llm is None:
        return {
            "memories": 0, "code_chunks": 0, "entities": 0,
            "current_fingerprint": "",
        }
    fingerprint = pipeline.llm.llm_fingerprint()
    svc = ReembedService(session)
    counts = await svc.count_missing(fingerprint)
    return {
        **counts,
        "current_fingerprint": fingerprint,
    }


@router.get("/obsolete/memories")
async def list_obsolete_memories(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = _resolve_fingerprint(request)
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_memories(fingerprint, limit=limit, offset=offset)
    return {"items": items, "total": total}


@router.get("/obsolete/code-chunks")
async def list_obsolete_code_chunks(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = _resolve_fingerprint(request)
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_code_chunks(fingerprint, limit=limit, offset=offset)
    return {"items": items, "total": total}


@router.get("/obsolete/entities")
async def list_obsolete_entities(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = _resolve_fingerprint(request)
    svc = ReembedService(session)
    items, total = await svc.list_obsolete_entities(fingerprint, limit=limit, offset=offset)
    return {"items": items, "total": total}


async def _dispatch_single_category(
    category: str,
    pipeline,
    session: AsyncSession,
):
    # Guard the embedder before taking the lock or computing a fingerprint, so a
    # missing LLM surfaces as a clean 503 rather than an AttributeError (and
    # batch_id can never be referenced before assignment).
    if pipeline is None or pipeline.llm is None:
        raise HTTPException(503, "Pipeline not initialized")

    if not reembed_locks.try_acquire(category):
        return JSONResponse(
            status_code=409,
            content={"accepted": False, "reason": "already_running"},
        )

    try:
        snapshot_fingerprint = pipeline.llm.llm_fingerprint()
        snapshot_llm = pipeline.llm
        batch_id = str(uuid4())

        svc = ReembedService(session)
        counts = await svc.count_missing(snapshot_fingerprint)
        total = counts.get(category, 0)

        method_name_map = {
            "memories": "reembed_memories",
            "code_chunks": "reembed_code_chunks",
            "entities": "reembed_entities",
        }
        method_name = method_name_map[category]

        async def _run():
            try:
                flags = await _get_flags()
                async with async_session_factory() as bg_session:
                    bg_svc = ReembedService(bg_session)
                    method = getattr(bg_svc, method_name)
                    await method(
                        current_fingerprint=snapshot_fingerprint,
                        llm=snapshot_llm,
                        batch_id=batch_id,
                        broadcast=event_manager.broadcast,
                        flags=flags,
                    )
            except Exception:
                logger.exception("Re-embed %s background task failed", category)
            finally:
                reembed_locks.release(category)

        spawn(_run(), name="reembed-category")
    except Exception:
        reembed_locks.release(category)
        raise

    return {"accepted": True, "batch_id": batch_id, "total": total}


@router.post("/memories", status_code=202)
async def reembed_memories(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("memories", pipeline, session)


@router.post("/code-chunks", status_code=202)
async def reembed_code_chunks(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("code_chunks", pipeline, session)


@router.post("/entities", status_code=202)
async def reembed_entities(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return await _dispatch_single_category("entities", pipeline, session)


@router.post("/all", status_code=202)
async def reembed_all(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")

    acquired: list[str] = []
    for cat in ("memories", "entities", "code_chunks"):
        if reembed_locks.try_acquire(cat):
            acquired.append(cat)
        else:
            for released in acquired:
                reembed_locks.release(released)
            return JSONResponse(
                status_code=409,
                content={
                    "accepted": False, "reason": "already_running",
                    "conflict_category": cat,
                },
            )

    try:
        snapshot_fingerprint = pipeline.llm.llm_fingerprint()
        snapshot_llm = pipeline.llm
        batch_id = str(uuid4())

        svc = ReembedService(session)
        totals = await svc.count_missing(snapshot_fingerprint)

        async def _run_all():
            try:
                flags = await _get_flags()
                async with async_session_factory() as bg_session:
                    bg_svc = ReembedService(bg_session)
                    sequence = [
                        ("memories", bg_svc.reembed_memories),
                        ("entities", bg_svc.reembed_entities),
                        ("code_chunks", bg_svc.reembed_code_chunks),
                    ]
                    for category, method in sequence:
                        try:
                            await method(
                                current_fingerprint=snapshot_fingerprint,
                                llm=snapshot_llm,
                                batch_id=batch_id,
                                broadcast=event_manager.broadcast,
                                flags=flags,
                            )
                        except Exception:
                            logger.exception(
                                "Re-embed %s failed under batch %s", category, batch_id,
                            )
            finally:
                for cat in ("memories", "entities", "code_chunks"):
                    reembed_locks.release(cat)

        spawn(_run_all(), name="reembed-all")
    except Exception:
        for cat in ("memories", "entities", "code_chunks"):
            reembed_locks.release(cat)
        raise

    return {"accepted": True, "batch_id": batch_id, "totals": totals}


@router.post("/prune-cache")
async def prune_cache(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = _resolve_fingerprint(request)
    svc = ReembedService(session)
    deleted = await svc.prune_obsolete_cache_entries(fingerprint)
    return {"deleted": deleted}
