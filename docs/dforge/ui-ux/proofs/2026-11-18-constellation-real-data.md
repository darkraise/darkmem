# UI proof: Constellation real data

**Contract:** docs/dforge/specs/2026-11-18-constellation-real-data-design.md
**Fingerprint:** 1b80fcaade5ed8da
**Judge:** ship 1b80fcaade5ed8da — docs/dforge/ui-ux/proofs/2026-11-18-constellation-real-data.judge.md
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

Proven at c04859e0 (branch `auto/constellation-real-data-2`, base c55267df) on 2026-11-19. This proof follows the fix wave f83ea83c..c04859e0, which answered the previous judge's `fix 5502e386a9073533`. Every row is re-evidenced at c04859e0.

**Second round, e5cb25e0.** The judge's `fix 00e597c7bfc6d76e` disputed one item: the EntityLayer board drew every fixture entity, while the page shows only entities that two or more drawn memories assert. The rule now lives in an exported `entityVisible` in `use-graph-filters.ts`, and both the page's hook and the board call it. The EntityLayer board applies the page's default (shared only), and a new `EntityLayerAll` board keeps the unfiltered state. Only the EntityLayer boards were re-captured. The hook's behaviour is unchanged: it is the same comparison moved into a function, and `use-graph-filters-shared-entities.test.tsx` passes. Every other capture stands from c04859e0.

e5cb25e0 is deployed too. The plan's integration check passed through `suite-run`, then the image was built with `DARKMEM_PUSH=0` and started, and it reports healthy on image `7ac072826c9f`, tagged `e5cb25e0`. The live entity-layer state re-captured on it (`live/live-entity-layer-e5cb25e0-1280x800-dark.png`) draws the same diamonds in the same outer positions as the c04859e0 capture. It has 0 white canvas pixels, 0 page or console errors and 0 attempted writes.

**This build is deployed.** The image `darkraise/darkmem:c04859e0` was built with `DARKMEM_PUSH=0` and started on this host with `docker compose up -d`. The container reports healthy and runs image `1b110e5d3635`, tagged `c04859e0`. The served bundle carries this branch's graph-prefs migration (`version:1,migrate` in `/app/web/assets/selection-settings-*.js`). The gate was run before the deploy, leg by leg: `./scripts/gate.sh` stops at preflight because this checkout has no F1 bench cache, so every other leg was run with the gate's own commands. The alembic head count is 1. Backend: 8,462 passed. Benchlib: 1,062 passed. Frontend typecheck, 2,458 frontend tests and the build: green. Extension, SDK Python (36), SDK TypeScript (20) and the SDK build: green. The F1 bench did not run; this branch changes no backend file.

**Harnesses** (per the profile):
- **Boards:** the six `Graph/Constellation/RealCorpus` boards (Default1000, All, Small200, HighEdges, EntityLayer, Selected) on Storybook :6006. Each was captured at both viewports in both themes, 20 s after load (30 s for All), driven by Node Playwright with Chromium on SwiftShader.
- **Live page:** `http://127.0.0.1:8000/memory-graph` on the deployed build, with the cloned corpus of 4,759 memories. A session was minted inside the container, and each state starts from a fresh browser profile. **Read-only:** every request other than GET, HEAD and OPTIONS was routed to abort, and none was attempted (0 blocked in every run). The light theme is stored server-side (`GET /api/v1/config/theme`), so for light runs the test browser answered that one GET with the stored settings plus `mode: "light"`; nothing was written.
- **Live states:** reached through the page's own controls. Node limit 200 was typed into the "Node limit" field, "All nodes" was checked, Edges was moved 0.5 → 0.8 with six ArrowRight presses on the slider, and the "Entity layer" switch was turned on.

The scripts are under `.dforge/ui-ux/constellation-real-data/scripts/` and the live captures under `.dforge/ui-ux/constellation-real-data/live/`. Both are git-ignored and stay local. The live captures show real memory titles in hover labels, so they are not quoted here. The previous proof's captures are kept in `prev-ddc3037a/` for the OP-5 comparison.

Role split on the fixtures (A2 test output at c04859e0), as core / satellites / halo shares: 200: 43.5% / 21.5% / 35.0%, 15 clumps. 1,000: 44.5% / 17.3% / 38.2%, 63 clumps. All 4,759: 44.4% / 15.0% / 40.5%, 271 clumps.

Storybook's preview renders a "Not Found" line in a 24-pixel strip at the top of every board. It comes from the preview's own TanStack router and is harness noise, not product.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .dforge/ui-ux/constellation-real-data/live/live-default-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-default-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/live/a15-live-default-1920x1080-dark-beside-reference.png, .dforge/ui-ux/constellation-real-data/board-default-1000-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/board-small-200-1920x1080-dark.png; tests `constellation-real-data.acceptance.test.tsx` "UI-1: at rest an edge shows only inside the core or one clump, and hovering a node lights its others" (A20), `constellation-layout.test.ts` `spreadCore` (A22), A5, A6, A7 | See **UI-1 details** below the table. |
| UI-2 | pass | .dforge/ui-ux/constellation-real-data/board-entity-layer-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/board-entity-layer-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/board-all-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/board-high-edges-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-entity-layer-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/live/live-all-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/ui-5-zoomed-1280x800-dark.png; tests `node-glow-program.test.ts` "UI-2: screen-blends the memory canvas's light so an overlap never passes its brighter colour", "draws a packed memory core crisp at its measured spacing, and leaves the code canvas at CORE_K", "crispStyle lifts its cap once zooming in widens the spacing" (A23), A8 | No canvas pixel reaches white at the fit view on any dark board or live state, the entity layer included. See **UI-2 measurements**. |
| UI-3 | pass | .dforge/ui-ux/constellation-real-data/board-default-1000-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/op-5-code--worst-2000-before-after-1280x800-dark.png; tests `constellation-graphs.acceptance.test.tsx` "A9: halo nodes take one small size whatever their importance" | Halo points are one small size on both canvases. The runner sizes the halo at `min(HALO_SIZE, 0.4 × median core size)`, as spec Architecture §6 states. |
| UI-4 | pass | .dforge/ui-ux/constellation-real-data/board-default-1000-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/board-all-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/board-entity-layer-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/ui-5-zoomed-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/live/live-default-1280x800-light.png, .dforge/ui-ux/constellation-real-data/live/live-default-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/live/live-all-1920x1080-light.png; tests `node-glow-program.test.ts` "UI-4: only the memory canvas caps its core and clump discs in the light theme" (A23), "A8: the dark-theme shader scales halo radius and brightness by them; the light-theme shader does not" | Light theme, on the boards and live: crisp saturated points with no glow, a pale halo, and no rest-edge mesh visible at the fit view. Zoomed in on the board, the core's rest edges show as faint grey lines behind the points. The previous proof's dense grey edge mesh at the fit view is gone (the fix wave hides edges that cross groups and fades light rest edges to 0.4). |
| UI-5 | pass | .dforge/ui-ux/constellation-real-data/ui-5-hover-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/ui-5-hover-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/ui-5-zoomed-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/ui-5-zoomed-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/board-selected-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/live/live-hover-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-hover-1920x1080-light.png; tests `constellation-real-data.acceptance.test.tsx` "A10: at the fit view only a hovered or selected node carries a label", "A10: at most 2% of the 1,000 memories are hubs", `hubs.test.ts` A10 | See **UI-5 details** below the table. |
| UX-1 | pass | .dforge/ui-ux/constellation-real-data/board-small-200-1920x1080-dark.png, .dforge/ui-ux/constellation-real-data/board-all-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-small-200-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-all-1920x1080-dark.png; tests `real-corpus-roles.test.ts` A2 (200, 1000, all), `constellation-real-data.acceptance.test.tsx` A1 (five tests), `constellation-layout.test.ts` "A4: an attachment takes the highest linked role and never changes a memory's role" | Core share: 43.5% at 200, 44.5% at 1,000 and 44.4% at 4,759. The rest falls into clumps and halo (header). The live page shows the same three-part arrangement at 200, 1,000 and all. |
| UX-2 | pass | .dforge/ui-ux/constellation-real-data/board-high-edges-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-high-edges-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/live-high-edges-1920x1080-light.png; tests `real-corpus-roles.test.ts` "A3: raising Edges from 0.5 to 0.8 never pulls a memory inward while an 8+ core remains", `constellation-real-data.acceptance.test.tsx` "A3: raising Edges from 0.5 to 0.8 in steps of 0.05 never pulls a memory inward…", `constellation-graphs.acceptance.test.tsx` "A12: raising the Edges threshold so a memory loses its last edge makes it halo on the next build" | Live at Edges 0.8: more clumps and a fuller halo than the default. The core is drawn at the same radius R in every state, so its smaller membership shows as fewer, looser lobes, not a smaller disc. **Observation:** at 0.8 most halo points turn grey. The Colour encoding is Cluster, and memories that belong to no cluster at that threshold take the unclustered colour. That is the shipped colour rule, not this contract's. |
| UX-3 | pass | .dforge/ui-ux/constellation-real-data/live/keyboard-edges-slider-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/live/keyboard-edges-slider-1920x1080-light.png; tests `graph-prefs.test.ts` "A11: defaults to 1,000 memories", "A11: a stored 200 from before version 1 loads as 1,000, and any other stored value is kept", `constellation-real-data.acceptance.test.tsx` A11 (three tests) | Live: with no stored preference, the settings panel reads "Showing 1,000 of 4,759", and the Nodes field holds 1000. Changing the limit to 200 stores `nodeLimit: 200` under `version: 1` (the live run's `darkmem-graph-prefs` readback). |
| UX-4 | pass | .dforge/ui-ux/constellation-real-data/ux-4-twinkle-default-1000-a-1280x800-dark.png + -b, .dforge/ui-ux/constellation-real-data/ux-4-twinkle-all-a-1280x800-dark.png + -b, .dforge/ui-ux/constellation-real-data/live/live-hover-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/board-selected-1280x800-dark.png; tests `constellation-graphs.acceptance.test.tsx` A8 (motion loop: reduced motion, 2,000-node cap, hidden document), "A9: the motion loop never writes node positions", A18 (canvas keyboard) | Twinkle: of two frames taken 1.5 s apart at rest, 0.58% of pixels change on the 1,000 board and 0.00% on the 4,759 board, which is over the 2,000-node motion cap. Live hover shows ring, edges and dimming. Selection on the board shows focus, ring and adjacent labels. The WebGL-unavailable state is proven by test (`graph-2d-renderer.test.tsx`). |
| UX-5 | pass | every `board-*` capture (6 boards × 2 viewports × 2 themes, plus `board-entity-layer-all-1280x800-dark.png`) and every `live/live-*` capture (5 states × 2 viewports × 2 themes); tests `constellation-real-data.acceptance.test.tsx` "UX-5: the entity layer leaves every core memory where it was, and a core entity sits among its memories" (A21), A4 | See **UX-5 details** below the table. |
| OP-1 | pass | .dforge/ui-ux/constellation-real-data/live/a15-live-default-1280x800-dark-beside-reference.png, .dforge/ui-ux/constellation-real-data/live/a15-live-default-1920x1080-dark-beside-reference.png | The live default view (1,000 memories, dark) sits beside `graph.jpg` at both viewports. It shows a multi-coloured core, small clumps scattered around it, and a sparse halo thinning outward. It has 0 white canvas pixels and no rest edges across the halo. The contract allows exact positions and colours to differ. See **Differences from the reference** below the table. |
| OP-2 | pass | .dforge/ui-ux/constellation-real-data/live/ (20 state captures: default, 200, all, Edges 0.8, entity layer × 1280x800 and 1920x1080 × light and dark), .dforge/ui-ux/constellation-real-data/board-* (24 captures) | Both halves are met: the live page with the cloned corpus and the boards, at both viewports in both themes. |
| OP-3 | pass | test `constellation-layout.test.ts` "A14: roleCut + classify + placeOuter take 50 ms or less for 20,000 nodes and 110,000 scored edges"; `constellation-real-data.acceptance.test.tsx` A14 (median of 5) | At c04859e0: timings 42.8, 45.9, 33.7, 36.4 and 21.8 ms, median 36.4 ms. The test also passed inside the full 2,458-test frontend run. |
| OP-4 | pass | tests `real-corpus-fixture.test.ts` A13 (200, 1000, all) | The fixtures are unchanged since ddc3037a (`git diff` empty). A fresh grep for the UUID pattern over `frontend/src/features/graph/fixtures/` finds 0 hits. **Caveat (unchanged):** fixture ids are the first 12 hex characters of an unsalted SHA-256 of each real id. They cannot be reversed, but anyone holding a real id can confirm it is in the fixture. |
| OP-5 | pass | .dforge/ui-ux/constellation-real-data/op-5-code--mixed-before-after-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/op-5-code--worst-2000-before-after-1280x800-dark.png, .dforge/ui-ux/constellation-real-data/op-5-code--mixed-before-after-1920x1080-light.png, .dforge/ui-ux/constellation-real-data/op-5-code--worst-2000-before-after-1920x1080-light.png; tests `constellation-runner.test.ts` "A12: without roles the runner keeps today's ring placement", `constellation-real-data.acceptance.test.tsx` "A12: the roles a code graph gets are those of the unscored classification", `node-glow-program.test.ts` "…leaves the code canvas at CORE_K" (A23) | `git diff c55267df HEAD` is empty for `graph-3d-renderer.tsx`, `memory-graph-explorer.tsx` and `frontend/src/demo/`. See **OP-5 comparison** below the table. |

**UI-1 details:**
- **Live, dark, 1,000 memories:** a multi-coloured core of crisp, separate points with an irregular, lobed edge, sitting inside a soft purple glow.
- **Clumps:** small clumps of 2 to 6 points at varying distances (63 clumps at 1,000).
- **Halo:** faint, cluster-tinted points thinning outward.
- **Edges:** none cross the halo at rest (A20). On the boards the same arrangement holds at 200, 1,000 and all.

**UI-2 measurements:** pixels with every channel ≥ 250 at the fit view, dark theme.
- **Boards** (`scripts/white.py`, skipping Storybook's 24-pixel top bar):
  - HighEdges, Small200, Default1000, All and EntityLayer: 0 at both viewports.
  - Selected: 24 at 1280x800 and 53 at 1920x1080, all inside the label text "Memory 350" and "Memory 346" (1280), and "Memory 127", "Memory 350" and "Memory 161" (1920), located by bounding box. That is label ink, not glow.
- **EntityLayer:** was 173 and 101 at ddc3037a. With entities riding on the core outside FA2, and the memory canvas screen-blending, it is now 0 at both viewports. That holds both with the page's shared-only filter (e5cb25e0) and with every entity drawn (`board-entity-layer-all-1280x800-dark.png`, 0; and the c04859e0 captures in `prev-c04859e0/`, 0 at both viewports).
- **Live** (canvas area only, excluding the sidebar, the header and the chat button's white glyph): 0 in all ten dark captures (5 states × 2 viewports). The light theme is not measured: its background is itself ≥ 250.
- **What holds:** the core ≥ satellite ≥ halo brightness order. Zooming in restores full size and brightness (`ui-5-zoomed-*`). On All, the core reads as dense colour patches with no pixel near white; the previous proof's pale pink centre is gone.

**UI-5 details:**
- **Fit view:** sigma's label layer holds 0 drawn pixels before any hover, on the board (1280 dark, 1920 light) and on the live page (1280 dark, 1920 light).
- **Hover:** a pointer walk outward from the centre stops on the first node that draws on sigma's hover layer.
  - On the board it shows that node's label and ring.
  - On the live page it shows the label, ring and edges, and dims the rest.
  - In one live light run the label layer also held 789 pixels while hovering. A rerun on the same node drew 0. The cause is not verified; it was not reproduced.
- **Zoomed in** (three wheel steps): only hub labels show. The A10 test counts 20 labelled hubs on the 1,000 fixture once zoomed, against the 2% cap.
- **Selected board:** the selected label plus the adjacent memories' labels, by the pre-existing focus rule (tier `adjacent`).
- **Harness artefact:** the zoomed captures keep a hover ring on the node under the last wheel position, because the pointer left over Storybook's top bar, which sigma never reports as leaving the node.

**UX-5 details** (boards and live, both themes):
- **Default:** 1,000 memories.
- **All memories:** 4,759, with no twinkle (0.00% change) and no white pixels.
- **Small:** 200.
- **High Edges:** more clumps and more halo (see UX-2).
- **Entity layer:** diamonds with type-coloured borders, placed with their memories' roles (A4). Core-role entities ride among their linked core memories, and core memory positions do not move (A21).
  - With the page's default filter (shared entities only), on the board and live, the diamonds sit over part of the core and scatter through the clumps and halo, and core memory points stay visible.
  - With every entity drawn (`EntityLayerAll`, the page's "Shared" switch off), the diamonds cover most of the core and dominate the outer field.
- **Selected and hovered:** focus, ring, dimming and labels.
- **Light:** every state.
- **A18:** the boards and the live page agree, state by state, now that the EntityLayer board applies the page's shared-entity filter (`board-entity-layer-1280x800-dark.png` beside `live/live-entity-layer-1280x800-dark.png`). Each shows a lobed multi-coloured core, scattered clumps and a halo at 200, 1,000, all, Edges 0.8 and with the entity layer. Exact lobes and colours differ, since the live corpus is the fixture's source at another date and FA2 is not deterministic across loads.

**Differences from the reference (`graph.jpg`)** that remain on the live page, each inside what OP-1 allows ("exact positions and colours may differ"):
- **Colour placement:** each cluster's colour sits in its own lobe of the core, where the reference interleaves colours point by point. That is position and colour, which OP-1 allows to differ.
- **Core texture:** the core's points sit on a near-regular lattice (`spreadCore` spaces them at `CORE_GAP`). The reference's core is a looser scatter with mixed point sizes. UI-1 asks for "crisp, separate points", which this is.
- **Halo:** sparser and dimmer than the reference's, and the core takes a smaller share of the field. UI-1 and OP-1 ask for a "sparse" halo.
- **Clumps:** 2 to 6 points each, where the reference shows a few rings of 10 to 20. UI-1 asks for "small clumps".

These are recorded so the owner can judge the look on the live instance. None of them contradicts a contract clause.

**OP-5 comparison:** the before/after images put ddc3037a's capture on the left and c04859e0's on the right, and the same structure shows in all four pairs. The fix wave changed three files the code canvas shares:
- `constellation-runner.ts`: without roles, the runner still calls plain `fit` (A12).
- `node-glow-program.ts`: crisp sizing, the light-theme crisp cap and screen blending are gated on `memoryCanvas`; the code canvas keeps `densityStyle` and additive blending (A23).
- `constellation-layout.ts`: the legacy `placeOuterRing` the code canvas uses returns `clumpSpacing: CLUMP_R0`, the value used before.

Pixel differences (tolerance 8, below the top bar):

Both loads of c04859e0 are on disk: the first under `op5-load1/`, the second as the top-level `op-5-board-*` files.

| Board | c04859e0 vs ddc3037a | Two loads of c04859e0 |
|---|---|---|
| Code Mixed, dark | 3.42% | 2.19% |
| Code Worst2000, dark | 7.01% | 6.61% |
| Code Mixed, light | 0.92% | 0.72% |
| Code Worst2000, light | 5.22% | 4.44% |

The between-build differences are close to the load-to-load noise of the same build, where FA2 places core nodes differently each load. The synthetic memory board, which this branch is meant to change, differs by 4.21% (dark) and 3.36% (light). No code or memory board has a white pixel.

**Keyboard walk** (live page; 1280x800 dark and 1920x1080 light, `scripts/keys.mjs`, `scripts/keys2.mjs`):
- **Order:** Tab moves through the skip link, the sidebar, the header, "Filters", then "Toggle graph settings", every stop with a visible focus ring.
- **Panel:** Enter opens the settings panel. Tab then visits, in order: Node limit, All nodes, 2D, Colour, Regions, Size, Entity layer, the Edges slider (ArrowRight moves it by 0.05), Min size, selection colour, and Dim unrelated.
- **Escape:** from inside the panel it closes the panel and returns focus to "Toggle graph settings". Enter reopens it.
- **Panel closed:** Tab after the trigger reaches "Reset graph view" and "Show details panel".
- The canvas's own keys (+/− zoom, arrows pan, 0 fits, Escape clears selection) are proven by the A18 tests.

**Adjacent findings** (pre-existing; no file involved changed on this branch):
- **Focus enters a hidden panel.** With the filter panel collapsed, Tab after "Show details panel" lands on three controls the operator cannot see: the content filter input, the "Any tag" button and a tag checkbox. Each measures 0 px high at x = 281, y = 112 (`scripts/keys3.mjs`).
- **Panel exit drops focus.** Tabbing past the last control in the open settings panel ("Dim unrelated nodes, percent") moves focus to `<body>`, then to the top of the page, not back to the toolbar. The panel appears to be rendered outside the toolbar's DOM order.

## Automated checks

- **axe** (axe-core 4.11.4):
  - Live page, 1280x800 dark: 1 moderate (`region`, 17 nodes), 0 serious, 0 critical.
  - RealCorpus Default1000 board: 1 moderate (`region`, 9 nodes, the bare Storybook iframe has no landmarks).
- **Page errors:** 0 across the 24 board captures, the zoom and hover walk, the twinkle pairs, the code and memory boards (two loads), the axe run, the 20 live state captures, the live hover probes and the keyboard walks.
- **Console errors:** 0 on the live page (every state capture recorded console messages) and 0 across the 24 board captures. The zoom, twinkle and code-board scripts recorded page errors only.
- **Writes attempted against production:** 0. Every non-GET request was routed to abort, and none occurred.
- **Horizontal overflow:** none, on every board and every live state, at both viewports and in both themes.
- **Tests:** all 41 graph test files pass at c04859e0, 473 tests (`npx vitest run src/features/graph`). At e5cb25e0 the graph and memory-graph tests pass, 506 tests, `tsc -b` is clean, and the plan's integration check (typecheck, the full frontend suite, build) passes through `suite-run`.
- **Spec and code:** Architecture §7 and `node-glow-program.ts` both use the densest 2% for `localSpacing` (aligned in c04859e0).
