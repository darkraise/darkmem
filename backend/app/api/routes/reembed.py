"""Re-embed API routes.

After the per-fingerprint redesign these endpoints are a missing-fingerprint
backfill: they look for memories/entities/code chunks whose vector for the
active embedder partition does not yet exist, and produce one.

The obsolete listings are deliberately deployment-wide — every project and every
lifecycle state needs a vector under the active embedder, exactly as the write
path does — and `partition_missing` is what keeps that honest: when the active
partition is absent no row can be singled out, so the count stays exact and the
enumeration is withheld rather than paging the whole table. The decision and its
reasoning live in `app.services.content_surfaces`.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import refuse_when_read_only
from app.api.auth import require_auth
from app.api.websocket import event_manager
from app.utils.background import spawn
from app.services.llm import lease_llm, spawn_with_llm
from app.database import async_session_factory, get_session
from app.services.feature_flags import get_feature_flags_dict
from app.services.usage_recorder import UsageSubject, subject_scope
from app.services.reembed import (
    CachePruneFingerprintUnresolved,
    ReembedService,
    reembed_locks,
)
from app.repositories.vector import (
    EmbedderFingerprintUnresolved,
    PostgresVectorRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reembed", tags=["reembed"])


async def _get_flags() -> dict:
    """Fetch feature flags in a fresh session (for background tasks)."""
    async with async_session_factory() as session:
        return await get_feature_flags_dict(session)


def _is_sentinel(fingerprint: str) -> bool:
    """``llm_fingerprint()``'s answer while ``dimensions`` is unset."""
    return fingerprint.rsplit("|", 1)[-1] == "0"


async def _read_fingerprint(llm, session: AsyncSession) -> str:
    """The partition the counts, listings and cache prune read against.

    With ``dimensions`` configured this is ``llm_fingerprint()``, as it always
    was. Unset -- which is what the setup wizard writes unless the operator
    types a number -- ``llm_fingerprint()`` is the ``model|0`` sentinel, which
    names no partition: every row counted as "missing a vector" although all
    of them had one, and the cache prune refused. The populated partition for
    the same model is resolved instead (``resolve_read_fingerprint``), and
    with nothing embedded yet the sentinel stands, which counts honestly as
    everything missing.
    """
    configured = llm.llm_fingerprint()
    if not _is_sentinel(configured):
        return configured
    try:
        return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)
    except EmbedderFingerprintUnresolved:
        return configured


# Never stored; it only makes the active embedder name its fingerprint.
_FINGERPRINT_PROBE_TEXT = "darkmem re-embed active-fingerprint probe"


async def _write_fingerprint(llm) -> str:
    """The partition a re-embed fills: the one the active embedder produces.

    Unset ``dimensions`` used to hand the background task the ``model|0``
    sentinel, which it refused ("Embedder fingerprint dims must be
    positive"), so every re-embed failed with an empty journal detail. A
    probe embed names the real one, the way the block sweep's
    ``resolve_active_fingerprint`` does. Only the write doors come here, and
    they refuse in read-only mode.
    """
    configured = llm.llm_fingerprint()
    if not _is_sentinel(configured):
        return configured
    try:
        _, fingerprint = await llm.embed(_FINGERPRINT_PROBE_TEXT)
    except Exception as exc:
        raise HTTPException(
            503, f"The embedder could not be reached to name its partition: {exc}",
        ) from exc
    return fingerprint


def _pipeline_llm(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None or pipeline.llm is None:
        raise HTTPException(503, "Pipeline not initialized")
    return pipeline.llm


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
    fingerprint = await _read_fingerprint(pipeline.llm, session)
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
    fingerprint = await _read_fingerprint(_pipeline_llm(request), session)
    svc = ReembedService(session)
    items, total, partition_missing = await svc.list_obsolete_memories(
        fingerprint, limit=limit, offset=offset,
    )
    return {
        "items": items, "total": total, "limit": limit, "offset": offset,
        "partition_missing": partition_missing,
    }


@router.get("/obsolete/code-chunks")
async def list_obsolete_code_chunks(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = await _read_fingerprint(_pipeline_llm(request), session)
    svc = ReembedService(session)
    items, total, partition_missing = await svc.list_obsolete_code_chunks(
        fingerprint, limit=limit, offset=offset,
    )
    return {
        "items": items, "total": total, "limit": limit, "offset": offset,
        "partition_missing": partition_missing,
    }


@router.get("/obsolete/entities")
async def list_obsolete_entities(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    fingerprint = await _read_fingerprint(_pipeline_llm(request), session)
    svc = ReembedService(session)
    items, total, partition_missing = await svc.list_obsolete_entities(
        fingerprint, limit=limit, offset=offset,
    )
    return {
        "items": items, "total": total, "limit": limit, "offset": offset,
        "partition_missing": partition_missing,
    }


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
        raise HTTPException(status_code=409, detail=f"Re-embed of {category!r} is already running")

    released = False

    def release_category(_task=None):
        nonlocal released
        if not released:
            released = True
            reembed_locks.release(category)

    try:
        with lease_llm(pipeline.llm) as snapshot_llm:
            snapshot_fingerprint = await _write_fingerprint(snapshot_llm)
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
                # Set inside the task, not around its creation: the request
                # scope this was spawned from is long gone by the time the
                # embeds run.
                with subject_scope(UsageSubject(
                    "maintenance", f"reembed_{category}:{batch_id}", None,
                )):
                    from app.services.events import record_maintenance_run
                    try:
                        flags = await _get_flags()
                        async with async_session_factory() as bg_session:
                            bg_svc = ReembedService(bg_session)
                            method = getattr(bg_svc, method_name)
                            result = await method(
                                current_fingerprint=snapshot_fingerprint,
                                llm=snapshot_llm,
                                batch_id=batch_id,
                                broadcast=event_manager.broadcast,
                                flags=flags,
                            )
                        await record_maintenance_run(
                            async_session_factory,
                            operation=f"reembed_{category}",
                            outcome="ok" if not result.get("errors") else "error",
                            detail=result,
                        )
                    except Exception:
                        logger.exception("Re-embed %s background task failed", category)
                        await record_maintenance_run(
                            async_session_factory, operation=f"reembed_{category}", outcome="error",
                        )
                    finally:
                        release_category()

            task = spawn_with_llm(snapshot_llm, _run(), spawn=spawn, name="reembed-category")
            task.add_done_callback(release_category)
    except BaseException:
        release_category()
        raise

    return {"accepted": True, "batch_id": batch_id, "total": total}


@router.post("/memories", status_code=202)
async def reembed_memories(
    request: Request,
    _read_only=Depends(refuse_when_read_only),
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
    _read_only=Depends(refuse_when_read_only),
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
    _read_only=Depends(refuse_when_read_only),
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
    _read_only=Depends(refuse_when_read_only),
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
            raise HTTPException(
                status_code=409,
                detail=f"Re-embed of {cat!r} is already running",
            )

    released = False

    def release_locks(_task=None):
        nonlocal released
        if not released:
            released = True
            for category in ("memories", "entities", "code_chunks"):
                reembed_locks.release(category)

    try:
        with lease_llm(pipeline.llm) as snapshot_llm:
            snapshot_fingerprint = await _write_fingerprint(snapshot_llm)
            batch_id = str(uuid4())

            svc = ReembedService(session)
            totals = await svc.count_missing(snapshot_fingerprint)

            async def _run_all():
                with subject_scope(UsageSubject(
                    "maintenance", f"reembed_all:{batch_id}", None,
                )):
                    from app.services.events import record_maintenance_run
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
                                    result = await method(
                                        current_fingerprint=snapshot_fingerprint,
                                        llm=snapshot_llm,
                                        batch_id=batch_id,
                                        broadcast=event_manager.broadcast,
                                        flags=flags,
                                    )
                                    await record_maintenance_run(
                                        async_session_factory,
                                        operation=f"reembed_{category}",
                                        outcome="ok" if not result.get("errors") else "error",
                                        detail={**result, "batch_id": batch_id},
                                    )
                                except Exception:
                                    logger.exception(
                                        "Re-embed %s failed under batch %s", category, batch_id,
                                    )
                                    await record_maintenance_run(
                                        async_session_factory,
                                        operation=f"reembed_{category}",
                                        outcome="error",
                                        detail={"batch_id": batch_id},
                                    )
                    finally:
                        release_locks()

            task = spawn_with_llm(snapshot_llm, _run_all(), spawn=spawn, name="reembed-all")

            task.add_done_callback(release_locks)
    except BaseException:
        release_locks()
        raise

    return {"accepted": True, "batch_id": batch_id, "totals": totals}


@router.post("/prune-cache")
async def prune_cache(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.events import record_event

    fingerprint = await _read_fingerprint(_pipeline_llm(request), session)
    svc = ReembedService(session)
    try:
        deleted = await svc.prune_obsolete_cache_entries(fingerprint)
    except CachePruneFingerprintUnresolved as exc:
        # A destructive maintenance op that refuses without a trace is
        # invisible to the timeline, so the refusal journals the same
        # operation the successful run does, with deleted=0 to say plainly
        # that nothing was dropped.
        await record_event(
            session,
            event_type="maintenance_run",
            object_type="system",
            payload={
                "operation": "prune_caches",
                "outcome": "error",
                "detail": {
                    "deleted": 0,
                    "fingerprint": fingerprint,
                    "error": str(exc),
                },
            },
        )
        await session.commit()
        raise HTTPException(409, str(exc)) from exc
    # prune_obsolete_cache_entries already committed its own DROP TABLEs, so
    # this journal write rides its own transaction on the same session,
    # committed explicitly here rather than left to the request teardown.
    await record_event(
        session,
        event_type="maintenance_run",
        object_type="system",
        payload={
            "operation": "prune_caches",
            "outcome": "ok",
            "detail": {"deleted": deleted, "fingerprint": fingerprint},
        },
    )
    await session.commit()
    return {"deleted": deleted}
