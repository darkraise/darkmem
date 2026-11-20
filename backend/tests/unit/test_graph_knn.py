import random

import numpy as np
import pytest

from app.utils import graph_knn
from app.utils.graph_knn import (
    KnnGraph,
    _auto_chunk,
    cluster_labels,
    knn_graph,
    similarity_edges,
)


def _normalized(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def _reference(vectors: np.ndarray, k: int, threshold: float) -> dict[tuple[int, int], int]:
    """Brute force: every pair in either endpoint's top k at or above the
    threshold, mapped to its lower rank."""
    x = _normalized(vectors.astype(np.float64))
    sims = x @ x.T
    np.fill_diagonal(sims, -np.inf)
    pairs: dict[tuple[int, int], int] = {}
    for i in range(len(x)):
        order = np.argsort(-sims[i], kind="stable")[:k]
        for rank, j in enumerate(order):
            if sims[i, j] < threshold:
                continue
            key = (min(i, int(j)), max(i, int(j)))
            pairs[key] = min(rank, pairs.get(key, rank))
    return pairs


def _as_dict(graph) -> dict[tuple[int, int], int]:
    return {
        (int(s), int(d)): int(r)
        for s, d, r in zip(graph.src, graph.dst, graph.rank)
    }


def test_matches_the_brute_force_top_k():
    rng = np.random.default_rng(7)
    vectors = rng.normal(size=(60, 8)).astype(np.float32)
    graph = knn_graph(vectors, k=5, threshold=-1.0)
    assert _as_dict(graph) == _reference(vectors, 5, -1.0)


def test_chunk_boundaries_do_not_change_the_answer():
    rng = np.random.default_rng(11)
    vectors = rng.normal(size=(53, 6)).astype(np.float32)
    whole = knn_graph(vectors, k=4, threshold=0.0, chunk_size=1000)
    chunked = knn_graph(vectors, k=4, threshold=0.0, chunk_size=7)
    assert _as_dict(chunked) == _as_dict(whole)
    assert np.allclose(np.sort(chunked.sim), np.sort(whole.sim))


def test_auto_chunk_bounds_scratch_memory():
    assert _auto_chunk(100) == 1000
    for n in (20_000, 50_000):
        assert 12 * _auto_chunk(n) * n <= 128 * 1024 * 1024
    assert _auto_chunk(10_000_000) == 64
    rng = np.random.default_rng(13)
    vectors = rng.normal(size=(45, 4)).astype(np.float32)
    assert _as_dict(knn_graph(vectors, k=3, threshold=0.0)) == _as_dict(
        knn_graph(vectors, k=3, threshold=0.0, chunk_size=5)
    )


def test_threshold_drops_weak_pairs_and_pairs_are_undirected():
    rng = np.random.default_rng(3)
    vectors = rng.normal(size=(40, 5)).astype(np.float32)
    graph = knn_graph(vectors, k=6, threshold=0.3)
    assert len(graph) > 0
    assert (graph.sim >= 0.3).all()
    assert (graph.src < graph.dst).all()
    assert len(set(zip(graph.src.tolist(), graph.dst.tolist()))) == len(graph)
    assert _as_dict(graph) == _reference(vectors, 6, 0.3)


def test_k_larger_than_the_corpus_links_every_pair():
    vectors = np.eye(4, dtype=np.float32) + 0.1
    graph = knn_graph(vectors, k=50, threshold=-1.0)
    assert len(graph) == 6


def test_fewer_than_two_points_yield_an_empty_graph():
    assert len(knn_graph(np.zeros((0, 3), dtype=np.float32), k=5, threshold=0.0)) == 0
    assert len(knn_graph(np.ones((1, 3), dtype=np.float32), k=5, threshold=0.0)) == 0


def test_zero_vectors_do_not_divide_by_zero():
    vectors = np.array([[0.0, 0.0], [1.0, 0.0], [0.9, 0.1]], dtype=np.float32)
    graph = knn_graph(vectors, k=2, threshold=0.5)
    assert np.isfinite(graph.sim).all()


def test_cluster_labels_separate_blobs_and_drop_small_communities():
    pytest.importorskip("igraph")
    rng = np.random.default_rng(5)
    a = np.array([1.0, 0.0, 0.0]) + rng.normal(scale=0.01, size=(10, 3))
    b = np.array([0.0, 1.0, 0.0]) + rng.normal(scale=0.01, size=(10, 3))
    loner = np.array([[0.0, 0.0, 1.0]])
    vectors = np.vstack([a, b, loner]).astype(np.float32)
    # k=9 makes each blob a complete graph, which the clustering keeps whole.
    graph = knn_graph(vectors, k=9, threshold=0.9)
    labels = cluster_labels(graph, len(vectors), min_cluster_size=3)
    assert len(set(labels[:10])) == 1
    assert len(set(labels[10:20])) == 1
    assert labels[0] != labels[10]
    assert sorted({labels[0], labels[10]}) == [0, 1]
    assert labels[20] == -1


def test_cluster_labels_without_edges_are_all_unclustered():
    pytest.importorskip("igraph")
    vectors = np.eye(3, dtype=np.float32)
    graph = knn_graph(vectors, k=2, threshold=0.9)
    assert cluster_labels(graph, 3, min_cluster_size=2) == [-1, -1, -1]
    assert cluster_labels(graph, 0, min_cluster_size=2) == []


def _hand_graph(edges: list[tuple[int, int, float]]) -> KnnGraph:
    edges = sorted((min(a, b), max(a, b), w) for a, b, w in edges)
    return KnnGraph(
        np.array([a for a, _, _ in edges], dtype=np.int32),
        np.array([b for _, b, _ in edges], dtype=np.int32),
        np.array([w for _, _, w in edges], dtype=np.float32),
        np.zeros(len(edges), dtype=np.int16),
    )


def _ring_of_cliques(cliques: int = 30, size: int = 5) -> KnnGraph:
    edges = []
    for c in range(cliques):
        base = c * size
        for i in range(size):
            for j in range(i + 1, size):
                edges.append((base + i, base + j, 0.9))
        edges.append((base + size - 1, ((c + 1) % cliques) * size, 0.9))
    return _hand_graph(edges)


def _joined_triangles_and_loners() -> KnnGraph:
    edges = [
        (0, 1, 0.9), (1, 2, 0.9), (0, 2, 0.9),
        (3, 4, 0.9), (4, 5, 0.9), (3, 5, 0.9),
        (2, 3, 0.5),
    ]
    return _hand_graph(edges)


def test_cluster_labels_are_deterministic():
    pytest.importorskip("igraph")
    rng = np.random.default_rng(21)
    centres = np.eye(3, 6)
    vectors = np.vstack(
        [c + rng.normal(scale=0.2, size=(20, 6)) for c in centres]
    ).astype(np.float32)
    graph = knn_graph(vectors, k=9, threshold=0.0)

    random.seed(1)
    random.random()
    before = random.getstate()
    first = cluster_labels(graph, 60, 3)
    assert random.getstate() == before

    random.seed(999)
    before = random.getstate()
    second = cluster_labels(graph, 60, 3)
    assert random.getstate() == before
    assert first == second


def test_cluster_labels_split_a_ring_of_cliques():
    pytest.importorskip("igraph")
    labels = cluster_labels(_ring_of_cliques(), 150, 3)
    per_clique = [set(labels[c * 5:(c + 1) * 5]) for c in range(30)]
    assert all(len(s) == 1 for s in per_clique)
    flat = [next(iter(s)) for s in per_clique]
    assert all(flat[c] != flat[(c + 1) % 30] for c in range(30))
    assert len(set(flat)) == 30
    assert -1 not in flat


def test_near_duplicate_view_falls_back_to_one_cluster():
    pytest.importorskip("igraph")
    vectors = np.array([[1.0, 0.01 * i, 0.0, 0.0] for i in range(5)], dtype=np.float32)
    graph = knn_graph(vectors, k=15, threshold=0.5)
    assert len(graph) == 10
    assert cluster_labels(graph, 5, 3) == [0, 0, 0, 0, 0]


def test_fallback_keeps_the_fine_result_unless_coarse_labels_more(monkeypatch):
    pytest.importorskip("igraph")
    monkeypatch.setattr(graph_knn, "FALLBACK_RESOLUTION", 0.0)

    ring = cluster_labels(_ring_of_cliques(), 150, 3)
    assert len(set(ring)) == 30

    labels = cluster_labels(_joined_triangles_and_loners(), 10, 3)
    assert labels[6:] == [-1, -1, -1, -1]
    assert len(set(labels[:3])) == 1
    assert len(set(labels[3:6])) == 1
    assert labels[0] != labels[3]
    assert sorted({labels[0], labels[3]}) == [0, 1]


def test_similarity_edges_keep_only_top_ranks_and_map_ids():
    rng = np.random.default_rng(9)
    vectors = rng.normal(size=(30, 4)).astype(np.float32)
    graph = knn_graph(vectors, k=10, threshold=-1.0)
    ids = [f"id-{i}" for i in range(30)]
    edges = similarity_edges(graph, ids, edge_k=2)
    expected = {(s, d) for (s, d), r in _as_dict(graph).items() if r < 2}
    assert {(ids.index(e["source"]), ids.index(e["target"])) for e in edges} == expected
    assert all(e["score"] == round(e["score"], 3) for e in edges)
    assert all(isinstance(e["score"], float) for e in edges)
