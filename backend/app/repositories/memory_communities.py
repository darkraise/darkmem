"""Table access for `memory_communities` / `memory_community_members`.

**Why this is a repository and not a service.** Once T2.53 wires the detector
into the dream-job umbrella, invariant 15's source scan forbids every file
under `app/` from importing `app.services.memory_community_detection`. Each
downstream consumer (T2.19's reports, T2.20's browsing, T2.21's overview,
T2.32's ranking, T2.39's UI) therefore has to reach these tables through
something that is *not* the detector — this module. Putting table access under
`app/services/` would make those tasks unimplementable, and it is what lets
`app/services/memory.py` clear a moved memory's memberships without importing
a Tier-C job.

Raw SQL, matching `project_registry.py`'s idiom, and deliberately **no ORM
model**: nothing maps these two tables today, and a model would be a second
shape to keep in sync with a baseline that is still regenerated in place.

**The rewrite is one transaction per project (doc 06 §7).** `DELETE` then
`INSERT` inside a single transaction, so a concurrent reader sees the complete
old set or the complete new set and never a community with no members, and so
a failure anywhere in the write leaves the *previous* run's communities intact
— ids and all. That ordering is what keeps this from reproducing T1.21, where
a strip outside the savepoint that wrote the replacement left a memory with no
graph on either path. The caller must have a completed partition in hand
before it calls; nothing fallible happens between the delete and the inserts.

**Reading it back is one query, not two.** A reader that lists communities and
then lists members can straddle the commit and join an old community id
against new member rows, yielding an empty result that looks like an empty
topic. `list_with_members` is the documented read contract handed to T2.19 and
downstream for exactly that reason.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.ids import new_id

CROSS_PROJECT_VIOLATION = "cross_project_violation"
STALE_SNAPSHOT = "stale_snapshot"


class MemberWriteError(RuntimeError):
    """A member insert wrote fewer rows than it was handed candidates.

    `reason` separates the two causes, because conflating them mislabels a
    benign event as a defect. Phase R's snapshot is read before the write
    transaction opens, so a memory can be deleted in between — that is
    `stale_snapshot`, a race, and aborting is still right because the rewrite
    would be built on stale input. A candidate that exists in *another*
    project is `cross_project_violation`, and only that one is a defect.
    """

    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason


@dataclass(frozen=True)
class CommunityDraft:
    label: str
    memory_ids: tuple[UUID, ...]
    properties: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CommunityRow:
    id: UUID
    project: str
    label: str | None
    report_string: str | None
    properties: dict
    created_at: datetime
    memory_ids: tuple[UUID, ...]


_DELETE_PROJECT = text(
    "DELETE FROM memory_communities WHERE project = CAST(:project AS text)"
)

_INSERT_COMMUNITY = text(
    "INSERT INTO memory_communities (id, project, label, properties) "
    "VALUES (CAST(:id AS uuid), CAST(:project AS text), :label, "
    "CAST(:properties AS jsonb))"
)

# The row's *existence*, not merely its acceptance, depends on
# `m.project = c.project`: this is a join, never an INSERT ... VALUES. A
# foreign candidate produces no row at all, which the rowcount check below
# then turns from a silent drop into a loud abort.
_INSERT_MEMBERS = text(
    """
    INSERT INTO memory_community_members (community_id, memory_id)
    SELECT c.id, m.id
    FROM memory_communities c
    JOIN jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(memory_id uuid) ON TRUE
    JOIN memories m ON m.id = d.memory_id AND m.project = c.project
    WHERE c.id = CAST(:community_id AS uuid)
    """
)

_CLASSIFY_SHORTFALL = text(
    """
    SELECT d.memory_id AS candidate, m.project AS actual_project
    FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(memory_id uuid)
    LEFT JOIN memories m ON m.id = d.memory_id
    WHERE m.id IS NULL OR m.project <> CAST(:project AS text)
    ORDER BY d.memory_id
    """
)

_COUNT_CROSS_PROJECT = text(
    """
    SELECT count(*)
    FROM memory_community_members mm
    JOIN memory_communities c ON c.id = mm.community_id
    JOIN memories m ON m.id = mm.memory_id
    WHERE c.project = CAST(:project AS text) AND m.project <> c.project
    """
)

_LIST_WITH_MEMBERS = """
    SELECT c.id, c.project, c.label, c.report_string, c.properties,
           c.created_at,
           COALESCE(
               array_agg(mm.memory_id ORDER BY mm.memory_id)
                   FILTER (WHERE mm.memory_id IS NOT NULL),
               CAST('{}' AS uuid[])
           ) AS memory_ids
    FROM memory_communities c
    LEFT JOIN memory_community_members mm ON mm.community_id = c.id
    WHERE c.project = CAST(:project AS text)
    --EXTRA--
    GROUP BY c.id, c.project, c.label, c.report_string, c.properties,
             c.created_at
    ORDER BY c.label, c.id
"""

_LIST_ALL = text(_LIST_WITH_MEMBERS.replace("--EXTRA--", ""))
_LIST_BY_LABEL = text(
    _LIST_WITH_MEMBERS.replace("--EXTRA--", "AND c.label = CAST(:label AS text)")
)

_SET_REPORT = text(
    "UPDATE memory_communities SET "
    "label = COALESCE(CAST(:label AS text), label), "
    "report_string = COALESCE(CAST(:report_string AS text), report_string) "
    "WHERE id = CAST(:id AS uuid)"
)

_DELETE_MEMBERSHIPS = text(
    "DELETE FROM memory_community_members WHERE memory_id = CAST(:id AS uuid)"
)


def _row_payload(memory_ids: tuple[UUID, ...]) -> str:
    return json.dumps([{"memory_id": str(m)} for m in memory_ids])


async def replace_project_communities(
    session: AsyncSession,
    project: str,
    communities: list[CommunityDraft],
) -> list[UUID]:
    """Delete-and-rewrite one project's communities. Caller owns the commit."""
    await session.execute(_DELETE_PROJECT, {"project": project})

    written: list[UUID] = []
    for draft in communities:
        community_id = new_id()
        await session.execute(
            _INSERT_COMMUNITY,
            {
                "id": str(community_id),
                "project": project,
                "label": draft.label,
                "properties": json.dumps(draft.properties, default=str),
            },
        )
        if not draft.memory_ids:
            written.append(community_id)
            continue

        rows = _row_payload(draft.memory_ids)
        result = await session.execute(
            _INSERT_MEMBERS,
            {"community_id": str(community_id), "rows": rows},
        )
        inserted = result.rowcount or 0
        if inserted != len(draft.memory_ids):
            await _raise_for_shortfall(
                session, project, draft, rows, inserted
            )
        written.append(community_id)

    return written


async def _raise_for_shortfall(
    session: AsyncSession,
    project: str,
    draft: CommunityDraft,
    rows: str,
    inserted: int,
) -> None:
    missing = await session.execute(
        _CLASSIFY_SHORTFALL, {"rows": rows, "project": project}
    )
    foreign: list[str] = []
    absent: list[str] = []
    for row in missing.mappings():
        if row["actual_project"] is None:
            absent.append(str(row["candidate"]))
        else:
            foreign.append(f"{row['candidate']}@{row['actual_project']}")

    if foreign:
        raise MemberWriteError(
            CROSS_PROJECT_VIOLATION,
            f"community {draft.label!r} in project {project!r} was handed "
            f"candidates belonging to another project: {', '.join(foreign)}",
        )
    raise MemberWriteError(
        STALE_SNAPSHOT,
        f"community {draft.label!r} in project {project!r} wrote {inserted} of "
        f"{len(draft.memory_ids)} members; candidates no longer exist: "
        f"{', '.join(absent) or 'unknown'}",
    )


async def assert_no_cross_project_members(
    session: AsyncSession, project: str
) -> None:
    """Post-write backstop over the whole project's membership.

    Deliberately temporary: once the members table carries `project` and both
    composite foreign keys, no row this looks for can exist, and an assertion
    with no reachable failure is dead code the runbook cannot prove.
    """
    count = await session.scalar(_COUNT_CROSS_PROJECT, {"project": project})
    if count:
        raise MemberWriteError(
            CROSS_PROJECT_VIOLATION,
            f"{count} cross-project member row(s) survived the rewrite of "
            f"project {project!r}",
        )


def _to_row(mapping) -> CommunityRow:
    return CommunityRow(
        id=mapping["id"],
        project=mapping["project"],
        label=mapping["label"],
        report_string=mapping["report_string"],
        properties=mapping["properties"] or {},
        created_at=mapping["created_at"],
        memory_ids=tuple(mapping["memory_ids"]),
    )


async def list_with_members(
    session: AsyncSession, project: str
) -> list[CommunityRow]:
    result = await session.execute(_LIST_ALL, {"project": project})
    return [_to_row(m) for m in result.mappings()]


async def get_by_label(
    session: AsyncSession, project: str, label: str
) -> CommunityRow | None:
    """Look a community up by its deterministic label rather than its id.

    Ids churn on every rewrite; labels are derived from dominant entities and
    survive one, which is what lets T2.19 carry a prior run's `report_string`
    forward instead of regenerating every report every night.
    """
    result = await session.execute(
        _LIST_BY_LABEL, {"project": project, "label": label}
    )
    rows = [_to_row(m) for m in result.mappings()]
    return rows[0] if rows else None


async def set_report(
    session: AsyncSession,
    community_id: UUID,
    *,
    label: str | None = None,
    report_string: str | None = None,
) -> None:
    await session.execute(
        _SET_REPORT,
        {
            "id": str(community_id),
            "label": label,
            "report_string": report_string,
        },
    )


async def delete_memberships_for_memory(
    session: AsyncSession, memory_id: UUID
) -> int:
    """Evict one memory from every community it belongs to.

    A memory that leaves project A has genuinely left A's topic space —
    doc 06 §7's lifecycle already decays members out of communities — and this
    is also the same shape as the demote-before-delete rule: clear the
    dependent rows first, or the constraint aborts the operation.
    """
    result = await session.execute(_DELETE_MEMBERSHIPS, {"id": str(memory_id)})
    return result.rowcount or 0
