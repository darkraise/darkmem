"""REPLACES-supersession detector.

When a newly ingested memory carries a high-confidence REPLACES relation
("we switched from X to Y"), this module finds same-project, still-active
memories that mention the deprecated technology X and flips their status
to 'superseded' with a pointer to the new memory.

Guards that must all pass before a candidate is flipped (see
`fine-tuning/SCHEMA_V2_PLAN.md` Phase 5.3):

1. Same project as the new memory.
2. Candidate status is 'active'.
3. Candidate's `technologies` array contains the deprecated target name
   (GIN-indexed, cheap).
4. Candidate is younger than SUPERSESSION_WINDOW_DAYS.
5. The source memory text does not use speculative phrasing (acts as the
   per-relation confidence gate until the extractor emits one).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.services.relations import (
    SPECULATIVE_REPLACES_MARKERS,
    SUPERSESSION_WINDOW_DAYS,
)


def is_speculative(text: str | None) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(marker in low for marker in SPECULATIVE_REPLACES_MARKERS)


async def detect_supersessions(
    session: AsyncSession,
    *,
    new_memory_id: UUID,
    new_memory_text: str | None,
    project: str,
    new_relations: list[dict],
    now: datetime | None = None,
) -> list[UUID]:
    """Mark same-project active memories as superseded by ``new_memory_id``.

    Returns the list of old memory ids that were flipped.

    Safe to call inside an existing transaction; callers commit.
    """
    if is_speculative(new_memory_text):
        return []

    # Lowercase the target so the overlap check survives canonical_map case
    # drift: `memories.technologies` are stored lowercase by the pipeline.
    replaces_targets: list[str] = []
    for rel in new_relations or []:
        if rel.get("type") != "REPLACES":
            continue
        target = rel.get("target")
        if isinstance(target, str) and target:
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
