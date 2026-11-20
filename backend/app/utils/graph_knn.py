"""Exact k-nearest-neighbour graph over embeddings, in bounded memory.

The unified graph needs two things from pairwise similarity: a sparse graph to
cluster and a few edges per node to draw. One pass yields both without ever
materialising the N x N matrix: each chunk of rows is scored against every row
and only its top k survive.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

import numpy as np

CLUSTER_K = 15
CLUSTER_RESOLUTION = 2.0
FALLBACK_RESOLUTION = 1.0
MIN_CLUSTERED_SHARE = 0.9
CLUSTER_SEED = 42
EDGE_K = 5
# Scratch per chunk is a float32 similarity block plus argpartition's int64
# index, 12 bytes per cell; this keeps it near 128 MB at any corpus size.
CHUNK_SCRATCH_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class KnnGraph:
    src: np.ndarray
    dst: np.ndarray
    sim: np.ndarray
    rank: np.ndarray

    def __len__(self) -> int:
        return int(self.src.size)


_EMPTY = KnnGraph(
    np.empty(0, dtype=np.int32),
    np.empty(0, dtype=np.int32),
    np.empty(0, dtype=np.float32),
    np.empty(0, dtype=np.int16),
)


def _normalize_rows(vectors) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms


def _auto_chunk(n: int) -> int:
    return max(64, min(1000, CHUNK_SCRATCH_BYTES // (12 * max(n, 1))))


def knn_graph(vectors, k: int, threshold: float, chunk_size: int | None = None) -> KnnGraph:
    x = _normalize_rows(vectors)
    n = x.shape[0]
    if n < 2 or k < 1:
        return _EMPTY
    k_eff = min(k, n - 1)
    step = chunk_size or _auto_chunk(n)

    srcs: list[np.ndarray] = []
    dsts: list[np.ndarray] = []
    sims: list[np.ndarray] = []
    ranks: list[np.ndarray] = []
    for start in range(0, n, step):
        stop = min(start + step, n)
        block = x[start:stop] @ x.T
        local = np.arange(stop - start)
        block[local, start + local] = -np.inf
        top = np.argpartition(block, -k_eff, axis=1)[:, -k_eff:]
        top_sims = np.take_along_axis(block, top, axis=1)
        order = np.argsort(-top_sims, axis=1, kind="stable")
        top = np.take_along_axis(top, order, axis=1)
        top_sims = np.take_along_axis(top_sims, order, axis=1)
        rows, positions = np.nonzero(top_sims >= threshold)
        srcs.append((start + rows).astype(np.int32))
        dsts.append(top[rows, positions].astype(np.int32))
        sims.append(top_sims[rows, positions].astype(np.float32))
        ranks.append(positions.astype(np.int16))

    src = np.concatenate(srcs)
    dst = np.concatenate(dsts)
    if src.size == 0:
        return _EMPTY
    sim = np.concatenate(sims)
    rank = np.concatenate(ranks)

    lo = np.minimum(src, dst)
    hi = np.maximum(src, dst)
    order = np.lexsort((rank, hi, lo))
    lo, hi, sim, rank = lo[order], hi[order], sim[order], rank[order]
    first = np.ones(lo.size, dtype=bool)
    first[1:] = (lo[1:] != lo[:-1]) | (hi[1:] != hi[:-1])
    return KnnGraph(lo[first], hi[first], sim[first], rank[first])


def _drop_small(membership: list[int], min_cluster_size: int) -> list[int]:
    sizes = Counter(membership)
    renumbered: dict[int, int] = {}
    for community in sorted(sizes):
        if sizes[community] >= min_cluster_size:
            renumbered[community] = len(renumbered)
    return [renumbered.get(community, -1) for community in membership]


def _leiden(g, resolution: float, min_cluster_size: int) -> list[int]:
    import igraph

    # A private Random leaves Python's global state alone. igraph's generator
    # is process-global: the kNN executor runs one job at a time, and the
    # default is put back so no other igraph caller inherits the seeded one
    # (leidenalg in app/utils/leiden.py seeds its own generator).
    igraph.set_random_number_generator(random.Random(CLUSTER_SEED))
    try:
        membership = g.community_leiden(
            objective_function="modularity",
            weights="weight",
            resolution=resolution,
            n_iterations=-1,
        ).membership
    finally:
        igraph.set_random_number_generator(random)
    return _drop_small(membership, min_cluster_size)


def cluster_labels(graph: KnnGraph, n: int, min_cluster_size: int) -> list[int]:
    import igraph

    if n == 0:
        return []
    if len(graph) == 0:
        return _drop_small(list(range(n)), min_cluster_size)

    g = igraph.Graph(
        n=n,
        edges=np.column_stack((graph.src, graph.dst)).tolist(),
        directed=False,
    )
    g.es["weight"] = graph.sim.astype(float).tolist()
    labels = _leiden(g, CLUSTER_RESOLUTION, min_cluster_size)
    labelled = sum(1 for label in labels if label >= 0)
    if labelled < MIN_CLUSTERED_SHARE * n:
        # Modularity at the fine resolution scores a small near-duplicate view
        # best as singletons, which the size floor then drops.
        coarse = _leiden(g, FALLBACK_RESOLUTION, min_cluster_size)
        if sum(1 for label in coarse if label >= 0) > labelled:
            return coarse
    return labels


def similarity_edges(graph: KnnGraph, ids: list[str], edge_k: int = EDGE_K) -> list[dict]:
    keep = graph.rank < edge_k
    return [
        {"source": ids[s], "target": ids[t], "score": round(float(v), 3)}
        for s, t, v in zip(
            graph.src[keep].tolist(),
            graph.dst[keep].tolist(),
            graph.sim[keep].tolist(),
        )
    ]
