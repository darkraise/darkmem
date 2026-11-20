"""REPLACES-family supersession detector.

When a newly ingested memory carries a high-confidence replacement relation
("we switched from X to Y"), this module finds same-project, still-active
memories that mention the deprecated technology X and flips their status
to 'superseded' with a pointer to the new memory.

Guards that must all pass before a candidate is flipped (doc 08 §2.1):

1. Same project as the new memory.
2. Candidate status is 'active'.
3. Candidate's `technologies` array overlaps the lowercased target names
   (GIN-indexed, cheap).
4. Candidate is inside the SUPERSESSION_WINDOW_DAYS look-back window.
5. Candidate is strictly older, with an `(created_at, id)` tie-break.
6. The clause asserting the replacement does not use speculative phrasing
   (acts as the per-relation confidence gate until the extractor emits one).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.services.events import record_event
from app.services.relations import (
    SPECULATIVE_REPLACES_MARKERS,
    SUPERSESSION_WINDOW_DAYS,
    family_key,
)

_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")


def is_supersession_trigger(rel_type: str | None) -> bool:
    """True for the REPLACES family — REPLACES, IMPROVES_ON, legacy BUILDS_ON.

    The Phase-5 call site and the detector below must agree on this predicate
    exactly: the pipeline uses it to decide whether to call the detector at
    all, so widening only one side leaves a relation that the pipeline never
    forwards or that the detector then discards.
    """
    return family_key(rel_type or "") == "REPLACES"


def is_speculative(text: str | None) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(marker in low for marker in SPECULATIVE_REPLACES_MARKERS)


def _replacement_is_speculative(text: str | None, target: str) -> bool:
    """True when a clause mentioning ``target`` carries a speculative marker.

    Scopes the speculative gate to the replacement clause so an unrelated
    speculative aside elsewhere in the memory ("we might also try Kafka") does
    not suppress a definitive replacement of ``target``. Falls back to the
    whole-text check when the target isn't located in any sentence.
    """
    if not text:
        return False
    low_target = target.lower()
    mentioning = [s for s in _SENTENCE_SPLIT.split(text) if low_target in s.lower()]
    if not mentioning:
        return is_speculative(text)
    return any(is_speculative(s) for s in mentioning)


def candidate_stmt(
    *,
    new_memory_id: UUID,
    new_memory_created_at: datetime,
    project: str,
    replaces_targets: list[str],
    cutoff: datetime,
):
    """The candidate SELECT, extracted so its query plan is checkable.

    ``memories.technologies`` is denormalised and GIN-indexed precisely so the
    overlap guard below is an index scan rather than a join against
    ``entities``; a test EXPLAINs this statement to prove the index is reached,
    which is only meaningful while the tested statement is the executed one.
    """
    return (
        select(Memory.id)
        .where(Memory.project == project)
        .where(Memory.status == "active")
        .where(Memory.created_at >= cutoff)
        # Strictly-older, with a deterministic id tie-break for equal timestamps.
        # Same-batch memories share an identical server-side created_at (one
        # transaction), so a bare `<` never fires within a batch; the id tie-break
        # lets exactly one of an equal-timestamp pair supersede the other, which
        # both enables within-batch supersession and preserves the no-mutual-flip
        # guarantee the strict guard was added for.
        .where(
            or_(
                Memory.created_at < new_memory_created_at,
                and_(
                    Memory.created_at == new_memory_created_at,
                    Memory.id < new_memory_id,
                ),
            )
        )
        .where(Memory.id != new_memory_id)
        .where(Memory.technologies.overlap(replaces_targets))
    )


async def demote_dependents(
    session: AsyncSession, memory_ids: Sequence[UUID | str]
) -> None:
    """Clear the supersession pointer of everything pointing at ``memory_ids``.

    ``fk_memories_superseded_by`` is ON DELETE SET NULL, so deleting a
    superseding memory nulls its dependents' ``superseded_by`` while their
    status stays 'superseded' — violating ``chk_superseded_has_pointer`` and
    aborting the whole statement, which in the TTL sweep means no expired row
    is ever reclaimed. Every delete path must call this FIRST, in the same
    transaction. It is one function rather than a copy per caller so the two
    orders can never drift apart (doc 08 §2.3).
    """
    ids = [str(m) for m in memory_ids]
    if not ids:
        return
    await session.execute(
        text(
            "UPDATE memories SET status='deprecated', superseded_by=NULL "
            "WHERE superseded_by = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": ids},
    )


async def detect_supersessions(
    session: AsyncSession,
    *,
    new_memory_id: UUID,
    new_memory_text: str | None,
    new_memory_created_at: datetime,
    project: str,
    new_relations: list[dict],
    now: datetime | None = None,
    candidate_memory_ids: list[UUID] | None = None,
    excluded_memory_ids: list[UUID] | None = None,
) -> list[UUID]:
    """Mark same-project active memories as superseded by ``new_memory_id``.

    Returns the list of old memory ids that were flipped.

    Candidates must be strictly older than ``new_memory_created_at``.
    Without this guard, two memories that both carry the same replacement
    relation will supersede each other when both are processed (a
    bidirectional flip during reprocess), making both vanish from the
    default ``status='active'`` view.

    Safe to call inside an existing transaction; callers commit.
    """
    # Lowercase the target so the overlap check survives canonical_map case
    # drift: `memories.technologies` are stored lowercase by the pipeline.
    # The speculative gate is scoped per-target to the clause asserting the
    # replacement, not the whole memory, so a definitive replacement still
    # fires even when the memory speculates about something unrelated.
    replaces_targets: list[str] = []
    for rel in new_relations or []:
        if not is_supersession_trigger(rel.get("type")):
            continue
        target = rel.get("target")
        if isinstance(target, str) and target and not _replacement_is_speculative(new_memory_text, target):
            replaces_targets.append(target.lower())
    if not replaces_targets:
        return []

    reference = now or datetime.now(timezone.utc)
    cutoff = reference - timedelta(days=SUPERSESSION_WINDOW_DAYS)

    stmt = candidate_stmt(
        new_memory_id=new_memory_id,
        new_memory_created_at=new_memory_created_at,
        project=project,
        replaces_targets=replaces_targets,
        cutoff=cutoff,
    )
    if candidate_memory_ids is not None:
        stmt = stmt.where(Memory.id.in_(candidate_memory_ids))
    if excluded_memory_ids:
        stmt = stmt.where(Memory.id.not_in(excluded_memory_ids))
    rows = await session.execute(stmt)
    old_ids = [row[0] for row in rows.all()]
    if not old_ids:
        return []

    # The status predicate is re-checked after a concurrent writer's commit, so
    # a candidate another memory superseded in the meantime is left alone.
    flipped = await session.execute(
        update(Memory)
        .where(Memory.id.in_(old_ids))
        .where(Memory.status == "active")
        .values(status="superseded", superseded_by=new_memory_id)
        .returning(Memory.id)
    )
    returned = set(flipped.scalars().all())
    old_ids = [memory_id for memory_id in old_ids if memory_id in returned]
    if not old_ids:
        return []

    # One row per flipped memory, before/after the mutation above. A journal
    # failure here (record_event never raises) must not undo the supersession
    # it is describing, so this always runs after the UPDATE, never gates it.
    for old_id in old_ids:
        await record_event(
            session,
            event_type="superseded",
            object_type="memory",
            object_id=old_id,
            project=project,
            payload={
                "before": {"status": "active"},
                "after": {"status": "superseded", "superseded_by": str(new_memory_id)},
            },
        )

    return old_ids
