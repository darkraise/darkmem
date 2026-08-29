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

import ast
import json
import pathlib
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories import memory_communities as repo
from app.services import memory_community_detection as detection
from app.services import memory_community_labels as labels
from app.services.community_detector import CommunityDetector
from app.services.dream_jobs import TOPIC_DETECTION_JOB_KEY, register_dream_jobs
from app.services.job_registry import JobRegistry
from app.services.memory_projection import (
    EntityAssertion,
    TRUNCATED_TOO_MANY_EDGES,
    build_projection,
)
from app.utils import leiden
from app.utils.ids import new_id

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


# ---------------------------------------------------------------------------
# The repository — the per-project delete-and-rewrite
# ---------------------------------------------------------------------------


async def test_rewrite_writes_communities_and_members(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()

    written = await repo.replace_project_communities(
        session,
        PROJECT,
        [repo.CommunityDraft(label="alpha", memory_ids=(a, b),
                             properties={"size": 2})],
    )
    await session.flush()

    (row,) = await repo.list_with_members(session, PROJECT)
    assert row.id == written[0]
    assert row.label == "alpha"
    assert row.properties == {"size": 2}
    assert set(row.memory_ids) == {a, b}
    assert row.report_string is None


async def test_rewrite_replaces_rather_than_accumulates(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()

    first = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()
    second = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="beta", memory_ids=(a,))]
    )
    await session.flush()

    assert set(first) & set(second) == set()
    assert await community_ids(session, PROJECT) == set(second)
    assert len(await member_rows(session, PROJECT)) == 1


async def test_rewrite_leaves_other_projects_untouched(session):
    """T6. Dropping `WHERE project = :p` from the DELETE takes every other
    project's topics with it."""
    mine = await seed_memory(session)
    theirs = await seed_memory(session, OTHER_PROJECT)
    await session.flush()

    other = await repo.replace_project_communities(
        session,
        OTHER_PROJECT,
        [repo.CommunityDraft(label="theirs", memory_ids=(theirs,))],
    )
    await session.flush()
    await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="mine", memory_ids=(mine,))]
    )
    await session.flush()

    assert await community_ids(session, OTHER_PROJECT) == set(other)
    assert len(await member_rows(session, OTHER_PROJECT)) == 1


async def test_member_shortfall_names_a_cross_project_violation(session):
    """T3. Without the rowcount check the foreign row is dropped silently and
    the write reports success on a membership it never wrote."""
    mine = await seed_memory(session)
    theirs = await seed_memory(session, OTHER_PROJECT)
    await session.flush()

    with pytest.raises(repo.MemberWriteError) as excinfo:
        await repo.replace_project_communities(
            session,
            PROJECT,
            [repo.CommunityDraft(label="mixed", memory_ids=(mine, theirs))],
        )

    assert excinfo.value.reason == repo.CROSS_PROJECT_VIOLATION
    assert str(theirs) in str(excinfo.value)


async def test_member_shortfall_distinguishes_a_stale_snapshot(session):
    """The read-to-write race is not a defect and must not be journalled as
    one: Phase R's snapshot is read before the write transaction opens."""
    kept = await seed_memory(session)
    await session.flush()
    vanished = new_id()

    with pytest.raises(repo.MemberWriteError) as excinfo:
        await repo.replace_project_communities(
            session,
            PROJECT,
            [repo.CommunityDraft(label="raced", memory_ids=(kept, vanished))],
        )

    assert excinfo.value.reason == repo.STALE_SNAPSHOT


async def test_a_failed_rewrite_leaves_the_previous_run_intact(session):
    """T5, repository half. The T1.21 guard: the strip and the rewrite are one
    atomic unit, so a failure anywhere in the write leaves the previous run's
    communities intact — ids and all — rather than leaving the project with
    none."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()

    good = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()
    before_ids = await community_ids(session, PROJECT)
    before_members = await member_rows(session, PROJECT)

    with pytest.raises(repo.MemberWriteError):
        async with session.begin_nested():
            await repo.replace_project_communities(
                session,
                PROJECT,
                [repo.CommunityDraft(label="doomed", memory_ids=(a, new_id()))],
            )

    assert await community_ids(session, PROJECT) == before_ids == set(good)
    assert await member_rows(session, PROJECT) == before_members


async def test_get_by_label_and_set_report_carry_reports_across_a_rewrite(
    session,
):
    """The T2.19 seam: ids churn every run, labels do not, so a prior run's
    report can be carried forward instead of regenerated nightly."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()

    (first,) = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()
    await repo.set_report(session, first, report_string="a report")
    await session.flush()

    carried = await repo.get_by_label(session, PROJECT, "alpha")
    assert carried is not None
    assert carried.report_string == "a report"

    (second,) = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a,))]
    )
    await session.flush()

    assert second != first
    rewritten = await repo.get_by_label(session, PROJECT, "alpha")
    assert rewritten is not None
    assert rewritten.id == second
    assert rewritten.report_string is None
    assert await repo.get_by_label(session, PROJECT, "nothing") is None


async def test_delete_memberships_for_memory_clears_only_that_memory(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()

    removed = await repo.delete_memberships_for_memory(session, a)
    await session.flush()

    assert removed == 1
    assert {m for _, m in await member_rows(session, PROJECT)} == {b}


async def test_the_database_rejects_a_cross_project_member_row(session):
    """T17 — the literal proof of "unrepresentable".

    The member insert's join already makes a cross-project row unproducible by
    the detection path, but that is a property of the write path, not of the
    table. This is the table refusing the row: a hand-written INSERT with no
    application code in the way. It replaces the runtime assertion that used to
    stand in for it, which the composite keys leave with no reachable failure.
    """
    mine = await seed_memory(session)
    theirs = await seed_memory(session, OTHER_PROJECT)
    await session.flush()

    (community,) = await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="mine", memory_ids=(mine,))]
    )
    await session.flush()

    async def raw_insert(project: str) -> None:
        await session.execute(
            text(
                "INSERT INTO memory_community_members "
                "(community_id, memory_id, project) "
                "VALUES (CAST(:c AS uuid), CAST(:m AS uuid), CAST(:p AS text))"
            ),
            {"c": str(community), "m": str(theirs), "p": project},
        )
        await session.flush()

    # Claiming the community's project fails the memory-side key; claiming the
    # memory's project fails the community-side key. There is no third value:
    # the single `project` column has to satisfy both parents at once.
    for claimed in (PROJECT, OTHER_PROJECT):
        async with session.begin_nested() as savepoint:
            with pytest.raises(IntegrityError):
                await raw_insert(claimed)
            await savepoint.rollback()

    assert {m for _, m in await member_rows(session, PROJECT)} == {mine}


# ---------------------------------------------------------------------------
# The schema these tables actually carry
# ---------------------------------------------------------------------------


async def test_nothing_durable_references_a_churning_community_id(session):
    """T14, first half. Community ids are rewritten every run, so a durable FK
    onto one would break on the next nightly pass (doc 04 §8.4)."""
    result = await session.execute(
        text(
            "SELECT conname, conrelid::regclass::text AS referencing "
            "FROM pg_constraint "
            "WHERE contype = 'f' "
            "AND confrelid = CAST('memory_communities' AS regclass)"
        )
    )
    referencing = {row.referencing for row in result}
    assert referencing == {"memory_community_members"}


async def test_membership_carries_both_composite_foreign_keys(session):
    """T14, second half. One composite key is not enough: with only the
    memory-side key, a row naming a project-A community, a project-B memory and
    project B satisfies every constraint and is still cross-project."""
    result = await session.execute(
        text(
            "SELECT c.conname, "
            "       c.confrelid::regclass::text AS parent, "
            "       ARRAY(SELECT attname FROM unnest(c.conkey) k "
            "             JOIN pg_attribute a "
            "               ON a.attrelid = c.conrelid AND a.attnum = k) AS cols "
            "FROM pg_constraint c "
            "WHERE c.contype = 'f' "
            "AND c.conrelid = CAST('memory_community_members' AS regclass)"
        )
    )
    keys = {row.parent: sorted(row.cols) for row in result}
    assert keys == {
        "memories": ["memory_id", "project"],
        "memory_communities": ["community_id", "project"],
    }

    support = await session.scalar(
        text(
            "SELECT count(*) FROM pg_constraint "
            "WHERE contype = 'u' "
            "AND conrelid = CAST('memory_communities' AS regclass) "
            "AND conname = 'memory_communities_id_project_key'"
        )
    )
    assert support == 1


async def test_community_tables_carry_the_columns_the_writer_assumes(session):
    result = await session.execute(
        text(
            "SELECT table_name, column_name, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name IN "
            "('memory_communities', 'memory_community_members')"
        )
    )
    columns = {(r.table_name, r.column_name): r.is_nullable for r in result}

    assert columns[("memory_communities", "id")] == "NO"
    assert columns[("memory_communities", "project")] == "NO"
    assert columns[("memory_communities", "label")] == "YES"
    assert columns[("memory_communities", "report_string")] == "YES"
    assert columns[("memory_communities", "properties")] == "YES"
    assert columns[("memory_community_members", "community_id")] == "NO"
    assert columns[("memory_community_members", "memory_id")] == "NO"
    assert columns[("memory_community_members", "project")] == "NO"


# ---------------------------------------------------------------------------
# Labelling
# ---------------------------------------------------------------------------


def _assertion(name, members, *, n_e=None, display_name=None, entity_type="tool"):
    return EntityAssertion(
        entity_id=new_id(),
        name=name,
        display_name=display_name,
        entity_type=entity_type,
        n_e=n_e if n_e is not None else len(members),
        member_indices=tuple(members),
    )


def test_label_ranks_by_member_count_then_specificity():
    index = [
        _assertion("broad", [0, 1, 2], n_e=90),
        _assertion("narrow", [0, 1, 2], n_e=3),
        _assertion("minor", [0]),
    ]

    (labelled,) = labels.label_communities(index, [(0, 1, 2)])

    assert labelled.label == "narrow, broad, minor"
    assert [e.name for e in labelled.dominant_entities] == [
        "narrow", "broad", "minor"
    ]
    assert labelled.dominant_entities[0].members == 3


def test_label_renders_the_display_form_but_ranks_on_the_stored_name():
    index = [
        _assertion("postgresql", [0, 1], display_name="PostgreSQL"),
        _assertion("alembic", [0, 1]),
    ]

    (labelled,) = labels.label_communities(index, [(0, 1)])

    assert labelled.label == "alembic, PostgreSQL"
    assert labelled.dominant_entities[1].name == "postgresql"
    assert labelled.dominant_entities[1].display_name == "PostgreSQL"


def test_label_is_deterministic_across_calls():
    index = [
        _assertion("a", [0, 1]),
        _assertion("b", [0, 1]),
        _assertion("c", [0, 1]),
        _assertion("d", [1]),
    ]

    first = labels.label_communities(index, [(0, 1)])
    second = labels.label_communities(index, [(0, 1)])

    assert [c.label for c in first] == [c.label for c in second]


def test_colliding_labels_are_disambiguated_deterministically():
    """Two communities whose top three entities coincide must not share a
    label: the journal references communities by label, and doc 09's
    pin-suggestion diff keys on it."""
    index = [
        _assertion("a", [0, 1, 2, 3]),
        _assertion("b", [0, 1, 2, 3]),
        _assertion("c", [0, 1, 2, 3]),
        _assertion("d", [0, 1], n_e=40),
        _assertion("e", [2, 3], n_e=40),
    ]

    first, second = labels.label_communities(index, [(2, 3), (0, 1)])

    assert first.label != second.label
    assert first.label == "a, b, c, e"
    assert second.label == "a, b, c, d"
    # The widening entity has to reach the provenance too: a label naming four
    # entities whose dominant_entities lists three omits the one that made the
    # label distinct.
    assert [e.name for e in first.dominant_entities] == ["a", "b", "c", "e"]
    assert [e.name for e in second.dominant_entities] == ["a", "b", "c", "d"]


def test_an_indistinguishable_collision_falls_back_to_a_stable_ordinal():
    index = [_assertion("only", [0, 1, 2, 3])]

    first, second = labels.label_communities(index, [(2, 3), (0, 1)])

    assert {first.label, second.label} == {"only (1)", "only (2)"}
    # The ordinal is derived from the sorted member list, not from the order
    # the communities arrived in, so it survives a reordered partition.
    reordered = labels.label_communities(index, [(0, 1), (2, 3)])
    assert reordered[0].label == second.label
    assert reordered[1].label == first.label


def test_a_community_with_no_ranked_entity_is_still_labelled():
    first, second = labels.label_communities([], [(0, 1), (2, 3)])

    assert first.label == f"{labels.UNLABELLED} (1)"
    assert second.label == f"{labels.UNLABELLED} (2)"


# ---------------------------------------------------------------------------
# The orchestrator
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def committing(setup_database):
    """A real session factory with real commits.

    The rollback-per-test session cannot express the property the atomicity
    tests are about — that a failed rewrite leaves the *committed* previous run
    intact — so these few tests own their cleanup instead.
    """
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM memory_communities WHERE project LIKE 't218-%'")
            )
            await cleanup.execute(
                text("DELETE FROM entities WHERE name LIKE 't218-%'")
            )
            await cleanup.execute(
                text("DELETE FROM memories WHERE project LIKE 't218-%'")
            )
            await cleanup.commit()
        await engine.dispose()


async def _seed_two_clusters(session, project=PROJECT, prefix="t218-cluster"):
    left = [await seed_memory(session, project) for _ in range(3)]
    right = [await seed_memory(session, project) for _ in range(3)]
    await session.flush()
    await seed_entity(session, f"{prefix}-left", left)
    await seed_entity(session, f"{prefix}-right", right)
    await session.flush()
    return left, right


async def test_disjoint_clusters_do_not_merge(session):
    """T16, and it is what gives this file teeth.

    Every other test here passes with the partition replaced by a constant
    `[0] * n` — the degenerate single-blob output §3.4's weighting exists to
    prevent. Two entity-disjoint clusters are two disconnected components, and
    a modularity maximiser can never merge those: merging adds no internal
    edges while raising the expected-edges penalty, so modularity strictly
    falls. It asserts a structural property, never a membership list, so
    doc 17 §7's ban is not in play.
    """
    left, right = await _seed_two_clusters(session)

    outcome = await detection.detect_for_project(session, PROJECT)
    await session.flush()

    assert outcome.community_count >= 2
    rows = await repo.list_with_members(session, PROJECT)
    for row in rows:
        members = set(row.memory_ids)
        assert not (members & set(left) and members & set(right)), (
            "two entity-disjoint clusters were merged into one community"
        )


async def test_detection_never_bridges_projects(session):
    """T2, orchestrator half. `entities.memory_ids` reaches every project, so
    the node set being closed under project is the whole isolation story."""
    mine_a = await seed_memory(session)
    mine_b = await seed_memory(session)
    theirs_a = await seed_memory(session, OTHER_PROJECT)
    theirs_b = await seed_memory(session, OTHER_PROJECT)
    await session.flush()
    await seed_entity(
        session, "t218-global", [mine_a, mine_b, theirs_a, theirs_b]
    )
    await session.flush()

    await detection.detect_for_project(session, PROJECT)
    await session.flush()

    members = {m for _, m in await member_rows(session, PROJECT)}
    assert members == {mine_a, mine_b}
    assert await member_rows(session, OTHER_PROJECT) == set()


async def test_an_isolated_memory_joins_no_community(session):
    """T8. Membership is not a partition: a memory sharing no entity with
    anything is not topically related to anything, and sweeping it into an
    everything-community would assert a relationship the projection denies."""
    left, right = await _seed_two_clusters(session)
    orphan = await seed_memory(session)
    await session.flush()

    outcome = await detection.detect_for_project(session, PROJECT)
    await session.flush()

    members = {m for _, m in await member_rows(session, PROJECT)}
    assert orphan not in members
    assert members == set(left) | set(right)
    assert outcome.unassigned_count == 1


async def test_rerunning_on_an_unchanged_corpus_is_stable(session):
    """T7. Reframed to its own declared fallback — count and size multiset,
    never a membership list — plus the rewrite properties that do have teeth:
    the previous ids are gone and no member row is orphaned."""
    await _seed_two_clusters(session)

    first = await detection.detect_for_project(session, PROJECT)
    await session.flush()
    first_ids = await community_ids(session, PROJECT)
    first_sizes = sorted(len(r.memory_ids) for r in await repo.list_with_members(session, PROJECT))

    second = await detection.detect_for_project(session, PROJECT)
    await session.flush()
    second_ids = await community_ids(session, PROJECT)
    second_sizes = sorted(len(r.memory_ids) for r in await repo.list_with_members(session, PROJECT))

    assert first.community_count == second.community_count
    assert first_sizes == second_sizes
    assert first_ids & second_ids == set()

    orphaned = await session.scalar(
        text(
            "SELECT count(*) FROM memory_community_members mm "
            "LEFT JOIN memory_communities c ON c.id = mm.community_id "
            "WHERE c.id IS NULL"
        )
    )
    assert orphaned == 0


async def test_a_tiny_graph_falls_back_to_one_community(session):
    """T10."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await seed_entity(session, "t218-tiny", [a, b])
    await session.flush()

    outcome = await detection.detect_for_project(session, PROJECT)
    await session.flush()

    assert outcome.fallback == detection.FALLBACK_TINY_GRAPH
    (row,) = await repo.list_with_members(session, PROJECT)
    assert set(row.memory_ids) == {a, b}
    assert row.properties["fallback"] == detection.FALLBACK_TINY_GRAPH


async def test_a_timeout_falls_back_to_one_community(session):
    """T11. The degraded answer is still an answer: the graph was real, the
    clustering just did not finish."""
    left, right = await _seed_two_clusters(session)

    outcome = await detection.detect_for_project(
        session, PROJECT, leiden_timeout_seconds=0
    )
    await session.flush()

    assert outcome.fallback == detection.FALLBACK_TIMEOUT
    (row,) = await repo.list_with_members(session, PROJECT)
    assert set(row.memory_ids) == set(left) | set(right)
    assert row.properties["fallback"] == detection.FALLBACK_TIMEOUT


async def test_a_missing_library_writes_nothing_and_deletes_nothing(
    session, monkeypatch
):
    """T9, the second T1.21 guard. A missing clustering library means nothing
    was computed, so collapsing the project into one topic would fabricate a
    result — and deleting the previous run's good topics to write it would be
    T1.21 from another direction."""
    await _seed_two_clusters(session)
    await detection.detect_for_project(session, PROJECT)
    await session.flush()
    before_ids = await community_ids(session, PROJECT)
    before_members = await member_rows(session, PROJECT)
    assert before_ids

    monkeypatch.setitem(sys.modules, "leidenalg", None)
    outcome = await detection.detect_for_project(session, PROJECT)
    await session.flush()

    assert outcome.skipped_reason == detection.SKIPPED_LIBRARY_UNAVAILABLE
    assert outcome.community_count == 0
    assert await community_ids(session, PROJECT) == before_ids
    assert await member_rows(session, PROJECT) == before_members


async def test_an_over_budget_projection_is_skipped_not_truncated(session):
    await _seed_two_clusters(session)
    await detection.detect_for_project(session, PROJECT)
    await session.flush()
    before_ids = await community_ids(session, PROJECT)

    outcome = await detection.detect_for_project(
        session, PROJECT, max_projection_edges=1
    )
    await session.flush()

    assert outcome.skipped_reason == TRUNCATED_TOO_MANY_EDGES
    assert await community_ids(session, PROJECT) == before_ids


async def test_the_run_journals_one_row_naming_no_community_id(session):
    """T12. Ids churn every run, so a community id in `object_id` or anywhere
    in the payload would be exactly the durable reference doc 04 §8.4
    forbids."""
    await _seed_two_clusters(session)

    outcome = await detection.detect_for_project(session, PROJECT)
    await session.flush()
    written = await community_ids(session, PROJECT)

    rows = (
        await session.execute(
            text(
                "SELECT object_id, payload FROM events "
                "WHERE event_type = 'consolidated' AND object_type = 'topic' "
                "AND project = CAST(:p AS text)"
            ),
            {"p": PROJECT},
        )
    ).all()

    assert len(rows) == 1
    (object_id, payload) = rows[0]
    assert object_id is None
    assert payload["community_count"] == outcome.community_count
    assert {c["label"] for c in payload["communities"]} == set(outcome.labels)

    serialized = json.dumps(payload)
    for community_id in written:
        assert str(community_id) not in serialized


async def test_a_failed_rewrite_leaves_the_committed_previous_run_intact(
    committing, monkeypatch
):
    """T5, orchestrator half, with real commits — the property the
    rollback-per-test session cannot express."""
    async with committing() as session:
        left, right = await _seed_two_clusters(session)
        await session.commit()

    first = await detection.run_topic_detection(committing, batch_size=50)
    assert first.communities >= 1

    async with committing() as session:
        before_ids = await community_ids(session, PROJECT)
        before_members = await member_rows(session, PROJECT)
    assert before_ids

    monkeypatch.setattr(
        repo,
        "_INSERT_MEMBERS",
        text("SELECT CAST(:community_id AS uuid), CAST(:rows AS jsonb), 1 / 0"),
    )
    second = await detection.run_topic_detection(committing, batch_size=50)

    assert second.skipped >= 1
    async with committing() as session:
        assert await community_ids(session, PROJECT) == before_ids
        assert await member_rows(session, PROJECT) == before_members


async def test_a_project_with_no_live_memories_is_still_visited(committing):
    """T18. Deriving the cursor from `memories` alone loses a project whose
    memories have all been superseded or archived: it would never be visited
    again and its stale topics would linger forever, surfacing dead memories
    through browsing."""
    async with committing() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        await session.flush()
        await seed_entity(session, "t218-doomed", [a, b])
        # The pointer lives in another project so PROJECT is left with no
        # eligible memory at all.
        pointer = await seed_memory(session, OTHER_PROJECT)
        await session.commit()

    await detection.run_topic_detection(committing, batch_size=50)
    async with committing() as session:
        assert await community_ids(session, PROJECT)

    async with committing() as session:
        await session.execute(
            text(
                "UPDATE memories SET status = 'superseded', "
                "superseded_by = CAST(:p AS uuid) "
                "WHERE project = CAST(:project AS text)"
            ),
            {"p": str(pointer), "project": PROJECT},
        )
        await session.commit()

    async with committing() as session:
        assert PROJECT in await detection.next_projects(session, None, 50)

    await detection.run_topic_detection(committing, batch_size=50)

    async with committing() as session:
        assert await community_ids(session, PROJECT) == set()


async def test_the_cursor_rotates_in_project_order(committing):
    async with committing() as session:
        await seed_memory(session, PROJECT)
        await seed_memory(session, OTHER_PROJECT)
        await session.commit()

    async with committing() as session:
        first = await detection.next_projects(session, None, 1)
        after = await detection.next_projects(session, first[0], 50)

    assert first == [min(first[0], *after)]
    assert first[0] not in after
    assert after == sorted(after)


def test_the_connected_filter_keeps_isolated_nodes_out_of_a_community():
    """T8's mechanism, driven directly.

    A degree-zero vertex changes modularity by exactly nothing wherever it is
    placed, so its assignment is implementation-defined; leidenalg happens to
    give it its own community today, which `min_community_size` would then
    drop. That makes the filter's failure unreachable through the library and
    the guarantee an accident of a library version rather than a property of
    this code — so it is asserted here against a membership vector that does
    place an isolated node inside a real community.
    """
    membership = [0, 0, 0, 0]

    groups = detection._groups_from_membership(membership, (0, 1, 2), 2)

    assert groups == [(0, 1, 2)]

def _partition_spy(monkeypatch, seen: dict):
    real = detection.partition_graph

    async def spy(n_nodes, edges, **kwargs):
        seen.clear()
        seen.update(kwargs)
        return await real(n_nodes, edges, **kwargs)

    monkeypatch.setattr(detection, "partition_graph", spy)


async def test_the_resolution_knob_reaches_the_clustering(session, monkeypatch):
    """Without this the knob is decoration: dropping `resolution=` from the
    call leaves the whole suite green."""
    await _seed_two_clusters(session)
    seen: dict = {}
    _partition_spy(monkeypatch, seen)

    await detection.detect_for_project(session, PROJECT)
    assert seen["resolution"] == detection.DEFAULT_RESOLUTION
    assert seen["n_iterations"] == -1

    await detection.detect_for_project(session, PROJECT, resolution=0.25)
    assert seen["resolution"] == 0.25


async def test_a_large_graph_tightens_resolution_and_iterations(
    session, monkeypatch
):
    """The >10k-node branch, driven through `large_graph_nodes` rather than by
    seeding ten thousand memories."""
    await _seed_two_clusters(session)
    seen: dict = {}
    _partition_spy(monkeypatch, seen)

    await detection.detect_for_project(session, PROJECT, large_graph_nodes=1)
    await session.flush()

    assert seen["resolution"] == detection.LARGE_GRAPH_RESOLUTION
    assert seen["n_iterations"] == detection.LARGE_GRAPH_ITERATIONS
    rows = await repo.list_with_members(session, PROJECT)
    assert rows
    assert all(
        row.properties["resolution"] == detection.LARGE_GRAPH_RESOLUTION
        for row in rows
    )


async def test_phase_c_runs_with_no_transaction_open(committing, monkeypatch):
    """Phase R commits before the clustering starts.

    `leiden_timeout_seconds` runs to 600, so holding the read transaction
    across Phase C would leave a pooled connection `idle in transaction` for
    minutes per project — pinning xmin, and inviting a kill wherever
    `idle_in_transaction_session_timeout` is set.
    """
    async with committing() as session:
        await _seed_two_clusters(session)
        await session.commit()

    observed: dict = {}
    real = detection.partition_graph

    async def spy(n_nodes, edges, **kwargs):
        observed["in_transaction"] = probe.in_transaction()
        return await real(n_nodes, edges, **kwargs)

    monkeypatch.setattr(detection, "partition_graph", spy)

    async with committing() as probe:
        await detection.detect_for_project(probe, PROJECT)
        await probe.commit()

    assert observed["in_transaction"] is False


async def test_the_graph_build_stays_off_the_event_loop(monkeypatch):
    """The build is part of the blocking work, not a cheap preamble: at the
    2M-edge budget it stalls for ~0.4s, in the process serving capture and
    retrieval."""
    import igraph

    threads: list[str] = []
    real_graph = igraph.Graph

    def recording(*args, **kwargs):
        threads.append(threading.current_thread().name)
        return real_graph(*args, **kwargs)

    monkeypatch.setattr(igraph, "Graph", recording)

    result = await leiden.partition_graph(3, [(0, 1), (1, 2)])

    assert result.outcome == "ok"
    assert threads
    assert all(name.startswith("leiden") for name in threads), threads
    assert threading.current_thread().name not in threads


async def test_an_aborted_project_journals_the_reason_it_aborted(
    committing, monkeypatch
):
    """`_journal_abort` writes from a fresh session because the abort rolled
    its own transaction back — a journal row written inside it would have gone
    with it, and a skipped project would read as one the run never reached."""
    async with committing() as session:
        await _seed_two_clusters(session)
        await session.commit()

    for reason in (repo.CROSS_PROJECT_VIOLATION, repo.STALE_SNAPSHOT):
        async def raiser(*args, _reason=reason, **kwargs):
            raise repo.MemberWriteError(_reason, "forced for the drill")

        monkeypatch.setattr(
            detection, "replace_project_communities", raiser
        )
        outcome = await detection.run_topic_detection(committing, batch_size=50)
        assert outcome.skipped >= 1

        async with committing() as reader:
            journalled = await reader.scalar(
                text(
                    "SELECT count(*) FROM events "
                    "WHERE event_type = 'consolidated' "
                    "AND object_type = 'topic' "
                    "AND project = CAST(:p AS text) "
                    "AND payload->>'skipped_reason' = CAST(:r AS text)"
                ),
                {"p": PROJECT, "r": reason},
            )
        assert journalled >= 1, reason


# ---------------------------------------------------------------------------
# The project-move door
# ---------------------------------------------------------------------------


async def test_moving_a_memory_between_projects_clears_its_memberships(
    session, client, auth_headers
):
    """T19. `PUT /memories/{id}` is a live endpoint and `MemoryUpdate.project`
    is writable, so once the composite FK is live the update raises unless the
    memberships go first. The fix has to sit *before* `memory_repo.update`: it
    flushes, so the post-update project branch that looks like its natural home
    is unreachable by then."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()

    response = await client.put(
        f"/api/v1/memories/{a}",
        json={"project": OTHER_PROJECT},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["project"] == OTHER_PROJECT
    assert {m for _, m in await member_rows(session, PROJECT)} == {b}


async def test_writing_the_same_project_leaves_memberships_intact(
    session, client, auth_headers
):
    """T20. Comparing against the memory's current project, not merely the
    field's presence: a no-op write must not evict a memory from its topic."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await session.flush()
    await repo.replace_project_communities(
        session, PROJECT, [repo.CommunityDraft(label="alpha", memory_ids=(a, b))]
    )
    await session.flush()

    response = await client.put(
        f"/api/v1/memories/{a}",
        json={"project": PROJECT},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert {m for _, m in await member_rows(session, PROJECT)} == {a, b}


# ---------------------------------------------------------------------------
# Invariant 15
# ---------------------------------------------------------------------------

BACKEND = pathlib.Path(__file__).resolve().parent.parent
DETECTOR_BASENAME = "memory_community_detection"
DETECTOR_MODULE = f"app.services.{DETECTOR_BASENAME}"
DETECTOR_PATH = "app/services/memory_community_detection.py"

# The Tier-C umbrella, and the only file besides the detector itself permitted
# to name it (T2.53). The guard's point is that nothing on a *capture or
# retrieval* path may reach detection to accelerate a gate; the dream-job
# family is the sanctioned scheduled caller, exactly as
# `verification_recompute.py` is for the ladder in
# `tests/test_verification_ladder.py`'s `_ALLOWED_LADDER_FILES`.
#
# Registering it here does not weaken the guard: `dream_jobs.py` is itself
# covered by `tests/test_dream_jobs.py`'s family scan, which forbids every
# other module under `app/` from reaching *it*. The two guards compose into
# "detection is reachable only from the scheduler".
DETECTOR_UMBRELLA_PATH = "app/services/dream_jobs.py"
_DETECTOR_EXEMPT = frozenset({DETECTOR_PATH, DETECTOR_UMBRELLA_PATH})

# T2.67 lifted this scan's walk into the shared `_reachability_scan` module
# so it and `tests/test_dream_jobs.py`'s family scan share one implementation
# instead of two independently-drifting AST walks. `_docstring_constants` is
# `_reachability_scan.docstring_node_ids` under its old name — kept as an
# alias because nothing else in this file needs the rename.
from tests._reachability_scan import (  # noqa: E402
    ReachabilityRules,
    app_sources,
    docstring_node_ids as _docstring_constants,
    find_forbidden_reach,
)

# `forbidden_literals` carries only the bare basename (exact-match route);
# the dotted `DETECTOR_MODULE` path belongs in `forbidden_modules` only —
# it is covered there by the boundary-substring literal check T2.67's
# Critical fix added (exec/eval, a bytes-decoded literal, a loader-spec
# string), and putting it in both would just be redundant, not stronger.
_DETECTOR_RULES = ReachabilityRules(
    forbidden_modules=frozenset({DETECTOR_MODULE}),
    forbidden_attrs=frozenset({DETECTOR_BASENAME}),
    forbidden_literals=frozenset({DETECTOR_BASENAME}),
)


def _detector_offenders(paths, backend_root) -> list[str]:
    """Every route from a file under `app/` to the detector module.

    Delegates to the shared scanner (`_reachability_scan.find_forbidden_reach`)
    for all three routes — import, attribute, and literal — rather than the
    two this function checked before T2.67 (import and literal only). The
    attribute route is what closes T2.18's own residual: `from app import
    services` followed by `services.memory_community_detection.detect(...)`
    named the module in no import statement at all, and was invisible to
    both the old line-based scan and the first AST rebuild.
    """
    return find_forbidden_reach(
        paths, backend_root, _DETECTOR_RULES, skip_files=_DETECTOR_EXEMPT
    )


def test_no_app_code_reaches_the_detector():
    """T13. Detection is Tier C: nothing on a capture or retrieval path may
    reach it to 'accelerate' a gate."""
    assert not _detector_offenders(app_sources(BACKEND), BACKEND)


def test_the_detector_exemption_holds_exactly_the_module_and_its_umbrella():
    """The allowlist is two entries and must stay two.

    A guard whose exemption list can grow quietly is a guard that stops
    meaning anything — this is the same pin `test_verification_ladder.py`
    keeps on `_ALLOWED_LADDER_FILES`. `dream_jobs.py` joined when T2.53 wired
    the productive runner; a third entry is a new path to Tier-C work and
    belongs in review, not in a passing test run.
    """
    assert _DETECTOR_EXEMPT == {DETECTOR_PATH, DETECTOR_UMBRELLA_PATH}


def test_the_detector_scan_still_catches_a_non_exempt_reacher(tmp_path):
    """The exemption is per-file, not a hole in the rules: an ordinary module
    naming the detector is still an offender."""
    offender = _write(
        tmp_path,
        "from app.services.memory_community_detection import run_topic_detection\n",
    )

    assert _detector_offenders([offender], tmp_path)


def _write(tmp_path, body: str):
    offender = tmp_path / "app" / "services" / "pipeline.py"
    offender.parent.mkdir(parents=True, exist_ok=True)
    offender.write_text(body)
    return offender


def test_the_detector_scan_catches_a_plain_import(tmp_path):
    """The negative control: a scan nobody has seen fail is a scan nobody
    knows works."""
    offender = _write(
        tmp_path,
        "from app.services.memory_community_detection import detect_for_project\n",
    )

    offenders = _detector_offenders([offender], tmp_path)

    assert len(offenders) == 1
    assert offenders[0].startswith("app/services/pipeline.py:1:")


def test_the_detector_scan_catches_a_wrapped_import(tmp_path):
    """The form an import formatter produces, and the one a line-based scan
    misses entirely — the import statement spans three lines and no single
    line carries both the package and the module."""
    offender = _write(
        tmp_path,
        "from app.services import (\n    memory_community_detection,\n)\n",
    )

    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_split_dotted_path(tmp_path):
    """Adjacent string literals concatenate at parse time, so a dynamic reach
    spelled across two fragments is one constant by the time the scan sees it
    — which a substring match over the raw source would never find."""
    offender = _write(
        tmp_path,
        'from importlib import import_module\n'
        'import_module("app.services." "memory_community_detection")\n',
    )

    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_relative_import(tmp_path):
    offender = _write(tmp_path, "from . import memory_community_detection\n")

    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_relative_symbol_import(tmp_path):
    """A relative import of a *symbol inside* the detector module, not the
    module itself, is a second shape a naive combined `base.alias` string
    misses: `base` alone ("memory_community_detection") carries the real
    module path, and appending the imported symbol name pushes a
    trailing-segment comparison one slot out of alignment. Found by
    inventing an evasion the existing battery did not cover, per the
    mutation-discipline note in T2.67's brief."""
    offender = _write(
        tmp_path, "from .memory_community_detection import detect_for_project\n"
    )

    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_parent_package_attribute_reach(tmp_path):
    """T2.18's own residual, closed here: importing the parent package and
    reaching the detector through attribute access names the detector in no
    import statement at all, so the import route alone is structurally blind
    to it — inert until something imports `app.services` as a bare handle,
    which is exactly what this shape does."""
    offender = _write(
        tmp_path,
        "from app import services\n"
        "\n"
        "def call():\n"
        "    return services.memory_community_detection.detect_for_project\n",
    )

    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_an_exec_import(tmp_path):
    """T2.67's Critical fix, shared with the family scan: the literal route
    used to match a `str` constant by exact equality only, so a dotted path
    spelled inside an `exec` body — one whole-line string, never equal to
    the bare path alone — passed clean."""
    offender = _write(tmp_path, 'exec("import app.services.memory_community_detection")\n')
    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_bytes_decoded_dynamic_import(tmp_path):
    """`bytes` constants were not examined at all before this fix."""
    offender = _write(
        tmp_path,
        "from importlib import import_module\n"
        'import_module(b"app.services.memory_community_detection".decode())\n',
    )
    offenders = _detector_offenders([offender], tmp_path)
    assert offenders
    assert any("bytes" in o for o in offenders), offenders


def test_the_detector_scan_catches_a_loader_spec_literal(tmp_path):
    offender = _write(
        tmp_path, '_SPEC = "app.services.memory_community_detection:detect_for_project"\n'
    )
    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_catches_a_relative_loader_call_with_package(tmp_path):
    """Restored after a re-review's Important finding: `import_module`
    called with a relative literal name and a literal `package=` is a
    fully static, literal-spelled executable reach that predates this
    scan's own history of misses — shared across all three scans via the
    walker rather than fixed here alone."""
    offender = _write(
        tmp_path,
        "from importlib import import_module\n"
        'import_module(".memory_community_detection", package="app.services")\n',
    )
    offenders = _detector_offenders([offender], tmp_path)
    assert offenders
    assert any("loader-call" in o for o in offenders), offenders


def test_the_detector_scan_catches_a_non_docstring_prose_constant(tmp_path):
    offender = _write(
        tmp_path,
        "def f():\n"
        "    pass\n"
        '_NOTE = "See app.services.memory_community_detection for the implementation"\n',
    )
    assert _detector_offenders([offender], tmp_path)


def test_the_detector_scan_does_not_flag_a_bare_name_inside_ordinary_prose(tmp_path):
    """The bare basename `forbidden_literals` route stays exact-match only.
    A non-docstring constant that merely *mentions* the detector's own bare
    basename inside a full sentence — not a docstring (so the docstring
    exemption is not what is being tested here), not the dotted
    `app.services.` path (so the boundary-substring module route is not
    what is being tested here either) — must not be flagged: a
    boundary-substring check over `forbidden_literals` would catch this
    sentence (the basename sits at a clean word boundary on both sides),
    which is exactly the false-positive shape this discipline exists to
    avoid. Mutating the exact check to `_contains_at_boundary` and rerunning
    this file's tests during T2.67's re-review verification made only this
    test (and its family-scan counterpart) fail — confirming it actually
    exercises the discipline it names, unlike an earlier draft of this test
    that searched for a dream-job key the detector scan's own vocabulary
    does not even contain."""
    offender = _write(
        tmp_path,
        'NOTE = "Do not call memory_community_detection directly from a hot path."\n',
    )
    assert _detector_offenders([offender], tmp_path) == []


def test_the_detector_scan_does_not_fail_on_prose(tmp_path):
    """The other half of the control. The repository's docstring has to name
    the module to explain why it exists, so a scan that flagged prose would be
    loosened away the first time it fired."""
    innocent = tmp_path / "app" / "repositories" / "memory_communities.py"
    innocent.parent.mkdir(parents=True)
    innocent.write_text(
        '"""No file under `app/` may import '
        'app.services.memory_community_detection."""\n'
    )

    assert _detector_offenders([innocent], tmp_path) == []


def test_the_detector_scan_does_not_fail_on_a_docstring_that_is_the_bare_module_path(
    tmp_path,
):
    """The literal route matches a string constant by exact equality, not by
    substring, so the sentence-shaped prose test above passes for a reason
    unrelated to docstring exemption: no full sentence equals the bare
    module path. This is the case where the exemption actually carries
    weight — a docstring whose entire text *is* exactly the forbidden
    literal, the shape a bare "see also" reference would take."""
    innocent = tmp_path / "app" / "repositories" / "memory_communities.py"
    innocent.parent.mkdir(parents=True)
    innocent.write_text('"""app.services.memory_community_detection"""\n')

    assert _detector_offenders([innocent], tmp_path) == []


def test_the_detector_scan_does_not_fail_on_the_sibling_repository(tmp_path):
    """`memory_communities` is not `memory_community_detection`; a sloppier
    substring would forbid the repository every consumer must use."""
    innocent = _write(
        tmp_path,
        "from app.repositories import memory_communities\n",
    )

    assert _detector_offenders([innocent], tmp_path) == []


# ---------------------------------------------------------------------------
# The code-side detector, on the shared kernel
# ---------------------------------------------------------------------------


async def _seed_code_graph(session, repo_id, clusters):
    await session.execute(
        text(
            "INSERT INTO repositories (id, name, status) "
            "VALUES (CAST(:id AS uuid), 't218-repo', 'ready')"
        ),
        {"id": str(repo_id)},
    )
    for cluster, keys in enumerate(clusters):
        for key in keys:
            await session.execute(
                text(
                    "INSERT INTO code_graph_nodes "
                    "(repo_id, kind, key, label, properties) "
                    "VALUES (CAST(:r AS uuid), 'symbol', :k, :k, "
                    "CAST(:p AS jsonb))"
                ),
                {
                    "r": str(repo_id),
                    "k": key,
                    "p": json.dumps(
                        {"kind": "function", "file_path": f"pkg{cluster}/mod.py"}
                    ),
                },
            )
        for source, target in zip(keys, keys[1:] + keys[:1]):
            await session.execute(
                text(
                    "INSERT INTO code_edges (repo_id, source_kind, source_key, "
                    "target_kind, target_key, edge_type, properties) "
                    "VALUES (CAST(:r AS uuid), 'symbol', :s, 'symbol', :t, "
                    "'calls', CAST('{}' AS jsonb))"
                ),
                {"r": str(repo_id), "s": source, "t": target},
            )
    await session.flush()


async def _code_communities(session, repo_id) -> int:
    return await session.scalar(
        text(
            "SELECT count(*) FROM code_graph_nodes "
            "WHERE repo_id = CAST(:r AS uuid) AND kind = 'community'"
        ),
        {"r": str(repo_id)},
    )


async def test_the_code_detector_still_clusters_through_the_kernel(session):
    """Step 9 is a refactor of code nobody was exercising, so it gets a test
    rather than an inspection: two call-disjoint symbol clusters must still
    produce at least two communities with `member_of` edges."""
    repo_id = new_id()
    await _seed_code_graph(
        session,
        repo_id,
        [["t218-a1", "t218-a2", "t218-a3"], ["t218-b1", "t218-b2", "t218-b3"]],
    )

    members = await CommunityDetector(session, str(repo_id)).detect()
    await session.flush()

    assert members == 6
    assert await _code_communities(session, repo_id) >= 2
    edges = await session.scalar(
        text(
            "SELECT count(*) FROM code_edges "
            "WHERE repo_id = CAST(:r AS uuid) AND edge_type = 'member_of'"
        ),
        {"r": str(repo_id)},
    )
    assert edges == 6


async def test_the_code_detector_keeps_its_communities_without_the_library(
    session, monkeypatch
):
    """The unavailable branch has to return before the deletes, or a missing
    library wipes the previous run and writes nothing in its place."""
    repo_id = new_id()
    await _seed_code_graph(
        session,
        repo_id,
        [["t218-c1", "t218-c2", "t218-c3"], ["t218-d1", "t218-d2", "t218-d3"]],
    )
    await CommunityDetector(session, str(repo_id)).detect()
    await session.flush()
    before = await _code_communities(session, repo_id)
    assert before >= 2

    monkeypatch.setitem(sys.modules, "leidenalg", None)
    members = await CommunityDetector(session, str(repo_id)).detect()
    await session.flush()

    assert members == 0
    assert await _code_communities(session, repo_id) == before


def test_the_config_seam_keeps_the_placeholders_batch_key():
    """T2.53 swaps the placeholder's `config_schema` for this one.

    `JobRegistry.set_config` merges `{**cfg.config, **partial}` and never drops
    a key, so a schema swap that renamed `batch_size` would orphan any value an
    operator had already persisted under it — silently, with the old value
    still sitting in the config row. Keeping the key, its default and its
    ceiling is what makes the swap safe; the new knobs are additions.
    """
    engine = create_async_engine(settings.test_database_url)
    registry = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))
    register_dream_jobs(registry)
    try:
        placeholder = {
            fd.key: fd
            for fd in registry.get(TOPIC_DETECTION_JOB_KEY).config_schema
        }
        seam = {fd.key: fd for fd in detection.TOPIC_DETECTION_CONFIG_SCHEMA}

        assert set(placeholder) <= set(seam)
        for key, field in placeholder.items():
            assert seam[key].default == field.default
            assert seam[key].min == field.min
            assert seam[key].max == field.max
    finally:
        engine.sync_engine.dispose()
