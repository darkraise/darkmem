# Auto run: graph-cluster-quality

**Source:** items the auto run for `docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md` deferred
**Covers:** docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | Switching graph Regions off leaves the region outlines and chips drawn beside the centre names until a repaint | - | - | deferred | final review follow-up: pre-existing in the regions feature; this branch changes no frontend file |
| 2 | Two clusters can receive the same computed name (e.g. both carry only the tag retrieval); the filter panel then lists two identical rows | - | - | deferred | final review follow-up: spec Naming rules 1-9 set no uniqueness rule and the old tag fallback had none; needs a spec rule (tie-break term or suffix) |
| 3 | A chosen term that is part of the prefix (darkraise under prefix darkraise-modder) is not skipped, so a name can partly repeat its prefix | - | - | deferred | final review follow-up: matches spec rules 5-6 as written; extend rule 6's overlap test to the prefix key in the spec first |
| 4 | Measure entity_terms_for_memories latency on an all_memories view (up to GRAPH_MAX_NODES ids); only the 1,000-id page view was measured | - | - | deferred | final review follow-up: reviewer recommendation, not a finding |
| 5 | QA acceptance helpers _leiden and _louvain_r1 in test_graph_cluster_quality_acceptance.py set igraph's and Python's global generators without restoring them | - | - | open | - |
| 6 | A term made only of non-ASCII characters has an empty spelling key and is dropped from cluster names (Naming rule 3 keeps [a-z0-9] only); decide whether the spec should keep such terms | - | - | open | - |
| 7 | gate.sh is GATE BLOCKED on this checkout: the F1 bench cache backend/scripts/extraction_bench/.cache/manifest.json is missing, so the gate's legs run one by one and the F1 leg is skipped | - | - | open | - |
| 8 | Stale Louvain wording in a kept graph test comment (preflight-7) | - | - | deferred | parked Task 1: the claim still holds under Leiden; only the name is stale |
| 9 | ENTITY_TERM_TYPES location (preflight-9) | - | - | deferred | parked Task 1: stays in app/repositories/graph.py per C3 |
| 10 | Two cluster-naming tests deleted rather than rewritten (preflight-12) | - | - | deferred | parked Task 1: recorded deviation; Task 4's tests cover the behaviours |
