"""The unified graph at scale: selection order, counts, clustering and cache."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from sqlalchemy import text

import app.services.graph as graph_module
import app.utils.graph_knn as graph_knn_module
from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.graph import GraphService

FINGERPRINT = "graph-scale-embedder|4"
DIMS = 4
SCOPE = MemoryFilter(project="alpha", statuses=("active",))
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


async def _add_memory(session, *, vector: list[float] | None = None, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="graph scale memory",
        source="test",
        memory_type="fact",
        importance=0.5,
        metadata_={},
        project="alpha",
        status="active",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()
    if vector is not None:
        child = child_table("memory_embeddings", FINGERPRINT)
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
            ),
            {
                "mid": base["id"],
                "fp": FINGERPRINT,
                "vec": str(vector),
                "payload": '{"content": "%s", "source": "test", "tags": []}' % base["content"],
            },
        )
        await session.flush()
    return memory


@pytest.mark.asyncio
async def test_bulk_read_is_newest_first(session):
    await _seed_partition(session)
    old = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], created_at=BASE)
    new = await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0], created_at=BASE + timedelta(days=2))
    mid = await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.0], created_at=BASE + timedelta(days=1))

    points = await PostgresVectorRepository(session).get_all_vectors(FINGERPRINT, limit=2, filters=SCOPE)

    assert [p["memory_id"] for p in points] == [new.id, mid.id]
    assert old.id not in {p["memory_id"] for p in points}


@pytest.mark.asyncio
async def test_bulk_read_returns_native_floats_and_importance(session, monkeypatch):
    await _seed_partition(session)
    await _add_memory(session, vector=[0.5, 0.25, 0.0, 1.0], importance=0.9)

    def _no_text_parsing(raw):
        raise AssertionError("the bulk read must not parse the text form")

    monkeypatch.setattr(PostgresVectorRepository, "_parse_vector", staticmethod(_no_text_parsing))
    [point] = await PostgresVectorRepository(session).get_all_vectors(FINGERPRINT, limit=10, filters=SCOPE)

    assert point["vector"] == pytest.approx([0.5, 0.25, 0.0, 1.0])
    assert all(isinstance(v, float) for v in point["vector"])
    assert point["importance"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_vector_matrix_matches_the_bulk_read(session):
    await _seed_partition(session)
    for i in range(3):
        await _add_memory(session, vector=[1.0, float(i), 0.0, 0.5], created_at=BASE + timedelta(days=i))
    repo = PostgresVectorRepository(session)

    points = await repo.get_all_vectors(FINGERPRINT, limit=10, filters=SCOPE)
    matrix_points, matrix = await repo.get_vector_matrix(FINGERPRINT, limit=10, filters=SCOPE)

    assert [p["memory_id"] for p in matrix_points] == [p["memory_id"] for p in points]
    assert matrix.dtype == np.float32
    assert matrix.shape == (3, 4)
    assert np.allclose(matrix, [p["vector"] for p in points])
    assert "vector" not in matrix_points[0]
    assert matrix_points[0]["project"] == "alpha"


@pytest.mark.asyncio
async def test_vector_matrix_of_an_empty_scope(session):
    await _seed_partition(session)
    points, matrix = await PostgresVectorRepository(session).get_vector_matrix(FINGERPRINT, filters=SCOPE)
    assert points == []
    assert matrix.shape == (0, 0)


@pytest.mark.asyncio
async def test_scope_stamp_counts_the_readable_set(session):
    await _seed_partition(session)
    await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], updated_at=BASE)
    newest = BASE + timedelta(hours=3)
    await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0], updated_at=newest)
    await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.0], project="beta")
    await _add_memory(session)  # no vector: not readable

    repo = PostgresVectorRepository(session)
    count, last_updated = await repo.scope_stamp(FINGERPRINT, SCOPE)

    assert count == 2
    assert last_updated == newest

    await _add_memory(session, vector=[0.0, 0.0, 0.0, 1.0], updated_at=BASE)
    assert (await repo.scope_stamp(FINGERPRINT, SCOPE))[0] == 3


@pytest.mark.asyncio
async def test_scope_stamp_moves_when_a_row_leaves_scope(session):
    await _seed_partition(session)
    await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], updated_at=BASE)
    retired = await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0], updated_at=BASE)
    deleted = await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.0], updated_at=BASE)
    repo = PostgresVectorRepository(session)
    assert (await repo.scope_stamp(FINGERPRINT, SCOPE))[0] == 3

    await session.execute(
        text("UPDATE memories SET status = 'deprecated' WHERE id = :id"), {"id": retired.id},
    )
    assert await repo.scope_stamp(FINGERPRINT, SCOPE) == (2, BASE)

    await session.execute(text("DELETE FROM memories WHERE id = :id"), {"id": deleted.id})
    assert await repo.scope_stamp(FINGERPRINT, SCOPE) == (1, BASE)


@pytest.mark.asyncio
async def test_knn_clustering_labels_blobs_and_bounds_edges(session):
    await _seed_partition(session)
    blob_a = [await _add_memory(session, vector=[1.0, 0.01 * i, 0.0, 0.0]) for i in range(4)]
    blob_b = [await _add_memory(session, vector=[0.0, 0.0, 1.0, 0.01 * i]) for i in range(4)]

    points, edges = await PostgresVectorRepository(session).get_louvain_clustered_vectors(
        FINGERPRINT, min_score=0.9, min_cluster_size=3, limit=100, filters=SCOPE,
    )

    cluster = {p["memory_id"]: p["cluster"] for p in points}
    assert len({cluster[m.id] for m in blob_a}) == 1
    assert len({cluster[m.id] for m in blob_b}) == 1
    assert cluster[blob_a[0].id] != cluster[blob_b[0].id]
    assert all(c >= 0 for c in cluster.values())

    ids = {str(p["memory_id"]) for p in points}
    assert edges and all(e["source"] in ids and e["target"] in ids for e in edges)
    assert all(e["score"] >= 0.9 for e in edges)
    assert len(edges) <= len(points) * 5
    a_ids = {str(m.id) for m in blob_a}
    assert all((e["source"] in a_ids) == (e["target"] in a_ids) for e in edges)


@pytest.mark.asyncio
async def test_knn_clustering_on_an_empty_partition(session):
    await _seed_partition(session)
    assert await PostgresVectorRepository(session).get_louvain_clustered_vectors(
        FINGERPRINT, filters=SCOPE,
    ) == ([], [])


@pytest.mark.asyncio
async def test_knn_pass_runs_off_the_event_loop(session, monkeypatch):
    await _seed_partition(session)
    await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0])
    await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0])

    seen: list[str] = []
    original = graph_knn_module.knn_graph

    def spy(*args, **kwargs):
        seen.append(threading.current_thread().name)
        return original(*args, **kwargs)

    monkeypatch.setattr(graph_knn_module, "knn_graph", spy)

    await PostgresVectorRepository(session).get_louvain_clustered_vectors(
        FINGERPRINT, min_score=0.0, filters=SCOPE,
    )

    assert seen and seen[0].startswith("graph-knn")


class _FakeLLM:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def llm_fingerprint(self) -> str:
        return FINGERPRINT

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("naming down")
        return "named cluster"


def _service(session, llm=None) -> GraphService:
    return GraphService(session, vector_repo=PostgresVectorRepository(session), llm=llm or _FakeLLM())


async def _seed_five(session) -> list[Memory]:
    await _seed_partition(session)
    return [
        await _add_memory(
            session,
            vector=[1.0, 0.01 * i, 0.0, 0.0],
            created_at=BASE + timedelta(days=i),
        )
        for i in range(5)
    ]


@pytest.mark.asyncio
async def test_unified_graph_reports_total_and_truncation(session):
    rows = await _seed_five(session)
    svc = _service(session)

    limited = await svc.get_unified_graph(limit=2, project="alpha")
    assert [m["id"] for m in limited["memories"]] == [str(rows[4].id), str(rows[3].id)]
    assert limited["total_memories"] == 5
    assert limited["memories_truncated"] is True

    everything = await svc.get_unified_graph(limit=2, project="alpha", all_memories=True)
    assert len(everything["memories"]) == 5
    assert everything["memories_truncated"] is False


@pytest.mark.asyncio
async def test_all_memories_is_bounded_by_the_ceiling(session, monkeypatch):
    await _seed_five(session)
    monkeypatch.setattr(graph_module, "GRAPH_MAX_NODES", 3)

    result = await _service(session).get_unified_graph(project="alpha", all_memories=True)

    assert len(result["memories"]) == 3
    assert result["total_memories"] == 5
    assert result["memories_truncated"] is True


@pytest.mark.asyncio
async def test_importance_comes_from_the_memory_row(session):
    await _seed_partition(session)
    memory = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0], importance=0.2)

    result = await _service(session).get_unified_graph(project="alpha")

    [node] = result["memories"]
    assert node["id"] == str(memory.id)
    assert node["importance"] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_unchanged_corpus_is_served_from_cache(session, monkeypatch):
    await _seed_five(session)
    calls = 0
    original = PostgresVectorRepository.get_louvain_clustered_vectors

    async def counting(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(PostgresVectorRepository, "get_louvain_clustered_vectors", counting)
    svc = _service(session)

    first = await svc.get_unified_graph(project="alpha")
    second = await svc.get_unified_graph(project="alpha")
    assert calls == 1
    assert second["memories"] == first["memories"]

    await _add_memory(session, vector=[0.0, 1.0, 0.0, 0.0])
    third = await svc.get_unified_graph(project="alpha")
    assert calls == 2
    assert third["total_memories"] == 6


def _count_builds(monkeypatch) -> list[int]:
    calls = [0]
    original = PostgresVectorRepository.get_louvain_clustered_vectors

    async def counting(self, *args, **kwargs):
        calls[0] += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(PostgresVectorRepository, "get_louvain_clustered_vectors", counting)
    return calls


@pytest.mark.asyncio
async def test_cache_is_keyed_on_project_limit_and_cluster_size(session, monkeypatch):
    await _seed_five(session)
    # Same count and same newest updated_at (one transaction's now()) as
    # alpha, so only the project itself can tell the two keys apart.
    beta_ids = {
        str((await _add_memory(session, project="beta", vector=[0.0, 1.0, 0.01 * i, 0.0])).id)
        for i in range(5)
    }
    calls = _count_builds(monkeypatch)
    svc = _service(session)

    await svc.get_unified_graph(project="alpha")
    await svc.get_unified_graph(project="alpha", limit=3)
    await svc.get_unified_graph(project="alpha", min_cluster_size=2)
    beta = await svc.get_unified_graph(project="beta")
    assert calls[0] == 4
    assert {m["id"] for m in beta["memories"]} == beta_ids

    await svc.get_unified_graph(project="alpha", limit=3)
    assert calls[0] == 4


@pytest.mark.asyncio
async def test_cache_evicts_the_least_recently_used_entry(session, monkeypatch):
    await _seed_five(session)
    calls = _count_builds(monkeypatch)
    svc = _service(session)

    for limit in (1, 2, 3, 4):
        await svc.get_unified_graph(project="alpha", limit=limit)
    await svc.get_unified_graph(project="alpha", limit=1)  # refreshes limit=1
    await svc.get_unified_graph(project="alpha", limit=5)  # evicts limit=2
    assert calls[0] == 5

    await svc.get_unified_graph(project="alpha", limit=1)
    assert calls[0] == 5
    await svc.get_unified_graph(project="alpha", limit=2)
    assert calls[0] == 6


@pytest.mark.asyncio
async def test_entity_overlay_is_added_to_a_cached_arm(session, monkeypatch):
    await _seed_partition(session)
    plotted = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0])
    await _add_entity(session, "scale-cached", [plotted.id])
    calls = _count_builds(monkeypatch)
    svc = GraphService(
        session,
        vector_repo=PostgresVectorRepository(session),
        graph_repo=PostgresGraphRepository(session),
        llm=_FakeLLM(),
    )

    bare = await svc.get_unified_graph(project="alpha")
    overlaid = await svc.get_unified_graph(project="alpha", include_entities=True)

    assert calls[0] == 1
    assert "entities" not in bare
    assert [e["name"] for e in overlaid["entities"]] == ["scale-cached"]


@pytest.mark.asyncio
async def test_degraded_naming_is_not_cached(session, monkeypatch):
    await _seed_five(session)
    calls = 0
    original = PostgresVectorRepository.get_louvain_clustered_vectors

    async def counting(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(PostgresVectorRepository, "get_louvain_clustered_vectors", counting)
    svc = _service(session, llm=_FakeLLM(fail=True))

    await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)
    await svc.get_unified_graph(project="alpha", similarity_threshold=0.5)

    assert calls == 2


@pytest.mark.asyncio
async def test_similarity_edges_come_from_the_knn_pass(session):
    await _seed_five(session)

    result = await _service(session).get_unified_graph(project="alpha", similarity_threshold=0.9)

    ids = {m["id"] for m in result["memories"]}
    assert result["similarity_edges"]
    assert all(e["source"] in ids and e["target"] in ids for e in result["similarity_edges"])
    assert all(e["score"] >= 0.9 for e in result["similarity_edges"])


@pytest.mark.asyncio
async def test_empty_arm_still_reports_counts(session):
    result = await GraphService(session).get_unified_graph()
    assert result["total_memories"] == 0
    assert result["memories_truncated"] is False
    assert result["memories"] == []


async def _add_entity(session, name: str, memory_ids: list[uuid.UUID]) -> uuid.UUID:
    return (
        await session.execute(
            text(
                "INSERT INTO entities (name, entity_type, memory_ids) "
                "VALUES (:name, 'concept', CAST(:ids AS uuid[])) RETURNING id"
            ),
            {"name": name, "ids": memory_ids},
        )
    ).scalar_one()


async def _add_relation(
    session, source: uuid.UUID, target: uuid.UUID, memory_ids: list[uuid.UUID],
) -> None:
    await session.execute(
        text(
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, rel_type, memory_ids) "
            "VALUES (:source, :target, 'RELATED_TO', CAST(:memory_ids AS uuid[]))"
        ),
        {"source": source, "target": target, "memory_ids": memory_ids},
    )


@pytest.mark.asyncio
async def test_entity_overlay_holds_only_entities_of_plotted_memories(session):
    m1 = await _add_memory(session)
    m2 = await _add_memory(session)
    elsewhere = await _add_memory(session)
    single = await _add_entity(session, "scale-single", [m1.id])
    shared = await _add_entity(session, "scale-shared", [m1.id, m2.id])
    foreign = await _add_entity(session, "scale-foreign", [elsewhere.id])
    await _add_relation(session, single, shared, [m1.id])
    await _add_relation(session, single, foreign, [m1.id])
    await _add_relation(session, shared, single, [elsewhere.id])

    result = await PostgresGraphRepository(session).get_entities_for_memories(
        [str(m1.id), str(m2.id)], limit=10,
    )

    assert [e["name"] for e in result["entities"]] == ["scale-shared", "scale-single"]
    assert result["relations"] == [
        {"source": str(single), "target": str(shared), "type": "RELATED_TO", "weight": 0.5},
    ]
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_entity_overlay_reports_truncation(session):
    m1 = await _add_memory(session)
    await _add_entity(session, "scale-a", [m1.id])
    await _add_entity(session, "scale-b", [m1.id])

    result = await PostgresGraphRepository(session).get_entities_for_memories([str(m1.id)], limit=1)

    assert len(result["entities"]) == 1
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_entity_overlay_of_nothing_is_empty(session):
    result = await PostgresGraphRepository(session).get_entities_for_memories([], limit=10)
    assert result == {"entities": [], "relations": [], "truncated": False}


@pytest.mark.asyncio
async def test_unified_graph_overlay_uses_plotted_memories(session):
    await _seed_partition(session)
    plotted = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0])
    unplotted = await _add_memory(session, project="beta", vector=[0.0, 1.0, 0.0, 0.0])
    await _add_entity(session, "scale-plotted", [plotted.id])
    await _add_entity(session, "scale-unplotted", [unplotted.id])
    svc = GraphService(
        session,
        vector_repo=PostgresVectorRepository(session),
        graph_repo=PostgresGraphRepository(session),
        llm=_FakeLLM(),
    )

    result = await svc.get_unified_graph(project="alpha", include_entities=True)

    assert [e["name"] for e in result["entities"]] == ["scale-plotted"]
    assert result["entities_truncated"] is False
