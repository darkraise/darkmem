# Auto run: graph-cluster-quality

**Source:** items the auto run for `docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md` deferred
**Covers:** docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | Switching graph Regions off leaves the region outlines and chips drawn beside the centre names until a repaint | - | - | deferred | final review follow-up: pre-existing in the regions feature; this branch changes no frontend file |
| 2 | Two clusters can receive the same computed name (e.g. both carry only the tag retrieval); the filter panel then lists two identical rows | - | - | done | c03c42b |
| 3 | A chosen term that is part of the prefix (darkraise under prefix darkraise-modder) is not skipped, so a name can partly repeat its prefix | - | - | done | c03c42b |
| 4 | Measure entity_terms_for_memories latency on an all_memories view (up to GRAPH_MAX_NODES ids); only the 1,000-id page view was measured | - | - | done | measured 2026-11-21 on production (read-only EXPLAIN ANALYZE, view ids selected in the statement): all_memories view of 4,759 memories, execution 437 ms (310 ms in the ix_entities_memory_ids bitmap scan, 7,215 term rows) |
| 5 | QA acceptance helpers _leiden and _louvain_r1 in test_graph_cluster_quality_acceptance.py set igraph's and Python's global generators without restoring them | 126f64f9 | - | done | owner ruling 2026-11-20: fixed; helpers restore igraph's generator and Python's random state, which also removes A2's order dependence |
| 6 | A term made only of non-ASCII characters has an empty spelling key and is dropped from cluster names (Naming rule 3 keeps [a-z0-9] only); decide whether the spec should keep such terms | 798478a3 | - | done | owner ruling 2026-11-20: keep them; rule 3 now keys letters and digits in any script after NFKC + casefold (prod had 0 dropped, 8 mangled terms) |
| 7 | gate.sh is GATE BLOCKED on this checkout: the F1 bench cache backend/scripts/extraction_bench/.cache/manifest.json is missing, so the gate's legs run one by one and the F1 leg is skipped | - | - | deferred | owner ruling 2026-11-20: environment, not this branch (2026-10-08 re-clone); no warm cache on host or image; clears with an owner DeepSeek key and one live run_bench.py run |
| 8 | Stale Louvain wording in a kept graph test comment (preflight-7) | - | - | done | not reproduced: no comment in test_graph_scale.py names Louvain; only the method name get_louvain_clustered_vectors |
| 9 | ENTITY_TERM_TYPES location (preflight-9) | - | - | deferred | parked Task 1: stays in app/repositories/graph.py per C3 |
| 10 | Two cluster-naming tests deleted rather than rewritten (preflight-12) | - | - | deferred | parked Task 1: recorded deviation; Task 4's tests cover the behaviours |
