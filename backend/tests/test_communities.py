"""Memory communities — the projection, the clustering kernel, the rewrite.

**The organising principle.** Doc 17 §7 bans pinning exact community
membership: Leiden is not bit-identical across implementations, so a pinned
partition is a permanent flake. The way to get teeth anyway is to split the
system at the projection/clustering boundary. The projection is fully
deterministic and gets value-level assertions; the clustering gets structural
and invariant assertions only.

**The load-bearing structural one is `test_disjoint_clusters_do_not_merge`.**
Replacing the partition with a constant `[0] * n` — the degenerate single-blob
output the whole weighting scheme exists to prevent — leaves every other test
in this file green. That test is what kills it. Disconnected components can
never be merged by a modularity maximiser (merging adds no internal edges while
raising the expected-edges penalty, so modularity strictly falls), which is why
asserting "at least two communities" is a property rather than a coin flip.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text

from app.services.memory_projection import (
    TRUNCATED_TOO_MANY_EDGES,
    build_projection,
)
from app.utils import leiden
from app.utils.ids import new_id

pytestmark = pytest.mark.asyncio

PROJECT = "t218-topics"
OTHER_PROJECT = "t218-topics-other"

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures — direct SQL, so the suite is offline: no pipeline, no embedder, no
# model call. Hand-populating `entities.memory_ids` is also the only way to
# build the cross-project entity the isolation tests need, which the pipeline
# would never produce.
# ---------------------------------------------------------------------------

_INSERT_MEMORY = text(
    """
    INSERT INTO memories (
        id, content, source, project, status, is_archived, expires_at,
        superseded_by
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), :is_archived,
        CAST(:expires_at AS timestamptz), CAST(:superseded_by AS uuid)
    )
    """
)

_INSERT_ENTITY = text(
    """
    INSERT INTO entities (name, entity_type, properties, memory_ids)
    VALUES (:name, :entity_type, CAST(:properties AS jsonb),
            CAST(:memory_ids AS uuid[]))
    RETURNING id
    """
)


async def seed_memory(
    session,
    project: str = PROJECT,
    *,
    status: str = "active",
    is_archived: bool = False,
    expires_at: datetime | None = None,
    superseded_by: UUID | None = None,
    content: str = "seeded memory",
) -> UUID:
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(memory_id),
            "content": content,
            "project": project,
            "status": status,
            "is_archived": is_archived,
            "expires_at": expires_at,
            "superseded_by": str(superseded_by) if superseded_by else None,
        },
    )
    return memory_id


async def seed_entity(
    session,
    name: str,
    memory_ids: list[UUID],
    *,
    entity_type: str = "tool",
    display_name: str | None = None,
) -> UUID:
    properties: dict = {}
    if display_name is not None:
        properties["display_name"] = display_name
    result = await session.execute(
        _INSERT_ENTITY,
        {
            "name": name,
            "entity_type": entity_type,
            "properties": json.dumps(properties),
            "memory_ids": [str(m) for m in memory_ids],
        },
    )
    return result.scalar_one()


async def member_rows(session, project: str) -> set[tuple[UUID, UUID]]:
    result = await session.execute(
        text(
            "SELECT mm.community_id, mm.memory_id "
            "FROM memory_community_members mm "
            "JOIN memory_communities c ON c.id = mm.community_id "
            "WHERE c.project = CAST(:project AS text)"
        ),
        {"project": project},
    )
    return {(row[0], row[1]) for row in result}


async def community_ids(session, project: str) -> set[UUID]:
    result = await session.execute(
        text(
            "SELECT id FROM memory_communities WHERE project = CAST(:p AS text)"
        ),
        {"p": project},
    )
    return {row[0] for row in result}


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------


async def test_eligibility_admits_only_the_live_set(session):
    """T4. Six cases, because five of them are silent when wrong.

    `expires_at` is the load-bearing clause: the sweep is periodic, so an
    expired-but-unswept row is still `status='active'` and a status-only
    predicate lets it into a topic.
    """
    keeper = await seed_memory(session)
    future = await seed_memory(session, expires_at=NOW + timedelta(days=3650))
    pointer = await seed_memory(session)
    superseded = await seed_memory(
        session, status="superseded", superseded_by=pointer
    )
    deprecated = await seed_memory(session, status="deprecated")
    expired = await seed_memory(session, expires_at=NOW - timedelta(days=1))
    archived = await seed_memory(session, is_archived=True)
    await session.flush()

    projection = await build_projection(session, PROJECT)

    assert set(projection.node_ids) == {keeper, future, pointer}
    for excluded in (superseded, deprecated, expired, archived):
        assert excluded not in projection.node_ids


async def test_hub_entities_weigh_less_than_specific_ones(session):
    """T15. A pair sharing only a 100-asserter entity must weigh strictly less
    than a pair sharing only a 2-asserter entity, or one hub collapses the
    project into a single blob while reporting success."""
    hub_members = [await seed_memory(session) for _ in range(100)]
    rare_a = await seed_memory(session)
    rare_b = await seed_memory(session)
    await session.flush()

    await seed_entity(session, "t218-hub", hub_members)
    await seed_entity(session, "t218-rare", [rare_a, rare_b])
    await session.flush()

    projection = await build_projection(session, PROJECT)
    index_of = {mid: i for i, mid in enumerate(projection.node_ids)}
    weights = {(u, v): w for u, v, w in projection.edges}

    def weight(a: UUID, b: UUID) -> float:
        key = tuple(sorted((index_of[a], index_of[b])))
        return weights[key]

    hub_pair = weight(hub_members[0], hub_members[1])
    rare_pair = weight(rare_a, rare_b)

    assert rare_pair == pytest.approx(1.0)
    assert hub_pair == pytest.approx(1.0 / 99)
    assert hub_pair < rare_pair


async def test_hub_cap_drops_entities_above_the_bound(session):
    """`hub_cap` is a materialisation bound, not a ranking one: normalising the
    score of 124 750 rows still materialises 124 750 rows."""
    members = [await seed_memory(session) for _ in range(5)]
    await session.flush()
    await seed_entity(session, "t218-capped", members)
    await session.flush()

    under = await build_projection(session, PROJECT, hub_cap=5)
    over = await build_projection(session, PROJECT, hub_cap=4)

    assert under.edge_count == 10
    assert over.edge_count == 0


async def test_projection_is_project_scoped(session):
    """T2, projection half. A globally shared entity reaches other projects
    through `entities.memory_ids`; the `JOIN eligible` happens before the
    self-join, so a foreign memory is never an edge endpoint."""
    mine_a = await seed_memory(session)
    mine_b = await seed_memory(session)
    theirs = await seed_memory(session, OTHER_PROJECT)
    await session.flush()

    await seed_entity(session, "t218-shared", [mine_a, mine_b, theirs])
    await session.flush()

    projection = await build_projection(session, PROJECT)

    assert theirs not in projection.node_ids
    assert projection.node_count == 2
    # n_e is counted after the project restriction, so this reads as a
    # two-asserter entity here even though three memories assert it globally.
    assert projection.edges == ((0, 1, pytest.approx(1.0)),)
    assert [e.n_e for e in projection.entity_index] == [2]


async def test_single_asserter_entities_build_no_edge(session):
    """`HAVING count(*) >= 2` after the project restriction: a globally shared
    entity with one in-project asserter is not a connection here."""
    mine = await seed_memory(session)
    lonely = await seed_memory(session)
    theirs = await seed_memory(session, OTHER_PROJECT)
    await session.flush()
    await seed_entity(session, "t218-onesided", [mine, theirs])
    await session.flush()

    projection = await build_projection(session, PROJECT)

    assert projection.node_count == 2
    assert lonely in projection.node_ids
    assert projection.edges == ()
    assert projection.entity_index == ()


async def test_weights_add_across_shared_entities(session):
    """Two memories sharing two entities are more connected than two sharing
    one — the sum is over `shared(u, v)`, not a max."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    await session.flush()
    await seed_entity(session, "t218-both-1", [a, b])
    await seed_entity(session, "t218-both-2", [a, b], entity_type="concept")
    await seed_entity(session, "t218-single", [b, c])
    await session.flush()

    projection = await build_projection(session, PROJECT)
    index_of = {mid: i for i, mid in enumerate(projection.node_ids)}
    weights = {(u, v): w for u, v, w in projection.edges}

    ab = weights[tuple(sorted((index_of[a], index_of[b])))]
    bc = weights[tuple(sorted((index_of[b], index_of[c])))]
    assert ab == pytest.approx(2.0)
    assert bc == pytest.approx(1.0)


async def test_excluded_entity_types_are_dropped(session):
    """The excluded-type set is a config knob defaulting to empty, so a future
    tuning run can move it without a code change."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await seed_entity(session, "t218-conceptual", [a, b], entity_type="concept")
    await session.flush()

    kept = await build_projection(session, PROJECT)
    dropped = await build_projection(session, PROJECT, excluded_types=("concept",))

    assert kept.edge_count == 1
    assert dropped.edge_count == 0


async def test_projection_is_deterministically_ordered(session):
    """Not a determinism claim about leidenalg — measured, that is already
    true. The ordering buys a diffable projection dump, stable label
    tie-breaking, and cross-version hygiene."""
    memories = [await seed_memory(session) for _ in range(6)]
    await session.flush()
    await seed_entity(session, "t218-order-1", memories[:3])
    await seed_entity(session, "t218-order-2", memories[3:])
    await session.flush()

    first = await build_projection(session, PROJECT)
    second = await build_projection(session, PROJECT)

    assert first.node_ids == tuple(sorted(memories))
    assert first.node_ids == second.node_ids
    assert first.edges == second.edges
    assert [e.entity_id for e in first.entity_index] == [
        e.entity_id for e in second.entity_index
    ]
    assert all(u < v for u, v, _ in first.edges)


async def test_edge_budget_skips_rather_than_truncates(session):
    """Silently truncating to the top-N edges would change the clustering
    semantics with no error and no symptom."""
    members = [await seed_memory(session) for _ in range(5)]
    await session.flush()
    await seed_entity(session, "t218-budget", members)
    await session.flush()

    projection = await build_projection(session, PROJECT, max_projection_edges=5)

    assert projection.truncated_reason == TRUNCATED_TOO_MANY_EDGES
    assert projection.edges == ()
    assert projection.node_count == 5


async def test_entity_index_carries_display_form_and_members(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await seed_entity(
        session, "postgresql", [a, b], display_name="PostgreSQL"
    )
    await session.flush()

    projection = await build_projection(session, PROJECT)
    (assertion,) = projection.entity_index

    assert assertion.name == "postgresql"
    assert assertion.rendered == "PostgreSQL"
    assert assertion.n_e == 2
    assert assertion.member_indices == (0, 1)
    assert projection.connected_indices() == (0, 1)


# ---------------------------------------------------------------------------
# The clustering kernel
# ---------------------------------------------------------------------------


class _RecordingExecutor(ThreadPoolExecutor):
    instances: list["_RecordingExecutor"] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_calls: list[dict] = []
        _RecordingExecutor.instances.append(self)

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.shutdown_calls.append({"wait": wait, "cancel_futures": cancel_futures})
        super().shutdown(wait=wait, cancel_futures=cancel_futures)


@pytest.fixture
def recorded_executors(monkeypatch):
    _RecordingExecutor.instances = []
    monkeypatch.setattr(
        leiden, "_make_executor", lambda: _RecordingExecutor(max_workers=1)
    )
    return _RecordingExecutor.instances


async def test_kernel_partitions_deterministically(recorded_executors):
    edges = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)]

    first = await leiden.partition_graph(6, edges)
    second = await leiden.partition_graph(6, edges)

    assert first.outcome == "ok"
    assert first.membership is not None
    assert len(first.membership) == 6
    assert first.membership == second.membership
    assert all(e.shutdown_calls == [{"wait": False, "cancel_futures": True}]
               for e in recorded_executors)


async def test_kernel_reports_timeout_and_still_reaps_its_executor(
    recorded_executors,
):
    result = await leiden.partition_graph(3, [(0, 1), (1, 2)], timeout_seconds=0)

    assert result.outcome == "timeout"
    assert result.membership is None
    assert recorded_executors
    assert all(e.shutdown_calls == [{"wait": False, "cancel_futures": True}]
               for e in recorded_executors)


async def test_kernel_reports_unavailable_when_the_library_is_missing(
    monkeypatch, recorded_executors
):
    """`unavailable` must be distinguishable from `timeout`: the two route to
    opposite behaviours in the orchestrator."""
    monkeypatch.setitem(sys.modules, "leidenalg", None)

    result = await leiden.partition_graph(3, [(0, 1), (1, 2)])

    assert result.outcome == "unavailable"
    assert result.membership is None
    # Nothing was started, so nothing needed reaping.
    assert recorded_executors == []


async def test_kernel_honours_weights(recorded_executors):
    """Weighted and unweighted partitions of the same edge list may differ; the
    kernel must forward weights rather than silently ignore them."""
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]

    weighted = await leiden.partition_graph(
        4, edges, weights=[10.0, 0.01, 10.0, 0.01]
    )

    assert weighted.outcome == "ok"
    assert weighted.membership is not None
    assert weighted.membership[0] == weighted.membership[1]
    assert weighted.membership[2] == weighted.membership[3]
    assert weighted.membership[1] != weighted.membership[2]
