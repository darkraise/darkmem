"""The one reader of a fact's latest ``verified`` journal entry (T2.43, D8).

Two surfaces need the same row: the review queue lists a disputed fact with
the decision evidence a human adjudicates against, and doc 07 §5's composition
serves that same fact labelled with both sides. Both read the most recent
``verified`` event per fact and neither may re-derive the finding — the
deterministic scan's sole legitimate caller is the ladder's applier, enforced
tree-wide, so a retrieval surface owning its own scan is forbidden by
construction rather than merely discouraged.

This module exists so there is **one** reader instead of two. Two readers of
one journal shape is precisely how this epic acquired three ranking
implementations; the second copy is always cheap to write and always the one
that drifts.

**What the caller must not infer from the block's absence.** ``contradiction``
is written where the finding was already in scope, and is absent on a
recovery, on a caller-overridden verdict, and on any dispute predating the
commit that started writing it. Absent means "no scan produced one here", never
"no counterpart exists" — the three causes are not distinguishable from the
journal, so no consumer may pretend to distinguish them.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["CONTRADICTION_EVIDENCE_KEY", "latest_verified_evidence"]

# The payload key the applier writes its counterpart block under. A nested
# block rather than sibling keys, so the closed top-level payload vocabulary
# widens by one entry rather than six.
CONTRADICTION_EVIDENCE_KEY = "contradiction"


async def latest_verified_evidence(
    session: AsyncSession, fact_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Best-effort decision evidence from the most recent ``verified`` event
    per fact. Empty for a fact with no verification history yet (e.g. a
    freshly seeded row) — that is a legitimate ``None``, not a fetch failure.

    One batched query (``DISTINCT ON``) rather than one round trip per row,
    same reasoning as ``PipelineFailureService.list_unresolved``'s single
    join: the caller holds a bounded page, not a per-item fan-out.
    """
    if not fact_ids:
        return {}
    result = await session.execute(
        text(
            """
            SELECT DISTINCT ON (object_id) object_id, payload, created_at
            FROM events
            WHERE object_type = 'fact'
              AND event_type = 'verified'
              AND object_id = ANY(CAST(:ids AS uuid[]))
            ORDER BY object_id, created_at DESC, id DESC
            """
        ),
        {"ids": fact_ids},
    )
    out: dict[str, dict[str, Any]] = {}
    for row in result.mappings().all():
        out[str(row["object_id"])] = {
            "payload": row["payload"],
            "recorded_at": row["created_at"],
        }
    return out
