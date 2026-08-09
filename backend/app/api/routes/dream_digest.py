"""The dream digest read surface and its two undo doors (doc 08 §7).

Undo is authenticated: it is a curation action (doc 12), so every route here
takes ``require_auth`` and the journal records ``user.sub`` as the actor.

Both POSTs answer **409** with every failing action and its reason — the
convention for "the resource is in a conflicting state" — rather than 200 with
a partial result, because a partial result is the one thing this primitive
refuses to represent. 200-with-a-body rather than 204 because the digest
re-renders from the response and a 204 would give the UI nothing to mark
undone with.

**The rollback obligation is discharged structurally here.** ``dream_undo``
owns no savepoint and cannot roll itself back; any raise other than
``UndoRefused`` leaves restores in the session. ``get_session`` rolls back on
an unhandled exception, so letting everything but ``UndoRefused`` propagate is
what makes this door correct — and ``UndoRefused`` is caught precisely because
it is the one raise that guarantees nothing was written.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.dream_digest import (
    DreamCycleDigest,
    DreamCycleListResponse,
    UndoBatchResponse,
    UndoRequest,
)
from app.services import dream_digest, dream_undo

router = APIRouter(prefix="/api/v1/dream-digest", tags=["dream-digest"])


def _blocked_detail(refusal: dream_undo.UndoRefused) -> list[dict]:
    """Every failing action and its reason, as a **list**.

    `app/main.py`'s error handler surfaces a list `detail` on
    `error.details` and flattens anything else to a generic message, so the
    list is what actually reaches the client. Widening that handler to carry a
    structured message would touch every route's error path and is not this
    task's to make.
    """
    return [
        {"event_id": item.event_id, "action": item.action, "reason": item.reason}
        for item in refusal.blocked
    ]


async def _undo(session: AsyncSession, event_ids: list[int], *, actor: str) -> dict:
    try:
        batch = await dream_undo.undo(session, event_ids=event_ids, actor=actor)
    except dream_undo.UndoActionNotFound as missing:
        raise HTTPException(
            status_code=404,
            detail=(
                "no dream action for event id(s) "
                f"{list(missing.missing_event_ids)}"
            ),
        )
    except dream_undo.UndoRefused as refusal:
        # The one raise that guarantees nothing was written, which is why it is
        # safe to convert into a response instead of letting the session's
        # rollback handle it.
        raise HTTPException(status_code=409, detail=_blocked_detail(refusal))
    return {
        "undo_batch_id": batch.undo_batch_id,
        "undone": [
            {
                "event_id": item.event_id,
                "action": item.action,
                "object_id": item.object_id,
                "restored": list(item.restored),
                "not_restored": list(item.not_restored),
            }
            for item in batch.undone
        ],
    }


@router.get("/cycles", response_model=DreamCycleListResponse)
async def list_cycles(
    project: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=dream_digest.MAX_CYCLE_LIMIT),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await dream_digest.list_cycles(
        session, project=project, since=since, until=until,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/cycles/{cycle_id}", response_model=DreamCycleDigest)
async def read_cycle(
    cycle_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    actions = await dream_digest.read_cycle_actions(
        session, cycle_id, since=since, until=until
    )
    if not actions:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return dream_digest.digest_of(
        cycle_id, await dream_digest.annotate_undoability(session, actions)
    )


@router.post("/actions/{event_id}/undo", response_model=UndoBatchResponse)
async def undo_action(
    event_id: int,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """The batch of one. There is no single-action code path behind it."""
    return await _undo(session, [event_id], actor=user.sub)


@router.post("/cycles/{cycle_id}/undo", response_model=UndoBatchResponse)
async def undo_cycle(
    cycle_id: str,
    body: UndoRequest | None = None,
    user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Undo a cycle, or a named subset of it.

    A subset is a *different batch*, not a partial one: whatever set this
    request names is undone in full or not at all. Scoped to the request rather
    than to the cycle because the alternative reading — that a cycle is the
    only legal batch — would make a per-item bulk action unbuildable on this
    primitive.

    **The already-undone prefilter applies only to the body-less whole-cycle
    form.** There it is what the request means — *undo what is left of this
    cycle* — and skipping the rest is defensible. Applied to a request that
    *names* its actions it is a silent shrink of an explicitly named set: two
    curators race, the second submits a set containing one the first already
    undid, and a prefilter answers 200 with contents that differ from the
    request instead of the 409-then-refetch flow the digest is built around.
    The primitive would refuse that set on `already_undone`; a prefilter here
    defeats it. So a named set goes through whole and the primitive decides.
    """
    actions = await dream_digest.read_cycle_actions(session, cycle_id)
    if not actions:
        raise HTTPException(status_code=404, detail="Cycle not found")

    names_a_subset = body is not None and (
        body.action is not None or body.event_ids is not None
    )
    selected = actions if names_a_subset else [
        view for view in actions if not view.undone
    ]
    if body is not None and body.action is not None:
        selected = [view for view in selected if view.action == body.action]
    if body is not None and body.event_ids is not None:
        in_cycle = {view.event_id for view in selected}
        # An id this cycle does not hold is refused rather than dropped, for
        # the same reason an already-undone one is: the caller named it.
        stray = sorted(set(body.event_ids) - in_cycle)
        if stray:
            raise HTTPException(
                status_code=404,
                detail=f"event id(s) {stray} are not in this cycle",
            )
        named = set(body.event_ids)
        selected = [view for view in selected if view.event_id in named]
    if not selected:
        raise HTTPException(
            status_code=404, detail="No undoable action matched the request"
        )
    return await _undo(
        session, [view.event_id for view in selected], actor=user.sub
    )
