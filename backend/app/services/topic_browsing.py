"""Topic browsing and the report's injectable unit (doc 09 §3.1, §3.2) — T2.20.

**Scope, and where it stops.** Doc 09 §3 names three read/derive operations
over doc 06's durable `memory_communities` rows: browsing membership, report
injection, and the pin-suggestion diff (`app/services/pin_suggestions.py`).
This module owns the first two. Browsing is a clean read straight off
`memory_communities` / `memory_community_members` (§3.1) — no clustering, no
recomputation, exactly the discipline T2.18's tables were built for.

**The boundary with T2.43 (doc 07's local report injection).** §3.2 is
explicit: "the local injection shape ... belongs to retrieval and is doc 07's
to wire; this doc only notes that the report a community carries is the
injectable unit." `get_injectable_report` below *is* that unit — a plain
`(project, label) -> report text or None` read, gated through
`report_status()` so a `pending`/`skipped`/`failed` community never hands a
retrieval caller a non-answer to inject. T2.43 is expected to call this
function from doc 07's composition step. Nothing in this module, or anywhere
else in this task's diff, imports from `app/services/pipeline.py`,
`app/services/hybrid_search.py`, `app/services/retrieval*`, or any
`app/api/routes` module — that is the line the brief's boundary warning
draws, and crossing it is T2.43's job, not this one's.

**The boundary with T2.21 (`memory_overview`).** §3.3's global map-reduce is
a project-wide "what does this project's memory contain" summary-of-summaries
over *every* community's report, cached against a community-set hash. Nothing
here builds that: no reduce call, no `config` row cache, no MCP tool. This
module answers per-topic and per-memory questions only.

**`report_status()`, never re-derived.** `memory_community_reports.py` left
`report_status` as the one read-time projection of `report_string` /
`properties["report_error"]` / `properties["size"]` into the four-value
state, specifically so downstream readers do not invent a fifth answer
(`pending` vs `skipped` are both "no report", for different, load-bearing
reasons). Every view built here calls it rather than checking
`report_string is None` itself.

**"Impact rating" is aspirational, not invented here.** Doc 09 §3.1 lists an
"impact rating" among what browsing surfaces from `properties`, but T2.18's
detector (`memory_community_detection.py`) never writes an `impact_rating`
key — only `dominant_entities`, `size`, `fallback`, `resolution`,
`edge_count`, `hub_cap`. `TopicView.impact_rating` reads
`properties.get("impact_rating")` and is `None` today for every community;
this module does not compute one, because doing so would mean inventing a
ranking metric that belongs to whichever task actually owns it. Recorded as
an open item, not silently worked around.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_communities import (
    CommunityRow,
    get_by_label,
    list_for_memory,
    list_with_members,
)
from app.services.memory_community_reports import (
    REPORT_STATUS_READY,
    report_status,
)


@dataclass(frozen=True)
class TopicView:
    label: str
    dominant_entities: tuple[dict, ...]
    impact_rating: float | None
    member_count: int
    report_status: str
    report_string: str | None


def _to_view(row: CommunityRow) -> TopicView:
    status = report_status(row)
    return TopicView(
        label=row.label or "",
        dominant_entities=tuple(row.properties.get("dominant_entities") or ()),
        impact_rating=row.properties.get("impact_rating"),
        member_count=len(row.memory_ids),
        report_status=status,
        report_string=row.report_string if status == REPORT_STATUS_READY else None,
    )


async def browse_topics(session: AsyncSession, project: str) -> list[TopicView]:
    """Every topic in `project`, membership included — "which memories are in
    this topic" (doc 09 §3.1), one joined query via `list_with_members`."""
    rows = await list_with_members(session, project)
    return [_to_view(row) for row in rows]


async def get_topic(
    session: AsyncSession, project: str, label: str
) -> TopicView | None:
    """One topic by its stable dominant-entity label — never by a community
    id a caller might have cached from a prior load (doc 09 §3.1)."""
    row = await get_by_label(session, project, label)
    return _to_view(row) if row else None


async def topics_for_memory(
    session: AsyncSession, project: str, memory_id: UUID
) -> list[TopicView]:
    """"Which topics is this memory in" (doc 09 §3.1) — the other browsing
    direction, an index lookup on `memory_id` rather than a scan."""
    rows = await list_for_memory(session, project, memory_id)
    return [_to_view(row) for row in rows]


async def get_injectable_report(
    session: AsyncSession, project: str, label: str
) -> str | None:
    """The unit doc 09 §3.2 hands to doc 07: a community's report text, or
    `None` if it has none to inject (not yet generated, too small to ever
    get one, or a failed attempt). T2.43 is the intended caller from
    retrieval's composition step; this function does not call into
    retrieval itself."""
    row = await get_by_label(session, project, label)
    if row is None:
        return None
    return row.report_string if report_status(row) == REPORT_STATUS_READY else None
