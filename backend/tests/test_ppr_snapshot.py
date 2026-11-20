"""The PPR snapshot, its refresh job, and the graph arms' inertness (T2.32).

**The organising principle is the same split `test_communities.py` uses.** The
snapshot's *construction* — which entities become vertices, which pairs become
edges, what a pair weighs — is fully deterministic and gets value-level
assertions. PageRank's *numbers* are an iterative library computation, so what
is asserted about them is structural: mass reaches what the seed connects to,
never what it does not, and an empty seed produces nothing at all.

**The load-bearing test is `test_the_arm_is_inert_at_weight_zero`.** Everything
else here could pass while the arm quietly changed the shipped order for every
install, because the flags default off and no other suite would notice. It
compares the fused rows against a fusion that never saw a PPR list — the same
rows in the same order, not merely the same scores, since a zero-weight list
still *admits* rows it alone found.
"""

from __future__ import annotations

import ast
import json
import pathlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text

from app.config import FEATURE_FLAGS_DEFAULTS
from app.services import ppr_snapshot as ppr
from app.services.hybrid_search import HybridSearchService
from app.services.rank_fusion import LIST_WEIGHT_KEYS, RANK_ARMS, ppr_list_weight
from app.utils.ids import new_id

PROJECT = "t232-ppr"
OTHER_PROJECT = "t232-ppr-other"

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)

BACKEND = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures — direct SQL, so this suite is offline: no pipeline, no embedder,
# no model call. Hand-populating `entities.memory_ids` is also the only way to
# build the cross-project entity the isolation test needs.
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
    VALUES (:name, :entity_type, '{}'::jsonb, CAST(:memory_ids AS uuid[]))
    RETURNING id
    """
)

_INSERT_RELATION = text(
    """
    INSERT INTO entity_relations (
        source_entity_id, target_entity_id, rel_type, memory_ids
    )
    VALUES (
        CAST(:src AS uuid), CAST(:tgt AS uuid),
        :rel_type, CAST(:memory_ids AS uuid[])
    )
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
    session, name: str, memory_ids: list[UUID], *, entity_type: str = "tool"
) -> UUID:
    result = await session.execute(
        _INSERT_ENTITY,
        {
            "name": name,
            "entity_type": entity_type,
            "memory_ids": [str(m) for m in memory_ids],
        },
    )
    return result.scalar_one()


async def seed_relation(
    session, src: UUID, tgt: UUID, memory_ids: list[UUID], *, rel_type: str = "USES"
) -> UUID:
    result = await session.execute(
        _INSERT_RELATION,
        {
            "src": str(src),
            "tgt": str(tgt),
            "rel_type": rel_type,
            "memory_ids": [str(m) for m in memory_ids],
        },
    )
    return result.scalar_one()


async def build(session, project: str = PROJECT, **kwargs) -> ppr.BuildOutcome:
    return await ppr.build_snapshot(session, project, **kwargs)


# ---------------------------------------------------------------------------
# The node set
# ---------------------------------------------------------------------------


async def test_only_entities_of_live_memories_become_vertices(session):
    """Four exclusions, every one of them silent when wrong.

    `expires_at` is the load-bearing clause for the same reason the topic
    projection records: sweeping is periodic, so an expired-but-unswept row is
    still `status='active'`, and a status-only predicate would let a memory the
    system has already promised to forget carry PageRank mass.
    """
    live = await seed_memory(session)
    superseded = await seed_memory(
        session, status="superseded", superseded_by=live,
    )
    archived = await seed_memory(session, is_archived=True)
    expired = await seed_memory(session, expires_at=NOW - timedelta(days=1))
    future = await seed_memory(session, expires_at=NOW + timedelta(days=3650))

    keeper = await seed_entity(session, "keeper", [live])
    also_keeper = await seed_entity(session, "future-keeper", [future])
    for name, mem in (
        ("gone-superseded", superseded),
        ("gone-archived", archived),
        ("gone-expired", expired),
    ):
        await seed_entity(session, name, [mem])

    outcome = await build(session)

    assert outcome.snapshot is not None
    assert set(outcome.snapshot.entity_ids) == {str(keeper), str(also_keeper)}


async def test_an_entity_carries_only_this_projects_memories(session):
    """The mapping PPR projects mass through is project-scoped even when the
    entity row is not. `entities` is global by design — one row accumulates
    every memory that asserts it — so an unscoped read would let a query in one
    project pull another project's memories into its own ranked list, which is
    the leak doc 02 §9 names, arriving through the graph instead of through
    SQL."""
    mine = await seed_memory(session, PROJECT)
    theirs = await seed_memory(session, OTHER_PROJECT)
    shared = await seed_entity(session, "postgres", [mine, theirs])

    outcome = await build(session)

    assert outcome.snapshot is not None
    index = outcome.snapshot.index_of[str(shared)]
    assert outcome.snapshot.memory_ids[index] == (str(mine),)


async def test_a_project_with_no_live_memory_yields_no_snapshot(session):
    pointer = await seed_memory(session, OTHER_PROJECT)
    await seed_memory(
        session, PROJECT, status="superseded", superseded_by=pointer,
    )
    outcome = await build(session)
    assert outcome.snapshot is None
    assert outcome.skipped_reason == ppr.SKIPPED_NO_NODES


# ---------------------------------------------------------------------------
# The edge set
# ---------------------------------------------------------------------------


async def test_relations_between_two_nodes_become_one_weighted_edge(session):
    memory = await seed_memory(session)
    a = await seed_entity(session, "alpha", [memory])
    b = await seed_entity(session, "beta", [memory])
    await seed_relation(session, a, b, [memory], rel_type="USES")

    outcome = await build(session)
    snapshot = outcome.snapshot

    assert snapshot is not None
    assert snapshot.relation_edges == 1
    assert snapshot.graph.ecount() == 1
    i, j = snapshot.index_of[str(a)], snapshot.index_of[str(b)]
    assert snapshot.graph.are_adjacent(i, j)


async def test_a_pair_asserted_through_two_relation_types_weighs_more(session):
    """`entity_relations` is unique on (source, target, rel_type), so two rows
    for one pair mean two independently asserted relationships. Counting rows
    says that without inventing a magnitude — and collapsing them to weight 1
    would make a pair the extractor connected twice indistinguishable from one
    it connected once."""
    memory = await seed_memory(session)
    a = await seed_entity(session, "alpha", [memory])
    b = await seed_entity(session, "beta", [memory])
    c = await seed_entity(session, "gamma", [memory])
    await seed_relation(session, a, b, [memory], rel_type="USES")
    await seed_relation(session, a, b, [memory], rel_type="DEPENDS_ON")
    await seed_relation(session, a, c, [memory], rel_type="USES")

    snapshot = (await build(session)).snapshot
    assert snapshot is not None

    def weight_between(x: UUID, y: UUID) -> float:
        edge = snapshot.graph.get_eid(
            snapshot.index_of[str(x)], snapshot.index_of[str(y)]
        )
        return snapshot.graph.es[edge]["weight"]

    assert weight_between(a, b) == 2.0
    assert weight_between(a, c) == 1.0


async def test_both_directions_of_one_pair_are_one_undirected_edge(session):
    """Keying on the ordered pair would give one conceptual edge two entries
    with half its weight each — the same silent halving invariant 9's id drift
    produces at the fusion."""
    memory = await seed_memory(session)
    a = await seed_entity(session, "alpha", [memory])
    b = await seed_entity(session, "beta", [memory])
    await seed_relation(session, a, b, [memory], rel_type="USES")
    await seed_relation(session, b, a, [memory], rel_type="USES")

    snapshot = (await build(session)).snapshot
    assert snapshot is not None
    assert snapshot.graph.ecount() == 1
    edge = snapshot.graph.get_eid(
        snapshot.index_of[str(a)], snapshot.index_of[str(b)]
    )
    assert snapshot.graph.es[edge]["weight"] == 2.0


async def test_a_relation_reaching_outside_the_project_builds_no_edge(session):
    mine = await seed_memory(session, PROJECT)
    theirs = await seed_memory(session, OTHER_PROJECT)
    inside = await seed_entity(session, "inside", [mine])
    outside = await seed_entity(session, "outside", [theirs])
    await seed_relation(session, inside, outside, [mine])

    snapshot = (await build(session)).snapshot
    assert snapshot is not None
    assert snapshot.node_count == 1
    assert snapshot.graph.ecount() == 0


async def test_a_self_relation_builds_no_edge(session):
    """A self-loop adds mass to the vertex it already came from, so it
    inflates exactly the entity a query seeded on and looks like signal."""
    memory = await seed_memory(session)
    a = await seed_entity(session, "alpha", [memory])
    await seed_relation(session, a, a, [memory])

    snapshot = (await build(session)).snapshot
    assert snapshot is not None
    assert snapshot.graph.ecount() == 0


async def test_a_graph_past_the_edge_bound_is_skipped_not_truncated(session):
    memory = await seed_memory(session)
    a = await seed_entity(session, "alpha", [memory])
    b = await seed_entity(session, "beta", [memory])
    await seed_relation(session, a, b, [memory])

    outcome = await build(session, max_snapshot_edges=0)

    assert outcome.snapshot is None
    assert outcome.skipped_reason == ppr.SKIPPED_TOO_MANY_EDGES


async def test_synonymy_above_the_node_ceiling_is_recorded_not_hidden(session):
    """The skip has to be visible on the artefact. A relation-only snapshot
    that does not say so is indistinguishable from one whose entities simply
    had no near neighbours, and the arm's measurement would silently be taken
    against a different graph than the one it names."""
    memory = await seed_memory(session)
    await seed_entity(session, "alpha", [memory])
    await seed_entity(session, "beta", [memory])

    outcome = await build(
        session, fingerprint="fake-model|8", synonymy_max_nodes=1,
    )

    assert outcome.snapshot is not None
    assert ppr.DEGRADED_SYNONYMY_SKIPPED in outcome.snapshot.degraded
    assert outcome.snapshot.synonymy_edges == 0


# ---------------------------------------------------------------------------
# Spending it
# ---------------------------------------------------------------------------


async def _line_graph(session):
    """a — b — c, plus an isolated d, all in one memory each."""
    m_a = await seed_memory(session, content="a")
    m_b = await seed_memory(session, content="b")
    m_c = await seed_memory(session, content="c")
    m_d = await seed_memory(session, content="d")
    a = await seed_entity(session, "alpha", [m_a])
    b = await seed_entity(session, "beta", [m_b])
    c = await seed_entity(session, "gamma", [m_c])
    d = await seed_entity(session, "delta", [m_d])
    await seed_relation(session, a, b, [m_a])
    await seed_relation(session, b, c, [m_b])
    snapshot = (await build(session)).snapshot
    assert snapshot is not None
    return snapshot, {"a": a, "b": b, "c": c, "d": d}, {
        "a": m_a, "b": m_b, "c": m_c, "d": m_d,
    }


async def test_mass_flows_along_relations_and_stops_at_the_component(session):
    """What PPR actually guarantees, and deliberately not more.

    **The seed does not necessarily hold the most mass**, which is worth
    stating because it is the assertion this test was first written with. On
    the line a—b—c seeded at `a`, the middle vertex `b` finishes ahead of the
    seed: it has twice the degree, and every walk from `a` passes through it.
    Pinning "the seed ranks first" would be pinning this graph's shape, and it
    would fail the first time a real project's seed sat on a leaf.

    What is structural: mass never crosses into another component, it decays
    with distance from the seed, and it sums to one.
    """
    snapshot, ents, _ = await _line_graph(session)
    seeds = [snapshot.index_of[str(ents["a"])]]

    mass = ppr.personalized_pagerank(snapshot, seeds)

    at = lambda name: mass[snapshot.index_of[str(ents[name])]]  # noqa: E731
    assert at("a") > at("c") > 0.0
    assert at("b") > 0.0
    assert at("d") == pytest.approx(0.0, abs=1e-9)
    assert sum(mass) == pytest.approx(1.0)


async def test_the_seed_is_what_the_ranking_depends_on(session):
    """The guard against silently running unseeded PageRank: a global-
    popularity list fused into every query would look plausible in every
    eyeball check and rank the project's hubs into every result set. If the
    personalization vector were ignored, these two distributions would be
    identical."""
    snapshot, ents, _ = await _line_graph(session)

    from_a = ppr.personalized_pagerank(
        snapshot, [snapshot.index_of[str(ents["a"])]]
    )
    from_c = ppr.personalized_pagerank(
        snapshot, [snapshot.index_of[str(ents["c"])]]
    )

    at_a = snapshot.index_of[str(ents["a"])]
    assert from_a[at_a] > from_c[at_a]


async def test_an_empty_seed_set_produces_no_mass_rather_than_uniform(session):
    """Falling back to unseeded PageRank would put the project's hub entities
    into every result set regardless of the query — a different signal wearing
    this one's name, and one that looks plausible in every eyeball check."""
    snapshot, _, _ = await _line_graph(session)
    assert ppr.personalized_pagerank(snapshot, []) == [0.0] * snapshot.node_count


async def test_seeds_resolve_from_the_snapshots_own_mapping(session):
    snapshot, ents, mems = await _line_graph(session)
    seeds = ppr.seed_vertices_for_memories(snapshot, [str(mems["a"])])
    assert seeds == [snapshot.index_of[str(ents["a"])]]
    assert ppr.seed_vertices_for_memories(snapshot, []) == []
    assert ppr.seed_vertices_for_memories(snapshot, [str(new_id())]) == []


async def test_memory_scores_sum_the_mass_of_their_asserting_entities(session):
    memory = await seed_memory(session, content="shared")
    lonely = await seed_memory(session, content="lonely")
    a = await seed_entity(session, "alpha", [memory])
    b = await seed_entity(session, "beta", [memory])
    c = await seed_entity(session, "gamma", [lonely])
    await seed_relation(session, a, b, [memory])
    await seed_relation(session, b, c, [memory])

    snapshot = (await build(session)).snapshot
    assert snapshot is not None
    mass = [0.0] * snapshot.node_count
    for entity, value in ((a, 0.5), (b, 0.3), (c, 0.4)):
        mass[snapshot.index_of[str(entity)]] = value

    ranked = ppr.rank_memories(snapshot, mass)

    by_id = {row["memory_id"]: row["score"] for row in ranked}
    assert by_id[str(memory)] == pytest.approx(0.8)
    assert by_id[str(lonely)] == pytest.approx(0.4)
    assert ranked[0]["memory_id"] == str(memory)
    assert all(isinstance(row["memory_id"], str) for row in ranked)


async def test_the_arm_returns_nothing_rather_than_raising_when_cold(session):
    cache = ppr.SnapshotCache()
    assert await ppr.ppr_ranked_list(PROJECT, [str(new_id())], limit=10, cache=cache) == []
    assert await ppr.ppr_ranked_list(None, [str(new_id())], limit=10, cache=cache) == []


async def test_the_arm_ranks_against_the_cached_snapshot(session):
    snapshot, _, mems = await _line_graph(session)
    cache = ppr.SnapshotCache()
    cache.put(snapshot)

    ranked = await ppr.ppr_ranked_list(
        PROJECT, [str(mems["a"])], limit=10, cache=cache,
    )

    ranked_ids = [row["memory_id"] for row in ranked]
    assert set(ranked_ids) == {str(mems["a"]), str(mems["b"]), str(mems["c"])}
    # The far end of the line ranks below the seed; the middle may outrank
    # both by degree, which is why only this pair is ordered here.
    assert ranked_ids.index(str(mems["a"])) < ranked_ids.index(str(mems["c"]))
    assert str(mems["d"]) not in set(ranked_ids)


# ---------------------------------------------------------------------------
# Inertness — the arms default off and must cost the shipped order nothing
# ---------------------------------------------------------------------------


def test_the_graph_flags_ship_off():
    assert FEATURE_FLAGS_DEFAULTS["ppr_enabled"] is False
    assert FEATURE_FLAGS_DEFAULTS["dual_level_enabled"] is False
    assert FEATURE_FLAGS_DEFAULTS["w_ppr"] == 0.0
    assert FEATURE_FLAGS_DEFAULTS["w_dual"] == 0.0


def test_the_list_weights_are_never_per_row_arms():
    """`w_ppr` names a producer of candidates, so its weight belongs to the
    fusion. Filed as a `RankArm` it would have multiplied rows the graph never
    proposed."""
    assert {"w_ppr", "w_dual"} <= LIST_WEIGHT_KEYS
    assert {arm.flag for arm in RANK_ARMS}.isdisjoint(LIST_WEIGHT_KEYS)


def test_a_weight_without_its_flag_stays_inert():
    """Both doors read the weight through one helper, so a half-flipped config
    cannot mean one thing to chat and another to the search surface."""
    assert ppr_list_weight({}) == 0.0
    assert ppr_list_weight({"w_ppr": 0.4}) == 0.0
    assert ppr_list_weight({"ppr_enabled": True, "w_ppr": 0.4}) == 0.4
    assert ppr_list_weight({"ppr_enabled": True}) == 0.0
    assert ppr_list_weight({"ppr_enabled": True, "w_ppr": "nonsense"}) == 0.0


def test_the_arm_is_inert_at_weight_zero():
    """The one test that fails if the arm ever leaks into the shipped order.

    Same rows in the same order, not merely the same scores: a zero-weight
    list contributes 0.0 to `rrf_score`, which displaces nothing — but a row
    only PPR found would still *enter* the fused set and appear on a page that
    would not have contained it.
    """
    semantic = [{"memory_id": "m1", "score": 0.9}, {"memory_id": "m2", "score": 0.5}]
    keyword = [{"memory_id": "m2", "score": 0.4}]
    intruder = [{"memory_id": "m9", "score": 1.0}]

    without = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)
    with_inert_arm = HybridSearchService._rrf_fuse(
        semantic, keyword, 0.7, 10, intruder, 0.0,
    )

    assert [r["memory_id"] for r in with_inert_arm] == [r["memory_id"] for r in without]
    assert [r["rrf_score"] for r in with_inert_arm] == [r["rrf_score"] for r in without]
    assert "m9" not in {r["memory_id"] for r in with_inert_arm}


def test_the_arm_moves_the_order_once_it_carries_weight():
    """The complement of the test above: inert at zero has to mean *chosen*
    inertness, not an arm that was never wired at all."""
    semantic = [{"memory_id": "m1", "score": 0.9}, {"memory_id": "m2", "score": 0.5}]
    keyword = [{"memory_id": "m2", "score": 0.4}]
    graph = [{"memory_id": "m2", "score": 1.0}]

    fused = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10, graph, 5.0)

    assert fused[0]["memory_id"] == "m2"


async def test_the_zero_weight_arm_never_reads_a_snapshot(monkeypatch, session):
    """Inert must also mean *free*: an install that never turns the arm on must
    not pay a snapshot lookup on every query."""
    called = False

    async def _boom(*args, **kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(ppr, "ppr_ranked_list", _boom)
    service = HybridSearchService(llm=None, session=session)

    from app.repositories.vector import MemoryFilter

    assert await service._ppr_search(
        [{"memory_id": "m1"}], MemoryFilter(project=PROJECT), 0.0, 300,
    ) == []
    assert called is False


async def test_a_wide_request_skips_the_arm(session):
    """The snapshot is project-scoped, and mass has no defined meaning across
    two of them — the same reason the facts channel reports its arms
    `ran=False` for a wide request rather than answering half-scoped."""
    service = HybridSearchService(llm=None, session=session)
    from app.repositories.vector import MemoryFilter

    assert await service._ppr_search(
        [{"memory_id": "m1"}], MemoryFilter(project=None), 0.5, 300,
    ) == []
    assert await service._ppr_search([{"memory_id": "m1"}], None, 0.5, 300) == []


async def test_an_arm_failure_costs_the_fused_order_nothing(monkeypatch, session):
    async def _raise(*args, **kwargs):
        raise RuntimeError("snapshot exploded")

    monkeypatch.setattr(ppr, "ppr_ranked_list", _raise)
    service = HybridSearchService(llm=None, session=session)
    from app.repositories.vector import MemoryFilter

    assert await service._ppr_search(
        [{"memory_id": "m1"}], MemoryFilter(project=PROJECT), 0.5, 300,
    ) == []


# ---------------------------------------------------------------------------
# The cache and the refresh job
# ---------------------------------------------------------------------------


async def test_a_failed_rebuild_leaves_the_previous_snapshot(session, monkeypatch):
    """Stale is not corrupt. Emptying the cache on a failed rebuild would
    retire the arm for that project until the next successful run, with no
    error anywhere — the same shape the topic detector's per-project rewrite
    refuses. The rotation also has to *continue*: one project's bad graph must
    not cost every project behind it its refresh."""
    snapshot, _, _ = await _line_graph(session)
    cache = ppr.SnapshotCache()
    cache.put(snapshot)

    async def _explode(*args, **kwargs):
        raise RuntimeError("no graph today")

    monkeypatch.setattr(ppr, "build_snapshot", _explode)

    outcome = await ppr.refresh_snapshots(
        _session_factory(session), batch_size=10, cache=cache,
    )

    assert outcome.projects_visited >= 1
    assert outcome.snapshots_built == 0
    assert outcome.skipped == outcome.projects_visited
    assert cache.get(PROJECT) is snapshot


def _session_factory(session):
    """A factory handing back the test's own session, so the refresh runs
    inside the test transaction instead of committing real rows."""

    class _Factory:
        def __call__(self):
            class _Ctx:
                async def __aenter__(self_inner):
                    return session

                async def __aexit__(self_inner, *exc):
                    return False

            return _Ctx()

    return _Factory()


def test_the_job_is_registered_with_a_lock_a_floor_and_a_schema():
    """Registrability is not the same as being wired at boot. This reads the
    literal registration in `app/main.py` rather than building a registry of
    its own, which is what `test_main_wires_the_family_at_boot` had to learn:
    every registry-level assertion passes while the running app has no such
    job at all."""
    tree = ast.parse((BACKEND / "app" / "main.py").read_text())
    registrations = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Job"
    ]
    keywords = None
    for call in registrations:
        kw = {k.arg: k.value for k in call.keywords}
        key = kw.get("key")
        if isinstance(key, ast.Name) and key.id == "PPR_SNAPSHOT_JOB_KEY":
            keywords = kw
            break

    assert keywords is not None, "the PPR snapshot job is not registered at boot"
    # The registry gives every job its per-job asyncio.Lock, so what a
    # registration owes is the floor, the ceiling and the schema.
    assert isinstance(keywords["min_interval_seconds"], ast.Constant)
    assert keywords["min_interval_seconds"].value >= 60
    assert isinstance(keywords["max_run_seconds"], ast.Constant)
    assert "config_schema" in keywords


def test_the_job_key_and_schema_are_coherent():
    from app.services.job_registry import is_valid_cron

    keys = {fd.key for fd in ppr.PPR_SNAPSHOT_CONFIG_SCHEMA}
    assert "batch_size" in keys
    assert {"synonymy_threshold_pct", "synonymy_top_k", "synonymy_max_nodes"} <= keys
    assert is_valid_cron("30 * * * *")
    assert ppr.PPR_SNAPSHOT_JOB_KEY == "ppr_snapshot"


async def test_the_refresh_rotates_and_caches(session, monkeypatch):
    """One session per project, and a snapshot lands in the cache per project
    that had one to build."""
    snapshot, _, _ = await _line_graph(session)

    cache = ppr.SnapshotCache()
    outcome = await ppr.refresh_snapshots(
        _session_factory(session), batch_size=10, cache=cache,
    )

    assert PROJECT in {o.project for o in outcome.outcomes}
    assert outcome.snapshots_built >= 1
    assert cache.get(PROJECT) is not None
    assert outcome.last_project is not None


# ---------------------------------------------------------------------------
# Tier-C placement
# ---------------------------------------------------------------------------


def test_retrieval_reads_the_artefact_and_never_the_job():
    """Invariant 15 by construction. `hybrid_search` may import the arm; it
    must never reach the refresh, the rotation, or the runner — those are the
    registry's to call, and a retrieval path that could rebuild a snapshot
    would put an unbounded graph read on the query's latency budget."""
    source = (BACKEND / "app" / "services" / "hybrid_search.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "app.services.ppr_snapshot":
            imported.update(alias.name for alias in node.names)

    assert imported == {"ppr_ranked_list"}, (
        "retrieval may spend the snapshot and nothing else; it reached "
        f"{sorted(imported - {'ppr_ranked_list'})}"
    )
    for forbidden in ("refresh_snapshots", "build_snapshot", "next_projects"):
        assert forbidden not in source


# ── the seed must stay a neighbourhood, not a census (T2.50's finding) ──
#
# The independent judge measured the shipped arm returning a **byte-identical
# ranked list for every query, including one matching nothing in the corpus**.
# Cause: the seed was every semantic hit, the semantic list is read to
# FUSION_FETCH_DEPTH (300), and any project smaller than that therefore put
# every entity in the reset set — and PPR with a full uniform reset set is
# global PageRank. Not an eval artifact: it was production behaviour.


def test_the_seed_is_bounded_to_the_top_hits():
    from app.services.ppr_snapshot import PPR_SEED_TOP_K

    class _Snap:
        memory_ids = tuple((f"m{i}",) for i in range(50))

    seeds = ppr.seed_vertices_for_memories(
        _Snap(), [f"m{i}" for i in range(50)], top_k=PPR_SEED_TOP_K,
    )
    assert len(seeds) == PPR_SEED_TOP_K
    assert seeds == list(range(PPR_SEED_TOP_K))


async def test_two_different_queries_seed_two_different_neighbourhoods(session):
    """The property whose absence was the defect. If these two ranked lists
    are identical, the arm is answering global popularity and the query is
    decoration."""
    snapshot, _, mems = await _line_graph(session)
    cache = ppr.SnapshotCache()
    cache.put(snapshot)

    from_a = await ppr.ppr_ranked_list(
        PROJECT, [str(mems["a"])], limit=10, cache=cache, seed_top_k=1,
    )
    from_c = await ppr.ppr_ranked_list(
        PROJECT, [str(mems["c"])], limit=10, cache=cache, seed_top_k=1,
    )

    assert from_a != from_c, (
        "the arm returned the same ranking for two different seeds — it is "
        "computing global PageRank, not a personalized one"
    )


async def test_an_unbounded_seed_over_a_small_corpus_degenerates(session):
    """The regression itself, stated as a measurement rather than a warning:
    seeding from every memory makes the ranking query-independent."""
    snapshot, _, mems = await _line_graph(session)
    cache = ppr.SnapshotCache()
    cache.put(snapshot)

    everything = [str(m) for m in mems.values()]
    unbounded_a = await ppr.ppr_ranked_list(
        PROJECT, everything, limit=10, cache=cache, seed_top_k=0,
    )
    unbounded_b = await ppr.ppr_ranked_list(
        PROJECT, list(reversed(everything)), limit=10, cache=cache, seed_top_k=0,
    )
    # Same reset set either way — which is exactly the degeneration.
    assert unbounded_a == unbounded_b

    bounded = await ppr.ppr_ranked_list(
        PROJECT, everything, limit=10, cache=cache, seed_top_k=1,
    )
    assert bounded != unbounded_a
