# Graph Cluster Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: dforge:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cluster the memory graph with seeded Leiden at resolution 2 (falling back to 1 on sparse views) and name clusters from their members' tags and entities, with no LLM call.

**Architecture:** `graph_knn.cluster_labels` swaps Louvain for deterministic Leiden at 2.0, re-clustering at 1.0 when 2.0 leaves more than 10% of the view unclustered. A new pure module `app/utils/cluster_names.py` scores terms per cluster (c-TF-IDF) and builds names. A new repository query supplies entity names. `GraphService._build_memory_arm` wires them together, and the LLM naming path and its `cluster_naming` prompt are removed. The response shape is unchanged.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, python-igraph 1.0.0, pytest; Postgres with pgvector.

**Spec:** docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md

**Execution:** inline — `claude --model opus --effort high` — the highest task total is 7 (Task 4)

**Parallelism:** sequential — inline execution

**Task check:** none — full suite every 3 tasks

**Integration check:** `./scripts/gate.sh`

**CI:** `.github/workflows/ci.yml .github/workflows/release.yml` — platforms: uutils (ubuntu-latest), darkmem-linux — local: `./scripts/gate.sh` — uncovered: uutils (ubuntu-latest)

**Worktree setup:** none
**Plan review:** 2026-11-20 — dforge:judge-opus — executability 7 / coherence 16 / coverage 14 / assumptions 9 (round 1)

## Global Constraints

- Run Python as `backend/.venv/bin/python` from `backend/`; there is no `python` on PATH.
- Tests use the dev Postgres on `127.0.0.1:5433`. Start only its service: `docker compose -f docker-compose.dev.yml up -d postgres` (never the whole dev stack, whose app collides with production on `:8000`). Never point pytest or a harness at production (`:5432`).
- The unified graph route makes no LLM `chat_completion` call, in any mode.
- `GET /api/v1/graph/unified` keeps its response keys and types.
- Names are at most 40 characters unless the prefix plus the first term already exceed it; terms are dropped whole, never cut.
- Comments: none unless the why is non-obvious. Never reference the task or plan in code.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, no attribution lines. Never push.
- uutils (ubuntu-latest): a lock built on `mkdir` failing when the directory exists does not exclude a second process — create the lock file with `set -C` (noclobber), or use `flock`.
- uutils (ubuntu-latest): `timeout` signals only the command it started, so the command's children keep running — run the command in its own process group (`setsid`) and signal the group.

## Contracts

- **C1 — clustering.** `app.utils.graph_knn.cluster_labels(graph: KnnGraph, n: int, min_cluster_size: int) -> list[int]` keeps its signature and its renumbering and `-1` contract. New module constants beside `CLUSTER_K`: `CLUSTER_RESOLUTION = 2.0`, `FALLBACK_RESOLUTION = 1.0`, `MIN_CLUSTERED_SHARE = 0.9`, `CLUSTER_SEED = 42`. Coverage is the share of all `n` memories labelled >= 0 after the `min_cluster_size` drop; the 1.0 result replaces the 2.0 result only when it labels strictly more memories. `cluster_labels` reads the four constants from the module at call time (never as default arguments), so tests can monkeypatch them.
- **C2 — namer.** `app.utils.cluster_names.name_clusters(members: dict[int, list[str]], tags: dict[str, list[str]], projects: dict[str, str | None], entity_terms: dict[str, set[str]]) -> dict[str, str]`. `members` maps cluster id → member memory ids; `tags`, `projects` and `entity_terms` are keyed by every memory id in the view (clustered or not; a missing key means no tags, no project, no entities). It returns `str(cluster_id) → name` for every key of `members`. Module constants: `PREFIX_SHARE = 0.6`, `MAX_NAME_CHARS = 40`, `MAX_TERMS = 3`, `MAX_TERM_CHARS = 30`, `FOLD_PREFIX_CHARS = 6`, `SEPARATOR = " · "`. Rules 1–9 of the spec's Naming section, verbatim, are its behaviour.
- **C3 — entity terms.** `PostgresGraphRepository.entity_terms_for_memories(memory_ids: list[str]) -> dict[str, set[str]]`: for each id in `memory_ids` that some entity of a type in `ENTITY_TERM_TYPES` asserts, the set of those entities' names, lowercased. Ids asserted by no such entity are absent. `ENTITY_TERM_TYPES = ("project", "tool", "artifact", "service", "protocol", "language")`, a module constant in `app/repositories/graph.py`. An empty `memory_ids` returns `{}` without a query.
- **C4 — memory arm.** `GraphService._build_memory_arm(...)` still returns `(arm, degraded)`. `degraded` is True only when `entity_terms_for_memories` raised. `cluster_names` comes from `name_clusters`, with `entity_terms` from C3 when `graph_repo` is set and `{}` otherwise.

## Assumptions (evidence)

- python-igraph 1.0.0's `community_leiden` takes `objective_function`, `weights`, `resolution`, `n_iterations` and rejects `objective=`. Checked with `inspect.signature` on 2026-11-20.
- `igraph.set_random_number_generator(random.Random(42))` before `community_leiden(..., n_iterations=-1)` yields identical memberships across calls, even after the global `random` state moves (Zachary graph, 2026-11-20).
- The kNN executor is single-threaded: `_KNN_EXECUTOR = ThreadPoolExecutor(max_workers=1, ...)` in `backend/app/repositories/vector.py`, so setting igraph's global generator before each call is race-free.
- Leiden costs about the same as Louvain at the 50,000-node ceiling: 0.31 s against 0.28 s on a synthetic kNN-shaped graph (2026-11-20).
- `entities.memory_ids` has GIN index `ix_entities_memory_ids` (production `pg_indexes`, 2026-11-20).
- Production stores no `system_prompts` config row, so removing `cluster_naming` orphans no override (2026-11-20).
- The frontend truncates labels at `ISLAND_LABEL_MAX_CHARS = 40` (`frontend/src/features/graph/lib/island-labels.ts`), matching `MAX_NAME_CHARS`.
- The dev Postgres container is stopped (`docker ps`, 2026-11-20). Task 1 starts it, and the lane databases `darkmem_test_2..5` may be missing (memory note, 2026-11-18).
- Task check rule 4: no gate file, no recorded backend suite timing in `.dforge/suites.tsv`, and `pytest-testmon` is not installed. Each task still runs its own tests.
- A ring of 30 five-node cliques joined by single edges is merged by Louvain at resolution 1 (16 communities, 14 adjacent pairs merged) and kept as 30 whole cliques by seeded Leiden at 2.0 (checked with igraph 1.0.0, 2026-11-20). Two cliques can never serve: if resolution 1 merges them, 2.0 scores singletons higher (plan review round 1).
- Resolution 2.0 dissolves a five-memory near-duplicate view into singletons, and 1.0 keeps it whole (modularity arithmetic: Q = -0.4 for singletons against -1 for one community at 2.0, and 0 for one community at 1.0; the pre-execution ruling `.dforge/rulings-preexec-3-report.md`). `test_graph_scale.py`'s `_seed_five` fixture is such a view, so its tests rely on the fallback.
- Deviation from the spec's Tests section, recorded: `tests/test_graph_cluster_naming.py` and `test_session_resource_lifetimes.py::test_read_only_graph_cluster_names_are_local` are deleted (Task 5) rather than rewritten, because their computed-naming replacements live in `tests/test_graph_scale.py` (Task 4), beside the seed helpers they need.
- The measurement export used by A4 is at `.dforge/ui-ux/graph-cluster-quality/measurements/export/` (`mem.tsv`, `ent.tsv`; gitignored, 2026-11-20).

## Task index

1. Seeded Leiden clustering
2. Computed cluster namer
3. Entity terms query
4. Graph service uses the computed namer
5. Remove the LLM cluster naming path
6. Remove the cluster naming prompt
7. Gate, deploy and live proof

---

### Task 1: Seeded Leiden clustering

**Files:**
- Modify: `backend/app/utils/graph_knn.py` (`cluster_labels`, constants beside `CLUSTER_K`)
- Test: `backend/tests/unit/test_graph_knn.py`

**Interfaces:**
- Consumes: none
- Produces: C1

**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

- `backend/tests/unit/test_graph_knn.py::test_cluster_labels_are_deterministic` (unit): given 60 vectors in three noisy blobs (seeded `np.random.default_rng`) and their `knn_graph(k=9, threshold=0.0)`, calling `cluster_labels(graph, 60, 3)` twice with `random.seed(1); random.random()` and then `random.seed(999)` run between the calls asserts the two label lists are equal and `random.getstate()` after each call equals the state taken just before it; fails today because igraph's default generator is Python's global `random` module, so the unseeded `community_multilevel` call consumes global state (and its labels may differ between the calls).
- `backend/tests/unit/test_graph_knn.py::test_cluster_labels_split_a_ring_of_cliques` (unit, A2): given a hand-built `KnnGraph` of a ring of 30 five-node cliques (intra-clique edges and one edge from each clique to the next, all weight 0.9; `n=150`), asserts every clique carries one label, no two adjacent cliques share a label, and 30 distinct labels come back. Fails today because Louvain at resolution 1 merges adjacent cliques (resolution limit: measured 2026-11-20, 16 communities with 14 adjacent pairs merged; Leiden at 2.0 gives 30 whole cliques).
- `backend/tests/unit/test_graph_knn.py::test_near_duplicate_view_falls_back_to_one_cluster` (unit, A22): given five vectors `[1.0, 0.01 * i, 0, 0]` for `i` in 0..4 and `knn_graph(k=15, threshold=0.5)` (a complete graph), asserts `cluster_labels(graph, 5, 3) == [0, 0, 0, 0, 0]`. Fails today only if Louvain splits it; it must fail against an intermediate build that runs Leiden at 2.0 with no fallback (the step checks this by temporarily setting `MIN_CLUSTERED_SHARE = 0.0` and seeing it fail).
- `backend/tests/unit/test_graph_knn.py::test_fallback_keeps_the_fine_result_unless_coarse_labels_more` (unit, A23), with `FALLBACK_RESOLUTION` monkeypatched to `0.0` (modularity at 0 puts each connected component in one community, so a fallback that ran is visible): (a) the ring-of-cliques fixture of the split test still returns 30 clusters, because 2.0 labels 100% and no fallback runs; (b) a hand-built `KnnGraph` of two triangles joined by one weak edge (weight 0.5, triangle edges 0.9) plus four memories with no edge (`n=10`) returns two clusters of 3 and four -1 labels: 2.0 labels 6 of 10 (under 90%), the 0.0 pass merges the triangles into one community of 6, also 6 labelled, so the 2.0 result stands. The step first checks that 2.0 does split the joined triangles (adjust the bridge weight down if not). Fails today because there is one pass and no `FALLBACK_RESOLUTION` to patch.
- The two existing tests, `test_cluster_labels_separate_blobs_and_drop_small_communities` and `test_cluster_labels_without_edges_are_all_unclustered`, are kept unchanged (A3).

- [ ] **Step 2: Run test to verify it fails**

Start the dev Postgres first: `docker compose -f docker-compose.dev.yml up -d postgres` (from the repository root).
Run: `cd backend && .venv/bin/python -m pytest -q tests/unit/test_graph_knn.py`
Expected: FAIL on `test_cluster_labels_split_a_ring_of_cliques` (and possibly `test_cluster_labels_are_deterministic`).

- [ ] **Step 3: Implement**

1. In `cluster_labels`, replace `g.community_multilevel(weights="weight")` with a helper that runs `g.community_leiden(objective_function="modularity", weights="weight", resolution=<r>, n_iterations=-1)`, each pass immediately preceded by `igraph.set_random_number_generator(random.Random(CLUSTER_SEED))`, and applies the `min_cluster_size` drop and renumbering. Add one comment naming the why: a private `Random` leaves Python's global state alone, and the single-worker kNN executor serialises the global igraph generator.
2. Run it at `CLUSTER_RESOLUTION`. When fewer than `MIN_CLUSTERED_SHARE * n` memories are labelled, run it at `FALLBACK_RESOLUTION` and return that result only when it labels strictly more memories (C1). One comment names the why: modularity at 2.0 scores a small near-duplicate view best as singletons.
3. Add the four constants beside `CLUSTER_K`. Keep the edge-free branch, the renumbering and the `min_cluster_size` drop unchanged.
4. Update the module docstring if it names Louvain (it does not today; leave it otherwise).

- [ ] **Step 4: Run test to verify it passes, and measure A4**

Run: `cd backend && .venv/bin/python -m pytest -q tests/unit/test_graph_knn.py tests/test_graph_scale.py tests/test_pushdown_remaining_channels.py`
Expected: PASS (the graph-scale tests seed near-duplicate views, which now cluster through the fallback).

A4: write a scratch script in the session scratchpad that reads the newest 1,000 rows of `.dforge/ui-ux/graph-cluster-quality/measurements/export/mem.tsv` (rows are newest first; columns `id, project, created_at, tags json, embedding text`), runs the shipped `knn_graph(X, k=CLUSTER_K, threshold=0.5)` and `cluster_labels(..., 3)` and the 1%-churn ARI exactly as `measure2.py`'s `perturb_ari` does (three trials, `np.random.default_rng(7)`). Save its output as `.dforge/ui-ux/graph-cluster-quality/measurements/a4-shipped.out`.
Expected: at least 15 clusters, largest at most 120, churn ARI at least 0.85.

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/graph_knn.py backend/tests/unit/test_graph_knn.py
git commit -m "feat(graph): cluster with seeded Leiden"
```

### Task 2: Computed cluster namer

**Files:**
- Create: `backend/app/utils/cluster_names.py`
- Test: `backend/tests/unit/test_cluster_names.py`

**Interfaces:**
- Consumes: none
- Produces: C2

**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

All tests are unit tests in `backend/tests/unit/test_cluster_names.py` and call `name_clusters` directly on hand-built dictionaries. Each fails today because the module does not exist.

- `::test_default_project_reads_its_project_tag` (A5): cluster 0 of 4 memories, all `project="default"` and all tagging `gpu`, with project tags by member `["project/darkfoto"]`, `["project/darkfoto"]`, `["project/darkfoto", "project/other"]`, `["project/other"]` (first-tag reading: darkfoto 75%, a prefix; a last-tag reading would give 50%, no prefix), and cluster 1 of 3 memories with `project="darkcloud"` and no tags (so the clustered view spans two projects). Asserts `names["0"] == "darkfoto · gpu"` and `names["1"] == "darkcloud"`.
- `::test_prefix_needs_sixty_percent` (A6): cluster 0 has 3 `alpha` and 2 `beta` members (60%), cluster 1 has 2 `alpha` and 2 `beta` (50%), and cluster 2 has 4 `default` members with no project tag. Every member carries its cluster's own tag (`t0`, `t1`, `t2`). Asserts `names == {"0": "alpha · t0", "1": "t1", "2": "t2"}`.
- `::test_single_project_view_has_no_prefix_and_skips_its_project` (A7, A8's last clause): clusters 0 and 1 of 3 members each, all `project="darkmem"`. Cluster 0 members tag `["darkmem", "schema"]`, cluster 1 members `["darkmem", "judge"]`. Asserts `names == {"0": "schema", "1": "judge"}`.
- `::test_excluded_terms_never_appear` (A8): cluster 0 of 5 `alpha` members and cluster 1 of 3 `beta` members. In cluster 0, `decision` (a `MEMORY_TYPES` value) is on all 5, `lonely` on 1, `keep` on 3, and `entity_terms` gives `{"alpha"}` (the prefix's own name) to all 5. Asserts `names["0"] == "alpha · keep"`.
- `::test_large_cluster_in_small_view_keeps_its_term`: a single-project view (`project="darkload"`) of 6 memories, cluster 0 of 4 members all tagging `gdrive` (67% of the view) and 2 unclustered memories with no tags. Asserts `names["0"] == "gdrive"`.
- `::test_spellings_fold_and_near_duplicates_skip` (A9): clusters 0 and 1 of 4 members each; cluster 0 has 2 `alpha` and 2 `beta` members (no prefix), cluster 1 has 4 `gamma` members tagging `other`. Cluster 0 tags, by member: m1 `["claude code", "dispose", "nodegraph"]`, m2 `["claude code", "dispose", "nodegraph"]`, m3 `["claude code", "dispose", "disposal", "node-graph"]`, m4 `["claude-code", "disposal", "node-graph"]`. Asserts `names["0"] == "claude code · node-graph · dispose"`: the `claudecode` and `nodegraph` keys score 1.0 x ln 2 and tie, broken by key; `dispose` scores 0.75 x ln(1 + 4/3); `disposal` shares `dispos` with `dispose`; `node-graph` and `nodegraph` tie at 2 each, so the alphabetical `node-graph` shows. A second case drops every `nodegraph`/`node-graph` tag and asserts `names["0"] == "claude code · dispose"`: `disposal` (0.5 x ln 3) is the third candidate and is skipped because it shares `dispos` with `dispose`.
- `::test_long_terms_drop_whole` (A10): cluster 0 of 5 members with `project="darkraise-ai-plugins"` (20 characters) and cluster 1 of 3 `beta` members tagging `other`. In cluster 0, `dr-superpowers` is on 5 members, `review-routing` on 4 and `planning` on 3 (so they score in that order). Asserts `names["0"] == "darkraise-ai-plugins · dr-superpowers"` (37 characters; adding ` · review-routing` would make 54). A second case renames the project to a 38-character string and tags all 5 with one 10-character term, and asserts the name is that project, ` · `, and the term (51 characters). A third case uses the project `alpha` (5 characters) with `dr-superpowers` on 5 members, `release-orchestrator` (20 characters) on 4 and `api` on 3: `alpha · dr-superpowers` is 22 characters, `release-orchestrator` would make 45, and `api` alone would fit (28), but adding stops at the first term that does not fit, so asserts the name is exactly `alpha · dr-superpowers`.
- `::test_long_terms_are_not_terms` (rule 2): cluster 0 of 3 members with projects `p1`, `p2`, `p3`, all tagging `"a" * 31` and `"b" * 30`. Asserts `names["0"] == "b" * 30`.
- `::test_score_uses_mean_cluster_size` (rule 5): cluster 0 of 4 members (projects `p1`..`p4`), all tagging `widget`, the first two also `gizmo`; cluster 1 of 2 members (`p5`, `p6`) tagging `other`; 20 unclustered memories, 4 of them tagging `widget`. With the mean cluster size 3, `gizmo` scores 0.5 x ln(1 + 3/2) = 0.46 and `widget` 1.0 x ln(1 + 3/8) = 0.32, so asserts `names["0"] == "gizmo · widget"`; a namer using the view size (26) would give `widget · gizmo`.
- `::test_unnamed_cluster_falls_back` (A11): cluster 7 of 3 members with projects `p1`, `p2`, `p3` and one distinct tag each. Asserts `names == {"7": "Cluster 7"}`, and that every key of `members` is in the result with a non-empty value.
- `::test_entity_terms_count_as_terms` (A12, the namer half): cluster 0 of 3 members with projects `p1`, `p2`, `p3`, no tags, and `entity_terms` giving `{"darkfoto"}` to all three. Asserts `names["0"] == "darkfoto"`.
- `::test_names_are_deterministic`: the A9 inputs named twice, with every dictionary's insertion order and each member list reversed the second time, give equal results.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest -q tests/unit/test_cluster_names.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.utils.cluster_names'`.

- [ ] **Step 3: Implement**

1. Create `name_clusters` per C2, following the spec's Naming rules 1–9 in order. Import `MEMORY_TYPES` from `app.taxonomy` for the stoplist.
2. The spelling key keeps only `[a-z0-9]` of the lowercased term. Document frequency counts view memories (every key of `tags`, `projects` and `entity_terms` combined), once per memory per key.
3. Score with the mean size of the clusters in `members`. Eligible: at least 2 members carry the key, and it is not the prefix's key nor, when the clustered memories share one effective project, that project's key. Pick in descending score, ties by key, skipping a key that contains or is contained in a chosen key or shares its first `FOLD_PREFIX_CHARS` characters with one.
4. Display each chosen key as its most frequent original (lowercased) spelling in the cluster, ties alphabetical. Join with `SEPARATOR` and add terms in score order, stopping at the first one that would take the name past `MAX_NAME_CHARS` (later, shorter terms are not tried); always keep the first term after the prefix.
5. The prefix applies only when the view's clustered memories span more than one effective project.
6. No I/O, no logging, no randomness.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest -q tests/unit/test_cluster_names.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/cluster_names.py backend/tests/unit/test_cluster_names.py
git commit -m "feat(graph): compute cluster names from tags"
```

### Task 3: Entity terms query

**Files:**
- Modify: `backend/app/repositories/graph.py` (new method beside `get_entities_for_memories`, `ENTITY_TERM_TYPES` constant)
- Test: `backend/tests/test_graph_repo.py`

**Interfaces:**
- Consumes: none
- Produces: C3

**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_graph_repo.py::test_entity_terms_for_memories_filters_types_and_ids` (integration): given memories `a`, `b`, `c` (rows via `Memory(...)` as the file's other tests do) and entities created with `create_entity`: `("DarkFoto", "project")` asserted by `a` and `b`, `("pgvector", "tool")` by `a`, `("some idea", "concept")` by `a`, and `("git", "tool")` by `c`. Calling `entity_terms_for_memories([str(a), str(b)])` asserts the result is exactly `{str(a): {"darkfoto", "pgvector"}, str(b): {"darkfoto"}}`: `concept` is excluded, names are lowercased, and `c` is absent though `git` exists. `entity_terms_for_memories([])` returns `{}`. Fails today because the method does not exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_graph_repo.py -k entity_terms`
Expected: FAIL with `AttributeError: 'PostgresGraphRepository' object has no attribute 'entity_terms_for_memories'`.

- [ ] **Step 3: Implement**

1. Add `ENTITY_TERM_TYPES` and `entity_terms_for_memories` per C3. One `text()` query: select `m.mid, lower(e.name)` from `entities e, unnest(e.memory_ids) AS m(mid)` where `e.memory_ids && CAST(:ids AS uuid[])`, `e.entity_type = ANY(CAST(:types AS text[]))` and `m.mid = ANY(CAST(:ids AS uuid[]))`. Bind ids as `UUID` objects, as `get_entities_for_memories` does.
2. Return `str(mid) → set of names`; return `{}` before querying when `memory_ids` is empty.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_graph_repo.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/graph.py backend/tests/test_graph_repo.py
git commit -m "feat(graph): query entity terms for memories"
```

### Task 4: Graph service uses the computed namer

**Files:**
- Modify: `backend/app/services/graph.py` (`_build_memory_arm`, the degraded-arm comment in `get_unified_graph`)
- Test: `backend/tests/test_graph_scale.py` (`_add_memory` gains `tags`, new `_NoChatLLM` stub)

**Interfaces:**
- Consumes: C2, C3
- Produces: C4

**Depends on:** Task 1, Task 2, Task 3
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All new tests are integration tests in `backend/tests/test_graph_scale.py`, using its `session` fixture, `_seed_partition` / `_add_memory` helpers and `FINGERPRINT`. `_add_memory` writes `"tags": []` into the embedding payload, which is where the graph service reads node tags from, so first give it a `tags: list[str] | None = None` keyword that it writes into the payload JSON (existing callers unchanged). The shared setup seeds five near-identical memories in project `alpha` (as `_seed_five` does; they form one cluster through Task 1's fallback), each tagged `retrieval` and the first three also tagged `lexical`, and builds the service with a new stub class `_NoChatLLM` whose `llm_fingerprint` returns `FINGERPRINT` and whose `chat_completion` raises `AssertionError("graph route called the LLM")`.

- `::test_arm_names_come_from_the_namer_and_never_call_the_llm` (A14, normal mode): asserts `get_unified_graph(project="alpha", similarity_threshold=0.5)` returns `cluster_names == {"0": "retrieval · lexical"}` (one project, so no prefix; `retrieval` scores 1.0 x ln 2, `lexical` 0.6 x ln(1 + 5/3)). Fails today because the stub's raising `chat_completion` makes the old path answer `"Cluster 0"`.
- `::test_read_only_graph_makes_no_llm_call` (A14, read-only mode): the same with `settings.read_only` monkeypatched to True; asserts `cluster_names == {"0": "retrieval · lexical"}`. Fails today because the old read-only path answers the most frequent tag, `"retrieval"`.
- `::test_entity_terms_feed_the_names` (A12, service half): the same seed with no tags, `graph_repo=PostgresGraphRepository(session)`, and `("darkfoto", "project")` created with `create_entity` for each of the five memories. Asserts `cluster_names == {"0": "darkfoto"}`. Fails today because entity names never reach naming.
- `test_degraded_naming_is_not_cached` becomes `::test_failed_entity_terms_are_not_cached` (A13): with the existing non-raising `_FakeLLM` and a `graph_repo` stub whose `entity_terms_for_memories` raises `RuntimeError`, two identical `get_unified_graph(project="alpha", similarity_threshold=0.5)` calls run `get_louvain_clustered_vectors` twice (the existing counting monkeypatch), and the first response's `cluster_names` is `{"0": "retrieval · lexical"}`. Fails today because the service never calls `entity_terms_for_memories` and `_FakeLLM` names the cluster successfully, so the arm is not degraded, the second call hits the cache (count 1), and the name is `"named cluster"`.
- Extend `::test_similarity_edges_come_from_the_knn_pass` (A16): the response's keys are exactly `{"memories", "clusters", "cluster_names", "similarity_edges", "total_memories", "memories_truncated", "fingerprint_unresolved"}`, and `cluster_names` has a non-empty value for every key of `clusters`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_graph_scale.py`
Expected: FAIL on the four new tests.

- [ ] **Step 3: Implement**

1. In `_build_memory_arm`, after building `memory_nodes`, build `tags` and `projects` keyed by memory id from the nodes. When `self.graph_repo` is set, `await self.graph_repo.entity_terms_for_memories(ids)` over every node id; on any exception, `logger.exception(...)`, use `{}` and report the arm degraded. Without `graph_repo`, use `{}`, not degraded. Name with `name_clusters(clusters, tags, projects, entity_terms)` and stop calling `_generate_cluster_names` (Task 5 deletes it).
2. Update the comment above the degraded-not-cached branch in `get_unified_graph`: a degraded arm now means names built without entity terms.
3. Keep `self.llm` and its `is not None` gate: fingerprint resolution needs it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/test_graph_repo.py tests/unit/test_cluster_names.py tests/unit/test_graph_knn.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph.py backend/tests/test_graph_scale.py
git commit -m "feat(graph): name clusters from tags and entities"
```

### Task 5: Remove the LLM cluster naming path

**Files:**
- Modify: `backend/app/services/graph.py` (remove `_generate_cluster_names`, `_tag_cluster_name`, `CLUSTER_NAME_LLM_CAP`, `_cluster_name_cache`, `_CLUSTER_NAME_CACHE_SIZE`; trim `reset_graph_caches`)
- Delete: `backend/tests/test_graph_cluster_naming.py`
- Modify: `backend/tests/test_session_resource_lifetimes.py` (`test_read_only_graph_cluster_names_are_local`), `backend/tests/test_graph_scale.py` (`_FakeLLM`)

**Interfaces:**
- Consumes: C4
- Produces: none

**Depends on:** Task 4
**Evaluation:** files 2 - spec 1 - coupling 0 - risk 1 = 4

- [ ] **Step 1: No new test, because the removed code is unreachable after Task 4, and `backend/tests/test_graph_scale.py::test_arm_names_come_from_the_namer_and_never_call_the_llm` fails if any naming call to the LLM returns**

- [ ] **Step 2: Remove**

1. Delete `_generate_cluster_names`, `_tag_cluster_name`, `CLUSTER_NAME_LLM_CAP`, `_cluster_name_cache` with its comment, and `_CLUSTER_NAME_CACHE_SIZE` from `backend/app/services/graph.py`. In `reset_graph_caches`, drop the name-cache line and change its docstring to "Test hook: forget every cached memory arm." Remove imports nothing else in the module uses (`asyncio`, `hashlib`, `Counter`, `prompt`; check each with `rg`).
2. Delete `backend/tests/test_graph_cluster_naming.py`: every test in it targets the removed functions, and Task 4's tests cover the computed path.
3. Delete `test_session_resource_lifetimes.py::test_read_only_graph_cluster_names_are_local`: it calls the removed `_generate_cluster_names`, and `test_graph_scale.py::test_read_only_graph_makes_no_llm_call` replaces it.
4. In `test_graph_scale.py`, remove `_FakeLLM`'s `fail` flag if no test still passes it. Keep `_NoChatLLM` and its raising `chat_completion`: Task 4's A14 tests depend on it.
5. Run `rg -n "_generate_cluster_names|CLUSTER_NAME_LLM_CAP|_cluster_name_cache|_tag_cluster_name" backend` and confirm no hit.

- [ ] **Step 3: Verify**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_graph_scale.py tests/test_session_resource_lifetimes.py tests/test_pushdown_remaining_channels.py`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A backend/app/services/graph.py backend/tests/test_graph_cluster_naming.py backend/tests/test_session_resource_lifetimes.py backend/tests/test_graph_scale.py
git commit -m "refactor(graph): drop LLM cluster naming"
```

### Task 6: Remove the cluster naming prompt

**Files:**
- Modify: `backend/app/services/prompt.py` (`PROMPTS["cluster_naming"]`), `backend/app/services/pipeline_aggregator.py` (`ORPHAN_PROMPT_KEYS`), `backend/tests/test_prompt_hardening.py` (`test_cluster_naming_guards_its_sample`), `frontend/src/features/settings/llm-purpose-prompts.ts` (header comment)
- Test: `backend/tests/test_llm_pipeline_config.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Depends on:** Task 5
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_llm_pipeline_config.py::test_cluster_naming_is_not_a_prompt_key` (integration, `client` and `auth_headers` fixtures as the neighbouring system-prompts tests use): asserts `GET /api/v1/config/system-prompts` answers 200 with no `cluster_naming` key in its defaults, and `PUT /api/v1/config/system-prompts` with body `{"overrides": {"cluster_naming": "x"}}` (the shape `test_put_system_prompts_rejects_unknown_purpose` uses) answers 422 (A15). Fails today because the key exists, so GET lists it and PUT answers 200.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_llm_pipeline_config.py -k cluster_naming`
Expected: FAIL.

- [ ] **Step 3: Implement**

1. Delete the `"cluster_naming"` entry from `PROMPTS`.
2. Remove `"cluster_naming"` from `ORPHAN_PROMPT_KEYS`.
3. Delete `test_prompt_hardening.py::test_cluster_naming_guards_its_sample`.
4. In `llm-purpose-prompts.ts`'s header comment, the parenthesis "(`chat`, `cluster_naming`," / "`agent_instructions`)" spans two lines; drop `` `cluster_naming`, `` so it reads "(`chat`, `agent_instructions`)", re-wrapping the comment if needed. Change no code.
5. Run `rg -n cluster_naming backend/app backend/tests frontend/src` and confirm no hit remains.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest -q tests/test_llm_pipeline_config.py tests/test_prompt_hardening.py tests/test_pipeline_aggregator.py && cd ../frontend && npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/prompt.py backend/app/services/pipeline_aggregator.py backend/tests/test_prompt_hardening.py backend/tests/test_llm_pipeline_config.py frontend/src/features/settings/llm-purpose-prompts.ts
git commit -m "refactor(prompt): drop the cluster naming prompt"
```

### Task 7: Gate, deploy and live proof

**Files:**
- Create: `docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-quality.md`, `docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-quality.judge.md`
- Create (gitignored evidence): `.dforge/ui-ux/graph-cluster-quality/` screenshots, run JSON and capture scripts

**Interfaces:**
- Consumes: C1, C2, C3, C4 as deployed
- Produces: none

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: No new test, because this task proves the delta in the running UI and adds no code; the earlier tasks' tests pin behaviour**

- [ ] **Step 2: Gate**

Run: `./scripts/gate.sh` (repository root). A red leg exiting 143 is an `earlyoom` kill: check `free -h` and re-run that leg alone, as CLAUDE.md's Gate section says. After any backend route or MCP change the guards leg is mandatory, but this plan adds none.
Expected: exit 0.

- [ ] **Step 3: Deploy**

Run: `DARKMEM_PUSH=0 ./scripts/build-push.sh`, then `docker compose up -d`, then wait for `darkmem-prod-darkmem-1` to report `healthy`. Confirm the build's short-sha tag equals `git rev-parse --short HEAD`, and confirm the code is in the running image: `docker exec darkmem-prod-darkmem-1 grep -c "community_leiden" /app/app/utils/graph_knn.py` prints 1 or more, and `docker exec darkmem-prod-darkmem-1 test -f /app/app/utils/cluster_names.py`. Never push.

- [ ] **Step 4: Live proof**

Follow dforge:ui-ux's walkthrough at touch depth against the live page `http://127.0.0.1:8000/memory-graph`, signed in by minting a session inside the container: `docker exec darkmem-prod-darkmem-1 python -c "from app.api.auth import create_access_token; print(create_access_token({'sub':'admin'}))"` gives the token, set as the `darkmem_session` cookie and in `localStorage['darkmem-auth']` (the profile's Harness line). Adapt `.dforge/ui-ux/graph-regions-soft-nodes/scripts/shot.mjs` (it blocks every non-GET) into `.dforge/ui-ux/graph-cluster-quality/scripts/`. Capture at 1280x800 and 1920x1080, light and dark:
- UI-1: the default view, with Regions off and on. Record `cluster_names` from the page's own `/api/v1/graph/unified` response beside each capture.
- UI-2: a project scope selected (for example `darkraise-framework`). Record that no name starts with that project.
- UI-3: the filter panel's cluster list beside the canvas.
- UI-4: Settings → Assistant Prompts, showing chat and agent instructions and no cluster naming prompt.
- OP-1: every run's JSON records 0 console or page errors and 0 blocked writes.
Write the proof report with the `## Delta` items UI-1 to UI-4 and OP-1 copied from the spec's UI/UX section, and a Results table mapping each ID to its evidence and verdict. Run `ui-proof stamp` on it, then dispatch `dforge:judge-sonnet-high` to review it into the `.judge.md` file.

- [ ] **Step 5: Verify and commit**

Run: `bash /root/.claude/plugins/cache/darkraise/dforge/5.0.1/scripts/ui-proof check --base fe098bb9 --spec docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md`
Expected: exit 0.

```bash
git add docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-quality.md docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-quality.judge.md
git commit -m "docs(ui-proof): prove computed cluster names"
```
