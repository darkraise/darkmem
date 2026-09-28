# Register — memory graph at scale

**Source:** owner requests in the 2026-09-28/29 session ("Current memory graph show only 200 items, why?" and the follow-up)
**Covers:** docs/superpowers/specs/2026-09-29-memory-graph-scale-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | Do them all: add a node count setting and pass limit through the hook | docs/superpowers/plans/2026-09-29-memory-graph-scale.md | graph settings carry a Nodes input; the hook sends limit=<n>; the route accepts 1..50,000 | planned | - |
| 2 | Do them all: add an order to the query so the selection is predictable (newest first) | docs/superpowers/plans/2026-09-29-memory-graph-scale.md | get_all_vectors orders by created_at DESC, memory_id DESC; a limit keeps the newest | planned | - |
| 3 | Do them all: check layout performance before going far past 1000 | docs/superpowers/plans/2026-09-29-memory-graph-scale.md | 20,000-node bench and 2k/20k story measurements recorded on this register | planned | - |
| 4 | for the node count setting, add additional All nodes checkbox | docs/superpowers/plans/2026-09-29-memory-graph-scale.md | an All checkbox sends all=true; the server returns every in-scope memory up to 50,000 and reports total_memories | planned | - |
| 5 | I see other app can perform very well with over 20000 nodes, need to make sure darkmem graph can work smoothly for large number of nodes | docs/superpowers/plans/2026-09-29-memory-graph-scale.md | bench cold <= 10 s and warm <= 1 s at 20,000; 20k story median >= 30 fps with no long task > 200 ms after settling; 3D shows a best-effort notice from 5,000 | planned | - |
