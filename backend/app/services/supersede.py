"""The Tier-C ``supersede()`` primitive — consolidation's slow path (doc 08 §2.2).

The write-time REPLACES detector fires inside Phase 5, on a relation, inside a
90-day window. A correction discovered later — by dreaming, or by a Tier-C fact
invalidation deciding a memory's every live fact is now closed (§3.4) — needs a
caller that is not the extraction path. This module is that caller: **a new
caller of an unchanged contract, not a new lifecycle.** It writes the one
pointer under the one CHECK, exactly as the detector does.

**The two writers do not collapse into one, and doc 08 says why.** §2.2 names
the guarantee of agreement as ``chk_superseded_has_pointer`` plus the single
pointer — explicitly not a shared function — and says the detector "stays the
fast path" while the primitive "stays the slow path". Three concrete reasons
back that up. The detector issues one set-based statement over N candidates;
this primitive is necessarily per-memory, because it reads the candidate's
status and project and the successor's before it writes, so routing N
candidates through it would turn one statement into N round trips inside
Phase 5's savepoint. The detector's six-rule gate already establishes
everything re-checked here, so these guards would be dead weight on the hot
path. And the promotion blocker deliberately *checks* rather than assumes the
newer-superseder comparison precisely because this module is a second writer;
collapsing to one writer would make that check dead code.

**The primitive never removes a row.** §2.2 requires it to demote dependents
before it would ever remove a referenced memory, and the honest discharge is
that the antecedent is false by construction: every path below issues one
``UPDATE`` and nothing else, so the ``ON DELETE SET NULL`` hazard is
unreachable from here. That is asserted by a scan over this file rather than
merely intended, so a later edit that adds a removal fails the build instead of
aborting a sweep in production.

## Three layers, and why the decision is pure

``decide_status_bridge`` takes already-read values and returns a record
carrying every input that produced it. No session, no clock. Doc 08 §7 makes
every consolidation action undoable from its journalled before/after payload
and the dream digest has to be able to *explain* the bridge's choice; a
three-way outcome derived inside a write is a decision no digest can
reconstruct. Reading the wall clock would additionally make a replay of the
same inputs answer differently. ``adjudicate_status_bridge`` is the impure half
that reads the guards' inputs, mirroring the verification ladder's split. The
writers are the primitive, and this module boundary *is* the enforcement
surface the single-path scan points at — which is why the two provenance reads
live on the repository instead of here.

## Transaction shape

Nothing here commits and nothing opens a session: the primitive runs inside the
caller's transaction, as the write-time detector does. It opens no savepoint
either — Phase 5 made the same call for the fast path, and a consolidation
caller must wrap each memory's application in its own savepoint so one failure
cannot abort a whole cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.events import record_event

logger = logging.getLogger(__name__)

SupersedeReason = Literal[
    "applied",
    "already_superseded",
    "terminal",
    "not_found",
    "cross_project",
    "self_reference",
    "successor_not_newer",
]

# The candidate's own row, locked for the rest of the caller's transaction. The
# lock is what makes every value read here authoritative until commit: no
# concurrent session can flip the row underneath the decision, so the
# journalled "before" cannot be made a lie and the code-level status check in
# front of the write cannot go stale. `superseded_by` rides this select even
# though an active row's pointer is always NULL today, because the journal must
# carry what was read rather than what is true by construction — that is
# exactly the criticism this module levels at the fast path's payload, and a
# rule it exempted itself from would be worth nothing. `created_at` rides it
# because it is the left operand of the ordering predicate below.
_LOCK_CANDIDATE = text("""
    SELECT status,
           CAST(superseded_by AS text) AS superseded_by,
           project,
           created_at
    FROM memories
    WHERE id = CAST(:memory_id AS uuid)
    FOR UPDATE
""")

_READ_SUCCESSOR = text("""
    SELECT CAST(id AS text) AS memory_id, project, created_at
    FROM memories
    WHERE id = CAST(:memory_id AS uuid)
""")

# One statement, always. The CHECK is evaluated once per row per statement, so
# the intermediate state in which the status has moved and the pointer has not
# is not merely unlikely — it has no existence for the constraint to observe.
# Split these into two and the same write raises, which a test provokes
# deliberately rather than taking on trust.
#
# `AND status = 'active'` is defence for a future caller that reaches this
# write without holding the lock above; it is not what the guards below rely
# on, because the locked read already decided the question.
_FLIP_TO_SUPERSEDED = text("""
    UPDATE memories
       SET status = 'superseded',
           superseded_by = CAST(:successor AS uuid)
     WHERE id = CAST(:memory_id AS uuid)
       AND status = 'active'
    RETURNING CAST(id AS text) AS memory_id,
              status,
              CAST(superseded_by AS text) AS superseded_by,
              project,
              updated_at
""")

_FLIP_TO_DEPRECATED = text("""
    UPDATE memories
       SET status = 'deprecated',
           superseded_by = NULL
     WHERE id = CAST(:memory_id AS uuid)
       AND status = 'active'
    RETURNING CAST(id AS text) AS memory_id,
              status,
              CAST(superseded_by AS text) AS superseded_by,
              project,
              updated_at
""")


@dataclass(frozen=True)
class SupersedeResult:
    """What the write did — including, explicitly, when it did nothing.

    A declined action is *reported*, never swallowed. A silently absorbed no-op
    is indistinguishable from a completed one to every caller, which is how a
    bridge that has stopped working goes unnoticed; the digest needs to be able
    to show a refusal and say which one it was.

    ``status`` is the row's status after the call, so on a refusal it is the
    unchanged current value, and it is ``None`` only when no such row exists.
    """

    memory_id: str
    applied: bool
    reason: SupersedeReason
    status: str | None
    superseded_by: str | None


def successor_is_newer(
    *,
    candidate_created_at: datetime,
    candidate_id: UUID | str,
    successor_created_at: datetime,
    successor_id: UUID | str,
) -> bool:
    """Is the proposed superseder strictly newer, ``(created_at, id)``?

    The same ordering the write-time detector's fifth rule enforces, spelled
    once and called from **both** entrances — the bridge's decision and the
    primitive itself — because the primitive is public and a consolidation
    caller may reach it without routing through the bridge. A rule enforced on
    one of two entrances is not enforced.

    Without it two spent memories, each the sole live source of the triple that
    invalidated the other's fact, supersede each other and both leave the
    active view with nothing to put them back. The tie-break matters for the
    same reason it does on the fast path: rows written in one transaction share
    a single server-side ``created_at``, so a bare ``>`` would never fire
    within a batch while a bare ``>=`` would fire in both directions.

    The decisive argument is not symmetry but visibility. The promotion blocker
    recognises a supersession signal only under a strictly newer superseder, so
    a pointer written here over an older one is invisible to it, and the fact
    that memory sources promotes unblocked on evidence the store already knows
    was replaced — a correctness leak with no error and no symptom.

    The accepted cost: fact lifting runs on a cadence and anchors a fact's
    reference time to its source memory's ``created_at``, so a backfilled
    successor genuinely older than the candidate is declined and the candidate
    lingers as active until a later pass. That is under-acting, which is this
    subsystem's stated preferred failure direction.
    """
    if successor_created_at != candidate_created_at:
        return successor_created_at > candidate_created_at
    # Normalised at the boundary: these arrive as UUID from the ORM and as text
    # from the provenance join, and comparing the two spellings would compare
    # nothing meaningful. UUID orders by the same big-endian bytes Postgres
    # compares, so the tie-break agrees with the fast path's SQL.
    return UUID(str(successor_id)) > UUID(str(candidate_id))


def _refusal_for_status(status: str) -> SupersedeReason:
    return "already_superseded" if status == "superseded" else "terminal"


async def _locked_candidate(session: AsyncSession, memory_id: UUID | str) -> dict | None:
    result = await session.execute(_LOCK_CANDIDATE, {"memory_id": str(memory_id)})
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def _journal(
    session: AsyncSession,
    *,
    event_type: str,
    memory_id: UUID | str,
    project: str,
    before: dict,
    after: dict,
    invalidating_fact_id: UUID | str | None,
) -> None:
    """One row per real transition, and never one per no-op.

    ``events`` is append-only, so "a row means a transition" has to be true by
    construction rather than by every future reader remembering to filter. This
    runs only after the write returned a row, and it never gates that write: a
    journal failure must not undo the transition it describes.
    """
    await record_event(
        session,
        event_type=event_type,
        object_type="memory",
        object_id=UUID(str(memory_id)),
        project=project,
        payload={
            "before": before,
            "after": after,
            "reason": "status_bridge",
            "invalidating_fact_id": (
                str(invalidating_fact_id) if invalidating_fact_id is not None else None
            ),
        },
    )


async def supersede(
    session: AsyncSession,
    *,
    memory_id: UUID | str,
    superseded_by: UUID | str,
    invalidating_fact_id: UUID | str | None = None,
) -> SupersedeResult:
    """Flip a memory to ``superseded`` with its pointer, atomically.

    Monotonic: a memory that has already left ``active`` is never re-pointed
    and never reverted. Re-pointing a ``superseded`` row would silently rewrite
    a lineage the digest has already reported, and ``deprecated`` is terminal
    in the documented lifecycle — the same rule the fast path's second guard
    applies, reached by a second path.

    **A refusal about the candidate outranks one about its proposed pointer.**
    The candidate's own status is decided first, before the successor is read
    and before the ordering predicate is evaluated at all, so a non-active
    candidate reports the status reason deterministically whatever the
    timestamps say. The candidate is the row being written; a refusal about
    that row is the more specific answer.

    ``not_found`` covers both rows: a candidate that does not exist, and a
    named successor that does not, which the self-FK would otherwise reject at
    the write. ``status`` disambiguates them — it is ``None`` in the first case
    and the candidate's unchanged status in the second.
    """
    candidate = await _locked_candidate(session, memory_id)
    if candidate is None:
        return SupersedeResult(
            memory_id=str(memory_id),
            applied=False,
            reason="not_found",
            status=None,
            superseded_by=None,
        )

    def declined(reason: SupersedeReason) -> SupersedeResult:
        return SupersedeResult(
            memory_id=str(memory_id),
            applied=False,
            reason=reason,
            status=candidate["status"],
            superseded_by=candidate["superseded_by"],
        )

    if candidate["status"] != "active":
        return declined(_refusal_for_status(candidate["status"]))

    if UUID(str(superseded_by)) == UUID(str(memory_id)):
        return declined("self_reference")

    successor_row = await session.execute(
        _READ_SUCCESSOR, {"memory_id": str(superseded_by)}
    )
    successor = successor_row.mappings().first()
    if successor is None:
        return declined("not_found")

    if successor["project"] != candidate["project"]:
        return declined("cross_project")

    if not successor_is_newer(
        candidate_created_at=candidate["created_at"],
        candidate_id=memory_id,
        successor_created_at=successor["created_at"],
        successor_id=successor["memory_id"],
    ):
        return declined("successor_not_newer")

    written = await session.execute(
        _FLIP_TO_SUPERSEDED,
        {"memory_id": str(memory_id), "successor": str(superseded_by)},
    )
    row = written.mappings().first()
    if row is None:
        return declined(_refusal_for_status(candidate["status"]))

    await _journal(
        session,
        event_type="superseded",
        memory_id=memory_id,
        project=candidate["project"],
        before={
            "status": candidate["status"],
            "superseded_by": candidate["superseded_by"],
        },
        after={"status": "superseded", "superseded_by": row["superseded_by"]},
        invalidating_fact_id=invalidating_fact_id,
    )
    return SupersedeResult(
        memory_id=row["memory_id"],
        applied=True,
        reason="applied",
        status=row["status"],
        superseded_by=row["superseded_by"],
    )


async def deprecate(
    session: AsyncSession,
    *,
    memory_id: UUID | str,
    invalidating_fact_id: UUID | str | None = None,
) -> SupersedeResult:
    """Retire a spent memory that has no single live successor to point at.

    ``superseded_by`` stays NULL, which is the honest record of "retired
    without a single live successor" rather than a workaround for a pointer we
    could not compute.

    Monotonic in the direction that matters most: this declines a
    ``superseded`` row rather than nulling its pointer, because nulling it
    would *revert* a supersession, and the bridge only ever adds one.
    """
    candidate = await _locked_candidate(session, memory_id)
    if candidate is None:
        return SupersedeResult(
            memory_id=str(memory_id),
            applied=False,
            reason="not_found",
            status=None,
            superseded_by=None,
        )

    if candidate["status"] != "active":
        return SupersedeResult(
            memory_id=str(memory_id),
            applied=False,
            reason=_refusal_for_status(candidate["status"]),
            status=candidate["status"],
            superseded_by=candidate["superseded_by"],
        )

    written = await session.execute(_FLIP_TO_DEPRECATED, {"memory_id": str(memory_id)})
    row = written.mappings().first()
    if row is None:
        return SupersedeResult(
            memory_id=str(memory_id),
            applied=False,
            reason=_refusal_for_status(candidate["status"]),
            status=candidate["status"],
            superseded_by=candidate["superseded_by"],
        )

    await _journal(
        session,
        event_type="deprecated",
        memory_id=memory_id,
        project=candidate["project"],
        before={
            "status": candidate["status"],
            "superseded_by": candidate["superseded_by"],
        },
        after={"status": "deprecated", "superseded_by": None},
        invalidating_fact_id=invalidating_fact_id,
    )
    return SupersedeResult(
        memory_id=row["memory_id"],
        applied=True,
        reason="applied",
        status=row["status"],
        superseded_by=row["superseded_by"],
    )
