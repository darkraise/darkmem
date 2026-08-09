"""Wire shapes for the dream digest and its undo doors (doc 08 §7, 13 §6.3)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DreamCycleSummary(BaseModel):
    cycle_id: str
    started_at: datetime
    ended_at: datetime
    projects: list[str]
    total: int
    counts: dict[str, int]
    undone_count: int
    # None for an automated dreaming tick; names the human surface (e.g.
    # "hygiene_queue") that ran the batch otherwise. Homogeneous per cycle.
    origin: str | None = None


class DreamCycleListResponse(BaseModel):
    items: list[DreamCycleSummary]
    total: int
    limit: int
    offset: int


class DreamAction(BaseModel):
    event_id: int
    created_at: datetime
    action: str
    object_id: str
    project: str | None = None
    # Absent for an action carrying `origin` — that action came from a human
    # curation surface, not a detector, and rendering "dedup" for it would be
    # a false provenance claim (see app/services/dream_digest.py).
    detector: str | None = None
    origin: str | None = None
    actor: str | None = None
    before: dict
    after: dict
    detail: dict
    undone: bool
    undone_at: datetime | None = None
    undone_by: str | None = None
    undo_batch_id: str | None = None
    # The undo's own two lists, reconstructed from the `undone` event's payload
    # rather than re-stored here — see app/services/dream_digest.py. Empty for
    # an action that has not been undone; `undone` is what disambiguates that
    # from "undone but restored nothing", which the inverses never produce.
    restored: list[str] = Field(default_factory=list)
    not_restored: list[str] = Field(default_factory=list)
    # Advisory. The door re-runs the same predicate under its locks and answers
    # 409 when they disagree, so a client handles a 409 by re-fetching rather
    # than by trusting its last render.
    undoable: bool
    undo_blocked_reason: str | None = None


class DreamObjectGroup(BaseModel):
    object_id: str
    project: str | None = None
    actions: list[DreamAction]


class DreamCycleDigest(BaseModel):
    cycle_id: str
    started_at: datetime
    ended_at: datetime
    counts: dict[str, int]
    undone_count: int
    objects: list[DreamObjectGroup]


class UndoRequest(BaseModel):
    """Names a subset of a cycle. Whatever set it names is undone in full or
    not at all — a subset is a different batch, not a partial one."""

    action: str | None = None
    event_ids: list[int] | None = None


class UndoneAction(BaseModel):
    event_id: int
    action: str
    object_id: str
    restored: list[str]
    not_restored: list[str] = Field(
        description=(
            "State this undo deliberately did not restore, either because it "
            "is physically unrestorable or because restoring it would undo the "
            "undo. Reported rather than left unmentioned."
        )
    )


class UndoBatchResponse(BaseModel):
    undo_batch_id: str
    undone: list[UndoneAction]


class BlockedAction(BaseModel):
    event_id: int
    action: str
    reason: str


# A 409's body is the app's standard error envelope; `error.details` carries a
# list of these, one per action that can no longer be undone.
