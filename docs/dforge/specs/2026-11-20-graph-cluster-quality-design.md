# Graph cluster quality — design

**Execution strategy:** sequential — inline execution
**Depth:** light — approach

The memory graph's clusters become finer and stable, and their names are
computed from the members' tags and entities instead of asked of an LLM. The
response shape of `GET /api/v1/graph/unified` is unchanged; the frontend
changes no code.

## Decisions

- **Direction (owner, 2026-11-20, before this session):** "I prefer the
  non-llm approaches, if we could not do it without LLM, then we will touch
  LLM".
- **Clustering (owner, 2026-11-20):** "Leiden r=2, cross-project
  (Recommended)". Clusters stay themes that may span projects.
- **Naming (owner, 2026-11-20):** "c-TF-IDF, drop LLM (Recommended)". The
  graph route makes no LLM call and keeps no name cache.
- **Process (owner, 2026-11-20):** "Full flow (Recommended)".
- **Rejected on measurement** (my call, from the numbers in the owner's
  question). Adding shared-entity edges to the kNN graph moved purity by at
  most 0.04 and left the 176-member cluster whole at every weight tried.
  Reusing `memory_communities` gives 72 communities over the 1,000-memory
  view (median 10), leaves 11% of it uncovered, labels with raw entity
  triples, and refreshes only when `topic_detection` runs.
- **Resolution is one constant, 2.0, for every view size** (my call). Across
  the six views measured it beat Louvain at resolution 1 on churn stability
  in every one (Riskiest assumption).
- **Determinism** (my call): Leiden runs with `n_iterations=-1` (until
  stable) after `igraph.set_random_number_generator(random.Random(42))`. A
  fresh `Random` never touches Python's global `random` state, and the call
  is serialised because `_KNN_EXECUTOR` has one worker under invariant 13.
- **Naming parameters** (my call): the prefix share (60%), the stoplist (`MEMORY_TYPES`), the entity types, the
  40-character budget (`ISLAND_LABEL_MAX_CHARS` on the frontend) and three
  terms at most. Each is a module constant beside the namer.
- **`get_louvain_clustered_vectors` keeps its name** (my call): six test call
  sites use it, and the rename buys nothing a reader needs.
- **State boards:** none (my call; touch depth, a text-only change on a
  surface that already has boards).
- **No hub cutoff (pre-execution ruling, 2026-11-20).** The approved draft
  also excluded terms carried by more than 25% of the view. That cut the
  defining term of any cluster holding over a quarter of a small view, and
  without it the names on the newest-1,000 view, the whole corpus and the
  cross-project views are identical (`measure3-hub100.out` against
  `measure2.out`): the score's document-frequency factor already keeps hub
  terms such as `darkraise-framework` down. Ruled by the pre-execution
  ruling seat (`.dforge/rulings-preexec-2-report.md`). Its gap (a
  single-project view could name clusters after the project itself) is
  closed by rule 5's sole-project clause, measured in `measure4.out` on the
  darkmem, darkload and darkraise-ai-plugins scopes.
- **Out of scope, reported:** 5 active production memories hold the literal
  `project/darkraise-modder` in `project`. The namer treats it as a project
  name like any other; the data fix belongs to the owner.

- **Spec review (owner, 2026-11-20):** "Approve and run unattended"; early
  CI "No early run (Recommended)".

Early CI: none

Finish: merge

Worktree: in-place

## Measured baseline and target

Measured on 2026-11-20 against a read-only export of production (4,759 active
memories, `qwen3-embedding:0.6b`), with the scripts and outputs in
`.dforge/ui-ux/graph-cluster-quality/measurements/` (`measure.py`,
`measure2.py`, and their `.out` files). "Churn ARI" drops 1% of the view, as
if those memories were new captures, re-clusters, and compares the remaining
memories' labels with the full run (adjusted Rand index, 1.0 identical).

| View | Louvain r=1: clusters / largest / churn ARI | Leiden r=2: clusters / largest / churn ARI |
|---|---|---|
| newest 1,000 (page default) | 12 / 174 / 0.66 | 17 / 104 / 0.88 |
| all 4,759 | 17 / 597 / 0.77 | 28 / 455 / 0.87 |
| project darkraise-framework (1,000) | 10 / 143 / 0.61 | 19 / 97 / 0.87 |
| project darkmem (189) | 7 / 58 / 0.56 | 13 / 25 / 0.81 |
| project darkload (64) | 5 / 15 / 0.84 | 6 / 14 / 0.93 (coverage 0.89) |
| project darkraise-ai-plugins (109) | 5 / 35 / 0.49 | 10 / 18 / 0.83 |

Tag coherence on the default view (how much more two members of a cluster
share non-project tags than two random memories) rises from 4.7x to 7.6x.
Leiden on a synthetic 50,000-node graph took 0.31 s against Louvain's 0.28 s.

## Design

### Clustering (`backend/app/utils/graph_knn.py`)

`cluster_labels` replaces `community_multilevel` with
`community_leiden(objective_function="modularity", weights="weight",
resolution=CLUSTER_RESOLUTION, n_iterations=-1)`, seeded as Decisions says.
`CLUSTER_RESOLUTION = 2.0` and `CLUSTER_SEED = 42` sit beside `CLUSTER_K`.
Renumbering and the `min_cluster_size` drop are unchanged. No other caller of
igraph community detection exists in `backend/app`.

### Naming (`backend/app/utils/cluster_names.py`, new, pure)

`name_clusters(members, tags, projects, entity_terms) -> dict[str, str]`,
where `members` maps a cluster id to its memory ids, and the other three map
every memory id in the view (clustered or not) to its tags, its `project`
value, and its entity names. Rules, in order:

1. **Effective project** of a memory: its `project` unless that is
   `default`; then its first `project/<name>` tag in tag order; else
   `default`.
2. **Terms** of a memory: its tags that do not start with `project/`, plus
   the entity names `entity_terms` gives for it, all lowercased; minus any
   value in `MEMORY_TYPES` and any longer than 30 characters.
3. **Spelling key** of a term: its lowercase letters and digits only, so
   `claude code` and `claude-code` are one term. Document frequency is the
   number of view memories carrying the key.
4. **Prefix:** the cluster's most common effective project, when it holds at
   least 60% of the cluster's members, is not `default`, and the view's
   clustered memories span more than one effective project.
5. **Score** of a key in a cluster: (members carrying it / cluster size) x
   ln(1 + mean size of the view's clusters / document frequency). Eligible only when at
   least 2 members carry it and it is not the prefix's key, nor, when the
   view's clustered memories share one effective project, that project's
   key.
6. **Pick** up to 3 keys by score, ties by key. Skip a key that contains, or
   is contained in, a chosen key, or shares its first 6 characters with one.
7. **Display** each key as its most frequent spelling in the cluster, ties
   alphabetical.
8. **Join** the prefix and the terms with ` · `, adding terms while the name
   stays within 40 characters. The first part after the prefix is always
   kept, so the name is never empty; the frontend's ellipsis covers the rare
   overlong one.
9. **Fallback:** no prefix and no eligible term gives `Cluster <id>`, the
   frontend's own fallback.

The function is deterministic: the same inputs give the same names.

### Entity terms (`backend/app/repositories/graph.py`)

New `PostgresGraphRepository.entity_terms_for_memories(memory_ids)` returns
each memory id's lowercased entity names for the types `project`, `tool`,
`artifact`, `service`, `protocol` and `language`, in one query:
`unnest(memory_ids)` over rows matching `memory_ids && CAST(:ids AS uuid[])`
(the GIN index `ix_entities_memory_ids`) and `entity_type = ANY(...)`,
keeping only unnested ids in the view. `concept` and the rest are left out:
on the live view they are mostly sentence fragments.

### Graph service (`backend/app/services/graph.py`)

`_build_memory_arm` collects tags and projects from the memory nodes, fetches
entity terms when `graph_repo` is present, and calls `name_clusters`. When the
entity query raises, it logs, names from tags alone and reports the arm
degraded, so `get_unified_graph` does not cache it (the existing
degraded-not-cached rule). With no `graph_repo` the names come from tags alone
and the arm is not degraded.

Removed: `_generate_cluster_names`, `_tag_cluster_name`,
`CLUSTER_NAME_LLM_CAP`, `_cluster_name_cache`, `_CLUSTER_NAME_CACHE_SIZE`, and
the name-cache line of `reset_graph_caches`. `self.llm` stays: fingerprint
resolution needs it.

### The `cluster_naming` prompt

Removed from `PROMPTS` (`app/services/prompt.py`) and from
`ORPHAN_PROMPT_KEYS` (`app/services/pipeline_aggregator.py`), and dropped from
the comment in `frontend/src/features/settings/llm-purpose-prompts.ts`.
Settings → Assistant Prompts renders orphans from the API, so its textarea
disappears with no frontend change. `PUT /api/v1/config/system-prompts` with
that key now answers 422 (unknown purpose). Production stores no
`system_prompts` override row (checked 2026-11-20), so no data is orphaned.
Historical analyses under `docs/planning/` stay as written.

### Tests

- `tests/unit/test_graph_knn.py` gains a determinism test: two calls on the
  same graph, with the global `random` state moved between them, return
  identical labels. A second test builds a graph where resolution 1 merges two
  weakly joined groups and checks they come back as two clusters; the plan's
  task finds the fixture and confirms it fails under the old call. The two
  existing `cluster_labels` tests are kept.
- `tests/unit/test_cluster_names.py` (new) covers rules 1 to 9, one test per
  rule.
- `tests/test_graph_cluster_naming.py` is rewritten for the computed namer
  through `GraphService`: no LLM call, entity terms used, and tags alone when
  the entity query fails.
- `tests/test_graph_scale.py::test_degraded_naming_is_not_cached` becomes "a
  failed entity-term query is not cached".
- `tests/test_session_resource_lifetimes.py::test_read_only_graph_cluster_names_are_local`
  is rewritten against `_build_memory_arm`'s naming: no `chat_completion`
  call in read-only mode.
- `tests/test_prompt_hardening.py::test_cluster_naming_guards_its_sample` is
  removed with its prompt; `test_pipeline_aggregator`'s orphan guard covers
  the shrunken set.
- `tests/test_graph_repo.py` gains a test for `entity_terms_for_memories`:
  type filter, lowercasing, ids outside the view excluded.

## UI/UX

**UI/UX depth:** touch — the only visible change is the text of cluster names
on the memory graph and one prompt leaving Settings; no layout changes.

The delta (carried into the proof report):

- **UI-1** — On the live memory graph (cloned corpus, default view), each
  island name and each region chip shows the computed name (`<project> ·
  term · term`, or terms alone), at 1280x800 and 1920x1080, light and dark.
  Names within 40 characters show without an ellipsis.
- **UI-2** — With a project selected in the graph's project scope, no name
  carries a project prefix.
- **UI-3** — The filter panel's cluster list shows the same names as the
  canvas.
- **UI-4** — Settings → Assistant Prompts shows the chat and agent
  instructions prompts and no cluster naming prompt.
- **OP-1** — Proven on the live page with 0 console or page errors and 0
  attempted writes, after the change is deployed to this host.

## Acceptance

A1. [test, high] Clustering the same similarity graph twice returns identical labels, including when Python's global `random` state changes between the calls.
A2. [test, high] Two dense groups joined weakly enough that Louvain at resolution 1 merges them come back as two clusters.
A3. [test, high] Communities smaller than `min_cluster_size` are labelled -1, and a graph with no edges labels every memory -1 (existing behaviour kept).
A4. [demo, high] Running the shipped `knn_graph` plus `cluster_labels` over the newest 1,000 memories of the measurement export gives at least 15 clusters, a largest cluster of at most 120 and a churn ARI of at least 0.85.
A5. [test, high] A memory whose `project` is `default` counts toward the project in its first `project/` tag when choosing a prefix.
A6. [test, high] A cluster whose most common effective project holds at least 60% of its members starts with that project's name; below 60%, or when that project is `default`, the name has no prefix.
A7. [test, high] When every clustered memory in the view shares one effective project, no name has a prefix.
A8. [test, neg, high] A name never contains a `MEMORY_TYPES` value, a term carried by fewer than 2 of the cluster's members, its own prefix a second time, or, in a view whose clustered memories share one effective project, that project's name.
A9. [test, high] Spellings that differ only in case, spaces or punctuation are one term, shown in the cluster's most frequent spelling; a term sharing its first 6 characters with a chosen term, or contained in one, is skipped.
A10. [test, high] A name is at most 40 characters unless the prefix plus the first term already exceed it; terms are dropped whole, never cut.
A11. [test, high] A cluster with no prefix and no eligible term is named `Cluster <id>`, and every cluster id in `clusters` has a non-empty name in `cluster_names`.
A12. [test, high] Names use the entity names of types project, tool, artifact, service, protocol and language asserted by the cluster's members, and no other entity type.
A13. [test, high] When the entity-term query raises, names are built from tags alone and the memory arm is not cached: a second identical request re-clusters.
A14. [test, neg, high] Building the unified graph makes no `chat_completion` call, in normal and in read-only mode.
A15. [test, neg, high] `cluster_naming` is no longer a prompt key: `GET /api/v1/config/system-prompts` does not list it and a `PUT` naming it answers 422.
A16. [test, high] The `GET /api/v1/graph/unified` response keeps its keys and types: `memories`, `clusters`, `cluster_names`, `similarity_edges`, `total_memories`, `memories_truncated`, `fingerprint_unresolved`.
A17. [demo, high] UI-1: the live memory graph shows the computed names on islands and region chips at both viewports and themes.
A18. [demo, high] UI-2: with a project scope selected, no cluster name carries a project prefix.
A19. [demo, high] UI-3: the filter panel lists the same cluster names as the canvas.
A20. [demo, high] UI-4: Settings → Assistant Prompts shows the chat and agent instructions prompts and no cluster naming prompt.
A21. [demo, neg, high] OP-1: the live proof records 0 console or page errors and 0 attempted writes.

## Riskiest assumption

That one fixed resolution, 2.0, suits every view the page serves, from a
64-memory project scope to the whole corpus. Evidence: `measure2.py` on
2026-11-20 (`.dforge/ui-ux/graph-cluster-quality/measurements/measure2.out`)
over six views from 64 to 4,759 memories. Leiden at 2.0 has the higher churn
ARI than Louvain at 1.0 in all six and roughly halves the largest cluster in
the large views. The weak point is the smallest scope: on `darkload` (64
memories), 11% of memories end up unclustered (coverage 0.89, against 1.00
today). If the owner finds small scopes over-split on the live page, the fix
is a resolution that falls with view size, not another algorithm.
