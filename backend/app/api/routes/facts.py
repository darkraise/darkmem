"""The facts read surface (doc 12 §4, doc 13 §5.1, T2.36a).

Provides:
  - GET /api/v1/knowledge/facts        — a page of live facts, each badged
  - GET /api/v1/knowledge/facts/{id}   — one fact with its provenance groups

Read-only, and deliberately so: belief is written by fact lifting and the
verification axis by the ladder's applier. A write here would put a second
writer on an axis whose sole writer is what makes its journal countable. The
human verdict doors live elsewhere for that reason — the review queue's reject,
and T2.05's ratify in ``ratification.py``, which is the only path to
``confirmed``.

Nothing on this surface ranks or filters by verification status by default.
``verification_status`` is a filter the caller opts into; absent it, a
candidate, a disputed and a corroborated fact are listed alike and labelled
apart. That is doc 08 §6's never-a-gate rule applied to a browsing read.

The filter matches the status each row is **served** with, not the column
behind it — while a claim gate is closed the two differ, and a filter on the
column would let two requests recover per fact the rung the label withholds.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.schemas.facts import FactDetailResponse, FactListResponse
from app.services import facts_read

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/facts", response_model=FactListResponse)
async def list_facts(
    project: str | None = None,
    subject_name: str | None = None,
    rel_type: str | None = None,
    object_name: str | None = None,
    verification_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    items, total = await facts_read.list_facts(
        session,
        project=project,
        subject_name=subject_name,
        rel_type=rel_type,
        object_name=object_name,
        served_status=verification_status,
        limit=limit,
        offset=offset,
    )
    facets = await facts_read.fact_facets(session, project=project)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "facets": facets,
    }


@router.get("/facts/{fact_id}", response_model=FactDetailResponse)
async def get_fact(
    fact_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    item = await facts_read.get_fact(session, fact_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return item
