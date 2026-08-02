"""Topic detection — Leiden communities per project (doc 06 §7).

**Tier C, and nothing may reach it from capture or retrieval** (invariant 15).
Detection is deterministic given its input graph: no model call appears
anywhere in this module. The only model-backed step doc 06 §7 names is
`report_string`, which is T2.19's.

**Three phases, and the ordering is the whole safety argument.**

- *Phase R* reads the projection. Read-only, so it takes no row locks.
- *Phase C* computes the partition with **no transaction open**: Phase R
  commits before it starts, so the connection goes back to the pool rather
  than sitting `idle in transaction` for the length of the clustering.
- *Phase W* deletes and rewrites the project's communities in one transaction.

The analogous defect to T1.21 is easy to write and would be invisible: delete
the project's communities, then run Leiden, then have Leiden raise — leaving
the project with zero topics after it had a good set a moment earlier. That is
unreachable here because the `DELETE` cannot run without a completed partition
already in hand. Every fallible step — the library import, the graph build,
the clustering, the timeout — lives in Phase C, which holds no transaction and
touches no row.

**One transaction per project, not one per run.** A whole-run transaction would
hold write locks on every project's community rows for the length of the run,
and one project's bad graph would abort every other project's good result. A
partial run therefore leaves each project internally consistent: those already
committed carry their new communities, those not yet reached carry their
previous run's. Stale is not corrupt.

**Three fallbacks, and they are not interchangeable.** A timeout means the
graph was real but the clustering did not finish, so one community over the
connected nodes is a degraded answer worth writing. A missing clustering
library means *nothing was computed*, so writing one would fabricate a result
and deleting the previous run's good topics to do it would be T1.21 from
another direction — that path writes nothing and deletes nothing. An
over-budget projection is skipped for the same reason.

**Membership is not a partition.** Two classes of eligible memory get no
membership row: isolated nodes, and members of communities below
`min_community_size`. A memory sharing no entity with anything is not topically
related to anything, and sweeping it into an everything-community would assert
a relationship the projection says does not exist.

**The project cursor derives from `memories`, not from the `projects`
registry.** `project_registry.register` never raises by design, so a failed
registry write leaves a project holding memories and no registry row — and
iterating the registry would then skip it silently and forever. The `UNION`
with `memory_communities` is not redundant either: a project whose memories
have all been superseded or archived has no eligible memory, so a
memories-only iteration would never visit it again and its stale topics would
linger, surfacing dead memories through browsing.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_communities import (
    CommunityDraft,
    MemberWriteError,
    replace_project_communities,
)
from app.services.events import record_event
from app.services.job_registry import FieldDescriptor
from app.services.memory_community_labels import label_communities
from app.services.memory_projection import (
    DEFAULT_EXCLUDED_ENTITY_TYPES,
    DEFAULT_HUB_CAP,
    DEFAULT_MAX_PROJECTION_EDGES,
    build_projection,
)
from app.utils.leiden import DEFAULT_TIMEOUT_SECONDS, partition_graph

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 5
MAX_BATCH_SIZE = 100
DEFAULT_MIN_COMMUNITY_SIZE = 2
DEFAULT_RESOLUTION = 1.0
DEFAULT_LARGE_GRAPH_NODES = 10_000

# Above the large-graph threshold, mirroring the code detector's own branch.
LARGE_GRAPH_RESOLUTION = 2.0
LARGE_GRAPH_ITERATIONS = 3

# Matching the code precedent: below three connected nodes there is nothing for
# a modularity maximiser to find.
TINY_GRAPH_NODES = 3

FALLBACK_TINY_GRAPH = "tiny_graph"
FALLBACK_TIMEOUT = "timeout"

SKIPPED_LIBRARY_UNAVAILABLE = "library_unavailable"

EVENT_TYPE = "consolidated"
OBJECT_TYPE = "topic"

# Keeps the placeholder registration's `batch_size` key, default and maximum
# verbatim. `JobRegistry.set_config` merges `{**cfg.config, **partial}` and
# never drops a key, so renaming it would orphan any persisted value silently.
TOPIC_DETECTION_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size", label="Projects Per Run",
        default=DEFAULT_BATCH_SIZE, min=1, max=MAX_BATCH_SIZE,
        help="Projects visited per topic_detection run, in rotating order.",
    ),
    FieldDescriptor(
        key="hub_cap", label="Hub Cap",
        default=DEFAULT_HUB_CAP, min=2, max=10_000,
        help=(
            "Entities asserted by more in-project memories than this build no "
            "edges at all — a materialisation bound, not a ranking one."
        ),
    ),
    FieldDescriptor(
        key="min_community_size", label="Minimum Community Size",
        default=DEFAULT_MIN_COMMUNITY_SIZE, min=2, max=100,
        help="Communities smaller than this are dropped; one memory is not a topic.",
    ),
    FieldDescriptor(
        key="leiden_timeout_seconds", label="Clustering Timeout (s)",
        default=int(DEFAULT_TIMEOUT_SECONDS), min=1, max=600,
        help="Past this the project falls back to one community over its connected nodes.",
    ),
    FieldDescriptor(
        key="max_projection_edges", label="Maximum Projection Edges",
        default=DEFAULT_MAX_PROJECTION_EDGES, min=1_000, max=100_000_000,
        help="A projection wider than this is skipped loudly rather than truncated.",
    ),
]


@dataclass(frozen=True)
class ProjectOutcome:
    project: str
    node_count: int
    edge_count: int
    community_count: int
    unassigned_count: int
    duration_ms: int
    labels: tuple[str, ...] = ()
    fallback: str | None = None
    skipped_reason: str | None = None


@dataclass
class DetectionOutcome:
    projects_processed: int = 0
    last_project: str | None = None
    communities: int = 0
    skipped: int = 0
    outcomes: list[ProjectOutcome] = field(default_factory=list)


_NEXT_PROJECTS = text(
    """
    SELECT project FROM (
        SELECT DISTINCT project FROM memories
        WHERE status = 'active'
          AND is_archived = false
          AND (expires_at IS NULL OR expires_at > now())
        UNION
        SELECT DISTINCT project FROM memory_communities
    ) p
    WHERE project > CAST(:after_project AS text)
       OR CAST(:after_project AS text) IS NULL
    ORDER BY project
    LIMIT CAST(:batch_size AS int)
    """
)


async def next_projects(
    session: AsyncSession, after_project: str | None, batch_size: int
) -> list[str]:
    result = await session.execute(
        _NEXT_PROJECTS,
        {"after_project": after_project, "batch_size": batch_size},
    )
    return [row[0] for row in result]


def _groups_from_membership(
    membership: Sequence[int],
    connected: Sequence[int],
    min_community_size: int,
) -> list[tuple[int, ...]]:
    """Communities over the *connected* nodes only.

    An isolated vertex has degree zero, so moving it between communities
    changes modularity by nothing at all and the maximiser may place it
    anywhere. Filtering here is what keeps a memory that shares no entity with
    anything out of somebody else's topic.
    """
    buckets: dict[int, list[int]] = {}
    for index in connected:
        buckets.setdefault(membership[index], []).append(index)
    groups = [
        tuple(sorted(members))
        for members in buckets.values()
        if len(members) >= min_community_size
    ]
    groups.sort()
    return groups


async def _journal(session: AsyncSession, outcome: ProjectOutcome, sizes: Sequence[int]) -> None:
    """One row per project per run, referencing communities by label.

    `object_id` stays NULL and no community id appears in the payload: ids are
    rewritten every run, so a value here would be the durable reference to a
    churning id that doc 04 §8.4 forbids.
    """
    await record_event(
        session,
        event_type=EVENT_TYPE,
        object_type=OBJECT_TYPE,
        object_id=None,
        project=outcome.project,
        payload={
            "communities": [
                {"label": label, "size": size}
                for label, size in zip(outcome.labels, sizes)
            ],
            "node_count": outcome.node_count,
            "edge_count": outcome.edge_count,
            "community_count": outcome.community_count,
            "unassigned_count": outcome.unassigned_count,
            "fallback": outcome.fallback,
            "duration_ms": outcome.duration_ms,
            "skipped_reason": outcome.skipped_reason,
        },
    )


async def detect_for_project(
    session: AsyncSession,
    project: str,
    *,
    hub_cap: int = DEFAULT_HUB_CAP,
    excluded_types: tuple[str, ...] = DEFAULT_EXCLUDED_ENTITY_TYPES,
    max_projection_edges: int = DEFAULT_MAX_PROJECTION_EDGES,
    min_community_size: int = DEFAULT_MIN_COMMUNITY_SIZE,
    leiden_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    resolution: float = DEFAULT_RESOLUTION,
    large_graph_nodes: int = DEFAULT_LARGE_GRAPH_NODES,
) -> ProjectOutcome:
    """Rewrite one project's communities. The caller owns the commit."""
    started = time.monotonic()

    # Phase R.
    projection = await build_projection(
        session,
        project,
        hub_cap=hub_cap,
        excluded_types=excluded_types,
        max_projection_edges=max_projection_edges,
    )

    def elapsed_ms() -> int:
        return int((time.monotonic() - started) * 1000)

    # End the read transaction before Phase C. `leiden_timeout_seconds` runs to
    # 600, so holding it would leave a pooled connection `idle in transaction`
    # for minutes per project — pinning xmin the whole time, and inviting a
    # kill on any install with `idle_in_transaction_session_timeout` set.
    # Committing rather than rolling back because Phase R wrote nothing, so the
    # two are equivalent here, and a rollback would discard the caller's own
    # uncommitted setup when the session is one it owns.
    await session.commit()

    if projection.truncated_reason is not None:
        logger.warning(
            "Topic detection skipped project %r: %s",
            project, projection.truncated_reason,
        )
        outcome = ProjectOutcome(
            project=project,
            node_count=projection.node_count,
            edge_count=0,
            community_count=0,
            unassigned_count=projection.node_count,
            duration_ms=elapsed_ms(),
            skipped_reason=projection.truncated_reason,
        )
        await _journal(session, outcome, ())
        return outcome

    # Phase C — no transaction is open across any of this.
    connected = projection.connected_indices()
    fallback: str | None = None
    resolution_used = resolution

    if len(connected) < TINY_GRAPH_NODES:
        fallback = FALLBACK_TINY_GRAPH
        groups = (
            [connected] if len(connected) >= min_community_size else []
        )
    else:
        n_iterations = -1
        if projection.node_count > large_graph_nodes:
            resolution_used = LARGE_GRAPH_RESOLUTION
            n_iterations = LARGE_GRAPH_ITERATIONS
        result = await partition_graph(
            projection.node_count,
            [(u, v) for u, v, _ in projection.edges],
            weights=[w for _, _, w in projection.edges],
            resolution=resolution_used,
            n_iterations=n_iterations,
            timeout_seconds=leiden_timeout_seconds,
        )
        if result.outcome == "unavailable":
            logger.warning(
                "Topic detection skipped project %r: no clustering library",
                project,
            )
            outcome = ProjectOutcome(
                project=project,
                node_count=projection.node_count,
                edge_count=projection.edge_count,
                community_count=0,
                unassigned_count=projection.node_count,
                duration_ms=elapsed_ms(),
                skipped_reason=SKIPPED_LIBRARY_UNAVAILABLE,
            )
            await _journal(session, outcome, ())
            return outcome
        if result.outcome == "timeout":
            fallback = FALLBACK_TIMEOUT
            groups = [connected]
        else:
            assert result.membership is not None
            groups = _groups_from_membership(
                result.membership, connected, min_community_size
            )

    labelled = label_communities(projection.entity_index, groups)
    drafts = [
        CommunityDraft(
            label=labelled[index].label,
            memory_ids=tuple(projection.node_ids[i] for i in group),
            properties={
                "dominant_entities": [
                    entity.as_payload()
                    for entity in labelled[index].dominant_entities
                ],
                "size": len(group),
                "fallback": fallback,
                "resolution": resolution_used,
                "edge_count": projection.edge_count,
                "hub_cap": hub_cap,
            },
        )
        for index, group in enumerate(groups)
    ]

    # Phase W.
    await replace_project_communities(session, project, drafts)

    assigned = sum(len(group) for group in groups)
    outcome = ProjectOutcome(
        project=project,
        node_count=projection.node_count,
        edge_count=projection.edge_count,
        community_count=len(groups),
        unassigned_count=projection.node_count - assigned,
        duration_ms=elapsed_ms(),
        labels=tuple(draft.label for draft in drafts),
        fallback=fallback,
    )
    await _journal(session, outcome, [len(group) for group in groups])
    return outcome


async def run_topic_detection(
    session_factory,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    after_project: str | None = None,
    **knobs,
) -> DetectionOutcome:
    """Visit one rotating batch of projects, each in its own transaction."""
    async with session_factory() as session:
        projects = await next_projects(session, after_project, batch_size)

    outcome = DetectionOutcome(last_project=after_project)
    for project in projects:
        outcome.last_project = project
        try:
            async with session_factory() as session:
                project_outcome = await detect_for_project(
                    session, project, **knobs
                )
                await session.commit()
        except MemberWriteError as exc:
            logger.error(
                "Topic detection aborted project %r: %s", project, exc
            )
            outcome.skipped += 1
            await _journal_abort(session_factory, project, exc.reason)
            continue
        except Exception:
            logger.exception("Topic detection failed for project %r", project)
            outcome.skipped += 1
            await _journal_abort(session_factory, project, "error")
            continue

        outcome.projects_processed += 1
        outcome.communities += project_outcome.community_count
        outcome.outcomes.append(project_outcome)
        if project_outcome.skipped_reason is not None:
            outcome.skipped += 1

    return outcome


async def _journal_abort(session_factory, project: str, reason: str) -> None:
    """Journal an aborted project from a *fresh* session.

    The abort rolled its own transaction back, so a journal row written inside
    it would have gone with it — which is how a run that skipped a project can
    end up looking like a run that never reached it.
    """
    async with session_factory() as session:
        await _journal(
            session,
            ProjectOutcome(
                project=project,
                node_count=0,
                edge_count=0,
                community_count=0,
                unassigned_count=0,
                duration_ms=0,
                skipped_reason=reason,
            ),
            (),
        )
        await session.commit()
