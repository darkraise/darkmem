# Memory Graph at Scale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the memory graph show a chosen number of memories or all of them, newest first, and keep the 2D view smooth at 20,000 nodes.

**Architecture:** The backend replaces the dense all-pairs similarity work with one exact k-nearest-neighbour pass (`app/utils/graph_knn.py`) that feeds both Louvain clustering and the drawn edges, caches the assembled memory arm per corpus stamp, bounds LLM cluster naming, and scopes the entity overlay to plotted memories. The frontend adds a Nodes control with an All checkbox, then tunes the Sigma 2D renderer by node-count tier (straight edges, hide-on-move, cached hulls, cluster-seeded layout, scaled ForceAtlas2) and gives 3D shared geometry plus a large-graph notice.

**Tech Stack:** FastAPI, SQLAlchemy async + asyncpg, pgvector, numpy, python-igraph; React 19, TanStack Query, zustand, Sigma 3 + graphology, react-force-graph-3d, darkraise-ui, vitest, Storybook.

**Spec:** docs/superpowers/specs/2026-09-29-memory-graph-scale-design.md

**Execution:** inline — `claude --model sonnet --effort high` — 4 of 18 tasks are heavy (2, 3, 4, 14) and 4 are four-band (9, 11, 13, 15), within a third, so all eight are delegated and the rest total 3 or less.

**Plan review:** 2026-09-29 — dr-superpowers:judge-opus — executability 15 / coherence 18 / coverage 12 / assumptions 14 (round 1)

## Global Constraints

- Language: English only in code, comments, docs, commits.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 chars, imperative, no period.
- Comments: none unless the WHY is non-obvious; never reference the task, plan or caller.
- Backend commands run from `backend/` with `.venv/bin/python`; there is no `python` on PATH and no host `psql`.
- Backend tests need the dev Postgres: `docker compose -f docker-compose.dev.yml up -d postgres` from the repo root (never the whole dev stack). Use `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` for a delegated task's runs; `darkmem_test` is the controller's.
- Every test, build and network command carries an explicit timeout; kill any process you start before the task ends.
- Frontend commands run from `frontend/`: `npm run typecheck` (never bare `tsc`), `npx vitest run <paths>`. Never run a repo-wide `prettier --write`. Never run `npx playwright test`.
- UI components come from darkraise-ui (`NumberInput`, `Checkbox`, `Button`, `Label`).
- Constants (spec): `GRAPH_MAX_NODES = 50_000`, `GRAPH_MAX_ENTITIES = 20_000`, `CLUSTER_K = 15`, `EDGE_K = 5`, `CLUSTER_NAME_LLM_CAP = 40`, result cache size 4, cluster-name cache size 1024.
- Selection order is newest first: `ORDER BY m.created_at DESC, e.memory_id DESC`.
- When a step appends tests to an existing file, put any new imports at the top of that file with its other imports.
- Invariant 13 (one process) is what makes module-level caches in `app/services/graph.py` sound; do not add cross-process machinery.

## Contracts

- **C1 `app/utils/graph_knn.py`** (Task 1): `CLUSTER_K = 15`, `EDGE_K = 5`; `@dataclass(frozen=True) class KnnGraph(src: np.ndarray[int32], dst: np.ndarray[int32], sim: np.ndarray[float32], rank: np.ndarray[int16])` with `__len__`, pairs stored `src < dst`, `rank` = the pair's 0-based position in the better-ranking endpoint's neighbour list; `knn_graph(vectors, k: int, threshold: float, chunk_size: int | None = None) -> KnnGraph` (None sizes chunks to about 128 MB of scratch); `cluster_labels(graph: KnnGraph, n: int, min_cluster_size: int) -> list[int]` (-1 = unclustered, valid communities renumbered from 0 in ascending Louvain id); `similarity_edges(graph: KnnGraph, ids: list[str], edge_k: int = EDGE_K) -> list[dict]` returning `{"source": str, "target": str, "score": float(3 dp)}`.
- **C2 `PostgresVectorRepository.get_all_vectors`** (Task 2): same signature; rows newest first; each point `{"memory_id": UUID, "vector": list[float], "payload": dict, "importance": float | None, "project": str, "status": str}`.
- **C2b `PostgresVectorRepository.get_vector_matrix(fingerprint: str, limit: int = 500, filters: MemoryFilter | None = None) -> tuple[list[dict], np.ndarray]`** (Task 2): the same rows in the same order as C2, streamed in batches of 1,000; points carry every C2 key except `vector`, and the float32 matrix holds one row per point.
- **C3 `PostgresVectorRepository.scope_stamp(fingerprint: str, filters: MemoryFilter | None = None) -> tuple[int, datetime | None]`** (Task 2): count of rows `get_all_vectors` could return without a limit, and their newest `memories.updated_at`.
- **C4 `PostgresVectorRepository.get_louvain_clustered_vectors(fingerprint: str, min_score: float = 0.5, min_cluster_size: int = 3, limit: int = 500, filters: MemoryFilter | None = None) -> tuple[list[dict], list[dict]]`** (Task 3): keeps its name (spec); now answers C2b points each with `"cluster": int`, plus C1 edge dicts.
- **C5 `app/services/graph.py`** (Task 4): module constants `GRAPH_MAX_NODES`, `GRAPH_MAX_ENTITIES`, `CLUSTER_NAME_LLM_CAP`; `reset_graph_caches() -> None` (test hook); `GraphService.get_unified_graph(limit=200, similarity_threshold=0.75, min_cluster_size=3, include_entities=False, project=None, all_memories=False) -> dict` whose result adds `total_memories: int` and `memories_truncated: bool`; `GraphService._generate_cluster_names(clusters, memory_nodes) -> tuple[dict[str, str], bool]` (names, degraded).
- **C6 REST** (Task 5): `GET /api/v1/graph/unified?limit=<1..50000>&all=<bool>&…`; `all=true` overrides `limit`.
- **C7 `PostgresGraphRepository.get_entities_for_memories(memory_ids: list[str], limit: int) -> dict`** (Task 7): `{"entities": [...], "relations": [...], "truncated": bool}` in `get_full_graph`'s row shapes.
- **C8 frontend hook** (Task 9): `useUnifiedGraph(similarityThreshold = 0.75, minClusterSize = 3, includeEntities = false, nodeLimit = 200, allNodes = false)`; query key `projectScopedKey("unifiedGraph", similarityThreshold, minClusterSize, includeEntities, allNodes ? "all" : nodeLimit)`; `UnifiedGraphData` gains `total_memories?: number`, `memories_truncated?: boolean`.
- **C9 `frontend/src/features/graph/lib/graph-prefs.ts`** (Task 10): exports `NODE_LIMIT_DEFAULT = 200`, `NODE_LIMIT_MIN = 50`, `NODE_LIMIT_MAX = 50_000`, `NODE_LIMIT_STEP = 100`; store fields `nodeLimit: number`, `allNodes: boolean`, `setNodeLimit(n: number)` (rounds, clamps to min/max, ignores non-finite), `setAllNodes(v: boolean)`.
- **C10 `frontend/src/features/graph/components/node-count-row.tsx`** (Task 10): `NodeCountRow({ nodeLimit, onNodeLimitChange, allNodes, onAllNodesChange, shown, total, truncated }: { nodeLimit: number; onNodeLimitChange: (n: number) => void; allNodes: boolean; onAllNodesChange: (v: boolean) => void; shown: number; total?: number; truncated?: boolean })`; `GraphToolbar` gains optional prop `nodes?: React.ReactNode` rendered as a first section titled "Nodes".
- **C11 `frontend/src/features/graph/lib/graph-scale.ts`** (Task 12): `type ScaleTier = "small" | "medium" | "large" | "huge"`; `scaleTier(nodeCount)`; `interface ScaleSettings { curvedEdges: boolean; hideOnMove: boolean; slowDown: number; barnesHutOptimize: boolean; layoutMs: number; sphereSegments: [number, number]; arrows3D: boolean; hulls3D: boolean; warmupTicks3D: number; cooldownTicks3D: number }`; `scaleSettings(nodeCount, edgeCount): ScaleSettings`; `CURVED_EDGE_LIMIT = 2000`; `LARGE_3D_NOTICE_NODES = 5000`; `interface ClusterAnchor { x: number; y: number; spread: number }`; `clusterAnchors(memories: { cluster: number }[]): Map<number, ClusterAnchor>`; `seedAroundAnchor(anchor: ClusterAnchor, u: number, v: number): { x: number; y: number }`.
- **C12 `frontend/src/features/graph/lib/graph-geometry.ts`** (Task 14): `framedHullVertices(sigma: Sigma, memberIds: string[]): Point[]`; `drawFramedHull(ctx, sigma, framed: Point[], color, fillAlpha, strokeAlpha): Point[]`; `drawHullForSigma` is deleted.
- **C13 `frontend/src/features/graph/lib/synthetic-graph.ts`** (Task 16): `syntheticMemoryGraph(nodeCount: number, clusterCount: number, edgesPerNode: number, seed = 1): { memories: UnifiedMemory[]; edges: SimilarityEdge[]; clusterNames: Record<string, string> }`; story title `Graph/Graph2DRenderer` with exports `Scale2k`, `Scale20k`, container `data-testid="scale-harness"`.

## Assumptions (evidence)

- Real corpus is 4,580 memories and 9,334 entities (darkmem MCP `memory_stats` against 192.168.0.199, 2026-09-29); this host's production database holds 0 memories (`docker exec darkmem-prod-postgres-1 psql … count(*)`, 2026-09-29).
- Exact top-15 by chunked matmul takes 0.40 s at 4,600 and 5.14 s at 20,000 synthetic 1024-d vectors, Louvain 0.01 s / 0.05 s (12-core host, backend venv, 2026-09-29).
- Text-parsing 20,000 vectors costs 1.6 s in Python (same run); pgvector casts `vector` to `real[]` (`SELECT '[1,2.5,3]'::vector::real[]` answered `{1,2.5,3}` on the production Postgres, read-only, 2026-09-29).
- asyncpg decodes `real[]` into a Python list per row (about 32 bytes per float), so a 20,000 × 1024 read held as lists is about 0.65 GB; `get_vector_matrix` streams 1,000-row batches into float32 instead, and `knn_graph` sizes its chunks so `chunk × N × 12` bytes stays near 128 MB. Task 8 reports peak RSS.
- `_fetch_importance_map` passes one bind parameter per id (`backend/app/services/graph.py:151-161`); asyncpg's per-statement ceiling is 32,767 parameters, so an all-memories read above that fails. Task 2 moves importance into the bulk read.
- `get_full_graph(limit=500)` backs the entity overlay (`backend/app/services/graph.py:241`); `ix_entities_memory_ids` is a GIN index (`backend/migrations/versions/0001_baseline.py:265`).
- `touch_updated_at` fires on UPDATE only (`backend/migrations/versions/0001_baseline.py:210`), so a test's explicit `updated_at` on INSERT is kept.
- `total_memories` counts memories that have a vector in the active partition (C3), not every in-scope memory: a memory whose embedding is pending or failed cannot be plotted, and counting it would report a truncation that no node budget can close.
- `get_louvain_clustered_vectors` has one production caller (`backend/app/services/graph.py:54`) and one test caller (`backend/tests/test_pushdown_remaining_channels.py:341`), whose spy returns `[]`; `_louvain_igraph` has two test callers (`backend/tests/unit/test_algorithms.py:582-614`); `cosine_similarity_matrix` has one caller (`backend/app/services/graph.py:169`).
- Sigma resolves `edgeProgramClasses` by replacing the default map, so `line` must be registered explicitly; `EdgeRectangleProgram` is exported from `sigma/rendering` (`frontend/node_modules/sigma/dist/declarations/src/rendering/index.d.ts:22`). `FA2Layout.isRunning()` exists (`frontend/node_modules/graphology-layout-forceatlas2/worker.d.ts:13`).
- `drawHullForSigma` has one caller, the memory 2D renderer (`rg drawHullForSigma frontend/src`, 2026-09-29). Convex hulls commute with the affine framed-graph → viewport map, so hulls computed in framed space and mapped per frame equal today's.
- The 3D selection effect mutates each node's own material (`frontend/src/features/graph/components/graph-3d-renderer.tsx:266-319`), so only geometry is shared.
- darkraise-ui `Checkbox` renders `role="checkbox"`; `NumberInputIncrementTrigger` defaults to `aria-label="Increment"` (`frontend/node_modules/darkraise-ui/dist/chunk-DNR4VRVQ.js`).
- The hook's project-scope test pins the four-part key (`frontend/src/hooks/api/__tests__/use-graph-api-project-scope.test.tsx:46-53`); Task 9 updates it to the five-part key.
- Browser fps in the Playwright MCP browser may use software WebGL — unverified — Task 17 reads the WebGL renderer string and labels the figure accordingly.
- The frontend tsconfig lib is ES2020 (`frontend/tsconfig.app.json`), so tests index arrays instead of calling `Array.prototype.at`.
- The Mode control is a radio group labelled "Render mode" whose options are radios (`frontend/src/features/memory-graph/components/__tests__/graph-reset.test.tsx:93-106` uses the same roles for its sibling groups).
- The Playwright MCP tools `browser_navigate`, `browser_evaluate`, `browser_run_code_unsafe`, `browser_wait_for`, `browser_take_screenshot` and `browser_close` are available in this session (deferred-tool list, 2026-09-29).
- The spec's hull-group memoisation test is covered by the Task 17 measurement only: the memo lives in the renderer's closure, which jsdom cannot run (no WebGL).
- Plan review round 1 scored coverage 12 (borderline); the gaps it named (deploy task, prefs persistence, cache isolation) are fixed in this revision, so no second round was run.
- Codex executor lane is off (`executors` gate: `usable=false reason=free-plan lane=false`, 2026-09-29), so no task carries an Executor line.

## Task index

1. kNN graph module
2. Bulk vector read: order, native floats, importance, stamp
3. kNN clustering in the vector repository
4. Unified graph service: node budget, counts, cache
5. Unified route: node ceiling and all
6. Cluster naming budget
7. Entity overlay scoped to plotted memories
8. Graph scale bench
9. Frontend hook: node limit and all
10. Node count control
11. Graph page wiring
12. Scale tiers and cluster seeding
13. 2D renderer scale settings
14. 2D hull caching
15. 3D best-effort and large-graph notice
16. Synthetic graph and 20k story
17. Scale verification
18. Gate and deploy

---

### Task 1: kNN graph module

**Files:**
- Create: `backend/app/utils/graph_knn.py`
- Test: `backend/tests/unit/test_graph_knn.py`

**Interfaces:**
- Consumes: nothing.
- Produces: C1.

**Items:** 5

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_graph_knn.py`:

```python
import numpy as np
import pytest

from app.utils.graph_knn import _auto_chunk, cluster_labels, knn_graph, similarity_edges


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
    # k=9 makes each blob a complete graph, which Louvain keeps whole.
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && timeout 120 .venv/bin/python -m pytest -q tests/unit/test_graph_knn.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.graph_knn'`.

- [ ] **Step 3: Write the module**

Create `backend/app/utils/graph_knn.py`:

```python
"""Exact k-nearest-neighbour graph over embeddings, in bounded memory.

The unified graph needs two things from pairwise similarity: a sparse graph to
cluster and a few edges per node to draw. One pass yields both without ever
materialising the N x N matrix: each chunk of rows is scored against every row
and only its top k survive.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

CLUSTER_K = 15
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
        top = np.argpartition(-block, k_eff - 1, axis=1)[:, :k_eff]
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


def cluster_labels(graph: KnnGraph, n: int, min_cluster_size: int) -> list[int]:
    import igraph

    if n == 0:
        return []
    if len(graph) == 0:
        membership = list(range(n))
    else:
        g = igraph.Graph(
            n=n,
            edges=np.column_stack((graph.src, graph.dst)).tolist(),
            directed=False,
        )
        g.es["weight"] = graph.sim.astype(float).tolist()
        membership = g.community_multilevel(weights="weight").membership

    sizes = Counter(membership)
    renumbered: dict[int, int] = {}
    for community in sorted(sizes):
        if sizes[community] >= min_cluster_size:
            renumbered[community] = len(renumbered)
    return [renumbered.get(community, -1) for community in membership]


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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && timeout 120 .venv/bin/python -m pytest -q tests/unit/test_graph_knn.py`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/graph_knn.py backend/tests/unit/test_graph_knn.py
git commit -m "feat(graph): add a bounded-memory kNN graph"
```

### Task 2: Bulk vector read: order, native floats, importance, stamp

**Files:**
- Modify: `backend/app/repositories/vector.py` (imports; `get_all_vectors` at 232-270; new `scope_stamp` after it)
- Test: `backend/tests/test_graph_scale.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: C2, C2b, C3.

**Items:** 2, 5

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_graph_scale.py`:

```python
"""The unified graph at scale: selection order, counts, clustering and cache."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table

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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_graph_scale.py`
Expected: FAIL — ordering assertion fails, the text parser is called, and `AttributeError`s for `get_vector_matrix` and `scope_stamp`.

- [ ] **Step 3: Implement**

In `backend/app/repositories/vector.py`, add `from datetime import datetime` to the imports (after `from dataclasses import dataclass`). Replace the whole `get_all_vectors` method with the following four members (`scope_stamp` follows them):

```python
    def _bulk_read(
        self, fingerprint: str, limit: int, filters: MemoryFilter | None,
    ) -> tuple[str, dict]:
        """The bulk partition read, newest first.

        A limit keeps the most recent memories rather than an arbitrary slice.
        The embedding is cast to ``real[]`` so asyncpg decodes it natively;
        parsing the text form costs seconds at tens of thousands of rows.
        ``importance`` rides the same row because a lookup by id would pass one
        bind parameter per memory, past asyncpg's limit.

        The join to ``memories`` is unconditional even when nothing is being
        scoped: the FK makes it lossless, and it is what puts ``project`` and
        ``status`` on every point, so an unscoped caller still hands back
        labelled rows rather than anonymous content snippets.
        """
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {"limit": limit}
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            where_sql = f"WHERE {filters.where_sql('m')}"
        sql = f"""
            SELECT e.memory_id,
                   e.embedding::real[] AS embedding,
                   e.payload,
                   m.importance AS importance,
                   {SCOPE_LABEL_COLUMNS}
            FROM {table} e
            {SCOPE_LABEL_JOIN}
            {where_sql}
            ORDER BY m.created_at DESC, e.memory_id DESC
            LIMIT :limit
        """
        return sql, params

    @staticmethod
    def _bulk_point(row) -> dict:
        return {
            "memory_id": UUID(str(row.memory_id)),
            "payload": row.payload,
            "importance": row.importance,
            **scope_labels(row),
        }

    async def get_all_vectors(
        self, fingerprint: str, limit: int = 500, filters: MemoryFilter | None = None,
    ) -> list[dict]:
        """Bulk read of one partition, for the projection and clustering views."""
        sql, params = self._bulk_read(fingerprint, limit, filters)
        result = await self.session.execute(text(sql), params)
        return [{**self._bulk_point(row), "vector": row.embedding} for row in result]

    async def get_vector_matrix(
        self, fingerprint: str, limit: int = 500, filters: MemoryFilter | None = None,
    ) -> tuple[list[dict], np.ndarray]:
        """``get_all_vectors`` without a Python list per vector.

        Rows stream in batches of 1,000 and each batch's embeddings are packed
        into float32 before the next arrives, so a 20,000 x 1024 read peaks
        near its 80 MB matrix rather than the ~0.65 GB its lists would hold.
        """
        sql, params = self._bulk_read(fingerprint, limit, filters)
        points: list[dict] = []
        blocks: list[np.ndarray] = []
        result = await self.session.stream(text(sql), params)
        async for batch in result.partitions(1000):
            points.extend(self._bulk_point(row) for row in batch)
            blocks.append(np.asarray([row.embedding for row in batch], dtype=np.float32))
        if not blocks:
            return [], np.empty((0, 0), dtype=np.float32)
        return points, np.vstack(blocks)

    async def scope_stamp(
        self, fingerprint: str, filters: MemoryFilter | None = None,
    ) -> tuple[int, datetime | None]:
        """How many rows ``get_all_vectors`` could return under ``filters``,
        and the newest ``memories.updated_at`` among them.

        Together they move whenever the readable set does: a capture or
        re-extraction bumps ``updated_at`` through the ``touch_updated_at``
        trigger, and a delete moves the count.
        """
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {}
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            where_sql = f"WHERE {filters.where_sql('m')}"

        row = (
            await self.session.execute(
                text(f"""
                    SELECT count(*) AS n, max(m.updated_at) AS last_updated
                    FROM {table} e
                    {SCOPE_LABEL_JOIN}
                    {where_sql}
                """),
                params,
            )
        ).one()
        return int(row.n), row.last_updated
```

- [ ] **Step 4: Run the new tests and the bulk-read neighbours**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/test_pushdown_remaining_channels.py tests/test_vectors_route.py tests/test_scope_labels.py`
Expected: PASS. If `session.stream` fails under the test fixture's transaction, report the error text rather than falling back to `execute`: the streamed read is what bounds peak memory.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/vector.py backend/tests/test_graph_scale.py
git commit -m "perf(graph): read vectors newest first, natively"
```

### Task 3: kNN clustering in the vector repository

**Files:**
- Modify: `backend/app/repositories/vector.py` (delete `_COMMUNITY_SAMPLE_CAP` at line 12, `_build_sparse_edges`, `_louvain_igraph`; rewrite `get_louvain_clustered_vectors`)
- Modify: `backend/tests/unit/test_algorithms.py` (delete `test_louvain_igraph_basic` and `test_louvain_igraph_no_edges_returns_singletons`, lines 582-614)
- Modify: `backend/tests/test_pushdown_remaining_channels.py:329-343` (the scope-forwarding spy)
- Test: `backend/tests/test_graph_scale.py`

**Interfaces:**
- Consumes: C1, C2b.
- Produces: C4.

**Items:** 5

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_graph_scale.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_graph_scale.py -k knn`
Expected: FAIL — the old method returns a list, so unpacking `points, edges` raises `ValueError`, and the empty case returns `[]`.

- [ ] **Step 3: Implement**

In `backend/app/repositories/vector.py`: delete the line `_COMMUNITY_SAMPLE_CAP = 10_000` (and the blank line after it), delete `_build_sparse_edges` and `_louvain_igraph` in full, and replace the whole `get_louvain_clustered_vectors` method with:

```python
    async def get_louvain_clustered_vectors(
        self,
        fingerprint: str,
        min_score: float = 0.5,
        min_cluster_size: int = 3,
        limit: int = 500,
        filters: MemoryFilter | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Points labelled with a ``cluster``, plus the similarity edges to draw.

        One exact k-nearest-neighbour pass feeds both: Louvain clusters the
        top-``CLUSTER_K`` graph, and the edges are the pairs in either
        endpoint's top ``EDGE_K``. Memory stays O(chunk x N).
        """
        from app.utils.graph_knn import CLUSTER_K, cluster_labels, knn_graph, similarity_edges

        points, vectors = await self.get_vector_matrix(fingerprint, limit=limit, filters=filters)
        if not points:
            return [], []

        graph = knn_graph(vectors, k=CLUSTER_K, threshold=min_score)
        for point, label in zip(points, cluster_labels(graph, len(points), min_cluster_size)):
            point["cluster"] = label
        ids = [str(p["memory_id"]) for p in points]
        return points, similarity_edges(graph, ids)
```

In `backend/tests/unit/test_algorithms.py` delete the two methods `test_louvain_igraph_basic` and `test_louvain_igraph_no_edges_returns_singletons` in full (their coverage moved to `tests/unit/test_graph_knn.py`).

In `backend/tests/test_pushdown_remaining_channels.py`, `test_clustered_reads_forward_the_scope_to_the_bulk_read` spies only `get_all_vectors`, which the Louvain read no longer calls. Add `import numpy as np` to the file's imports, and directly after the line `monkeypatch.setattr(PostgresVectorRepository, "get_all_vectors", spy)` insert:

```python
    async def matrix_spy(self, fingerprint, limit=500, filters=None):
        seen.append(filters)
        return [], np.empty((0, 0), dtype=np.float32)

    monkeypatch.setattr(PostgresVectorRepository, "get_vector_matrix", matrix_spy)
```

The assertion `seen == [ALPHA_ACTIVE, ALPHA_ACTIVE]` stays as it is.

`backend/app/services/graph.py` still treats the result as a list until Task 4; its call sits inside a `try` whose `except Exception` logs, so the service degrades to an empty memory arm in between, and this task's run excludes the service tests.

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/unit/test_algorithms.py tests/unit/test_graph_knn.py tests/test_pushdown_remaining_channels.py -k "not unified_graph"`
Expected: PASS. Then `rg -n "_louvain_igraph|_build_sparse_edges|_COMMUNITY_SAMPLE_CAP" backend` must print nothing.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/vector.py backend/tests/unit/test_algorithms.py backend/tests/test_pushdown_remaining_channels.py backend/tests/test_graph_scale.py
git commit -m "perf(graph): cluster on the kNN graph"
```

### Task 4: Unified graph service: node budget, counts, cache

**Files:**
- Modify: `backend/app/services/graph.py` (imports; module constants and caches; `get_unified_graph`; new `_build_memory_arm` and `_empty_memory_arm`; `_generate_cluster_names` return shape; delete `_fetch_importance_map` and `_compute_similarity_edges`)
- Modify: `backend/app/utils/math.py` (delete `cosine_similarity_matrix`)
- Modify: `backend/tests/conftest.py` (autouse cache reset)
- Test: `backend/tests/test_graph_scale.py`

**Interfaces:**
- Consumes: C2, C3, C4.
- Produces: C5.

**Items:** 4, 5

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_graph_scale.py`:

```python
import app.services.graph as graph_module
from app.services.graph import GraphService


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_graph_scale.py`
Expected: FAIL — `AttributeError: module 'app.services.graph' has no attribute 'GRAPH_MAX_NODES'` and missing `total_memories` keys.

- [ ] **Step 3: Implement**

In `backend/app/services/graph.py`:

1. Replace the import block's `import asyncio` / `import logging` / `from uuid import UUID` / `import numpy as np` lines with:

```python
import asyncio
import logging
from collections import OrderedDict
from uuid import UUID
```

(delete `import numpy as np`; keep every other import).

2. After the `GRAPH_MEMORY_STATUSES` definition, add:

```python
GRAPH_MAX_NODES = 50_000
GRAPH_MAX_ENTITIES = 20_000
CLUSTER_NAME_LLM_CAP = 40
_RESULT_CACHE_SIZE = 4

# The assembled memory arm, keyed on everything that decides it. Module-level
# state is sound only because invariant 13 pins one process.
_result_cache: OrderedDict[tuple, dict] = OrderedDict()


def reset_graph_caches() -> None:
    """Test hook: forget every cached memory arm."""
    _result_cache.clear()


def _empty_memory_arm() -> dict:
    return {
        "memories": [],
        "clusters": {},
        "cluster_names": {},
        "similarity_edges": [],
        "total_memories": 0,
        "memories_truncated": False,
    }
```

3. Replace the whole `get_unified_graph` method with:

```python
    async def get_unified_graph(
        self,
        limit: int = 200,
        similarity_threshold: float = 0.75,
        min_cluster_size: int = 3,
        include_entities: bool = False,
        project: str | None = None,
        all_memories: bool = False,
    ) -> dict:
        effective_limit = GRAPH_MAX_NODES if all_memories else min(limit, GRAPH_MAX_NODES)
        memory_arm = _empty_memory_arm()
        fingerprint_unresolved = False

        if self.vector_repo and self.llm is not None:
            try:
                fingerprint = await self.vector_repo.resolve_read_fingerprint(self.llm)
                scope = self._memory_scope(
                    MemoryFilter(project=project) if project is not None else None
                )
                total, last_updated = await self.vector_repo.scope_stamp(fingerprint, scope)
                key = (
                    fingerprint, project, similarity_threshold, min_cluster_size,
                    effective_limit, total, last_updated,
                )
                cached = _result_cache.get(key)
                if cached is not None:
                    _result_cache.move_to_end(key)
                    memory_arm = cached
                else:
                    memory_arm, degraded = await self._build_memory_arm(
                        fingerprint, scope, similarity_threshold, min_cluster_size,
                        effective_limit, total,
                    )
                    # A degraded arm carries fallback names for clusters whose
                    # naming call failed; caching it would pin them until the
                    # corpus next changes.
                    if not degraded:
                        _result_cache[key] = memory_arm
                        while len(_result_cache) > _RESULT_CACHE_SIZE:
                            _result_cache.popitem(last=False)
            except EmbedderFingerprintUnresolved:
                # Distinguishable from "no data": the embedding purpose's
                # dimensions is unset, or set to a value no real embed has
                # produced, and nothing has ever embedded under this model, so
                # there is no partition to read at all (invariant 2,
                # T2.68/T2.83) — surfaced on the response rather than only
                # logged, so an empty vector arm can never be mistaken for
                # "no data".
                fingerprint_unresolved = True
                logger.warning(
                    "Unified graph vector arm skipped: embedding fingerprint unresolved"
                )
            except Exception:
                logger.exception("Failed to fetch vector data")

        result = {**memory_arm, "fingerprint_unresolved": fingerprint_unresolved}

        if include_entities:
            entities, entity_relations, entities_truncated = await self._fetch_entity_overlay(
                result["memories"]
            )
            result["entities"] = entities
            result["entity_relations"] = entity_relations
            result["entities_truncated"] = entities_truncated

        return result

    async def _build_memory_arm(
        self,
        fingerprint: str,
        scope: MemoryFilter,
        similarity_threshold: float,
        min_cluster_size: int,
        limit: int,
        total: int,
    ) -> tuple[dict, bool]:
        clustered, similarity_edges = await self.vector_repo.get_louvain_clustered_vectors(
            fingerprint=fingerprint,
            min_score=similarity_threshold,
            min_cluster_size=min_cluster_size,
            limit=limit,
            filters=scope,
        )
        memory_nodes: list[dict] = []
        clusters: dict[int, list[str]] = {}
        for p in clustered:
            payload = p.get("payload") or {}
            mid = str(p["memory_id"])
            cluster_id = p.get("cluster", -1)
            importance = p.get("importance")
            memory_nodes.append({
                "id": mid,
                "content": payload.get("content", "") or "",
                "source": payload.get("source", ""),
                "tags": payload.get("tags", []),
                "memory_type": payload.get("memory_type"),
                "importance": importance if importance is not None else 0.5,
                "cluster": cluster_id,
                "project": p.get("project"),
                "status": p.get("status"),
            })
            if cluster_id >= 0:
                clusters.setdefault(cluster_id, []).append(mid)

        cluster_names, degraded = await self._generate_cluster_names(clusters, memory_nodes)
        return {
            "memories": memory_nodes,
            "clusters": {str(k): v for k, v in clusters.items()},
            "cluster_names": cluster_names,
            "similarity_edges": similarity_edges,
            "total_memories": total,
            "memories_truncated": len(memory_nodes) < total,
        }, degraded
```

4. Delete the methods `_fetch_importance_map` and `_compute_similarity_edges` in full.

5. Replace `_generate_cluster_names` with this version (same naming behaviour, now reporting whether any call failed):

```python
    async def _generate_cluster_names(
        self, clusters: dict[int, list[str]], memory_nodes: list[dict]
    ) -> tuple[dict[str, str], bool]:
        cluster_names: dict[str, str] = {}

        if not self.llm or not clusters:
            for cid in clusters:
                cluster_names[str(cid)] = f"Cluster {cid}"
            return cluster_names, False

        content_by_cluster: dict[int, list[str]] = {}
        for m in memory_nodes:
            cid = m.get("cluster", -1)
            if cid >= 0:
                content_by_cluster.setdefault(cid, []).append(m["content"][:100])

        cluster_system_prompt = prompt.get("cluster_naming")
        sem = asyncio.Semaphore(3)

        async def _name_one(cid: int, contents: list[str]) -> tuple[int, str, bool]:
            async with sem:
                try:
                    joined = "\n".join(contents[:8]).replace("</memories>", "")
                    sample = f"<memories>\n{joined}\n</memories>"
                    name = await self.llm.chat_completion(
                        "summarization",
                        messages=[
                            {"role": "system", "content": cluster_system_prompt},
                            {"role": "user", "content": sample},
                        ],
                    )
                    return cid, name.strip().strip('"').strip("'")[:40], False
                except Exception:
                    return cid, f"Cluster {cid}", True

        results = await asyncio.gather(
            *[_name_one(cid, contents) for cid, contents in content_by_cluster.items()]
        )
        degraded = False
        for cid, name, failed in results:
            cluster_names[str(cid)] = name
            degraded = degraded or failed

        return cluster_names, degraded
```

6. In `backend/app/utils/math.py` delete the function `cosine_similarity_matrix` in full (its only caller was `_compute_similarity_edges`). Keep `import numpy as np` if `pca_2d` still uses it (it does).

7. The caches are process-global, so every test must start without them. Append to `backend/tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _reset_graph_caches():
    from app.services.graph import reset_graph_caches

    reset_graph_caches()
    yield
    reset_graph_caches()
```

(If `pytest` is not already imported in `conftest.py`, add `import pytest`.)

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/test_api/test_graph.py tests/test_pushdown_remaining_channels.py tests/test_graph_cluster_naming.py tests/test_pushdown_keyword_graph.py`
Expected: PASS. Then `rg -n "cosine_similarity_matrix|_fetch_importance_map|_compute_similarity_edges" backend` must print nothing.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph.py backend/app/utils/math.py backend/tests/conftest.py backend/tests/test_graph_scale.py
git commit -m "feat(graph): add node budget, counts and a cache"
```

### Task 5: Unified route: node ceiling and all

**Files:**
- Modify: `backend/app/api/routes/graph.py:1-10` (import) and `:47-63` (`get_unified_graph` route)
- Test: `backend/tests/test_api/test_graph.py`

**Interfaces:**
- Consumes: C5.
- Produces: C6.

**Items:** 1, 4

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_api/test_graph.py`:

```python
from app.api.deps import get_graph_service
from app.main import app


class _SpyGraphService:
    def __init__(self):
        self.kwargs: dict = {}

    async def get_unified_graph(self, **kwargs):
        self.kwargs = kwargs
        return {"memories": [], "total_memories": 0, "memories_truncated": False}


async def test_unified_route_forwards_all_and_the_raised_limit(client, auth_headers):
    spy = _SpyGraphService()
    app.dependency_overrides[get_graph_service] = lambda: spy
    try:
        response = await client.get(
            "/api/v1/graph/unified?all=true&limit=20000", headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_graph_service, None)

    assert response.status_code == 200
    assert spy.kwargs["all_memories"] is True
    assert spy.kwargs["limit"] == 20000


async def test_unified_route_defaults_to_two_hundred_without_all(client, auth_headers):
    spy = _SpyGraphService()
    app.dependency_overrides[get_graph_service] = lambda: spy
    try:
        response = await client.get("/api/v1/graph/unified", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_graph_service, None)

    assert response.status_code == 200
    assert spy.kwargs["all_memories"] is False
    assert spy.kwargs["limit"] == 200


async def test_unified_route_refuses_a_limit_past_the_ceiling(client, auth_headers):
    response = await client.get("/api/v1/graph/unified?limit=50001", headers=auth_headers)
    assert response.status_code == 422
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_api/test_graph.py -k unified_route`
Expected: FAIL — `KeyError: 'all_memories'`, and the 20000 request answers 422.

- [ ] **Step 3: Implement**

In `backend/app/api/routes/graph.py` replace `from app.services.graph import GraphService` with:

```python
from app.services.graph import GRAPH_MAX_NODES, GraphService
```

and replace the `get_unified_graph` route function with:

```python
@router.get("/unified")
async def get_unified_graph(
    limit: int = Query(200, ge=1, le=GRAPH_MAX_NODES),
    all_memories: bool = Query(
        False,
        alias="all",
        description="Every in-scope memory, newest first, up to the node ceiling; overrides limit.",
    ),
    similarity_threshold: float = Query(0.75, ge=0.0, le=1.0),
    min_cluster_size: int = Query(3, ge=2, le=10),
    include_entities: bool = Query(False),
    project: str | None = Query(None),
    _user=Depends(require_auth),
    service: GraphService = Depends(get_graph_service),
):
    return await service.get_unified_graph(
        limit=limit,
        similarity_threshold=similarity_threshold,
        min_cluster_size=min_cluster_size,
        include_entities=include_entities,
        project=project,
        all_memories=all_memories,
    )
```

- [ ] **Step 4: Run the tests and the guards leg**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_api/test_graph.py`
Expected: PASS.

Run the guards leg (a served route's parameters changed):

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS. Exit 143 is an earlyoom kill: check `free -h` and re-run before treating it as a failure. A conformance failure naming the `all` alias is a real finding: report it with its message instead of renaming the parameter.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/graph.py backend/tests/test_api/test_graph.py
git commit -m "feat(graph): accept all and a 50,000 node ceiling"
```

### Task 6: Cluster naming budget

**Files:**
- Modify: `backend/app/services/graph.py` (imports; `_cluster_name_cache` beside `_result_cache`; `reset_graph_caches`; new `_tag_cluster_name`; `_generate_cluster_names`)
- Test: `backend/tests/test_graph_cluster_naming.py`

**Interfaces:**
- Consumes: C5.
- Produces: nothing new (C5's `_generate_cluster_names` shape unchanged).

**Items:** 5

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_graph_cluster_naming.py`:

```python
import app.services.graph as graph_module


class _CountingLLM:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        return f'"name {self.calls}"'


def _nodes(sizes: dict[int, int], tags: dict[int, list[str]] | None = None) -> tuple[dict, list[dict]]:
    clusters: dict[int, list[str]] = {}
    nodes: list[dict] = []
    for cid, size in sizes.items():
        for i in range(size):
            mid = f"{cid}-{i}"
            clusters.setdefault(cid, []).append(mid)
            nodes.append({
                "id": mid,
                "cluster": cid,
                "content": f"memory {mid}",
                "tags": (tags or {}).get(cid, []),
            })
    return clusters, nodes


@pytest.mark.asyncio
async def test_only_the_largest_clusters_cost_a_call(monkeypatch):
    monkeypatch.setattr(graph_module, "CLUSTER_NAME_LLM_CAP", 2)
    llm = _CountingLLM()
    clusters, nodes = _nodes({0: 3, 1: 5, 2: 1}, tags={2: ["project/darkmem", "retrieval"]})

    names, degraded = await GraphService(session=None, llm=llm)._generate_cluster_names(clusters, nodes)

    assert llm.calls == 2
    assert names["2"] == "retrieval"
    assert names["0"].startswith("name ") and names["1"].startswith("name ")
    assert degraded is False


@pytest.mark.asyncio
async def test_a_name_is_reused_while_its_sample_is_unchanged():
    llm = _CountingLLM()
    clusters, nodes = _nodes({0: 3})
    svc = GraphService(session=None, llm=llm)

    first, _ = await svc._generate_cluster_names(clusters, nodes)
    second, _ = await svc._generate_cluster_names(clusters, nodes)

    assert llm.calls == 1
    assert second == first


@pytest.mark.asyncio
async def test_tag_names_skip_project_tags_and_break_ties_alphabetically():
    clusters, nodes = _nodes(
        {0: 2, 1: 2},
        tags={0: ["project/x", "zeta", "alpha"], 1: ["project/x"]},
    )

    names, degraded = await GraphService(session=None, llm=None)._generate_cluster_names(clusters, nodes)

    assert names == {"0": "alpha", "1": "Cluster 1"}
    assert degraded is False


@pytest.mark.asyncio
async def test_a_failed_call_falls_back_and_is_not_cached():
    llm = _CountingLLM(fail=True)
    clusters, nodes = _nodes({0: 3}, tags={0: ["retrieval"]})
    svc = GraphService(session=None, llm=llm)

    names, degraded = await svc._generate_cluster_names(clusters, nodes)
    await svc._generate_cluster_names(clusters, nodes)

    assert names == {"0": "Cluster 0"}
    assert degraded is True
    assert llm.calls == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && timeout 120 .venv/bin/python -m pytest -q tests/test_graph_cluster_naming.py`
Expected: FAIL — the cap test sees 3 calls, the tag test sees `Cluster 0`, the reuse test sees 2 calls.

- [ ] **Step 3: Implement**

In `backend/app/services/graph.py`:

1. Extend the imports: `import hashlib` (after `import asyncio`) and `from collections import Counter, OrderedDict` (replacing `from collections import OrderedDict`).

2. Below `_RESULT_CACHE_SIZE = 4` add `_CLUSTER_NAME_CACHE_SIZE = 1024`, and below `_result_cache` add:

```python
# LLM cluster names keyed on a hash of the prompt and the naming sample, so a
# name is reused while the memories it was made from are unchanged.
_cluster_name_cache: OrderedDict[str, str] = OrderedDict()
```

3. Replace `reset_graph_caches` with:

```python
def reset_graph_caches() -> None:
    """Test hook: forget every cached memory arm and cluster name."""
    _result_cache.clear()
    _cluster_name_cache.clear()


def _tag_cluster_name(members: list[dict], cid: int) -> str:
    counts = Counter(
        tag
        for m in members
        for tag in (m.get("tags") or [])
        if not tag.startswith("project/")
    )
    if not counts:
        return f"Cluster {cid}"
    tag, _ = min(counts.items(), key=lambda item: (-item[1], item[0]))
    return tag[:40]
```

4. Replace `_generate_cluster_names` with:

```python
    async def _generate_cluster_names(
        self, clusters: dict[int, list[str]], memory_nodes: list[dict]
    ) -> tuple[dict[str, str], bool]:
        """Name every cluster; answers the names and whether any call failed.

        Only the ``CLUSTER_NAME_LLM_CAP`` largest clusters cost an LLM call,
        and a name is reused while its naming sample is unchanged. The rest
        are named after their most frequent non-project tag.
        """
        members: dict[int, list[dict]] = {}
        for m in memory_nodes:
            cid = m.get("cluster", -1)
            if cid >= 0:
                members.setdefault(cid, []).append(m)

        names = {str(cid): _tag_cluster_name(members.get(cid, []), cid) for cid in clusters}
        if not self.llm or not clusters:
            return names, False

        by_size = sorted(members, key=lambda cid: (-len(members[cid]), cid))
        to_name = [cid for cid in by_size[:CLUSTER_NAME_LLM_CAP] if cid in clusters]
        system_prompt = prompt.get("cluster_naming")
        sem = asyncio.Semaphore(3)

        async def _name_one(cid: int) -> tuple[int, str, bool]:
            contents = [m["content"][:100] for m in members[cid][:8]]
            key = hashlib.sha256("\x1f".join([system_prompt, *contents]).encode()).hexdigest()
            cached = _cluster_name_cache.get(key)
            if cached is not None:
                _cluster_name_cache.move_to_end(key)
                return cid, cached, False
            async with sem:
                try:
                    joined = "\n".join(contents).replace("</memories>", "")
                    sample = f"<memories>\n{joined}\n</memories>"
                    raw = await self.llm.chat_completion(
                        "summarization",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": sample},
                        ],
                    )
                    name = raw.strip().strip('"').strip("'")[:40]
                except Exception:
                    return cid, f"Cluster {cid}", True
            _cluster_name_cache[key] = name
            while len(_cluster_name_cache) > _CLUSTER_NAME_CACHE_SIZE:
                _cluster_name_cache.popitem(last=False)
            return cid, name, False

        degraded = False
        for cid, name, failed in await asyncio.gather(*[_name_one(cid) for cid in to_name]):
            names[str(cid)] = name
            degraded = degraded or failed
        return names, degraded
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_graph_cluster_naming.py tests/test_graph_scale.py tests/test_api/test_graph.py`
Expected: PASS (including the pre-existing `test_cluster_naming_dispatches_on_summarization`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph.py backend/tests/test_graph_cluster_naming.py
git commit -m "perf(graph): cap and cache LLM cluster names"
```

### Task 7: Entity overlay scoped to plotted memories

**Files:**
- Modify: `backend/app/repositories/graph.py` (new `get_entities_for_memories` after `get_full_graph`, ~line 486)
- Modify: `backend/app/services/graph.py` (`_fetch_entity_overlay`)
- Test: `backend/tests/test_graph_scale.py`

**Interfaces:**
- Consumes: C5 (`GRAPH_MAX_ENTITIES`).
- Produces: C7.

**Items:** 5

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_graph_scale.py`:

```python
from app.repositories.graph import PostgresGraphRepository


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


async def _add_relation(session, source: uuid.UUID, target: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, rel_type) "
            "VALUES (:s, :t, 'RELATED_TO')"
        ),
        {"s": source, "t": target},
    )


@pytest.mark.asyncio
async def test_entity_overlay_holds_only_entities_of_plotted_memories(session):
    m1 = await _add_memory(session)
    m2 = await _add_memory(session)
    elsewhere = await _add_memory(session)
    single = await _add_entity(session, "scale-single", [m1.id])
    shared = await _add_entity(session, "scale-shared", [m1.id, m2.id])
    foreign = await _add_entity(session, "scale-foreign", [elsewhere.id])
    await _add_relation(session, single, shared)
    await _add_relation(session, single, foreign)

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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_graph_scale.py -k overlay`
Expected: FAIL — `AttributeError: … has no attribute 'get_entities_for_memories'`.

- [ ] **Step 3: Implement**

In `backend/app/repositories/graph.py`, directly after `get_full_graph`, add:

```python
    async def get_entities_for_memories(self, memory_ids: list[str], limit: int) -> dict:
        """Entities asserted by any of ``memory_ids``, most-asserted first, and
        the relations between them.

        ``truncated`` is exact: one row past ``limit`` is fetched to tell a full
        page from a cut one.
        """
        if not memory_ids:
            return {"entities": [], "relations": [], "truncated": False}

        entity_rows = (
            await self.session.execute(
                text("""
                    SELECT id, name, entity_type, properties, memory_ids
                    FROM entities
                    WHERE memory_ids && CAST(:ids AS uuid[])
                    ORDER BY cardinality(memory_ids) DESC, id
                    LIMIT :limit
                """),
                {"ids": [UUID(m) for m in memory_ids], "limit": limit + 1},
            )
        ).mappings().all()
        truncated = len(entity_rows) > limit
        entity_rows = entity_rows[:limit]

        entities = [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "properties": r["properties"] or {},
                "memory_ids": [str(m) for m in (r["memory_ids"] or [])],
            }
            for r in entity_rows
        ]
        if not entities:
            return {"entities": [], "relations": [], "truncated": truncated}

        rel_rows = (
            await self.session.execute(
                text("""
                    SELECT r.source_entity_id, r.target_entity_id, r.rel_type, r.weight
                    FROM entity_relations r
                    WHERE r.source_entity_id = ANY(:ids) AND r.target_entity_id = ANY(:ids)
                """),
                {"ids": [r["id"] for r in entity_rows]},
            )
        ).mappings().all()
        relations = [
            {
                "source": str(r["source_entity_id"]),
                "target": str(r["target_entity_id"]),
                "type": r["rel_type"],
                "weight": r["weight"],
            }
            for r in rel_rows
        ]
        return {"entities": entities, "relations": relations, "truncated": truncated}
```

If `backend/app/repositories/graph.py` does not already import `UUID` (`rg -n "^from uuid import" backend/app/repositories/graph.py`), add `from uuid import UUID` to its imports.

In `backend/app/services/graph.py` replace the body of `_fetch_entity_overlay` with:

```python
        if not self.graph_repo:
            return [], [], False

        try:
            result = await self.graph_repo.get_entities_for_memories(
                [m["id"] for m in memory_nodes], limit=GRAPH_MAX_ENTITIES,
            )
            return result["entities"], result["relations"], result["truncated"]
        except Exception:
            logger.exception("Failed to fetch entity data")
            return [], [], False
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/test_graph_repo.py tests/test_api/test_graph.py tests/test_pushdown_keyword_graph.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/graph.py backend/app/services/graph.py backend/tests/test_graph_scale.py
git commit -m "fix(graph): scope the entity overlay to plotted nodes"
```

### Task 8: Graph scale bench

**Files:**
- Create: `backend/scripts/benchlib/run_graph_scale.py`

**Interfaces:**
- Consumes: C5.
- Produces: nothing.

**Items:** 3, 5

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 0 = 1

- [ ] **Step 1: Write the bench**

Create `backend/scripts/benchlib/run_graph_scale.py`:

```python
"""Time the unified graph at scale on darkmem_bench.

Run from backend/:
  .venv/bin/python scripts/benchlib/run_graph_scale.py [--nodes 20000] [--dims 1024] [--clusters 60]

Resets darkmem_bench, seeds N memories with clustered synthetic vectors under
one fingerprint, then times GraphService.get_unified_graph(all_memories=True)
cold and warm and reports the process's peak RSS. Exits 1 when cold exceeds
10 s, warm exceeds 1 s, or peak RSS exceeds 1,500 MB.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import resource
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
# Standalone execution only puts this file's directory on sys.path; both
# `benchlib` and `app` must resolve before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import bench_db  # noqa: E402  (overrides DATABASE_URL first)

import numpy as np  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.repositories.vector import PostgresVectorRepository  # noqa: E402
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry  # noqa: E402
from app.services.graph import GraphService, reset_graph_caches  # noqa: E402

COLD_BUDGET_S = 10.0
WARM_BUDGET_S = 1.0
PEAK_RSS_BUDGET_MB = 1500
BATCH = 1000


def _peak_rss_mb() -> float:
    # ru_maxrss is kilobytes on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class _BenchLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        self.calls = 0

    def llm_fingerprint(self) -> str:
        return self.fingerprint

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        return "bench cluster"


def _vectors(nodes: int, dims: int, clusters: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    centers = rng.normal(size=(clusters, dims)).astype(np.float32)
    x = centers[rng.integers(0, clusters, nodes)] + rng.normal(scale=1.2, size=(nodes, dims)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


async def _seed(nodes: int, dims: int, clusters: int, fingerprint: str) -> None:
    vectors = _vectors(nodes, dims, clusters)
    async with bench_db.session_factory() as session:
        await embedder_registry.register(
            session, EmbedderInfo(fingerprint=fingerprint, model_id="bench-graph-scale", dims=dims, source="llm"),
        )
        await session.commit()
        child = child_table("memory_embeddings", fingerprint)
        for start in range(0, nodes, BATCH):
            ids = [uuid.uuid4() for _ in range(min(BATCH, nodes - start))]
            await session.execute(
                text(
                    "INSERT INTO memories (id, content, source, importance, metadata, project, "
                    "status, memory_type, is_archived) "
                    "VALUES (:id, :content, 'bench', 0.5, '{}'::jsonb, 'bench', 'active', 'fact', FALSE)"
                ),
                [{"id": mid, "content": f"bench memory {start + i}"} for i, mid in enumerate(ids)],
            )
            await session.execute(
                text(
                    f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
                ),
                [
                    {
                        "mid": mid,
                        "fp": fingerprint,
                        "vec": "[" + ",".join(f"{v:.5f}" for v in vectors[start + i]) + "]",
                        "payload": json.dumps({"content": f"bench memory {start + i}", "source": "bench", "tags": [f"topic-{(start + i) % clusters}"]}),
                    }
                    for i, mid in enumerate(ids)
                ],
            )
            await session.commit()


async def _time_graph(fingerprint: str) -> tuple[float, float, dict, int]:
    llm = _BenchLLM(fingerprint)
    reset_graph_caches()
    async with bench_db.session_factory() as session:
        svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=llm)
        t0 = time.perf_counter()
        cold = await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t1 = time.perf_counter()
        await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t2 = time.perf_counter()
    return t1 - t0, t2 - t1, cold, llm.calls


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=20_000)
    parser.add_argument("--dims", type=int, default=1024)
    parser.add_argument("--clusters", type=int, default=60)
    args = parser.parse_args()
    fingerprint = f"bench-graph-scale|{args.dims}"

    await bench_db.reset_bench_db()
    t_seed = time.perf_counter()
    await _seed(args.nodes, args.dims, args.clusters, fingerprint)
    print(f"seeded {args.nodes} memories in {time.perf_counter() - t_seed:.1f}s")

    rss_before = _peak_rss_mb()
    cold_s, warm_s, result, llm_calls = await _time_graph(fingerprint)
    rss_after = _peak_rss_mb()
    print(
        f"nodes={len(result['memories'])} total={result['total_memories']} "
        f"edges={len(result['similarity_edges'])} clusters={len(result['clusters'])} "
        f"llm_calls={llm_calls} cold={cold_s:.2f}s warm={warm_s:.3f}s "
        f"peak_rss={rss_after:.0f}MB (after seeding {rss_before:.0f}MB)"
    )
    await bench_db.engine.dispose()
    ok = (
        cold_s <= COLD_BUDGET_S
        and warm_s <= WARM_BUDGET_S
        and rss_after <= PEAK_RSS_BUDGET_MB
        and len(result["memories"]) == args.nodes
    )
    print(
        "PASS" if ok else
        f"FAIL (budgets: cold <= {COLD_BUDGET_S}s, warm <= {WARM_BUDGET_S}s, "
        f"peak RSS <= {PEAK_RSS_BUDGET_MB}MB)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Check the memories column names before running**

Run: `timeout 60 docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_bench -c "\d memories" | head -40`
Expected: columns `content`, `source`, `importance`, `metadata`, `project`, `status`, `memory_type`, `is_archived` exist, and every other NOT NULL column has a default. If a NOT NULL column without a default is missing from the INSERT, add it to both the column list and the VALUES with a fixed value, then continue. (If `darkmem_bench` does not exist yet, create it: `timeout 60 docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_bench;"`.)

- [ ] **Step 3: Run the bench at 2,000 nodes as a smoke test**

Run: `cd backend && timeout 600 .venv/bin/python scripts/benchlib/run_graph_scale.py --nodes 2000`
Expected: prints `nodes=2000 total=2000 …` and `PASS`, with `llm_calls` ≤ 40.

- [ ] **Step 4: Run the bench at 20,000 nodes**

Run: `cd backend && timeout 1200 .venv/bin/python scripts/benchlib/run_graph_scale.py --nodes 20000`
Expected: `PASS` (cold ≤ 10 s, warm ≤ 1 s, peak RSS ≤ 1,500 MB). Record the printed line verbatim in the task report. A FAIL is reported with its numbers, not tuned away: the budgets are the spec's.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/benchlib/run_graph_scale.py
git commit -m "test(graph): add a 20,000-node unified graph bench"
```

### Task 9: Frontend hook: node limit and all

**Files:**
- Modify: `frontend/src/hooks/api/use-graph-api.ts:45-57` (types) and `:82-113` (`useUnifiedGraph`)
- Modify: `frontend/src/hooks/api/__tests__/use-graph-api-project-scope.test.tsx:46-53`
- Test: `frontend/src/hooks/api/__tests__/use-graph-api-node-limit.test.tsx` (create)

**Interfaces:**
- Consumes: C6.
- Produces: C8.

**Items:** 1, 4

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/use-graph-api-node-limit.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useUnifiedGraph } from "../use-graph-api"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { projectScopedKey } from "@/lib/query-keys"

const EMPTY = { memories: [], clusters: {}, cluster_names: {}, similarity_edges: [] }

function setup() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { queryClient, wrapper }
}

describe("useUnifiedGraph: node budget", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({ activeProject: DEFAULT_PROJECT })
    vi.mocked(apiFetch).mockResolvedValue(EMPTY)
  })

  it("sends the node limit when All is off", async () => {
    const { wrapper } = setup()
    renderHook(() => useUnifiedGraph(0.75, 3, false, 500, false), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("limit=500")
    expect(url).not.toContain("all=true")
  })

  it("sends all=true and no limit when All is on", async () => {
    const { wrapper } = setup()
    renderHook(() => useUnifiedGraph(0.75, 3, false, 500, true), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("all=true")
    expect(url).not.toContain("limit=")
  })

  it("keys the cache on the budget", async () => {
    const { queryClient, wrapper } = setup()
    const { result } = renderHook(() => useUnifiedGraph(0.75, 3, false, 500, true), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual(EMPTY))
    expect(queryClient.getQueryData(projectScopedKey("unifiedGraph", 0.75, 3, false, "all"))).toEqual(EMPTY)
    expect(queryClient.getQueryData(projectScopedKey("unifiedGraph", 0.75, 3, false, 500))).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/hooks/api/__tests__/use-graph-api-node-limit.test.tsx`
Expected: FAIL — URL lacks `limit=500` / `all=true`.

- [ ] **Step 3: Implement**

In `frontend/src/hooks/api/use-graph-api.ts`, add to `UnifiedGraphData` after `similarity_edges: SimilarityEdge[]`:

```ts
  /** In-scope memories the server could plot; `memories.length` of these
   *  were sent, newest first. */
  total_memories?: number
  /** True when fewer memories were sent than `total_memories`. */
  memories_truncated?: boolean
```

and replace the `useUnifiedGraph` function (signature through its closing brace) with:

```ts
export function useUnifiedGraph(
  similarityThreshold = 0.75,
  minClusterSize = 3,
  includeEntities = false,
  nodeLimit = 200,
  allNodes = false,
) {
  const queryKey = useProjectScopedKey(
    "unifiedGraph",
    similarityThreshold,
    minClusterSize,
    includeEntities,
    allNodes ? "all" : nodeLimit,
  )
  const project = useProjectStore((s) => s.activeProject)
  return useQuery<UnifiedGraphData>({
    queryKey,
    // `includeEntities` is part of the key, so toggling the entity layer asks
    // for a different cache entry and `isLoading` would flip true -- swapping
    // the whole page for a skeleton to add an overlay to a graph already on
    // screen. Holding the previous data keeps the graph up while the new
    // shape arrives.
    placeholderData: keepPreviousData,
    queryFn: () =>
      apiFetch(
        `/graph/unified?similarity_threshold=${similarityThreshold}&min_cluster_size=${minClusterSize}&include_entities=${includeEntities}` +
          (allNodes ? "&all=true" : `&limit=${nodeLimit}`) +
          // Omitted, never sent empty: `project=` would ask for a project
          // *named* the empty string, while an absent param is what the route
          // reads as every project.
          (project === ALL_PROJECTS
            ? ""
            : `&project=${encodeURIComponent(project)}`),
      ),
  })
}
```

In the same interface, replace the doc comment above `entities_truncated?: boolean` (it describes the old unscoped 500-row fetch) with:

```ts
  /** True when the plotted memories assert more entities than the overlay's
   *  20,000-entity ceiling carries; the most-asserted are kept (F10). Present
   *  only when `include_entities` was requested. */
```

In `frontend/src/hooks/api/__tests__/use-graph-api-project-scope.test.tsx`, replace both `projectScopedKey("unifiedGraph", 0.75, 3, false)` calls with `projectScopedKey("unifiedGraph", 0.75, 3, false, 200)`. Then run `rg -n 'projectScopedKey\("unifiedGraph"' frontend/src` and give any other four-part key the same fifth element `200`.

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && timeout 300 npx vitest run src/hooks/api/__tests__/ && timeout 600 npm run typecheck`
Expected: PASS, typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-graph-api.ts frontend/src/hooks/api/__tests__/
git commit -m "feat(graph): send the node budget from the hook"
```

### Task 10: Node count control

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-prefs.ts`
- Create: `frontend/src/features/graph/components/node-count-row.tsx`
- Modify: `frontend/src/features/graph/components/graph-toolbar.tsx` (props interface, destructuring, first `Section`)
- Test: `frontend/src/features/graph/components/__tests__/node-count-row.test.tsx` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: C9, C10.

**Items:** 1, 4

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/graph/components/__tests__/node-count-row.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NodeCountRow } from "../node-count-row"
import { useGraphPrefs, NODE_LIMIT_MAX, NODE_LIMIT_MIN } from "@/features/graph/lib/graph-prefs"

function renderRow(overrides: Partial<Parameters<typeof NodeCountRow>[0]> = {}) {
  const props = {
    nodeLimit: 200,
    onNodeLimitChange: vi.fn(),
    allNodes: false,
    onAllNodesChange: vi.fn(),
    shown: 200,
    total: 4580,
    truncated: true,
    ...overrides,
  }
  render(<NodeCountRow {...props} />)
  return props
}

describe("NodeCountRow", () => {
  it("steps the node limit", async () => {
    const user = userEvent.setup()
    const props = renderRow()
    await user.click(screen.getByRole("button", { name: "Increment" }))
    expect(props.onNodeLimitChange).toHaveBeenLastCalledWith(300)
  })

  it("toggles All and disables the number while it is on", async () => {
    const user = userEvent.setup()
    const props = renderRow()
    await user.click(screen.getByRole("checkbox", { name: "All nodes" }))
    expect(props.onAllNodesChange).toHaveBeenCalledWith(true)

    renderRow({ allNodes: true })
    expect(screen.getAllByRole("button", { name: "Increment" })[1]).toBeDisabled()
  })

  it("reports what is shown against the total", () => {
    renderRow()
    expect(screen.getByTestId("node-count-summary")).toHaveTextContent("Showing 200 of 4,580")
  })

  it("names the ceiling when All was capped", () => {
    renderRow({ allNodes: true, shown: 50000, total: 60000, truncated: true })
    expect(screen.getByTestId("node-count-summary")).toHaveTextContent("capped at 50,000")
  })

  it("hides the summary without a total", () => {
    renderRow({ total: undefined })
    expect(screen.queryByTestId("node-count-summary")).not.toBeInTheDocument()
  })
})

describe("graph prefs: node budget", () => {
  beforeEach(() => useGraphPrefs.setState({ nodeLimit: 200, allNodes: false }))

  it("clamps and rounds the node limit", () => {
    useGraphPrefs.getState().setNodeLimit(12.6)
    expect(useGraphPrefs.getState().nodeLimit).toBe(NODE_LIMIT_MIN)
    useGraphPrefs.getState().setNodeLimit(10_000_000)
    expect(useGraphPrefs.getState().nodeLimit).toBe(NODE_LIMIT_MAX)
    useGraphPrefs.getState().setNodeLimit(1234.4)
    expect(useGraphPrefs.getState().nodeLimit).toBe(1234)
    useGraphPrefs.getState().setNodeLimit(Number.NaN)
    expect(useGraphPrefs.getState().nodeLimit).toBe(1234)
  })

  it("stores All", () => {
    useGraphPrefs.getState().setAllNodes(true)
    expect(useGraphPrefs.getState().allNodes).toBe(true)
  })

  it("persists the budget under the graph prefs key", () => {
    useGraphPrefs.getState().setNodeLimit(750)
    useGraphPrefs.getState().setAllNodes(true)
    const stored = JSON.parse(localStorage.getItem("darkmem-graph-prefs") ?? "{}")
    expect(stored.state).toMatchObject({ nodeLimit: 750, allNodes: true })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/components/__tests__/node-count-row.test.tsx`
Expected: FAIL — cannot resolve `../node-count-row`.

- [ ] **Step 3: Implement**

In `frontend/src/features/graph/lib/graph-prefs.ts`, after `export const DIM_STEP = 5` add:

```ts
/** How many memories the graph asks for. The ceiling is the server's. */
export const NODE_LIMIT_DEFAULT = 200
export const NODE_LIMIT_MIN = 50
export const NODE_LIMIT_MAX = 50_000
export const NODE_LIMIT_STEP = 100
```

add to `GraphPrefsState` (after `detailPanelWidth: number`):

```ts
  /** Memories to plot, newest first, while `allNodes` is off. */
  nodeLimit: number
  /** Plot every in-scope memory, up to the server's ceiling. */
  allNodes: boolean
```

and (after `setDetailPanelWidth: (px: number) => void`):

```ts
  setNodeLimit: (n: number) => void
  setAllNodes: (all: boolean) => void
```

In the store body, after `detailPanelWidth: DEFAULT_DETAIL_PANEL_WIDTH,` add:

```ts
      nodeLimit: NODE_LIMIT_DEFAULT,
      allNodes: false,
```

and after the `setDetailPanelWidth` implementation add:

```ts
      setNodeLimit: (n) => {
        if (!Number.isFinite(n)) return
        set({
          nodeLimit: Math.min(NODE_LIMIT_MAX, Math.max(NODE_LIMIT_MIN, Math.round(n))),
        })
      },

      setAllNodes: (allNodes) => set({ allNodes }),
```

Create `frontend/src/features/graph/components/node-count-row.tsx`:

```tsx
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import {
  NumberInput,
  NumberInputControl,
  NumberInputDecrementTrigger,
  NumberInputField,
  NumberInputIncrementTrigger,
  NumberInputLabel,
  NumberInputTriggerGroup,
} from "darkraise-ui/components/number-input"
import { useId } from "react"
import {
  NODE_LIMIT_MAX,
  NODE_LIMIT_MIN,
  NODE_LIMIT_STEP,
} from "@/features/graph/lib/graph-prefs"

interface NodeCountRowProps {
  nodeLimit: number
  onNodeLimitChange: (n: number) => void
  allNodes: boolean
  onAllNodesChange: (all: boolean) => void
  /** Memories in the current response. */
  shown: number
  /** In-scope memories the server could plot; absent until a response lands. */
  total?: number
  truncated?: boolean
}

export function NodeCountRow({
  nodeLimit,
  onNodeLimitChange,
  allNodes,
  onAllNodesChange,
  shown,
  total,
  truncated = false,
}: NodeCountRowProps) {
  const allId = useId()
  return (
    <div className="space-y-1">
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Label className="w-16 shrink-0 text-right font-normal">Nodes</Label>
        <NumberInput
          className="w-28"
          value={nodeLimit}
          min={NODE_LIMIT_MIN}
          max={NODE_LIMIT_MAX}
          step={NODE_LIMIT_STEP}
          disabled={allNodes}
          onValueChange={(d) => {
            if (Number.isNaN(d.valueAsNumber)) return
            onNodeLimitChange(d.valueAsNumber)
          }}
        >
          <NumberInputLabel className="sr-only">Node limit</NumberInputLabel>
          <NumberInputControl>
            <NumberInputField />
            <NumberInputTriggerGroup>
              <NumberInputDecrementTrigger />
              <NumberInputIncrementTrigger />
            </NumberInputTriggerGroup>
          </NumberInputControl>
        </NumberInput>
        <Checkbox
          id={allId}
          size="sm"
          checked={allNodes}
          onCheckedChange={(checked) => onAllNodesChange(checked === true)}
          aria-label="All nodes"
        />
        <label htmlFor={allId} className="cursor-pointer">
          All
        </label>
      </div>
      {total !== undefined && (
        <p
          className="text-muted-foreground pl-[4.5rem] text-xs"
          data-testid="node-count-summary"
        >
          Showing {shown.toLocaleString("en-US")} of {total.toLocaleString("en-US")}
          {allNodes && truncated
            ? ` (capped at ${NODE_LIMIT_MAX.toLocaleString("en-US")})`
            : ""}
        </p>
      )}
    </div>
  )
}
```

In `frontend/src/features/graph/components/graph-toolbar.tsx`:
- add to `GraphToolbarProps` after `onReset: () => void`:

```ts
  /** The node budget control, shown first because it decides what every
   *  other setting acts on. */
  nodes?: React.ReactNode
```

- add `nodes,` to the destructured parameters after `onReset,`;
- directly after the `PopoverContent` comment block (before `<Section title="Render">`) insert:

```tsx
          {nodes && <Section title="Nodes">{nodes}</Section>}
```

- change `<Section title="Render">` to `<Section title="Render" divided={!!nodes}>`.

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/ && timeout 600 npm run typecheck`
Expected: PASS, typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-prefs.ts frontend/src/features/graph/components/node-count-row.tsx frontend/src/features/graph/components/graph-toolbar.tsx frontend/src/features/graph/components/__tests__/node-count-row.test.tsx
git commit -m "feat(graph): add a node count control with All"
```

### Task 11: Graph page wiring

**Files:**
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (imports; state at ~61-75; `GraphToolbar` props at ~318-352)
- Test: `frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx`

**Interfaces:**
- Consumes: C8, C9, C10.
- Produces: nothing.

**Items:** 1, 4

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx` change the hook mock line

```tsx
  useUnifiedGraph: () => mockUseUnifiedGraph(),
```

to

```tsx
  useUnifiedGraph: (...args: unknown[]) => mockUseUnifiedGraph(...args),
```

and append:

```tsx
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"

describe("RealMemoryGraphPage: node budget", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    useGraphPrefs.setState({ nodeLimit: 200, allNodes: false })
  })

  it("asks for the stored node limit", () => {
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    useGraphPrefs.setState({ nodeLimit: 750, allNodes: false })
    render(<RealMemoryGraphPage />, { wrapper })
    const calls = mockUseUnifiedGraph.mock.calls
    expect(calls[calls.length - 1]!.slice(3)).toEqual([750, false])
  })

  it("asks for every memory when All is stored", () => {
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    useGraphPrefs.setState({ allNodes: true })
    render(<RealMemoryGraphPage />, { wrapper })
    const calls = mockUseUnifiedGraph.mock.calls
    expect(calls[calls.length - 1]!.slice(3)).toEqual([200, true])
  })

  it("shows how many memories are plotted in the settings panel", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({
      data: { ...ONE_MEMORY, total_memories: 4580, memories_truncated: true },
      isLoading: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    await user.click(screen.getByRole("button", { name: /toggle graph settings/i }))
    expect(await screen.findByTestId("node-count-summary")).toHaveTextContent("Showing 1 of 4,580")
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx`
Expected: FAIL — the hook is called with three arguments; no `node-count-summary`.

- [ ] **Step 3: Implement**

In `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx`:

1. Add imports:

```tsx
import { NodeCountRow } from "@/features/graph/components/node-count-row"
```

(`useGraphPrefs` and `useDebouncedValue` are already imported.)

2. Directly before `const { data, isLoading, isFetching, isError } = useUnifiedGraph(` add:

```tsx
  const nodeLimit = useGraphPrefs((s) => s.nodeLimit)
  const allNodes = useGraphPrefs((s) => s.allNodes)
  const setNodeLimit = useGraphPrefs((s) => s.setNodeLimit)
  const setAllNodes = useGraphPrefs((s) => s.setAllNodes)
  const debouncedNodeLimit = useDebouncedValue(nodeLimit, 500)
```

3. Change the hook call to:

```tsx
  const { data, isLoading, isFetching, isError } = useUnifiedGraph(
    debouncedSimilarity,
    debouncedMinSize,
    entityLayerEnabled,
    debouncedNodeLimit,
    allNodes,
  )
```

4. Leave `handleReset` as it is: Reset restores the view's layout and encodings, while the node budget decides which data is loaded, and a view reset that silently dropped a 20,000-node graph back to 200 would refetch. On the `<GraphToolbar` element add the prop (after `onReset={handleReset}`):

```tsx
              nodes={
                <NodeCountRow
                  nodeLimit={nodeLimit}
                  onNodeLimitChange={setNodeLimit}
                  allNodes={allNodes}
                  onAllNodesChange={setAllNodes}
                  shown={memoryCount}
                  total={data?.total_memories}
                  truncated={data?.memories_truncated}
                />
              }
```

- [ ] **Step 4: Run the page tests and the typecheck**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/ src/features/graph/ && timeout 600 npm run typecheck`
Expected: PASS, typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/memory-graph/components/real-memory-graph-page.tsx frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx
git commit -m "feat(graph): wire the node budget into the page"
```

### Task 12: Scale tiers and cluster seeding

**Files:**
- Create: `frontend/src/features/graph/lib/graph-scale.ts`
- Test: `frontend/src/features/graph/lib/__tests__/graph-scale.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: C11.

**Items:** 5

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/graph/lib/__tests__/graph-scale.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import {
  CURVED_EDGE_LIMIT,
  clusterAnchors,
  scaleSettings,
  scaleTier,
  seedAroundAnchor,
} from "../graph-scale"

describe("scaleTier", () => {
  it("uses the code graph's boundaries", () => {
    expect(scaleTier(499)).toBe("small")
    expect(scaleTier(500)).toBe("medium")
    expect(scaleTier(1999)).toBe("medium")
    expect(scaleTier(2000)).toBe("large")
    expect(scaleTier(9999)).toBe("large")
    expect(scaleTier(10000)).toBe("huge")
  })
})

describe("scaleSettings", () => {
  it("keeps today's small-graph behaviour", () => {
    const s = scaleSettings(200, 500)
    expect(s.curvedEdges).toBe(true)
    expect(s.hideOnMove).toBe(false)
    expect(s.slowDown).toBe(12)
    expect(s.layoutMs).toBe(8000)
    expect(s.arrows3D).toBe(true)
    expect(s.hulls3D).toBe(true)
  })

  it("straightens edges past the curve limit", () => {
    expect(scaleSettings(200, CURVED_EDGE_LIMIT).curvedEdges).toBe(true)
    expect(scaleSettings(200, CURVED_EDGE_LIMIT + 1).curvedEdges).toBe(false)
  })

  it("trades detail for speed on huge graphs", () => {
    const s = scaleSettings(20000, 100000)
    expect(s.hideOnMove).toBe(true)
    expect(s.barnesHutOptimize).toBe(true)
    expect(s.layoutMs).toBe(20000)
    expect(s.sphereSegments).toEqual([8, 6])
    expect(s.arrows3D).toBe(false)
    expect(s.hulls3D).toBe(false)
    expect(s.slowDown).toBeLessThan(scaleSettings(200, 0).slowDown)
  })
})

describe("clusterAnchors", () => {
  it("places the largest cluster at the centre and skips unclustered nodes", () => {
    const memories = [
      ...Array.from({ length: 9 }, () => ({ cluster: 3 })),
      ...Array.from({ length: 4 }, () => ({ cluster: 1 })),
      { cluster: -1 },
    ]
    const anchors = clusterAnchors(memories)
    expect([...anchors.keys()]).toEqual([3, 1])
    expect(anchors.get(3)).toMatchObject({ x: 0, y: 0 })
    expect(anchors.get(3)!.spread).toBeGreaterThan(anchors.get(1)!.spread)
    expect(anchors.has(-1)).toBe(false)
  })

  it("is deterministic", () => {
    const memories = [{ cluster: 0 }, { cluster: 1 }, { cluster: 1 }]
    expect([...clusterAnchors(memories)]).toEqual([...clusterAnchors(memories)])
  })
})

describe("seedAroundAnchor", () => {
  it("stays within the anchor's spread", () => {
    const anchor = { x: 5, y: -3, spread: 2 }
    for (const [u, v] of [[0, 0], [0.25, 1], [0.9, 0.5]] as const) {
      const p = seedAroundAnchor(anchor, u, v)
      expect(Math.hypot(p.x - 5, p.y + 3)).toBeLessThanOrEqual(2 + 1e-9)
    }
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/graph-scale.test.ts`
Expected: FAIL — cannot resolve `../graph-scale`.

- [ ] **Step 3: Implement**

Create `frontend/src/features/graph/lib/graph-scale.ts`:

```ts
/**
 * How the memory graph's renderers trade detail for speed as it grows.
 *
 * Tier boundaries match the code graph's so both canvases change behaviour at
 * the same sizes.
 */

export type ScaleTier = "small" | "medium" | "large" | "huge"

export interface ScaleSettings {
  /** Curved edges cost several times a straight one per frame. */
  curvedEdges: boolean
  hideOnMove: boolean
  slowDown: number
  barnesHutOptimize: boolean
  /** How long ForceAtlas2 runs before it is stopped. */
  layoutMs: number
  sphereSegments: [number, number]
  arrows3D: boolean
  hulls3D: boolean
  warmupTicks3D: number
  cooldownTicks3D: number
}

export const CURVED_EDGE_LIMIT = 2000
export const LARGE_3D_NOTICE_NODES = 5000

const TIERS: Record<ScaleTier, Omit<ScaleSettings, "curvedEdges">> = {
  small: {
    hideOnMove: false,
    slowDown: 12,
    barnesHutOptimize: false,
    layoutMs: 8000,
    sphereSegments: [16, 12],
    arrows3D: true,
    hulls3D: true,
    warmupTicks3D: 80,
    cooldownTicks3D: 150,
  },
  medium: {
    hideOnMove: false,
    slowDown: 8,
    barnesHutOptimize: true,
    layoutMs: 10000,
    sphereSegments: [16, 12],
    arrows3D: true,
    hulls3D: true,
    warmupTicks3D: 80,
    cooldownTicks3D: 150,
  },
  large: {
    hideOnMove: true,
    slowDown: 5,
    barnesHutOptimize: true,
    layoutMs: 15000,
    sphereSegments: [8, 6],
    arrows3D: false,
    hulls3D: false,
    warmupTicks3D: 30,
    cooldownTicks3D: 100,
  },
  huge: {
    hideOnMove: true,
    slowDown: 3,
    barnesHutOptimize: true,
    layoutMs: 20000,
    sphereSegments: [8, 6],
    arrows3D: false,
    hulls3D: false,
    warmupTicks3D: 10,
    cooldownTicks3D: 60,
  },
}

export function scaleTier(nodeCount: number): ScaleTier {
  if (nodeCount < 500) return "small"
  if (nodeCount < 2000) return "medium"
  if (nodeCount < 10000) return "large"
  return "huge"
}

export function scaleSettings(nodeCount: number, edgeCount: number): ScaleSettings {
  return {
    ...TIERS[scaleTier(nodeCount)],
    curvedEdges: edgeCount <= CURVED_EDGE_LIMIT,
  }
}

export interface ClusterAnchor {
  x: number
  y: number
  spread: number
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const ANCHOR_SPACING = 10
const SPREAD_PER_ROOT_MEMBER = 0.8

/**
 * One anchor per cluster on a golden-angle spiral, largest cluster at the
 * centre. Seeding a node beside its cluster's anchor starts the layout close
 * to where it will settle, so a large graph converges in seconds rather than
 * untangling uniform noise.
 */
export function clusterAnchors(
  memories: { cluster: number }[],
): Map<number, ClusterAnchor> {
  const sizes = new Map<number, number>()
  for (const m of memories) {
    if (m.cluster >= 0) sizes.set(m.cluster, (sizes.get(m.cluster) ?? 0) + 1)
  }
  const ordered = [...sizes.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])
  const anchors = new Map<number, ClusterAnchor>()
  ordered.forEach(([cluster, size], i) => {
    const r = ANCHOR_SPACING * Math.sqrt(i)
    const theta = i * GOLDEN_ANGLE
    anchors.set(cluster, {
      x: r * Math.cos(theta),
      y: r * Math.sin(theta),
      spread: Math.sqrt(size) * SPREAD_PER_ROOT_MEMBER,
    })
  })
  return anchors
}

/** A point in the anchor's disc; `u` and `v` are uniform draws in [0, 1). */
export function seedAroundAnchor(
  anchor: ClusterAnchor,
  u: number,
  v: number,
): { x: number; y: number } {
  const angle = u * 2 * Math.PI
  const radius = anchor.spread * Math.sqrt(v)
  return {
    x: anchor.x + radius * Math.cos(angle),
    y: anchor.y + radius * Math.sin(angle),
  }
}
```

- [ ] **Step 4: Run the test and the typecheck**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/graph-scale.test.ts && timeout 600 npm run typecheck`
Expected: PASS, typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-scale.ts frontend/src/features/graph/lib/__tests__/graph-scale.test.ts
git commit -m "feat(graph): add scale tiers and cluster seeding"
```

### Task 13: 2D renderer scale settings

**Files:**
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (imports at 1-50; `place` at ~271; memory `addNode` at ~287; Sigma settings at ~410-429; FA2 at ~717-741)

**Interfaces:**
- Consumes: C11.
- Produces: nothing.

**Items:** 5

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Record the pre-change baseline**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/ src/features/graph/ && timeout 600 npm run typecheck`
Expected: PASS. (The renderer draws through WebGL, which jsdom lacks, so it has no unit test; behaviour is measured in Task 17. The pure logic it uses is tested in Task 12.)

- [ ] **Step 2: Imports**

Replace `import { NodeCircleProgram } from "sigma/rendering"` with:

```ts
import { EdgeRectangleProgram, NodeCircleProgram } from "sigma/rendering"
```

and add:

```ts
import {
  clusterAnchors,
  scaleSettings,
  seedAroundAnchor,
} from "@/features/graph/lib/graph-scale"
```

- [ ] **Step 3: Seed memories beside their cluster's anchor**

Replace the line

```ts
    const place = (id: string) => settled.get(id) ?? placeSeeded(id)
```

with

```ts
    // A never-seen memory starts beside its cluster's anchor, so the layout
    // begins near a clustered arrangement instead of untangling noise.
    const anchors = clusterAnchors(filteredMemories)
    const place = (id: string, cluster: number) => {
      const known = settled.get(id)
      if (known) return known
      const anchor = anchors.get(cluster)
      return anchor
        ? seedAroundAnchor(anchor, seededUnit(id, 0), seededUnit(id, 1))
        : placeSeeded(id)
    }
```

and in the memory loop change `...place(m.id),` to `...place(m.id, m.cluster),`. Run `rg -n "place\(" frontend/src/features/graph/components/graph-2d-renderer.tsx`: the only `place(` call left must be that one (`placeSeeded(` and `placeEntity(` are different functions).

- [ ] **Step 4: Settings from the tier**

Directly before `const sigma = new Sigma(graph, containerRef.current, {` add:

```ts
    const scale = scaleSettings(graph.order, graph.size)
```

In the Sigma settings object:
- after `renderEdgeLabels: false,` add

```ts
      hideEdgesOnMove: scale.hideOnMove,
      hideLabelsOnMove: scale.hideOnMove,
```

- replace `defaultEdgeType: "curve",` with `defaultEdgeType: scale.curvedEdges ? "curve" : "line",`
- replace `edgeProgramClasses: { curve: EdgeCurveProgram },` with

```ts
      // Sigma replaces its default program map with this one, so the
      // straight program must be registered here to be usable at all.
      edgeProgramClasses: { curve: EdgeCurveProgram, line: EdgeRectangleProgram },
```

In the `new FA2Layout(graph, { settings: { … } })` object, replace `slowDown: 12,` with

```ts
        slowDown: scale.slowDown,
        barnesHutOptimize: scale.barnesHutOptimize,
```

and in the stop timer replace `}, 8000)` with `}, scale.layoutMs)`.

- [ ] **Step 5: Verify and commit**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/ src/features/graph/ && timeout 600 npm run typecheck && timeout 600 npm run build`
Expected: PASS, typecheck clean, build succeeds.

```bash
git add frontend/src/features/graph/components/graph-2d-renderer.tsx
git commit -m "perf(graph): tune the 2D renderer by graph size"
```

### Task 14: 2D hull caching

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-geometry.ts` (replace `drawHullForSigma` at 172-230 with `framedHullVertices` and `drawFramedHull`)
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (imports; `drawHulls` at ~623-706; FA2 stop timer)
- Test: `frontend/src/features/graph/lib/__tests__/framed-hull.test.ts` (create)

**Interfaces:**
- Consumes: C11 (`scale.layoutMs` from Task 13 in the stop timer).
- Produces: C12.

**Items:** 5

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/graph/lib/__tests__/framed-hull.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest"
import type Sigma from "sigma"
import { drawFramedHull, framedHullVertices } from "../graph-geometry"

const POSITIONS: Record<string, { x: number; y: number }> = {
  a: { x: 0, y: 0 },
  b: { x: 1, y: 0 },
  c: { x: 1, y: 1 },
  d: { x: 0, y: 1 },
  inner: { x: 0.5, y: 0.5 },
}

function fakeSigma() {
  const framedGraphToViewport = vi.fn((p: { x: number; y: number }) => ({
    x: p.x * 100 + 10,
    y: -p.y * 100 + 200,
  }))
  const sigma = {
    getNodeDisplayData: (id: string) => POSITIONS[id],
    framedGraphToViewport,
  } as unknown as Sigma
  return { sigma, framedGraphToViewport }
}

function fakeContext(): CanvasRenderingContext2D {
  return new Proxy({} as Record<string, unknown>, {
    get: (target, key) => {
      if (!(key in target)) target[key as string] = vi.fn()
      return target[key as string]
    },
    set: (target, key, value) => {
      target[key as string] = value
      return true
    },
  }) as unknown as CanvasRenderingContext2D
}

describe("framedHullVertices", () => {
  it("keeps only the hull's corners, in framed space", () => {
    const { sigma } = fakeSigma()
    const hull = framedHullVertices(sigma, ["a", "b", "c", "d", "inner", "missing"])
    expect(hull).toHaveLength(4)
    expect(hull).not.toContainEqual(POSITIONS.inner)
  })

  it("passes one or two members through", () => {
    const { sigma } = fakeSigma()
    expect(framedHullVertices(sigma, ["a", "b"])).toEqual([POSITIONS.a, POSITIONS.b])
  })
})

describe("drawFramedHull", () => {
  it("maps only the stored vertices to the viewport", () => {
    const { sigma, framedGraphToViewport } = fakeSigma()
    const framed = framedHullVertices(sigma, ["a", "b", "c", "d", "inner"])
    const drawn = drawFramedHull(fakeContext(), sigma, framed, "#336699", 0.06, 0.28)
    expect(framedGraphToViewport).toHaveBeenCalledTimes(4)
    expect(drawn).toHaveLength(4)
  })

  it("draws nothing for fewer than two vertices", () => {
    const { sigma } = fakeSigma()
    const ctx = fakeContext()
    expect(drawFramedHull(ctx, sigma, [POSITIONS.a!], "#336699", 0.06, 0.28)).toHaveLength(1)
    expect(ctx.fill).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/framed-hull.test.ts`
Expected: FAIL — `framedHullVertices` is not exported.

- [ ] **Step 3: Replace `drawHullForSigma` in the geometry module**

In `frontend/src/features/graph/lib/graph-geometry.ts` replace the whole `drawHullForSigma` function with:

```ts
/**
 * A group's convex hull in sigma's framed-graph space.
 *
 * The camera maps framed-graph space to the viewport by an affine transform,
 * which carries a hull's vertices onto the hull of the mapped points. So the
 * hull is recomputed only when the layout moves, and each frame maps just its
 * few vertices.
 */
export function framedHullVertices(sigma: Sigma, memberIds: string[]): Point[] {
  const points: Point[] = []
  for (const id of memberIds) {
    const data = sigma.getNodeDisplayData(id)
    if (data) points.push({ x: data.x, y: data.y })
  }
  return points.length < 3 ? points : convexHull(points)
}

export function drawFramedHull(
  ctx: CanvasRenderingContext2D,
  sigma: Sigma,
  framed: Point[],
  color: string,
  fillAlpha: number,
  strokeAlpha: number,
): Point[] {
  const positions = framed.map((p) => sigma.framedGraphToViewport(p))
  if (positions.length < 2) return positions

  if (positions.length === 2) {
    const [a, b] = positions as [Point, Point]
    const cx = (a.x + b.x) / 2
    const cy = (a.y + b.y) / 2
    const dx = b.x - a.x
    const dy = b.y - a.y
    const dist = Math.sqrt(dx * dx + dy * dy) / 2 + 30
    ctx.save()
    ctx.beginPath()
    ctx.ellipse(cx, cy, dist, dist * 0.6, Math.atan2(dy, dx), 0, Math.PI * 2)
    ctx.fillStyle = hexToRgba(color, fillAlpha)
    ctx.fill()
    ctx.strokeStyle = hexToRgba(color, strokeAlpha)
    ctx.lineWidth = 1.5
    ctx.stroke()
    ctx.restore()
    return positions
  }

  const hull = expandHull(positions, 25)
  ctx.save()
  drawSmoothClosed(ctx, hull)
  ctx.fillStyle = hexToRgba(color, fillAlpha)
  ctx.fill()
  ctx.strokeStyle = hexToRgba(color, strokeAlpha)
  ctx.lineWidth = 1
  ctx.setLineDash([5, 4])
  ctx.stroke()
  ctx.restore()
  return hull
}
```

(`Point` is declared at line 145 of the same file; `framedHullVertices` receives framed points and returns hull vertices, so `drawFramedHull` no longer calls `convexHull`.)

- [ ] **Step 4: Use cached hulls in the renderer**

In `frontend/src/features/graph/components/graph-2d-renderer.tsx`:

1. In the `@/features/graph/lib/graph-geometry` import, replace `drawHullForSigma,` with `drawFramedHull,` and `framedHullVertices,`, and add `type Point,` to that import.

2. Below `const LABEL_ZOOM_RATIO = 0.72` add:

```ts
/** While the layout runs, hull shapes refresh at most this often; camera
 *  moves never recompute them. */
const HULL_REFRESH_MS = 250
```

3. Directly before `function drawHulls() {` add:

```ts
    // Hull groups change only with the data or the mode, and hull shapes only
    // while the layout moves. Recomputing both on every frame is what made a
    // large graph stutter on pan.
    let hullGroupsFor: { memories: UnifiedMemory[]; mode: HullMode } | null = null
    let hullGroups = new Map<string, string[]>()
    const framedHulls = new Map<string, Point[]>()
    let framedHullsAt = -Infinity
    let framedHullsStale = true
```

4. Inside `drawHulls`, replace

```ts
      const hullGroups = computeHullGroups(
        filteredMemoriesRef.current,
        hullModeRef.current,
      )
```

with

```ts
      const memories = filteredMemoriesRef.current
      const mode = hullModeRef.current
      if (
        !hullGroupsFor ||
        hullGroupsFor.memories !== memories ||
        hullGroupsFor.mode !== mode
      ) {
        hullGroups = computeHullGroups(memories, mode)
        hullGroupsFor = { memories, mode }
        framedHullsStale = true
      }
      const now = performance.now()
      const layoutRunning = fa2Ref.current?.isRunning() ?? false
      if (
        framedHullsStale ||
        (layoutRunning && now - framedHullsAt >= HULL_REFRESH_MS)
      ) {
        framedHulls.clear()
        for (const [groupKey, members] of hullGroups) {
          framedHulls.set(groupKey, framedHullVertices(sigmaRef.current, members))
        }
        framedHullsAt = now
        framedHullsStale = false
      }
```

5. In the same loop replace

```ts
        const hull = drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.06,
          0.28,
        )
```

with

```ts
        const hull = drawFramedHull(
          hullCtx,
          sigmaRef.current,
          framedHulls.get(groupKey) ?? [],
          color,
          0.06,
          0.28,
        )
```

(the chip below keeps `members.length` as its count).

6. Replace the FA2 stop timer body so the final positions refresh the hulls:

```ts
    fa2StopTimerRef.current = setTimeout(() => {
      fa2StopTimerRef.current = null
      if (fa2Ref.current) fa2Ref.current.stop()
      framedHullsStale = true
      sigmaRef.current?.refresh()
    }, scale.layoutMs)
```

7. If `HullMode` or `UnifiedMemory` is not already imported as a type in this file, add it to the existing type imports (`HullMode` from `@/features/graph/lib/graph-geometry`, `UnifiedMemory` from `@/hooks/api` — both are imported today at lines 40 and 57-61).

Run `rg -n "drawHullForSigma" frontend/src` — it must print nothing.

- [ ] **Step 5: Verify and commit**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/ src/features/memory-graph/ && timeout 600 npm run typecheck && timeout 600 npm run build`
Expected: PASS, typecheck clean, build succeeds.

```bash
git add frontend/src/features/graph/lib/graph-geometry.ts frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/graph/lib/__tests__/framed-hull.test.ts
git commit -m "perf(graph): cache hull shapes between frames"
```

### Task 15: 3D best-effort and large-graph notice

**Files:**
- Modify: `frontend/src/features/graph/components/graph-3d-renderer.tsx` (imports; refs after `hullMeshesRef`; `buildHulls` guard; unmount cleanup; `nodeThreeObject`; `linkDirectionalArrowLength`; `warmupTicks`/`cooldownTicks`)
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (notice)
- Test: `frontend/src/features/memory-graph/components/__tests__/large-3d-notice.test.tsx` (create)

**Interfaces:**
- Consumes: C11.
- Produces: nothing.

**Items:** 5

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/memory-graph/components/__tests__/large-3d-notice.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { UnifiedGraphData } from "@/hooks/api"
import { LARGE_3D_NOTICE_NODES } from "@/features/graph/lib/graph-scale"

vi.mock("@/features/chat/components/chat-overlay", () => ({
  ChatOverlay: () => null,
}))
vi.mock("@/features/graph/components/graph-2d-renderer", () => ({
  Graph2DRenderer: () => null,
}))
vi.mock("@/features/graph/components/graph-3d-renderer", () => ({
  Graph3DRenderer: () => null,
}))
vi.mock("@/features/graph/components/mini-graph", () => ({
  MiniGraph: () => null,
}))

const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: () => mockUseUnifiedGraph(),
}))

import { RealMemoryGraphPage } from "../real-memory-graph-page"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function graphOf(count: number): UnifiedGraphData {
  return {
    memories: Array.from({ length: count }, (_, i) => ({
      id: `m${i}`,
      content: `memory ${i}`,
      source: "api",
      tags: [],
      memory_type: null,
      importance: 0.5,
      cluster: 0,
    })),
    clusters: {},
    cluster_names: {},
    similarity_edges: [],
  }
}

async function switchTo3D(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /toggle graph settings/i }))
  const mode = await screen.findByRole("radiogroup", { name: "Render mode" })
  await user.click(within(mode).getByRole("radio", { name: "3D" }))
}

describe("RealMemoryGraphPage: large 3D notice", () => {
  beforeEach(() => mockUseUnifiedGraph.mockReset())

  it("recommends 2D for a large graph in 3D and can be dismissed", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({ data: graphOf(LARGE_3D_NOTICE_NODES), isLoading: false })
    render(<RealMemoryGraphPage />, { wrapper })
    await switchTo3D(user)

    expect(await screen.findByText(/3D is best-effort here/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Dismiss" }))
    expect(screen.queryByText(/3D is best-effort here/)).not.toBeInTheDocument()
  })

  it("stays quiet for a small graph", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({ data: graphOf(10), isLoading: false })
    render(<RealMemoryGraphPage />, { wrapper })
    await switchTo3D(user)
    expect(screen.queryByText(/3D is best-effort here/)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/components/__tests__/large-3d-notice.test.tsx`
Expected: FAIL — no text matching `3D is best-effort here`.

- [ ] **Step 3: Implement the notice**

In `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx`:
- add `import { LARGE_3D_NOTICE_NODES } from "@/features/graph/lib/graph-scale"`;
- after `const [viewMode, setViewMode] = useState<ViewMode>("2d")` add `const [large3DNoticeDismissed, setLarge3DNoticeDismissed] = useState(false)`;
- directly after the `{isRefetching && ( … )}` block inside the canvas container add:

```tsx
            {viewMode === "3d" &&
              !large3DNoticeDismissed &&
              graphData3D.nodes.length >= LARGE_3D_NOTICE_NODES && (
                <div
                  role="status"
                  className="bg-warning/12 border-warning/55 text-warning-text absolute bottom-3 left-1/2 z-30 flex -translate-x-1/2 items-center gap-2 rounded-md border px-2.5 py-1 text-sm shadow-lg backdrop-blur-sm"
                >
                  Large graph: 3D is best-effort here. Switch to 2D for smooth
                  navigation.
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setLarge3DNoticeDismissed(true)}
                  >
                    Dismiss
                  </Button>
                </div>
              )}
```

- [ ] **Step 4: Implement the 3D renderer changes**

In `frontend/src/features/graph/components/graph-3d-renderer.tsx`:

1. Add `import { scaleSettings } from "@/features/graph/lib/graph-scale"`.

2. After `const hullMeshesRef = useRef<THREE.Mesh[]>([])` add:

```tsx
  const scale = useMemo(
    () => scaleSettings(graphData.nodes.length, graphData.links.length),
    [graphData],
  )
  const scaleRef = useRef(scale)
  scaleRef.current = scale

  // Shared per shape: thousands of nodes would otherwise each upload their
  // own copy of the same sphere. Materials stay per node, because the
  // selection effect dims and highlights one node by mutating its material.
  const geometriesRef = useRef(new Map<string, THREE.BufferGeometry>())
  const geometryFor = (
    kind: Node3D["nodeKind"],
    radius: number,
  ): THREE.BufferGeometry => {
    const [w, h] = scaleRef.current.sphereSegments
    const r = Math.round(radius * 10) / 10
    const key = `${kind}:${r}:${w}x${h}`
    let geometry = geometriesRef.current.get(key)
    if (!geometry) {
      geometry =
        kind === "entity"
          ? new THREE.OctahedronGeometry(r * 0.6)
          : new THREE.SphereGeometry(r, w, h)
      geometriesRef.current.set(key, geometry)
    }
    return geometry
  }
```

3. In `buildHulls`, directly after `if (hullMode === "none") return` add `if (!scaleRef.current.hulls3D) return`.

4. In the unmount cleanup effect (the `useEffect(() => { return () => { document.body.style.cursor = "default" …` block), before its closing `}` of the returned function, add:

```tsx
      for (const geometry of geometriesRef.current.values()) geometry.dispose()
      geometriesRef.current.clear()
```

5. Replace the body of `nodeThreeObject` up to `const color = colorForNode(node, palette)` so it reads:

```tsx
  const nodeThreeObject = useCallback((node: Node3D) => {
    const geometry = geometryFor(node.nodeKind, 1 + node.val * 1.5)
    const color = colorForNode(node, palette)
```

(the material and `return new THREE.Mesh(geometry, material)` lines stay).

6. Replace `linkDirectionalArrowLength={(link) =>` … `}` with:

```tsx
      linkDirectionalArrowLength={(link) =>
        scale.arrows3D && link.linkKind === "relation" ? 4 : 0
      }
```

7. Replace `warmupTicks={80}` with `warmupTicks={scale.warmupTicks3D}` and `cooldownTicks={150}` with `cooldownTicks={scale.cooldownTicks3D}`.

- [ ] **Step 5: Verify and commit**

Run: `cd frontend && timeout 300 npx vitest run src/features/memory-graph/ src/features/graph/ && timeout 600 npm run typecheck && timeout 600 npm run build`
Expected: PASS, typecheck clean, build succeeds.

```bash
git add frontend/src/features/graph/components/graph-3d-renderer.tsx frontend/src/features/memory-graph/components/real-memory-graph-page.tsx frontend/src/features/memory-graph/components/__tests__/large-3d-notice.test.tsx
git commit -m "perf(graph): lighten 3D for large graphs"
```

### Task 16: Synthetic graph and 20k story

**Files:**
- Create: `frontend/src/features/graph/lib/synthetic-graph.ts`
- Create: `frontend/src/features/graph/components/graph-2d-renderer.stories.tsx`
- Test: `frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts`

**Interfaces:**
- Consumes: nothing new (renders `Graph2DRenderer` with its existing props).
- Produces: C13.

**Items:** 5

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { syntheticMemoryGraph } from "../synthetic-graph"

describe("syntheticMemoryGraph", () => {
  it("is deterministic for a seed", () => {
    expect(syntheticMemoryGraph(500, 10, 5, 3)).toEqual(syntheticMemoryGraph(500, 10, 5, 3))
  })

  it("builds the requested nodes and in-cluster edges without duplicates", () => {
    const g = syntheticMemoryGraph(2000, 20, 5)
    expect(g.memories).toHaveLength(2000)
    const cluster = new Map(g.memories.map((m) => [m.id, m.cluster]))
    const keys = new Set<string>()
    for (const e of g.edges) {
      expect(e.source).not.toBe(e.target)
      expect(cluster.get(e.source)).toBe(cluster.get(e.target))
      const key = [e.source, e.target].sort().join("|")
      expect(keys.has(key)).toBe(false)
      keys.add(key)
    }
    expect(g.edges.length).toBeGreaterThan(2000 * 4)
    expect(g.edges.length).toBeLessThanOrEqual(2000 * 5)
    expect(Object.keys(g.clusterNames)).toHaveLength(20)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/synthetic-graph.test.ts`
Expected: FAIL — cannot resolve `../synthetic-graph`.

- [ ] **Step 3: Implement the generator and the story**

Create `frontend/src/features/graph/lib/synthetic-graph.ts`:

```ts
import type { SimilarityEdge, UnifiedMemory } from "@/hooks/api"

export interface SyntheticGraph {
  memories: UnifiedMemory[]
  edges: SimilarityEdge[]
  clusterNames: Record<string, string>
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const TYPES = ["fact", "decision", "preference", "problem", "reference"]

/**
 * A deterministic memory graph for measuring the renderers at scale. About
 * 5% of nodes are unclustered; every other node draws its edges from members
 * of its own cluster.
 */
export function syntheticMemoryGraph(
  nodeCount: number,
  clusterCount: number,
  edgesPerNode: number,
  seed = 1,
): SyntheticGraph {
  const rand = mulberry32(seed)
  const members = new Map<number, string[]>()
  const memories: UnifiedMemory[] = []
  for (let i = 0; i < nodeCount; i++) {
    const id = `m${i}`
    const cluster = rand() < 0.05 ? -1 : i % clusterCount
    memories.push({
      id,
      content: `Synthetic memory ${i} about topic ${cluster}`,
      source: "synthetic",
      tags: [`topic-${cluster}`],
      memory_type: TYPES[i % TYPES.length]!,
      importance: rand(),
      cluster,
      status: "active",
    })
    if (cluster >= 0) {
      const list = members.get(cluster) ?? []
      list.push(id)
      members.set(cluster, list)
    }
  }

  const seen = new Set<string>()
  const edges: SimilarityEdge[] = []
  for (const m of memories) {
    const pool = members.get(m.cluster)
    if (!pool || pool.length < 2) continue
    for (let e = 0; e < edgesPerNode; e++) {
      const target = pool[Math.floor(rand() * pool.length)]!
      if (target === m.id) continue
      const key = m.id < target ? `${m.id}|${target}` : `${target}|${m.id}`
      if (seen.has(key)) continue
      seen.add(key)
      edges.push({ source: m.id, target, score: 0.5 + rand() * 0.5 })
    }
  }

  const clusterNames: Record<string, string> = {}
  for (const cluster of members.keys()) clusterNames[String(cluster)] = `Topic ${cluster}`
  return { memories, edges, clusterNames }
}
```

Create `frontend/src/features/graph/components/graph-2d-renderer.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react"
import { useMemo } from "react"
import { Graph2DRenderer } from "./graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"

// Stable identities: the renderer rebuilds its whole graph when a callback
// prop changes, which would restart the layout being measured.
const noop = () => {}
const noopSelect = (_id: string | null) => {}

function ScaleHarness({ nodes }: { nodes: number }) {
  const { tokens, palette } = useMemoryGraphTheme()
  const graph = useMemo(() => syntheticMemoryGraph(nodes, 60, 5), [nodes])
  return (
    <div
      data-testid="scale-harness"
      style={{ position: "relative", width: "100vw", height: "100vh" }}
    >
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={noop}
        sizeMode="connections"
        colorMode="cluster"
        spacing={100}
        clusterTightness={300}
        hullMode="cluster"
        entityLayerEnabled={false}
        entities={[]}
        entityRelations={[]}
        tokens={tokens}
        palette={palette}
        clusterNames={graph.clusterNames}
      />
    </div>
  )
}

const meta: Meta<typeof ScaleHarness> = {
  title: "Graph/Graph2DRenderer",
  component: ScaleHarness,
  parameters: { layout: "fullscreen" },
}
export default meta

type S = StoryObj<typeof ScaleHarness>

export const Scale2k: S = { args: { nodes: 2000 } }
export const Scale20k: S = { args: { nodes: 20000 } }
```

Check the prop values against the renderer: `rg -n "export type SizeMode|export type ColorMode|export type HullMode" frontend/src/features/graph/lib` — `"connections"`, `"cluster"` and `"cluster"` must be members; if a name differs, use the member that means "size by links", "colour by cluster" and "regions by cluster".

- [ ] **Step 4: Verify**

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/synthetic-graph.test.ts && timeout 600 npm run typecheck && out=$(mktemp -d) && timeout 900 npm run build:storybook -- --quiet --output-dir "$out"; rm -rf "$out"`
Expected: PASS, typecheck clean, Storybook builds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/synthetic-graph.ts frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts frontend/src/features/graph/components/graph-2d-renderer.stories.tsx
git commit -m "test(graph): add a 20,000-node 2D renderer story"
```

### Task 17: Scale verification

**Files:**
- Modify: `docs/superpowers/registers/2026-09-29-memory-graph-scale.md` (notes only, through `scripts/register set`)

**Interfaces:**
- Consumes: C13, and Task 8's bench.
- Produces: nothing.

**Items:** 3, 5

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Re-run the backend bench on the finished branch**

Run: `cd backend && timeout 1200 .venv/bin/python scripts/benchlib/run_graph_scale.py --nodes 20000`
Expected: `PASS`. Keep the printed result line.

- [ ] **Step 2: Start Storybook as a tracked background process**

Run (background, capture the PID): `cd frontend && timeout 1800 npx storybook dev -p 6006 --ci --no-open`
Then poll with `timeout 120 bash -c 'until curl -sf http://localhost:6006/index.json >/dev/null; do sleep 2; done'` and read the story ids: `curl -s http://localhost:6006/index.json | python3 -c "import json,sys; print([k for k in json.load(sys.stdin)['entries'] if 'graph2drenderer' in k])"`.

- [ ] **Step 3: Measure each story in the Playwright MCP browser**

For the `Scale2k` id and then the `Scale20k` id:

1. `browser_navigate` to `http://localhost:6006/iframe.html?id=<id>&viewMode=story`.
2. `browser_evaluate`:

```js
() => {
  const gl = document.createElement("canvas").getContext("webgl")
  const ext = gl && gl.getExtension("WEBGL_debug_renderer_info")
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unknown"
}
```

   Record the renderer string. `SwiftShader` or `llvmpipe` means software WebGL: the fps below is a lower bound, not the GPU figure.
3. `browser_wait_for` 25 seconds (the huge tier's layout runs 20 s).
4. `browser_evaluate`:

```js
() => {
  window.__lt = []
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) window.__lt.push(e.duration)
  }).observe({ entryTypes: ["longtask"] })
  window.__frames = []
  let last = performance.now()
  const tick = (t) => {
    window.__frames.push(t - last)
    last = t
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
  return true
}
```

5. `browser_run_code_unsafe`:

```js
async (page) => {
  const box = await page.locator('[data-testid="scale-harness"]').boundingBox()
  const cx = box.x + box.width / 2
  const cy = box.y + box.height / 2
  await page.evaluate(() => { window.__frames = [] })
  for (let i = 0; i < 5; i++) {
    await page.mouse.move(cx, cy)
    await page.mouse.down()
    await page.mouse.move(cx + 300, cy + 150, { steps: 40 })
    await page.mouse.up()
    await page.mouse.wheel(0, -400)
    await page.waitForTimeout(200)
    await page.mouse.wheel(0, 400)
  }
  const frames = await page.evaluate(() => window.__frames.slice(1))
  const sorted = [...frames].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]
  const longTasks = await page.evaluate(() => window.__lt)
  return {
    frames: frames.length,
    medianFps: Math.round(1000 / median),
    p95FrameMs: Math.round(sorted[Math.floor(sorted.length * 0.95)]),
    longTasksOver200ms: longTasks.filter((d) => d > 200).length,
    maxLongTaskMs: Math.round(Math.max(0, ...longTasks)),
  }
}
```

6. `browser_take_screenshot` of the settled 20k graph.

Pass for `Scale20k`: `medianFps >= 30` and `longTasksOver200ms === 0`. A miss under software WebGL is reported as such, with its numbers, and is not a pass or a fail until measured on a GPU; a miss under a hardware renderer is a failure to report, not to tune around here.

- [ ] **Step 4: Stop everything started**

`browser_close`; kill the Storybook tree (`pkill -P <pid>`, then `kill <pid>`, repeating `pkill -P` for grandchildren); confirm with `ss -ltnp | rg 6006` that nothing listens on 6006.

- [ ] **Step 5: Record the results**

```bash
P=/root/.claude-alt/plugins/cache/darkraise/dr-superpowers/1.22.1/scripts
R=docs/superpowers/registers/2026-09-29-memory-graph-scale.md
bash $P/register set $R 3 verify --note "bench 20k: <result line from Step 1>; story 2k: <fps/long tasks>; story 20k: <fps/long tasks> on <renderer string>"
bash $P/register set $R 5 verify --note "<same figures>; owner check on a GPU browser at the live instance owed"
bash $P/register check $R
git add $R
git commit -m "docs(graph): record the 20,000-node measurements"
```

### Task 18: Gate and deploy

**Files:**
- Modify: `docs/superpowers/registers/2026-09-29-memory-graph-scale.md` (notes only, through `scripts/register set`)

**Interfaces:**
- Consumes: every earlier task's committed work, merged to master.
- Produces: nothing.

**Items:** 1, 2, 4

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 2 = 3

This task runs after dr-superpowers:finishing-a-development-branch has merged the branch into master: CLAUDE.md redeploys this host after every change that lands, and production must not run unmerged code.

- [ ] **Step 1: Check the precondition**

Run: `git branch --show-current && git log --oneline master | head -30`
Expected: the current branch is `master` and its log contains the commits of Tasks 1–17. If not, stop and report: the branch has not been merged yet.

- [ ] **Step 2: Run the merge gate**

Run: `timeout 3600 ./scripts/gate.sh`
Expected: exit 0. Exit 2 (`GATE BLOCKED`) names a missing toolchain, not a red gate. Exit 143 is an earlyoom kill: check `free -h`, re-run the named leg alone, and report both results rather than treating the kill as a failure.

- [ ] **Step 3: Build without pushing and check the built commit**

Run: `timeout 3600 env DARKMEM_PUSH=0 ./scripts/build-push.sh && docker image inspect "darkraise/darkmem:$(git rev-parse --short HEAD)" --format '{{.Id}}'`
Expected: the build succeeds and the inspect prints an image id. No id means the build did not produce this commit's image; stop, because compose would redeploy the old one.

- [ ] **Step 4: Deploy and wait for health**

Run: `timeout 600 docker compose up -d && timeout 300 bash -c 'until [ "$(docker inspect -f "{{.State.Health.Status}}" darkmem-prod-darkmem-1)" = healthy ]; do sleep 5; done'`
Expected: both commands exit 0.

- [ ] **Step 5: Confirm the change is in the running image**

Run:

```bash
timeout 30 curl -sf http://127.0.0.1:8000/openapi.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(p['name'] for p in d['paths']['/api/v1/graph/unified']['get']['parameters']))"
timeout 30 docker exec darkmem-prod-darkmem-1 grep -rlq "node-count-summary" /app/web && echo "SPA carries the node control"
```

Expected: the parameter list contains `all` and `limit`, and the second line prints `SPA carries the node control`.

- [ ] **Step 6: Record and commit**

```bash
P=/root/.claude-alt/plugins/cache/darkraise/dr-superpowers/1.22.1/scripts
R=docs/superpowers/registers/2026-09-29-memory-graph-scale.md
SHA=$(git rev-parse --short HEAD)
for row in 1 2 4; do
  bash $P/register set $R $row verify --note "deployed $(date -u +%F) as image $SHA; owner review of the live graph owed"
done
bash $P/register check $R
git add $R
git commit -m "docs(graph): record the node budget deploy"
```
