## Verdict
verdict: ship 51698444ee69244a
scores: coverage 17 / fidelity 16 / states 17 / deviations 16

## Inputs read

- Criteria: `/root/.claude-alt2/plugins/cache/darkraise/dforge/4.17.1/criteria/ui-ux-proof.md`
- Contract: `docs/dforge/specs/2026-11-18-constellation-graphs-design.md`, "## UI/UX contract" (UI-1..7, UX-1..9, OP-1..5)
- Report: `docs/dforge/ui-ux/proofs/2026-11-18-constellation-graphs.md` (fingerprint 51698444ee69244a)
- Prior round: `.dforge/ui-proof-2026-11-18-constellation-graphs-round1-fix-report.md`. I read it for context only and did not carry its scores over.
- Scripts: `.dforge/ui-ux/scripts/hover2.js`, which captured the UX-9 hovers.
- Code: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (empty-state branches), and the `EmptyState` uses under `frontend/src/features/graph/components/`.
- Ledger: `.dforge/sdd/2026-11-18-constellation-graphs/progress.md`, the Task 8 line that holds OP-3's A23 measurement.
- Tests: I confirmed by grep that every test title the report names exists in the file it is attributed to. That covers the 12 titles checked directly, including `real-code-graph-view.test.tsx` "shows the honest never-indexed empty state pointing at Repositories".

### Screenshots opened

- **The three round-1 items, every capture at all four viewport/theme pairs:**
  - `ux-9-hover-*` (4 files);
  - `ux-6-real-nograph-*` (4 files);
  - `ux-5-page-empty-*` (4 files);
  - `ux-5-page-empty-filtered-*` (4 files).
- **Samples for every other ID:**
  - Memory boards: `board-memory--mixed-1280x800-dark`, `board-memory--scale-20-k-1280x800-dark`, `board-memory--entity-layer-1920x1080-light`.
  - Code boards: `board-code--mixed-1920x1080-light`, `board-code--blast-radius-1920x1080-dark`, `board-code--active-process-1920x1080-light`.
  - UI captures: `ui-1-resize-1-1920x1080-dark`, `ui-4-toolbar-2d-1280x800-dark`, `ui-4-toolbar-3d-1920x1080-dark`, `ui-6-real-host-1280x800-light`.
  - UX captures: `ux-7-deeplink-1920x1080-dark`, `ux-2-settling-t0/t1-1280x800-dark`, `ux-7-recolour-before/after-1280x800-dark`, `ux-8-focus-1280x800-light`, `ux-8-0-start` and `ux-8-3-arrowleft-1920x1080-light`, `ux-7-hover-1920x1080-light`, `ux-6-real-folded-1920x1080-light`.
- **Existence:** every file I opened exists. The evidence directory holds 249 files, and all the name families the report cites are present.

## The three round-1 items, re-checked

- **UX-9 is fixed.** All four `ux-9-hover-*` captures (1280 dark, 1280 light, 1920 dark, 1920 light) show the hovered node with its halo ring and the label "Synthetic memory 0 about topic…". In round 1, three of the four showed a resting node with no label.
  - `hover2.js` now finds the node from its drawn pixels, below Storybook's top bar, and moves the pointer onto it. It does not click.
- **UX-6 is fixed.** All four `ux-6-real-nograph-*` captures show the repository selector on "darkmem-backend", then "No graph yet — darkmem-backend has not been indexed yet." with the "Open reindex dialog on Repositories →" button.
  - This is the empty-repository branch: a repository is present and its graph has no nodes. It is not the no-repositories state.
  - The row now also cites `real-code-graph-view.test.tsx`, and labels `ux-6-real-empty-*` correctly as no repositories.
- **UX-5 is fixed.**
  - **Empty:** all four `ux-5-page-empty-*` captures show the page's existing `EmptyState`, "No graph yet — Capture memories and nodes appear here."
  - **Empty filtered:** all four `ux-5-page-empty-filtered-*` captures show the filter panel. The search reads "no memory says this", the counts are 60 per facet, and Show All is there. The canvas behind it draws only the nebula.
  - **The claim that the page has no separate filtered-empty message holds at HEAD.** `real-memory-graph-page.tsx` chooses the `EmptyState` only when `memoryCount === 0`, and `memoryCount` is `data?.memories.length`, the unfiltered count. With 60 memories filtered down to none, it renders `Graph2DRenderer`. That renderer's only `EmptyState` is the WebGL-unavailable one (line 991). So a view filtered to zero cannot show anything other than the canvas.
  - I could not run git, so I did not check the merge base itself. The contract asks only for "existing empty states", and the code at HEAD shows there is no filtered-empty state to keep.

## Disputed items

None.

## Per-criterion notes

**Every Item Has Evidence: 17.** Every contract item has a row, and every row's evidence that I opened shows the item.
- UI-1: the resize triplet keeps the nebula centred on the core.
- UI-4: the toolbar shows Edges and Min size in 2D, and adds Spacing (80) in 3D. There is no Tightness control.
- UI-6: the real host shows Colour by, the counters and the legend, with no Layout or Play/Pause control.
- UX-7: the deep link centres `memory_search`, hover reads "memory_search · function · api/mcp/mcp_tools.py", and the recolour pair keeps the zoom and the frame.
- UX-8: the frames show the inset focus ring and the pan on ArrowLeft.
- UX-3 and UX-4 rest on tests that exist.
- **The one weak spot is OP-3's first-frame half (A23).** The ledger's Task 8 line records medians of about 965 ms against 919 ms (+5%). That was measured before the density, edge and camera fixes and the final fix wave, and was not measured again afterwards. The row says so plainly, and the 20% bar leaves ample headroom, so I do not dispute it. A re-measurement at e457bb75 would close it.

**Built Matches Promised: 16.** Both themes match the contract.
- Dark is near-black with a violet nebula on the core. Light is pale paper with faint lavender.
- Dark discs have an additive glow. Light discs are crisp, with halo nodes as translucent grey.
- Rest edges are faint tints, and the selected neighbourhood is at full colour.
- The selection ring is solid primary (green), blast rings are dashed destructive (red), and process rings are dashed foreground. Labels are in the mono font.
- Entities are diamonds with type-coloured borders, inside the core.
- Points held back from full marks, none disputed:
  - At Scale20k the halo ring reads brighter than the core. That inverts the contract's "core 1.0, satellite 0.8, halo 0.45" order at the worst case. The UI-2 deviation row discloses it and ties it to register row 3.
  - The "Not Found" line at top left of every Storybook capture comes from the preview harness. The demo-host captures (`ux-7-deeplink`) do not have it, so it is not built UI.

**Every State Is Shown: 17.**
- Both canvas state matrices have captures at all four viewport/theme pairs.
- The memory-page empty and empty-filtered states now have captures, and the first-load skeleton has a test.
- Hover is shown at all four pairs on both canvases. Selection, blast, process, community, depth filter, hidden kinds, the 2,000-node and 20,000-node worst cases, and WebGL-unavailable all have boards.
- Settling has frames at three times. Twinkle and camera timing have pairs under normal and reduced motion.
- The keyboard-only walk has screenshots at every step plus the Playwright spec.
- Held back slightly: the `ux-4-*` twinkle pairs are 1280x800 dark only. The report says so, and `ambient-motion.test.ts` covers the eligibility rules.

**Deviations Are Cited: 16.** UI-2 is the only declared deviation. Under density, the dark theme lowers a role's brightness and then its disc size, against "overlapping glows brighten" and the fixed role brightness levels.
- It cites an accessibility need, perceivability: community colour is the only cluster cue, and additive clipping to white erased it at density. The criteria accept that kind of citation.
- It says plainly that no owner ruling exists, so the contract's literal wording stays unamended until the owner rules.
- Every other difference I found is either the Storybook harness or existing chrome:
  - the "Not Found" line;
  - the real host's legend falling below the fold at 1920 dark. The UI-6 row now describes this accurately, and the legend is visible at 1280 light.
- I found no uncited difference.

Verdict: ship 51698444ee69244a
