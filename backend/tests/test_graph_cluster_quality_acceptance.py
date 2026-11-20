"""Acceptance tests for the graph cluster quality spec, written from its text.

Clustering (A1-A3, A22, A23) goes through ``cluster_labels``; naming (A5-A11)
through ``name_clusters``; the rest through ``GraphService`` and the REST
routes. Expected values are literals worked out from the spec's rules.
"""
from __future__ import annotations

import json
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from sqlalchemy import text

from app.api.deps import get_graph_service
from app.config import settings
from app.main import app
from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services import prompt as prompt_mod
from app.services.embedder_registry import child_table
from app.services.graph import GraphService
from app.taxonomy import ENTITY_TYPES, MEMORY_TYPES
from app.utils.cluster_names import name_clusters
from app.utils.graph_knn import KnnGraph, cluster_labels, knn_graph


# --------------------------------------------------------------------------
# Clustering helpers
# --------------------------------------------------------------------------

def _hand_graph(edges: list[tuple[int, int, float]]) -> KnnGraph:
    edges = sorted((min(a, b), max(a, b), w) for a, b, w in edges)
    return KnnGraph(
        np.array([a for a, _, _ in edges], dtype=np.int32),
        np.array([b for _, b, _ in edges], dtype=np.int32),
        np.array([w for _, _, w in edges], dtype=np.float32),
        np.zeros(len(edges), dtype=np.int16),
    )


def _ring_of_cliques(sizes: list[int], weight: float = 0.9, bridge: float = 0.9):
    """Cliques of the given sizes in a ring, each joined to the next by one edge.

    Returns (graph, n, starts) where starts[c] is the first node of clique c.
    """
    edges: list[tuple[int, int, float]] = []
    starts: list[int] = []
    total = 0
    for size in sizes:
        starts.append(total)
        total += size
    for c, size in enumerate(sizes):
        base = starts[c]
        for i in range(size):
            for j in range(i + 1, size):
                edges.append((base + i, base + j, weight))
        edges.append((base + size - 1, starts[(c + 1) % len(sizes)], bridge))
    return _hand_graph(edges), total, starts


def _igraph(graph: KnnGraph, n: int):
    import igraph

    g = igraph.Graph(
        n=n, edges=np.column_stack((graph.src, graph.dst)).tolist(), directed=False,
    )
    g.es["weight"] = graph.sim.astype(float).tolist()
    return g


def _louvain_r1(graph: KnnGraph, n: int) -> list[int]:
    import igraph

    # Seeding the global module seeds igraph only while it is igraph's generator.
    state = random.getstate()
    igraph.set_random_number_generator(random)
    random.seed(3)
    try:
        return _igraph(graph, n).community_multilevel(weights="weight", resolution=1).membership
    finally:
        random.setstate(state)


def _leiden(graph: KnnGraph, n: int, resolution: float, seed: int = 0) -> list[int]:
    import igraph

    g = _igraph(graph, n)
    igraph.set_random_number_generator(random.Random(seed))
    try:
        return g.community_leiden(
            objective_function="modularity", weights="weight",
            resolution=resolution, n_iterations=-1,
        ).membership
    finally:
        igraph.set_random_number_generator(random)


def _coverage(membership: list[int], n: int, min_size: int) -> float:
    return sum(v for v in Counter(membership).values() if v >= min_size) / n


def _groups(labels: list[int], indices) -> set[int]:
    return {labels[i] for i in indices}


# --------------------------------------------------------------------------
# A1-A3, A22, A23: clustering
# --------------------------------------------------------------------------

def test_A1_same_graph_gives_identical_labels_whatever_the_global_random_state():
    pytest.importorskip("igraph")
    rng = np.random.default_rng(2024)
    centres = np.eye(4, 8)
    vectors = np.vstack(
        [c + rng.normal(scale=0.45, size=(40, 8)) for c in centres]
    ).astype(np.float32)
    graph = knn_graph(vectors, k=10, threshold=0.0)
    n = len(vectors)

    results = []
    for seed in (0, 1, 12345, 987654321):
        random.seed(seed)
        for _ in range(seed % 7):
            random.random()
        results.append(cluster_labels(graph, n, 3))

    assert all(r == results[0] for r in results[1:])
    assert len({label for label in results[0] if label >= 0}) >= 2


def test_A2_two_weakly_joined_dense_groups_stay_two_clusters():
    pytest.importorskip("igraph")
    graph, n, starts = _ring_of_cliques([5] * 40, weight=0.9, bridge=0.5)

    # Precondition: Louvain at resolution 1 merges neighbouring groups here.
    louvain = _louvain_r1(graph, n)
    merged = [
        c for c in range(40)
        if louvain[starts[c]] == louvain[starts[(c + 1) % 40]]
    ]
    assert merged, "fixture must be a graph Louvain at resolution 1 merges"

    labels = cluster_labels(graph, n, 3)
    for c in range(40):
        assert len(_groups(labels, range(starts[c], starts[c] + 5))) == 1
    clique_label = [labels[starts[c]] for c in range(40)]
    assert -1 not in clique_label
    for c in range(40):
        assert clique_label[c] != clique_label[(c + 1) % 40]
    assert len(set(clique_label)) == 40


def test_A3_small_communities_are_minus_one_and_edgeless_graphs_are_all_minus_one():
    pytest.importorskip("igraph")
    # A five-clique, a two-node pair and three isolated nodes.
    edges = [(i, j, 0.95) for i in range(5) for j in range(i + 1, 5)]
    edges.append((5, 6, 0.95))
    graph = _hand_graph(edges)
    labels = cluster_labels(graph, 10, 3)
    assert labels[0:5] == [0, 0, 0, 0, 0]
    assert labels[5:] == [-1] * 5

    # Raising the floor above the clique drops it too.
    assert cluster_labels(graph, 10, 6) == [-1] * 10

    empty = knn_graph(np.eye(4, dtype=np.float32), k=2, threshold=0.9)
    assert len(empty) == 0
    assert cluster_labels(empty, 4, 2) == [-1, -1, -1, -1]
    assert cluster_labels(empty, 0, 2) == []


def test_A22_five_near_identical_memories_come_back_as_one_cluster_of_five():
    pytest.importorskip("igraph")
    k5 = _hand_graph([(i, j, 0.99) for i in range(5) for j in range(i + 1, 5)])
    # Precondition: resolution 2.0 alone scores this view best as singletons.
    assert sorted(_leiden(k5, 5, 2.0)) == [0, 1, 2, 3, 4]
    assert cluster_labels(k5, 5, 3) == [0, 0, 0, 0, 0]

    rng = np.random.default_rng(8)
    vectors = (np.array([1.0, 2.0, 3.0, 4.0]) + rng.normal(scale=0.001, size=(5, 4))).astype(np.float32)
    graph = knn_graph(vectors, k=4, threshold=0.9)
    assert len(graph) == 10
    assert cluster_labels(graph, 5, 3) == [0, 0, 0, 0, 0]


def test_A23_a_view_clustered_at_ninety_percent_keeps_its_fine_labels():
    pytest.importorskip("igraph")
    # 27 six-cliques plus two five-cliques, floor 6: the five-cliques are
    # dropped at 2.0 (coverage 162/172), while 1.0 would label every node.
    graph, n, starts = _ring_of_cliques([6] * 27 + [5] * 2)
    for seed in (0, 1, 2):
        assert _coverage(_leiden(graph, n, 2.0, seed), n, 6) == pytest.approx(162 / 172)
        assert _coverage(_leiden(graph, n, 1.0, seed), n, 6) == pytest.approx(1.0)

    labels = cluster_labels(graph, n, 6)
    for c in range(27):
        assert len(_groups(labels, range(starts[c], starts[c] + 6))) == 1
    clique_label = [labels[starts[c]] for c in range(27)]
    assert len(set(clique_label)) == 27 and -1 not in clique_label
    assert all(label == -1 for label in labels[starts[27]:])


def test_A23_a_view_where_the_coarse_pass_labels_no_more_keeps_the_fine_labels():
    pytest.importorskip("igraph")
    # 30 five-cliques plus 30 isolated memories: coverage 150/180 at 2.0 is
    # under 90%, and the 1.0 pass labels the same 150 memories, in fewer groups.
    graph, _, starts = _ring_of_cliques([5] * 30)
    n = 180
    fine = _leiden(graph, n, 2.0)
    coarse = _leiden(graph, n, 1.0)
    assert _coverage(fine, n, 3) < 0.9
    assert _coverage(coarse, n, 3) == pytest.approx(_coverage(fine, n, 3))
    assert len({coarse[i] for i in range(150)}) < 30

    labels = cluster_labels(graph, n, 3)
    clique_label = [labels[starts[c]] for c in range(30)]
    for c in range(30):
        assert len(_groups(labels, range(starts[c], starts[c] + 5))) == 1
    assert len(set(clique_label)) == 30 and -1 not in clique_label
    assert labels[150:] == [-1] * 30


# --------------------------------------------------------------------------
# Naming helpers
# --------------------------------------------------------------------------

def M(project: str | None = "alpha", tags=(), entities=()):
    return SimpleNamespace(project=project, tags=list(tags), entities=set(entities))


def _names(clusters: dict[int, list], others=()) -> dict[str, str]:
    members: dict[int, list[str]] = {}
    tags: dict[str, list[str]] = {}
    projects: dict[str, str | None] = {}
    entities: dict[str, set[str]] = {}
    count = 0

    def register(m) -> str:
        nonlocal count
        mid = f"mem-{count}"
        count += 1
        tags[mid] = list(m.tags)
        projects[mid] = m.project
        entities[mid] = set(m.entities)
        return mid

    for cid, mems in clusters.items():
        members[cid] = [register(m) for m in mems]
    for m in others:
        register(m)
    return {str(k): v for k, v in name_clusters(members, tags, projects, entities).items()}


def _parts(name: str) -> list[str]:
    return name.split(" · ")


# --------------------------------------------------------------------------
# A5-A7: the project prefix
# --------------------------------------------------------------------------

def test_A5_a_default_memory_counts_toward_its_first_project_tag():
    cluster = [
        M("default", ["project/alpha", "search"]),
        M("default", ["project/alpha", "project/gamma", "search"]),
        M("default", ["misc-x", "project/alpha", "search"]),
        M("default", ["project/alpha", "search"]),
        M("beta", ["search"]),
    ]
    assert _names({0: cluster}) == {"0": "alpha · search"}


def test_A6_prefix_needs_sixty_percent_and_never_default():
    def cluster(alpha, beta, default=0):
        return (
            [M("alpha", ["topic"]) for _ in range(alpha)]
            + [M("beta", ["topic"]) for _ in range(beta)]
            + [M("default", ["topic"]) for _ in range(default)]
        )

    assert _names({0: cluster(6, 4)}) == {"0": "alpha · topic"}
    assert _names({0: cluster(60, 40)}) == {"0": "alpha · topic"}
    assert _names({0: cluster(59, 41)}) == {"0": "topic"}
    assert _names({0: cluster(5, 5)}) == {"0": "topic"}
    assert _names({0: cluster(3, 0, default=7)}) == {"0": "topic"}
    assert _names({0: cluster(2, 0, default=8)}) == {"0": "topic"}
    # Prefixing is decided per cluster.
    names = _names({0: cluster(6, 4), 1: cluster(2, 0, default=3)})
    assert names == {"0": "alpha · topic", "1": "topic"}


def test_A7_no_prefix_when_the_whole_view_shares_one_project():
    only_alpha = [M("alpha", ["search"]), M("default", ["project/alpha", "search"])] * 2
    other = [M("alpha", ["indexing"]), M("alpha", ["indexing"]), M("alpha", ["indexing"])]
    assert _names({0: only_alpha, 1: other}) == {"0": "search", "1": "indexing"}

    # A memory outside every cluster does not count toward "the view's clustered memories".
    assert _names({0: only_alpha}, others=[M("beta", ["search"])]) == {"0": "search"}


# --------------------------------------------------------------------------
# A8: what a name never contains
# --------------------------------------------------------------------------

def test_A8_a_name_never_holds_a_memory_type_or_a_term_of_fewer_than_two_members():
    type_tags = list(MEMORY_TYPES) + [t.upper() for t in MEMORY_TYPES]
    cluster = [
        M("alpha", type_tags + ["storage", "alpha", "duo", "oneoff"], ["alpha"]),
        M("alpha", type_tags + ["storage", "alpha", "duo"], ["alpha"]),
        M("alpha", type_tags + ["storage", "alpha"], ["alpha"]),
        M("alpha", type_tags + ["storage", "alpha"], ["alpha"]),
    ]
    name = _names({0: cluster})["0"]
    assert name == "storage · duo"
    for forbidden in (*MEMORY_TYPES, "oneoff", "alpha"):
        assert forbidden not in _parts(name)


def test_A8_a_name_never_repeats_its_own_prefix():
    cluster = [
        M("alpha", ["storage", "alpha", "ALPHA"], ["alpha"]),
        M("alpha", ["storage", "Alpha"], ["alpha"]),
        M("alpha", ["storage", "alpha"], ["alpha"]),
        M("alpha", ["storage", "alpha"], ["alpha"]),
        M("beta", ["storage", "alpha"], ["alpha"]),
    ]
    name = _names({0: cluster})["0"]
    assert name == "alpha · storage"
    assert name.lower().count("alpha") == 1


def test_A8_a_single_project_view_never_names_the_project():
    cluster = [M("alpha", ["alpha", "search"], ["alpha"]) for _ in range(5)]
    second = [M("alpha", ["alpha", "indexing"], ["alpha"]) for _ in range(5)]
    names = _names({0: cluster, 1: second})
    assert names == {"0": "search", "1": "indexing"}


# --------------------------------------------------------------------------
# A9: spellings and overlapping terms
# --------------------------------------------------------------------------

def test_A9_spellings_that_differ_in_case_space_or_punctuation_are_one_term():
    cluster = (
        [M("alpha", ["Claude Code"]) for _ in range(2)]
        + [M("alpha", ["claude-code"]) for _ in range(3)]
        + [M("alpha", ["CLAUDE_CODE"])]
    )
    assert _names({0: cluster}) == {"0": "claude-code"}


def test_A9_a_tied_spelling_is_chosen_alphabetically():
    cluster = (
        [M("alpha", ["claude-code"]) for _ in range(2)]
        + [M("alpha", ["Claude Code"]) for _ in range(2)]
    )
    assert _names({0: cluster}) == {"0": "claude code"}


def test_A9_a_term_sharing_six_leading_characters_with_a_chosen_term_is_skipped():
    cluster = [
        M("alpha", ["vectordb", "vectors", "cache"]),
        M("alpha", ["vectordb", "vectors", "cache"]),
        M("alpha", ["vectordb", "vectors", "cache"]),
        M("alpha", ["vectordb", "vectors"]),
        M("alpha", ["vectordb"]),
        M("alpha", ["vectordb"]),
    ]
    assert _names({0: cluster}) == {"0": "vectordb · cache"}


def test_A9_a_term_contained_in_a_chosen_term_is_skipped():
    cluster = [
        M("alpha", ["mysql", "sql", "cache"]),
        M("alpha", ["mysql", "sql", "cache"]),
        M("alpha", ["mysql", "sql", "cache"]),
        M("alpha", ["mysql", "sql"]),
        M("alpha", ["mysql"]),
        M("alpha", []),
    ]
    assert _names({0: cluster}) == {"0": "mysql · cache"}


def test_A9_a_term_containing_a_chosen_term_is_skipped():
    cluster = [
        M("alpha", ["sql", "mysql", "cache"]),
        M("alpha", ["sql", "mysql", "cache"]),
        M("alpha", ["sql", "mysql", "cache"]),
        M("alpha", ["sql", "mysql"]),
        M("alpha", ["sql"]),
        M("alpha", []),
    ]
    assert _names({0: cluster}) == {"0": "sql · cache"}


# --------------------------------------------------------------------------
# A10: the 40-character budget
# --------------------------------------------------------------------------

def _three_terms(prefix_project: str | None, terms: list[str], counts: list[int]):
    """Five members, four in prefix_project and one in beta, carrying each term
    on the given number of members (descending, so terms rank in order)."""
    projects = [prefix_project] * 4 + ["beta"] if prefix_project else ["alpha"] * 5
    return [
        M(projects[i], [t for t, c in zip(terms, counts) if i < c])
        for i in range(5)
    ]


def test_A10_terms_that_would_pass_forty_characters_are_dropped_whole():
    cluster = _three_terms("alpha", ["ingestion", "scheduler", "telemetry"], [5, 4, 3])
    # "alpha · ingestion · scheduler · telemetry" would be 41 characters.
    assert _names({0: cluster}) == {"0": "alpha · ingestion · scheduler"}


def test_A10_a_name_of_exactly_forty_characters_is_kept_whole():
    cluster = _three_terms("alpha", ["ingestion", "scheduler", "registry"], [5, 4, 3])
    name = _names({0: cluster})["0"]
    assert name == "alpha · ingestion · scheduler · registry"
    assert len(name) == 40


def test_A10_the_first_term_survives_a_long_prefix():
    long_project = "darkraise-framework-experimental"
    cluster = _three_terms(long_project, ["observability", "ingestion"], [5, 4])
    name = _names({0: cluster})["0"]
    assert name == "darkraise-framework-experimental · observability"
    assert len(name) > 40


def test_A10_without_a_prefix_terms_are_dropped_whole_to_stay_within_forty():
    long_terms = ["observability", "orchestration", "authorization"]
    cluster = _three_terms(None, long_terms, [5, 4, 3])
    name = _names({0: cluster})["0"]
    assert name == "observability · orchestration"
    assert len(name) <= 40

    short_terms = ["ingestion", "scheduler", "telemetry"]
    cluster = _three_terms(None, short_terms, [5, 4, 3])
    assert _names({0: cluster}) == {"0": "ingestion · scheduler · telemetry"}


# --------------------------------------------------------------------------
# A11: the fallback name
# --------------------------------------------------------------------------

def test_A11_a_cluster_with_nothing_to_name_it_is_named_cluster_id():
    bare = [M("alpha") for _ in range(3)]
    singles = [M("alpha", ["only-a"]), M("alpha", ["only-b"]), M("alpha", ["only-c"])]
    types_only = [M("alpha", ["decision", "fact"]) for _ in range(3)]
    named = [M("alpha", ["search"]) for _ in range(3)]
    names = _names({7: bare, 12: singles, 0: types_only, 3: named})
    assert names == {"7": "Cluster 7", "12": "Cluster 12", "0": "Cluster 0", "3": "search"}


def test_A11_every_cluster_id_gets_a_non_empty_name():
    clusters = {
        0: [M("alpha", ["search"]) for _ in range(3)],
        1: [M("beta") for _ in range(4)],
        2: [M("alpha", ["x-one"]), M("beta", ["x-two"]), M("default")],
        3: [M("beta", ["x"]) for _ in range(5)],
    }
    names = _names(clusters)
    assert set(names) == {"0", "1", "2", "3"}
    assert all(isinstance(v, str) and v.strip() for v in names.values())


def test_A11_a_prefix_alone_is_not_the_fallback():
    cluster = [M("alpha") for _ in range(4)] + [M("beta")]
    assert _names({4: cluster}) == {"4": "alpha"}


# --------------------------------------------------------------------------
# Database-backed fixtures for A12-A16
# --------------------------------------------------------------------------

FINGERPRINT = "qa-cluster-quality|4"
DIMS = 4
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": FINGERPRINT.split("|")[0], "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, *, vector, tags=None, project="alpha", created_at=None) -> Memory:
    memory = Memory(
        id=uuid.uuid4(), content="qa graph memory", source="test", memory_type="fact",
        importance=0.5, metadata_={}, project=project, status="active",
        is_archived=False, created_at=created_at or BASE,
    )
    session.add(memory)
    await session.flush()
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {
            "mid": memory.id, "fp": FINGERPRINT, "vec": str(vector),
            "payload": json.dumps({"content": "qa graph memory", "source": "test", "tags": tags or []}),
        },
    )
    await session.flush()
    return memory


async def _seed_five(session, tags_for=lambda i: None, *, axis: int = 0, offset: int = 0) -> list[Memory]:
    await _seed_partition(session)
    rows = []
    for i in range(5):
        vector = [0.0] * DIMS
        vector[axis] = 1.0
        vector[(axis + 1) % DIMS] = 0.01 * i
        rows.append(await _add_memory(
            session, vector=vector, tags=tags_for(i),
            created_at=BASE + timedelta(days=offset + i),
        ))
    return rows


def _retrieval_tags(i: int) -> list[str]:
    return ["retrieval", "lexical"] if i < 3 else ["retrieval"]


class _Llm:
    def __init__(self):
        self.chat_calls = 0

    def llm_fingerprint(self) -> str:
        return FINGERPRINT

    async def chat_completion(self, *args, **kwargs):
        self.chat_calls += 1
        raise AssertionError("the graph route called chat_completion")


def _service(session, llm=None, graph_repo=None) -> GraphService:
    return GraphService(
        session,
        vector_repo=PostgresVectorRepository(session),
        graph_repo=graph_repo,
        llm=llm or _Llm(),
    )


# --------------------------------------------------------------------------
# A12: entity types that name a cluster
# --------------------------------------------------------------------------

NAMING_ENTITY_TYPES = {"project", "tool", "artifact", "service", "protocol", "language"}


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_type", sorted(ENTITY_TYPES))
async def test_A12_only_six_entity_types_name_a_cluster(session, entity_type):
    rows = await _seed_five(session)
    repo = PostgresGraphRepository(session)
    for row in rows:
        await repo.create_entity("Widget Thing", entity_type, {}, row.id)

    result = await _service(session, graph_repo=repo).get_unified_graph(
        project="alpha", similarity_threshold=0.5,
    )

    assert list(result["clusters"]) == ["0"]
    expected = "widget thing" if entity_type in NAMING_ENTITY_TYPES else "Cluster 0"
    assert result["cluster_names"] == {"0": expected}


@pytest.mark.asyncio
async def test_A12_a_cluster_is_named_only_by_entities_its_own_members_assert(session):
    first = await _seed_five(session, axis=0)
    second = await _seed_five(session, axis=2, offset=10)
    repo = PostgresGraphRepository(session)
    for row in first:
        await repo.create_entity("Gizmo Tool", "tool", {}, row.id)
    for row in second:
        await repo.create_entity("Sprocket Service", "service", {}, row.id)
    # Asserted by one member of the first cluster only: carried by fewer than 2.
    await repo.create_entity("Lonely Language", "language", {}, first[0].id)

    result = await _service(session, graph_repo=repo).get_unified_graph(
        project="alpha", similarity_threshold=0.5,
    )

    by_member = {
        frozenset(members): result["cluster_names"][cid]
        for cid, members in result["clusters"].items()
    }
    assert by_member == {
        frozenset(str(r.id) for r in first): "gizmo tool",
        frozenset(str(r.id) for r in second): "sprocket service",
    }


# --------------------------------------------------------------------------
# A13: a failed entity-term query
# --------------------------------------------------------------------------

class _RaisingTerms:
    def __init__(self, session, *, sql: bool):
        self.session = session
        self.sql = sql

    async def entity_terms_for_memories(self, memory_ids):
        if self.sql:
            await self.session.execute(text("SELECT CAST('not-a-uuid' AS uuid)"))
        raise RuntimeError("entity term query failed")


class _EmptyTerms:
    async def entity_terms_for_memories(self, memory_ids):
        return {}


def _count_clusterings(monkeypatch) -> list[int]:
    calls = [0]
    original = PostgresVectorRepository.get_louvain_clustered_vectors

    async def counting(self, *args, **kwargs):
        calls[0] += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(PostgresVectorRepository, "get_louvain_clustered_vectors", counting)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", [False, True])
async def test_A13_a_failed_entity_query_names_from_tags_and_is_not_cached(session, monkeypatch, sql):
    await _seed_five(session, _retrieval_tags)
    calls = _count_clusterings(monkeypatch)
    svc = _service(session, graph_repo=_RaisingTerms(session, sql=sql))

    first = await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)
    second = await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)

    assert calls[0] == 2
    assert first["cluster_names"] == {"0": "retrieval · lexical"}
    assert second["cluster_names"] == {"0": "retrieval · lexical"}


@pytest.mark.asyncio
async def test_A13_control_a_healthy_entity_query_is_cached(session, monkeypatch):
    await _seed_five(session, _retrieval_tags)
    calls = _count_clusterings(monkeypatch)
    svc = _service(session, graph_repo=_EmptyTerms())

    first = await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)
    second = await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)

    assert calls[0] == 1
    assert first == second
    assert first["cluster_names"] == {"0": "retrieval · lexical"}


# --------------------------------------------------------------------------
# A11 end to end
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_A11_every_cluster_in_the_response_has_a_non_empty_name(session):
    await _seed_five(session, axis=0)  # untagged: nothing to name it
    await _seed_five(session, _retrieval_tags, axis=2, offset=10)

    result = await _service(session, graph_repo=PostgresGraphRepository(session)).get_unified_graph(
        project="alpha", similarity_threshold=0.5,
    )

    assert len(result["clusters"]) == 2
    assert set(result["cluster_names"]) == set(result["clusters"])
    assert all(name.strip() for name in result["cluster_names"].values())
    names = result["cluster_names"]
    fallbacks = {cid for cid, name in names.items() if name == f"Cluster {cid}"}
    assert len(fallbacks) == 1
    assert sorted(v for k, v in names.items() if k not in fallbacks) == ["retrieval · lexical"]


# --------------------------------------------------------------------------
# A14: no chat_completion call
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("read_only", [False, True])
@pytest.mark.parametrize("with_graph_repo", [False, True])
async def test_A14_building_the_graph_makes_no_chat_completion_call(
    session, monkeypatch, read_only, with_graph_repo,
):
    await _seed_five(session, _retrieval_tags)
    monkeypatch.setattr(settings, "read_only", read_only)
    llm = _Llm()
    repo = PostgresGraphRepository(session) if with_graph_repo else None

    result = await _service(session, llm=llm, graph_repo=repo).get_unified_graph(
        project="alpha", similarity_threshold=0.5,
    )

    assert llm.chat_calls == 0
    assert result["cluster_names"] == {"0": "retrieval · lexical"}


# --------------------------------------------------------------------------
# A15: the cluster_naming prompt is gone
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_A15_cluster_naming_is_no_longer_a_prompt_key(client, auth_headers):
    prompt_mod.set_overrides({})
    resp = await client.get("/api/v1/config/system-prompts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "extraction" in body["defaults"]
    for section in ("defaults", "overrides", "effective"):
        assert "cluster_naming" not in body[section]

    resp = await client.put(
        "/api/v1/config/system-prompts",
        headers=auth_headers,
        json={"overrides": {"cluster_naming": "Name this cluster."}},
    )
    assert resp.status_code == 422

    again = await client.get("/api/v1/config/system-prompts", headers=auth_headers)
    assert "cluster_naming" not in again.json()["overrides"]
    assert "cluster_naming" not in again.json()["effective"]


# --------------------------------------------------------------------------
# A16: the response keeps its shape
# --------------------------------------------------------------------------

UNIFIED_KEYS = {
    "memories", "clusters", "cluster_names", "similarity_edges",
    "total_memories", "memories_truncated", "fingerprint_unresolved",
}


@pytest.mark.asyncio
async def test_A16_the_unified_response_keeps_its_keys_and_types(session, client, auth_headers):
    await _seed_five(session, _retrieval_tags)
    service = _service(session, graph_repo=PostgresGraphRepository(session))
    app.dependency_overrides[get_graph_service] = lambda: service

    response = await client.get(
        "/api/v1/graph/unified?project=alpha&similarity_threshold=0.5", headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == UNIFIED_KEYS
    assert isinstance(body["memories"], list) and len(body["memories"]) == 5
    assert isinstance(body["clusters"], dict)
    assert all(
        isinstance(k, str) and isinstance(v, list) and all(isinstance(i, str) for i in v)
        for k, v in body["clusters"].items()
    )
    assert isinstance(body["cluster_names"], dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in body["cluster_names"].items())
    assert isinstance(body["similarity_edges"], list) and body["similarity_edges"]
    assert type(body["total_memories"]) is int and body["total_memories"] == 5
    assert body["memories_truncated"] is False
    assert body["fingerprint_unresolved"] is False
    assert {"id", "cluster"} <= set(body["memories"][0])
    assert body["clusters"] == {"0": [m["id"] for m in body["memories"] if m["cluster"] == 0]}
    assert body["cluster_names"] == {"0": "retrieval · lexical"}


@pytest.mark.asyncio
async def test_A16_an_unresolved_fingerprint_keeps_the_same_keys(session, client, auth_headers):
    class _Sentinel:
        def llm_fingerprint(self) -> str:
            return "qa-unresolved-model|0"

        async def chat_completion(self, *args, **kwargs):
            raise AssertionError("no chat call expected")

    service = _service(session, llm=_Sentinel(), graph_repo=PostgresGraphRepository(session))
    app.dependency_overrides[get_graph_service] = lambda: service

    response = await client.get("/api/v1/graph/unified", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == UNIFIED_KEYS
    assert body["memories"] == [] and body["clusters"] == {} and body["cluster_names"] == {}
    assert body["similarity_edges"] == []
    assert body["total_memories"] == 0
    assert body["memories_truncated"] is False
    assert body["fingerprint_unresolved"] is True
