"""Session checkpoints — the store half (spec §Feature-2, T3.16).

A checkpoint is one agent run's note to its successor: a compact ``summary``
and a structured ``next_steps`` list, keyed on the ``origin_key`` capture
already stamps for that run (T1.11). T3.17 turns the latest one into a
budgeted resume block; this module only stores and fetches.

**One writer for both doors.** REST and MCP are two transports over this
module, never two implementations — invariant 17 is two-door parity, and the
way parity survives a later change is that there is only one behaviour to
change. ``tests/test_door_parity.py`` asserts it from the outside; this
module's single-writer shape is what makes the assertion cheap to keep true.

**Bounds are enforced here and in the database, deliberately twice.** The
schema layer refuses an oversized payload with a 422 a caller can act on; the
CHECK constraints refuse it whatever route reached the table. Neither is
redundant: the first is the good error message, the second is the guarantee.

**No verification status, and no route into the vault.** A checkpoint is what
an agent said about its own run — nothing corroborated it, so it carries no
rung, and it is not a memory. T3.18 owns that rule as an invariant; the
absence of any capture call in this module is what implements it today.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkpoint import SessionCheckpoint
from app.services.events import record_event

__all__ = [
    "CHECKPOINT_SAVED_EVENT",
    "MAX_NEXT_STEPS",
    "MAX_STEP_LENGTH",
    "MAX_SUMMARY_LENGTH",
    "latest_checkpoint",
    "save_checkpoint",
]

CHECKPOINT_SAVED_EVENT = "checkpoint_saved"
OBJECT_TYPE = "checkpoint"

# The bounds the done-when asks for. Mirrored by CHECK constraints in the
# baseline; these produce the 422, those produce the guarantee.
MAX_SUMMARY_LENGTH = 4000
MAX_NEXT_STEPS = 50
MAX_STEP_LENGTH = 500


async def save_checkpoint(
    session: AsyncSession,
    *,
    origin_key: str,
    summary: str,
    next_steps: list[str] | None = None,
    project: str = "default",
    actor: str | None = None,
) -> SessionCheckpoint:
    """Store one checkpoint and journal it. Does not commit.

    Append-only by design: a run that saves twice keeps both rows, and
    ``latest_checkpoint`` reads the newer. Overwriting in place would make the
    checkpoint stream unreconstructable — a resume that loaded the wrong note
    could not be explained afterwards — and the row is small enough that
    keeping the history costs nothing worth the loss.

    The journal row is best-effort, unlike a verification transition: no metric
    is SQL over these events, so a checkpoint that saved but did not journal is
    a lost log line rather than a corrupted denominator. ``record_event``'s
    ordinary never-raises contract is therefore the right one here, and the
    return is deliberately ignored (see CLAUDE.md's events section for the four
    callers where it is not).
    """
    row = SessionCheckpoint(
        id=uuid4(),
        origin_key=origin_key,
        project=project,
        summary=summary,
        next_steps=list(next_steps or []),
    )
    session.add(row)
    await session.flush()

    await record_event(
        session,
        event_type=CHECKPOINT_SAVED_EVENT,
        object_type=OBJECT_TYPE,
        object_id=row.id,
        project=project,
        actor=actor,
        # The summary is not copied into the payload. Write-time minimization
        # is the standing rule (CLAUDE.md, events journal): the row itself
        # holds the text, the journal needs only that a checkpoint happened
        # and how big it was, and an event payload outlives deletion of what
        # it describes.
        payload={"origin_key": origin_key, "next_steps": len(row.next_steps)},
    )
    return row


async def latest_checkpoint(
    session: AsyncSession, *, origin_key: str, project: str = "default"
) -> SessionCheckpoint | None:
    """The newest checkpoint for one agent run, or ``None``.

    One indexed query, which is the done-when: ``ix_session_checkpoints_latest``
    is ``(project, origin_key, created_at DESC, id DESC)``, so this is a
    one-row index scan and not a sort over the run's history. The ``id``
    tie-break is not decoration — two checkpoints saved inside one transaction
    share ``now()``, and without it "latest" would be whichever the planner
    happened to return.
    """
    statement = (
        select(SessionCheckpoint)
        .where(
            SessionCheckpoint.project == project,
            SessionCheckpoint.origin_key == origin_key,
        )
        .order_by(
            SessionCheckpoint.created_at.desc(),
            SessionCheckpoint.id.desc(),
        )
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


def serialize(row: SessionCheckpoint) -> dict[str, Any]:
    """The wire shape both doors serve, so they cannot drift into two."""
    return {
        "id": str(row.id),
        "origin_key": row.origin_key,
        "project": row.project,
        "summary": row.summary,
        "next_steps": list(row.next_steps or []),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
