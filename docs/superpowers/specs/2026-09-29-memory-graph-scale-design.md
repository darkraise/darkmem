# Memory graph at scale — design

**Date:** 2026-09-29
**Register:** `docs/superpowers/registers/2026-09-29-memory-graph-scale.md`
**Status:** approved in chat 2026-09-29

## Problem

The memory graph (`/graph` in the SPA, `GET /api/v1/graph/unified`) always
shows 200 memories. The hook sends no `limit`, the route defaults to 200 and
caps at 1,000, and the bulk read (`PostgresVectorRepository.get_all_vectors`)
has `LIMIT` without `ORDER BY`, so the 200 are an arbitrary slice. The
corpus on 192.168.0.199 holds 4,580 memories and 9,334 entities; the owner
wants every node reachable and the graph smooth at 20,000+ nodes.

Measured costs at N nodes today:

| Stage | Where | Cost at 20,000 |
|---|---|---|
| Similarity edges | `GraphService._compute_similarity_edges` | dense N×N float32 matrix (1.6 GB) plus a Python double loop over 2×10⁸ pairs; result cut to 1,000 edges |
| Clustering graph | `_build_sparse_edges` / `_louvain_igraph` | every pair ≥ threshold becomes an igraph edge; at the UI default 0.5 that can be millions; above 10,000 points a sample-plus-centroid path runs instead |
| Vector decode | `_parse_vector` on `embedding::text` | 1.6 s of Python float parsing |
| Cluster names | `_generate_cluster_names` | one `summarization` LLM call per cluster, every request |
| Entity overlay | `_fetch_entity_overlay` | `get_full_graph(limit=500)`: 500 arbitrary entities, then filtered |
| 2D canvas | `graph-2d-renderer.tsx` | curved edges; hull groups and convex hulls recomputed on every `afterRender`; FA2 from hash-random positions, stopped after a fixed 8 s |
| 3D canvas | `graph-3d-renderer.tsx` | one `SphereGeometry(16,12)` and one `MeshPhongMaterial` per node; d3 force on the main thread |

Host measurement (12 cores, numpy + igraph in `backend/.venv`), synthetic
1024-d clustered vectors: exact top-15 neighbours by chunked matmul 0.40 s
at 4,600 and 5.14 s at 20,000; Louvain on that graph 0.01 s and 0.05 s.

## Scope

In: the unified graph's memory arm, its entity overlay, the graph page's
toolbar, the 2D renderer, best-effort 3D. Out: `GET /graph/full`,
`/graph/entities`, the code graph, the projection view's own UI, server-side
layout, cluster super-nodes. The 3D view is **best-effort** by owner ruling
(2026-09-29): it gets the cheap fixes and a notice, not a smoothness target.

## API — `GET /api/v1/graph/unified` (REST single-door, unchanged row on `docs/two-door-parity.md`)

- `limit`: int, default 200, `ge=1`, `le=GRAPH_MAX_NODES` (50,000).
- `all`: bool, default false (declared as `all_memories` with
  `alias="all"`). When true, `limit` is ignored and the read takes every
  in-scope memory up to `GRAPH_MAX_NODES`.
- Selection is **newest first**: `ORDER BY m.created_at DESC, e.memory_id
  DESC` in `get_all_vectors`. This also makes the projection route
  (`api/routes/vectors.py`) deterministic; nothing there relies on the old
  arbitrary order.
- The response gains `total_memories` (count of in-scope memories under the
  same `MemoryFilter`, i.e. project plus `GRAPH_MEMORY_STATUSES`, that have a
  vector in the active partition; a memory still awaiting its embedding
  cannot be plotted, so counting it would report a truncation no budget
  closes) and
  `memories_truncated` (`len(memories) < total_memories`). Existing keys keep
  their names and shapes.

## Backend

### Vector read

`get_all_vectors` selects `e.embedding::real[]` so asyncpg decodes floats
natively, and keeps its `vector` list per point for the projection route. The
graph path uses a sibling, `get_vector_matrix`, which streams the same rows in
batches of 1,000 and packs each batch into one `np.float32` matrix, so a
20,000 × 1024 read peaks near its 80 MB matrix rather than the ~0.65 GB the
per-row lists would hold. `importance` rides the same row, replacing a lookup
that passed one bind parameter per memory (past asyncpg's 32,767 limit at
the ceiling).

### One neighbour pass for clustering and edges

A new pure function in `app/utils/graph_knn.py` (no DB, no I/O):

`knn_graph(vectors, k, threshold, chunk_size) -> (src, dst, sim, rank)`

normalises the rows, then for each chunk of rows computes `chunk @ X.T`,
masks the diagonal, keeps each row's top `k` columns by `argpartition`, and
drops pairs below `threshold`. `rank` is the pair's position (0-based) in
the better-ranking endpoint's neighbour list. Output is undirected and
deduplicated (stored as `i < j`; on collision keep the lower rank; the
similarity is symmetric). Memory is O(chunk × N), never N×N; by default the
chunk is sized so its scratch (a float32 block plus argpartition's int64
index, 12 bytes per cell) stays near 128 MB.

- **Clustering** runs `community_multilevel` on the graph built from
  `k = CLUSTER_K` (15) with similarity weights, then applies
  `min_cluster_size` exactly as today (smaller communities become `-1`,
  valid ones renumbered from 0 in sorted community order). This replaces
  `_build_sparse_edges`, `_louvain_igraph`'s all-pairs graph and the
  `_COMMUNITY_SAMPLE_CAP` sample-plus-centroid branch. Cluster membership
  differs from today's (kNN graph vs. threshold graph); that is accepted.
- **Similarity edges** are the subset of those pairs with `rank < EDGE_K`
  (5), i.e. in either endpoint's top 5, threshold unchanged. The count is
  bounded by `N × EDGE_K`; the fixed 1,000-edge cap goes. Edge shape stays
  `{source, target, score}` with `score` rounded to 3 places.
- `get_louvain_clustered_vectors` keeps its name and return shape (points
  with `cluster`) and additionally returns the edge list, so the service
  computes similarities once. `GraphService._compute_similarity_edges` is
  deleted.

### Result cache

`GraphService` keeps a module-level LRU (4 entries) of the assembled memory
arm (`memories`, `clusters`, `cluster_names`, `similarity_edges`,
`total_memories`, `memories_truncated`), keyed on `(fingerprint, project,
similarity_threshold, min_cluster_size, effective_limit, corpus_stamp)`.
`corpus_stamp` is one query: `count(*)` and `max(updated_at)` over
`memories` under the same filter. Every capture and re-extraction moves
`updated_at` through the `touch_updated_at` trigger, so a stale hit needs a
write that changes neither; a delete moves the count. Module-level state is
valid because invariant 13 pins one process. The entity overlay is not
cached (it is a bounded indexed query).

### Cluster names

- Only the `CLUSTER_NAME_LLM_CAP` (40) largest clusters get an LLM name.
- A name is cached in a module-level dict keyed on a hash of the naming
  sample (the cluster's first 8 members in response order, whose content is
  what the prompt sees). If the sample is unchanged, no call is made.
- Other clusters are named after their most frequent tag, excluding
  `project/*` tags, falling back to `Cluster <id>`. No LLM call.
- Failure behaviour is unchanged: a failed call names the cluster
  `Cluster <id>` and is not cached.

### Entity overlay

`PostgresGraphRepository` gains `get_entities_for_memories(memory_ids,
limit)`: entities whose `memory_ids && CAST(:ids AS uuid[])` (served by
`ix_entities_memory_ids`, GIN), ordered by `cardinality(memory_ids) DESC,
id`, limited to `GRAPH_MAX_ENTITIES` (20,000), plus relations whose both
endpoints are in that set. `entities_truncated` is true when the limit was
hit. `_fetch_entity_overlay` uses it instead of `get_full_graph(limit=500)`;
`get_full_graph` itself is untouched.

## Frontend

### Toolbar and hook

- `GraphToolbar` gains a **Nodes** row: darkraise-ui `NumberInput` (min 50,
  max 50,000, step 100) and a darkraise-ui `Checkbox` labelled **All**; the
  input is disabled while All is checked. Under the row, a muted line reads
  `Showing {memories.length} of {total_memories}` with `(capped at 50,000)`
  when `memories_truncated` and All is checked.
- `useGraphPrefs` persists `nodeLimit` (default 200) and `allNodes`
  (default false) under the existing `darkmem-graph-prefs` key.
- `useUnifiedGraph(similarity, minSize, includeEntities, nodeLimit, all)`
  puts both in the query key and sends `limit=<n>` or `all=true`. The page
  debounces `nodeLimit` with the existing 500 ms `useDebouncedValue`.
- `UnifiedGraphData` gains `total_memories` and `memories_truncated`.

### 2D renderer (smoothness target)

Thresholds are one exported table in `features/graph/lib/graph-scale.ts`,
reusing the tiers `code-graph-renderer.tsx`'s `getFA2Settings` already uses
(small < 500 ≤ medium < 2,000 ≤ large < 10,000 ≤ huge):

- **Edges**: straight (sigma's default line program) when the edge count is
  above 2,000; curved below, as today.
- **Camera moves**: `hideEdgesOnMove` and `hideLabelsOnMove` on from large.
- **Hulls**: `computeHullGroups` runs once per `filteredMemories`/`hullMode`
  change, not per frame. Hull polygons are computed in graph coordinates
  and refreshed at most every 250 ms while FA2 runs, once when it stops;
  `afterRender` only maps the stored hull vertices to the viewport and
  draws.
- **Seeding**: a node with no settled position starts at its cluster's
  anchor (clusters placed on a golden-angle spiral, radius growing with
  cluster size) plus deterministic jitter; unclustered nodes keep today's
  hash seed. Settled positions still win.
- **FA2**: `slowDown` and `barnesHutOptimize` from the tier table (the
  spacing and tightness sliders keep driving `scalingRatio` and `gravity`),
  and the stop timer scales from 8 s (small) to 20 s (huge).

### 3D renderer (best-effort)

- Geometries shared per `(kind, radius, segments)`; sphere segments drop to
  8×6 from large. Materials stay per node: the selection effect dims and
  highlights one node by mutating its own material, so a shared material
  would dim every node of that colour.
- Directional arrows and hulls off from large.
- From 5,000 nodes, a dismissible notice over the canvas: "Large graph: 3D
  is best-effort here. Switch to 2D for smooth navigation."

## Verification

- **Backend unit** (`tests/unit/test_graph_knn.py`): exact top-k against a
  brute-force reference on small random input; threshold respected;
  undirected dedupe; memory stays O(chunk × N) (chunk boundary cases);
  cluster renumbering and `min_cluster_size`.
- **Backend integration**: newest-first ordering and `all` in
  `get_all_vectors`; `total_memories` / `memories_truncated`; the cache hits
  on an unchanged corpus and misses after a capture; the naming cap (a
  stub LLM counts calls, a second request makes none); the overlay returns
  only entities asserted by plotted memories and flags truncation. Existing
  `test_algorithms.py` Louvain tests move to the new function.
- **Guards leg** from CLAUDE.md on `darkmem_test_2` (a query parameter
  changes on a served route).
- **Backend bench** (`backend/scripts/benchlib/run_graph_scale.py`, on
  `darkmem_bench`): seeds 20,000 synthetic clustered 1024-d memories and
  times `get_unified_graph(all_memories=True)` cold and warm. Pass: cold ≤
  10 s, warm ≤ 1 s, process peak RSS ≤ 1,500 MB.
- **Frontend unit**: toolbar row and disabled state; hook query string
  (`limit` vs `all=true`); prefs persistence; hull-group memoisation;
  cluster-anchor seeding is deterministic.
- **Browser measurement**: a Storybook story renders `Graph2DRenderer` with
  a generated 20,000-node, 100,000-edge dataset. Driven through the
  Playwright MCP browser: after FA2 stops, a scripted pan and zoom samples
  `requestAnimationFrame` intervals and long tasks. Pass: median ≥ 30 fps
  during camera moves, no long task > 200 ms after layout settles.
- **Deploy** per CLAUDE.md (gate, `DARKMEM_PUSH=0` build, `up -d`, healthy,
  confirm `all` on `/openapi.json`). This host's production database holds
  0 memories, so the live check exercises the control and the empty path;
  scale is proven by the bench and the story.

## Constants

| Name | Value | Home |
|---|---|---|
| `GRAPH_MAX_NODES` | 50,000 | `app/services/graph.py` |
| `GRAPH_MAX_ENTITIES` | 20,000 | `app/services/graph.py` |
| `CLUSTER_K` | 15 | `app/utils/graph_knn.py` |
| `EDGE_K` | 5 | `app/utils/graph_knn.py` |
| `CLUSTER_NAME_LLM_CAP` | 40 | `app/services/graph.py` |
| Result cache size | 4 | `app/services/graph.py` |
