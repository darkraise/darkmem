"""REPLACES-supersession detector.

When a newly ingested memory carries a high-confidence REPLACES relation
("we switched from X to Y"), this module finds same-project, still-active
memories that mention the deprecated technology X and flips their status
to 'superseded' with a pointer to the new memory.

Guards that must all pass before a candidate is flipped:

1. Same project as the new memory.
2. Candidate status is 'active'.
3. Candidate's `technologies` array contains the deprecated target name
   (GIN-indexed, cheap).
4. Candidate is younger than SUPERSESSION_WINDOW_DAYS.
5. The source memory text does not use speculative phrasing (acts as the
   per-relation confidence gate until the extractor emits one).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.services.relations import (
    SPECULATIVE_REPLACES_MARKERS,
    SUPERSESSION_WINDOW_DAYS,
)

_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")


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


async def detect_supersessions(
    session: AsyncSession,
    *,
    new_memory_id: UUID,
    new_memory_text: str | None,
    new_memory_created_at: datetime,
    project: str,
    new_relations: list[dict],
    now: datetime | None = None,
) -> list[UUID]:
    """Mark same-project active memories as superseded by ``new_memory_id``.

    Returns the list of old memory ids that were flipped.

    Candidates must be strictly older than ``new_memory_created_at``.
    Without this guard, two memories that both carry the same REPLACES
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
        if rel.get("type") != "REPLACES":
            continue
        target = rel.get("target")
        if isinstance(target, str) and target and not _replacement_is_speculative(new_memory_text, target):
            replaces_targets.append(target.lower())
    if not replaces_targets:
        return []

    reference = now or datetime.now(timezone.utc)
    cutoff = reference - timedelta(days=SUPERSESSION_WINDOW_DAYS)

    stmt = (
        select(Memory.id)
        .where(Memory.project == project)
        .where(Memory.status == "active")
        .where(Memory.created_at >= cutoff)
        .where(Memory.created_at < new_memory_created_at)
        .where(Memory.id != new_memory_id)
        .where(Memory.technologies.overlap(replaces_targets))
    )
    rows = await session.execute(stmt)
    old_ids = [row[0] for row in rows.all()]
    if not old_ids:
        return []

    await session.execute(
        update(Memory)
        .where(Memory.id.in_(old_ids))
        .values(status="superseded", superseded_by=new_memory_id)
    )
    return old_ids
