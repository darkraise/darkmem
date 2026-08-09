"""The hygiene queue REST surface (doc 08 §6, T2.23).

Four read arms (candidate duplicates, low-confidence memories, expiring-soon
rows, superseded lineage) plus three bulk-action doors. See
``app/services/hygiene_queue.py`` for the membership rules, the disjointness
argument against the review queue, and why only three of doc 08's four named
bulk actions are undoable through the T2.13 primitive today.

REST shape follows ``docs/api-rest-conventions.md`` and mirrors T2.22's own
route module: plain GETs for membership, ``require_auth`` on every route (a
curation surface, doc 12). Bulk actions are synchronous (no 202 — nothing here
is a background job) and return 200 with a per-item result body, the same
choice ``dream_digest``'s undo doors make for the same reason: a 204 would
give the caller nothing to act on, and every item's own outcome (including a
refusal) is the point of the response, not an exception.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.hygiene_queue import (
    BulkConfirmDedupRequest,
    BulkPruneRequest,
    BulkSupersedeRequest,
    HygieneBulkActionResponse,
    HygieneCountsResponse,
    HygieneDuplicateListResponse,
    HygieneMemoryListResponse,
)
from app.services import hygiene_queue as hygiene_queue_service

router = APIRouter(prefix="/api/v1/hygiene-queue", tags=["hygiene-queue"])


def _action_response(cycle_id: str, results) -> dict:
    return {
        "cycle_id": cycle_id,
        "results": [
            {
                "id": item.item_id,
                "applied": item.applied,
                "event_id": item.event_id,
                "reason": item.reason,
            }
            for item in results
        ],
    }


@router.get("/duplicates", response_model=HygieneDuplicateListResponse)
async def list_duplicates(
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await hygiene_queue_service.list_duplicates(
        session, project=project, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/low-confidence", response_model=HygieneMemoryListResponse)
async def list_low_confidence(
    project: str | None = None,
    threshold: float = Query(
        default=hygiene_queue_service.DEFAULT_LOW_CONFIDENCE_THRESHOLD, ge=0.0, le=1.0,
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await hygiene_queue_service.list_low_confidence(
        session, project=project, threshold=threshold, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/expiring-soon", response_model=HygieneMemoryListResponse)
async def list_expiring_soon(
    project: str | None = None,
    within_days: int = Query(
        default=hygiene_queue_service.DEFAULT_EXPIRING_SOON_DAYS, ge=0, le=365,
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await hygiene_queue_service.list_expiring_soon(
        session, project=project, within_days=within_days, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/superseded", response_model=HygieneMemoryListResponse)
async def list_superseded(
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await hygiene_queue_service.list_superseded(
        session, project=project, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/counts", response_model=HygieneCountsResponse)
async def counts(
    project: str | None = None,
    threshold: float = Query(
        default=hygiene_queue_service.DEFAULT_LOW_CONFIDENCE_THRESHOLD, ge=0.0, le=1.0,
    ),
    within_days: int = Query(
        default=hygiene_queue_service.DEFAULT_EXPIRING_SOON_DAYS, ge=0, le=365,
    ),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return await hygiene_queue_service.counts(
        session, project=project,
        low_confidence_threshold=threshold, expiring_soon_days=within_days,
    )


@router.post("/bulk/supersede", response_model=HygieneBulkActionResponse)
async def bulk_supersede(
    body: BulkSupersedeRequest,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    cycle_id, results = await hygiene_queue_service.bulk_supersede(
        session,
        [
            {"memory_id": item.memory_id, "superseded_by": item.superseded_by}
            for item in body.items
        ],
        actor=user.sub,
    )
    await session.commit()
    return _action_response(cycle_id, results)


@router.post("/bulk/prune", response_model=HygieneBulkActionResponse)
async def bulk_prune(
    body: BulkPruneRequest,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    cycle_id, results = await hygiene_queue_service.bulk_prune(
        session, [str(memory_id) for memory_id in body.memory_ids], actor=user.sub,
    )
    await session.commit()
    return _action_response(cycle_id, results)


@router.post("/bulk/confirm-dedup", response_model=HygieneBulkActionResponse)
async def bulk_confirm_dedup(
    body: BulkConfirmDedupRequest,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    cycle_id, results = await hygiene_queue_service.bulk_confirm_dedup(
        session,
        [str(relation_id) for relation_id in body.relation_ids],
        actor=user.sub,
    )
    await session.commit()
    return _action_response(cycle_id, results)
