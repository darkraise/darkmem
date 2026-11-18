# Constellation graphs on real data — item register

**Source:** owner request 2026-11-18 ("Let verify the graph e2e to make sure it work as I want", then "yes, do it" to reopening the design), with the end-to-end findings on the cloned 192.168.0.199 corpus
**Covers:** docs/dforge/specs/2026-11-18-constellation-real-data-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | at the default Edges threshold every memory is one connected group, so everything is core | docs/dforge/plans/2026-11-18-constellation-real-data.md | A1-A4 | doing | - |
| 2 | the halo is a thick ring of large, overexposed white blobs | docs/dforge/plans/2026-11-18-constellation-real-data.md | A6, A8, A9 | doing | - |
| 3 | the core is a hard-edged, tightly packed disc | docs/dforge/plans/2026-11-18-constellation-real-data.md | A7 | doing | - |
| 4 | satellites collapse into a thin dotted arc instead of separate clusters | docs/dforge/plans/2026-11-18-constellation-real-data.md | A5 | doing | - |
| 5 | labels on nearly every node | docs/dforge/plans/2026-11-18-constellation-real-data.md | A10 | doing | - |
| 6 | show 1,000 memories by default | docs/dforge/plans/2026-11-18-constellation-real-data.md | A11 | doing | - |
| 7 | prove it on the real data: anonymised fixture in Storybook plus the live page on this machine | docs/dforge/plans/2026-11-18-constellation-real-data.md | A13, A18 | doing | - |
| 8 | A15-A18: prove the arrangement on the live memory graph page (OP-1, OP-2 live half) once this branch is deployed | - | A15, A16, A17, A18 | deferred | final review: the auto run never deploys; deploy per CLAUDE.md, then re-run the live half of the ui-proof in both themes |
| 9 | the placeOuter iteration of the 20,000-node timing loop (constellation-layout.test.ts) is covered by A14 | - | - | deferred | final review: for dforge:test-simplifier |
