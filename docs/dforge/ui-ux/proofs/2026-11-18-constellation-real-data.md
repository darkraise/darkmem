# UI proof: Constellation real data

**Contract:** docs/dforge/specs/2026-11-18-constellation-real-data-design.md
**Fingerprint:** 5ed45632331900a5
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

Proven at c46e5c39 (branch `auto/constellation-real-data-2`, base c55267df) on 2026-11-19.

Harness, per the profile: Storybook on :6006, driven by Playwright MCP. The six `Graph/Constellation/RealCorpus` boards (Default1000, All, Small200, HighEdges, EntityLayer, Selected) were captured at both viewports in both themes, 20 s after load (30 s for All). The theme was set through the app's ThemeProvider key `localStorage.mode`, as in the previous proof. The code boards and the synthetic `Graph/Constellation/Memory` board were captured for OP-5 and compared with the previous proof's captures of the same boards, taken at e457bb75. Evidence lives under `.playwright-mcp/constellation-real-data/`, and the walk scripts under `.playwright-mcp/constellation-real-data/scripts/`. Both directories are git-ignored and stay local.

**The live page reflects the deployed build, not this branch.** Production (`darkmem-prod-darkmem-1`, image tag `6042f0d7`) runs a commit that predates this branch's base c55267df. It carries none of this branch's changes. The page was opened read-only (signed in with a minted session; every non-GET request to :8000 was routed to abort, and none was attempted), and `live-default-*-dark.png` record what it shows: the old arrangement, zoomed in, with labels on most nodes. Nothing was deployed: deploying is outside this task. The branch's behaviour is proven on the boards. The live-only items (OP-1, OP-2's live half, acceptance A15–A17) are marked **fail, not yet deployed**. The live captures contain real memory text, so they stay local and are not quoted here. Live captures were taken in dark only: my `localStorage.mode` write did not switch the live app's theme, so the two captures labelled light were dark, and I deleted them.

Role split on the fixtures, from `classifyWithCut` (core / memories in clumps (number of clumps) / halo):
- 200: 87 / 43 (15) / 70.
- 1,000: 445 / 173 (63) / 382.
- All 4,759: 2,115 / 716 (271) / 1,928.
- 1,000 at Edges 0.8: 221 / 202 (78) / 577.

Storybook's preview renders a "Not Found" line at top left of every story. This is the preview's own TanStack router: harness noise, not product.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .playwright-mcp/constellation-real-data/board-default-1000-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-default-1000-1920x1080-dark.png, .playwright-mcp/constellation-real-data/ui-1-default-1000-outer-crop-1920x1080-dark.png, .playwright-mcp/constellation-real-data/board-small-200-1280x800-dark.png; tests `constellation-layout.test.ts` "A5: clumps never overlap, sit beyond 1.15R plus their radius, stay within 2R and spread around the core", "A6: the halo fills 1.15R to its outer radius, thins outward…", "A7: fitCore puts the 90th percentile at 0.85R and softens the tail inside R" | Board, dark theme. The core is multi-coloured, with a soft, irregular edge of community lobes. Small clumps sit at varying distances: the outer crop shows tight specks of 2–3 points, 63 of them on the 1,000 board. Around them is a field of small, faint, cluster-tinted halo points. **Differences from `graph.jpg`:** <br>- The core is drawn as overlapping glowing discs grouped by colour, where the reference shows crisp, interleaved points.<br>- The clumps average 2.7 memories, so they read as specks, not the reference's visible rings.<br>- Faint rest edges web across the halo, and the reference has none. |
| UI-2 | fail | .playwright-mcp/constellation-real-data/ui-2-high-edges-core-crop-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-high-edges-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-small-200-1280x800-dark.png, .playwright-mcp/constellation-real-data/ui-2-default-1000-core-crop-1920x1080-dark.png, .playwright-mcp/constellation-real-data/ui-5-zoomed-1280x800-dark.png | At the fit view, overlapping core discs still sum to white. See **UI-2 measurements** below the table. |
| UI-3 | pass | .playwright-mcp/constellation-real-data/board-default-1000-1920x1080-dark.png, .playwright-mcp/constellation-real-data/board-high-edges-1920x1080-light.png, .playwright-mcp/constellation-real-data/op-5-code-mixed-before-after-1280x800-dark.png, .playwright-mcp/constellation-real-data/op-5-code-worst-2000-before-after-1280x800-dark.png; tests `constellation-graphs.acceptance.test.tsx` "A9: halo nodes take one small size whatever their importance" | Halo points are one small size on both canvases. The runner sizes the halo at `min(HALO_SIZE, 0.4 × median core size)`, as spec Architecture §6 allows. The code canvas's halo shrank with it, which UI-3 and OP-5 permit. Architecture §6's closing sentence, "The code canvas keeps its sizes", contradicts that. The spec is inconsistent on this point, and the contract rows were followed. |
| UI-4 | pass | .playwright-mcp/constellation-real-data/board-default-1000-1280x800-light.png, .playwright-mcp/constellation-real-data/board-default-1000-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-all-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-high-edges-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-small-200-1280x800-light.png | Light theme: crisp, saturated points with no glow and no additive blending. Halo points are small and drawn at brightness 0.55: the light branch of the shader in `node-glow-program.ts` sets it, and twinkle modulates it by ±30% as shipped. **Observation:** at the 1,000 and all-memories fit views in light, the rest-edge mesh is dense and grey and competes with the points. That edge treatment is shipped and outside this contract. |
| UI-5 | pass | .playwright-mcp/constellation-real-data/board-default-1000-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-default-1000-1920x1080-light.png, .playwright-mcp/constellation-real-data/ui-5-hover-1280x800-dark.png, .playwright-mcp/constellation-real-data/ui-5-hover-1920x1080-light.png, .playwright-mcp/constellation-real-data/ui-5-zoomed-1280x800-dark.png, .playwright-mcp/constellation-real-data/ui-5-zoomed-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-selected-1280x800-dark.png; tests `constellation-graphs.acceptance.test.tsx` "A10: at the fit view with nothing hovered or selected, no memory carries a label, hubs included", `hubs.test.ts` "A10: takes the top 2%…", "A10: the 1,000-memory fixture has at most 20 hubs" | See **UI-5 details** below the table. |
| UX-1 | pass | .playwright-mcp/constellation-real-data/board-small-200-1920x1080-dark.png, .playwright-mcp/constellation-real-data/board-all-1280x800-dark.png; tests `real-corpus-roles.test.ts` "A2: the 200 fixture splits about 45% core, then clumps and halo" (and the 1000 and all variants), `constellation-layout.test.ts` "A1: returns the lowest score that keeps 8+ components at or below 45% of nodes" | Core share: 43.5% at 200, 44.5% at 1,000 and 44.4% at 4,759. The rest falls into clumps and halo (role split in the header). |
| UX-2 | pass | .playwright-mcp/constellation-real-data/board-high-edges-1280x800-dark.png; tests `real-corpus-roles.test.ts` "A3: raising Edges from 0.5 to 0.8 never pulls a memory inward while an 8+ core remains", `constellation-graphs.acceptance.test.tsx` "A12: raising the Edges threshold so a memory loses its last edge makes it halo on the next build" | Raising Edges to 0.8 on the 1,000 board shrinks the core from 445 to 221 memories. Clumps rise from 63 to 78 and halo from 382 to 577. |
| UX-3 | pass | tests `graph-prefs.test.ts` "A11: defaults to 1,000 memories", "A11: a stored 200 from before version 1 loads as 1,000, and any other stored value is kept" | Proven by test. The live page cannot show it until this branch is deployed. |
| UX-4 | pass | .playwright-mcp/constellation-real-data/ux-4-twinkle-default-1000-a-1280x800-dark.png + -b, .playwright-mcp/constellation-real-data/ux-4-twinkle-all-a-1280x800-dark.png + -b, .playwright-mcp/constellation-real-data/ui-5-hover-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-selected-1920x1080-light.png; tests `constellation-runner.test.ts` "places satellites and the halo before the run and never moves them", `ambient-motion.test.ts` (motionAllowed table, "never starts under reduced motion", "stops when the tab is hidden"), `graph-2d-renderer.test.tsx` "says so, still reports ready, and starts no motion" | Twinkle: of two frames taken 1.5 s apart at rest, 0.36% of pixels change on the 1,000 board and 0% on the 4,759 board, which is over the 2,000-node motion cap. Hover and selection work on real data. The WebGL-unavailable state is proven by test. |
| UX-5 | pass | .playwright-mcp/constellation-real-data/board-default-1000-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-all-1920x1080-dark.png, .playwright-mcp/constellation-real-data/board-small-200-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-high-edges-1920x1080-dark.png, .playwright-mcp/constellation-real-data/board-entity-layer-1280x800-dark.png, .playwright-mcp/constellation-real-data/board-entity-layer-1920x1080-light.png, .playwright-mcp/constellation-real-data/board-selected-1280x800-dark.png, .playwright-mcp/constellation-real-data/ui-5-hover-1920x1080-dark.png; test `constellation-graphs.acceptance.test.tsx` "A4: with the entity layer on, an entity takes its memories' highest role and memory roles do not change" | See **UX-5 details** below the table. |
| OP-1 | fail | .playwright-mcp/constellation-real-data/live-default-1280x800-dark.png, .playwright-mcp/constellation-real-data/live-default-1920x1080-dark.png | Not yet deployed. The live page runs image `6042f0d7`, which predates this branch. It shows the old default view: four large colour wedges, zoomed in, with labels on most nodes. This does not read as `graph.jpg`. The branch's default view is proven on the board (UI-1, with UI-2's saturation failure). A15 cannot be shown until the branch is deployed. |
| OP-2 | fail | .playwright-mcp/constellation-real-data/board-default-1000-1280x800-light.png, .playwright-mcp/constellation-real-data/board-default-1000-1920x1080-dark.png, .playwright-mcp/constellation-real-data/live-default-1920x1080-dark.png | The boards half is met: all six boards in all four viewport/theme pairs (24 captures). The live half is not: the live page does not run this branch (OP-1), and no light-theme live capture was made. A16 and A17 cannot be shown until the branch is deployed. |
| OP-3 | pass | test `constellation-layout.test.ts` "A14: roleCut + classify + placeOuter take 50 ms or less for 20,000 nodes and 110,000 scored edges" | Passed 3 of 3 runs with the host quiet. It failed 3 of 3 (52.7, 57.8 and 60.4 ms) while my headless Chromium was rendering the 1,000 board through SwiftShader, which used about 6 cores. The bar has little headroom on a loaded host. |
| OP-4 | pass | tests `real-corpus-fixture.test.ts` "A13: the 200 fixture carries no content, tags, project, real names or UUIDs" (and the 1000 and all variants) | A grep of the committed fixtures for real project and memory names seen on the live page, and for the UUID pattern, found 0 hits. Memory content is the placeholder "Memory N" and entity names are "Entity N". **Caveat:** fixture ids are the first 12 hex characters of an unsalted SHA-256 of each real id (`frontend/scripts/anonymise-graph-fixture.mjs`). They cannot be reversed, but anyone holding a real id can confirm it is in the fixture. |
| OP-5 | pass | .playwright-mcp/constellation-real-data/op-5-code-mixed-before-after-1280x800-dark.png, .playwright-mcp/constellation-real-data/op-5-code-worst-2000-before-after-1280x800-dark.png, .playwright-mcp/constellation-real-data/op-5-code-mixed-before-after-1920x1080-light.png, .playwright-mcp/constellation-real-data/op-5-board-memory--mixed-1280x800-dark.png | `git diff c55267df HEAD` is empty for `graph-3d-renderer.tsx`, `memory-graph-explorer.tsx` and `frontend/src/demo/`. The code canvas's one changed line passes the halo radii to `trackDensityGain`. The before/after pairs, compared with the previous proof's boards: the code halo is smaller and dimmer, and the core, clumps and ring are unchanged. Changed pixels: 2.55% on Mixed dark, 8.02% on Worst2000 dark (the halo field) and 0.65% on Mixed light. A19 is met on the boards. |

**UI-2 measurements:** pixels with every channel ≥ 250 at the fit view, excluding Storybook's top bar.

| Board | 1280x800 | 1920x1080 |
|---|---|---|
| HighEdges (Edges 0.8) | 2,226 | 703 |
| Small200 | 257 | 0 |
| Default1000 | 22 | 89 |
| All | 0 | 0 |

- **HighEdges:** the enlarged crop shows white centres in the cyan, magenta and pink lobes. Spec Architecture §7 promises "no part of the canvas sums to white at the fit view".
- **Small200:** at 1280x800, one pink lobe whitens.
- **Default1000:** isolated near-white specks only.
- **All:** no white.
- **What holds:** the core ≥ satellite ≥ halo brightness order, and zooming in restores full size and brightness (`ui-5-zoomed-*`).
- **Inference, not verified:** the gain is computed from mean coverage over the whole role. With Edges at 0.8 the core breaks into small, dense lobes, so the mean understates the overlap inside them.

**UI-5 details:**
- **Fit view with nothing selected:** no labels in any theme or viewport.
- **Hover:** shows the hovered node's label and ring, and nothing else.
- **Zoomed in:** three wheel steps show the hub labels only, about a dozen in frame, against the 20-hub cap.
- **Selected board:** shows the selected label and one adjacent label. Adjacent labels come from the pre-existing focus rule (`labelVisible`, tier `adjacent`).
- **Harness artefact:** in the zoomed captures, a hover ring remains on the node under the last wheel position. The pointer left over Storybook's top bar, which sigma never reports as leaving the node.

**UX-5 details:**
- **Default:** 1,000 memories.
- **All memories:** 4,759, with no twinkle (0% change) and no white pixels.
- **Small:** 200.
- **High Edges:** a smaller core, with more clumps and more halo.
- **Entity layer:** diamonds with type-coloured borders. At the fit view they dominate the frame, since most entities are halo- or clump-role. Their placement by role is proven by A4.
- **Selected and hovered:** focus, ring, dimming and label.
- **Light:** every state captured.
- **Saturation:** the white spots on Small200 and HighEdges are recorded under UI-2.
- **A18:** the boards' agreement with the live page cannot be shown until the branch is deployed. The boards agree with one another, and with the role split in the header.

## Automated checks

- **axe** (axe-core 4.x, RealCorpus Default1000 at 1280x800): 1 moderate (`region`, 9 nodes), raised because the bare Storybook iframe has no landmarks. 0 serious, 0 critical.
- **Page errors:** 0 across all 24 RealCorpus board captures, the zoom and hover walk (4 pairs), the 6 code and memory board captures, the twinkle pairs and the live page.
- **Console errors:** 0. The warnings are Storybook's TanStack `notFoundError` (the "Not Found" line) and React DevTools info.
- **Horizontal overflow:** none, on every RealCorpus board at both viewports.
- **Tests:** 109 tests across the eight branch graph files pass, plus the renderer, motion and runner files (24). The exception is A14 under load (OP-3).
