# UI proof: memory graph round islands, thin edges, selection chrome

**Contract:** touch
**Fingerprint:** 570f7c4638eedbd5
**Judge:** ship 570f7c4638eedbd5 — docs/dforge/ui-ux/proofs/2026-11-19-graph-round-islands.judge.md
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

## Delta

**UI/UX depth:** touch — owner request 2026-11-19 on the memory graph: islands "grouped in cluster and isolated from another cluster", "make them likely to around a circle, also reduce the width of edges, and fix the selected node style"

- **UI-1** — The islands pack into one round disc: bounding box 0.8 to 1.25 times as wide as tall, with no empty centre.
- **UI-2** — Islands sit close: their discs cover at least 58% of the disc enclosing them, and no two come closer than the sum of their radii.
- **UX-1** — Islands sharing edges touch, and sit closer than unlinked islands do on average.
- **UI-3** — Edges are thinner at rest, on hover and on selection (similarity 1.6, relation 1.2, membership 0.8, hover 2.4, selected 3.2; before 3.4, 2.4, 1.6, 4.5, 6.5), with the order similarity > relation > membership and rest < hover < selected kept.
- **UI-4** — A selected memory keeps its own dot: no shape is filled round the node, a 2 px accent ring with a soft glow sits 2.5 px off the dot as drawn (not its unscaled size), and the label sits on a rounded tag tinted 24% with the accent, outlined in it, with text at 4.5:1 or better.
- **UI-5** — Hover stays lighter than selection: a 1 px ring with no glow, and the plate in the page colour with an accent outline.
- **OP-1** — Proven on the live page with the cloned corpus at 1280x800 and 1920x1080, light and dark, with 0 console or page errors and 0 attempted writes.
- **OP-2** — `layoutIslands` still takes 50 ms or less at 20,000 memories and 110,000 edges (median of 5).

## Decisions

Two rulings are mine, made under the owner's complaint that islands were "isolated from another cluster". Neither was put to the owner, and both are reported for review:

- **Collision radius 1.15·(rₐ+r_b) → 1.0·(rₐ+r_b)** (A2, `ISLAND_REACH`). At 1.15, the bodies of two neighbours (85% of members inside 0.8r) kept about 0.8r of open space between them, which is the isolation complained of. At 1.0 a gap of about 0.4r remains between bodies, and only the tapered stragglers between 1.0r and 1.15r can meet a neighbour's.
- **A3 restated** from "closer than every unlinked island" to "touches, and sits closer than the unlinked islands on average". The stricter form cannot hold in the compact disc the owner asked for, where unlinked neighbours also touch (measured 138.7 against 138.0 at a touching distance of 139).

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .dforge/ui-ux/graph-round-islands/final-default-1920x1080-dark.png, .dforge/ui-ux/graph-round-islands/final-default-1920x1080-light.png, .dforge/ui-ux/graph-round-islands/final-default-1280x800-dark.png, .dforge/ui-ux/graph-round-islands/final-default-1280x800-light.png, .dforge/ui-ux/graph-round-islands/before-default-1920x1080-dark.png; test `cluster-layout.test.ts` "UX-1: on … the islands pack into a round, compact disc" (200, 1,000, full, 60 equal islands) | Bounding aspect 1.07, 1.01, 1.09, 0.98. The live captures show one round clump with islands at the centre; the before capture is the wide rectangle with wide channels. A first build left the centre empty (the first seed slot sat at 0.3 of the disc radius and a hard rim squeezed small sets into a ring); the first island now takes the centre and the rim is gone. |
| UI-2 | pass | same captures; tests "UX-1: … round, compact disc" (disc fill) and "A2: on the … fixture no two islands come closer than their summed radii", "A2: a loose island and many small islands still never overlap" | Disc fill 0.65, 0.75, 0.67, 0.74 (floor 0.58). Collisions moved from 1.15·(rₐ+r_b) to 1.0·(rₐ+r_b): 85% of an island's members sit inside 0.8r, so the bodies still keep a clear gap while the tapered stragglers between 1.0r and 1.15r may meet a neighbour's. |
| UX-1 | pass | test "A3: an island sharing many edges with another touches it, closer than the islands sharing none on average" | Twelve equal islands, 0 and 7 linked. Restated from "closer than every unlinked island": in a compact disc unlinked neighbours touch too (five islands gave the linked and an unlinked pair 138.7 and 138.0 against a touching distance of 139). The new A3 and UX-1 tests fail on the old layout code. |
| UI-3 | pass | .dforge/ui-ux/graph-round-islands/final-selected-1920x1080-dark.png, .dforge/ui-ux/graph-round-islands/final-selected-1920x1080-light.png, .dforge/ui-ux/graph-round-islands/before-selected-1920x1080-dark.png; tests `memory-edge-width.test.ts` "draws thin edges: similarity 1.6, relation 1.2, membership 0.8, hover 2.4, selected 3.2", "keeps similarity over relation over membership at rest", "draws a %s edge heavier on hover and heavier still on selection" | The widths moved out of the renderer into `lib/memory-edge-width.ts` (`restEdgeSize`, `memoryEdgeSize`), which the edge reducer now calls, so the test pins the values the canvas draws. The captures only illustrate it: the before and after frames select different nodes. On them, selected edges are hairlines of about 1.5 px against about 3 px before. A first pass at 2.4 for selected edges was too faint on the live page and was raised to 3.2. |
| UI-4 | pass | .dforge/ui-ux/graph-round-islands/final-selected-zoom-1920x1080-dark.png, .dforge/ui-ux/graph-round-islands/final-selected-zoom-1920x1080-light.png, .dforge/ui-ux/graph-round-islands/before-sel-zoom.png; tests `node-hover.test.ts` "fills no shape round the node under focus", "keeps the … label readable on its own plate" (4 cases), "picks the text colour by contrast, not by theme polarity", "puts the resting label at the same offset as the plated one" | Before: the plate was filled round the node as well as behind the label, at the node's unscaled size, so the selection showed as a solid accent disc about 30 px wide with a full-accent bar. The glow program shrinks dense roles' discs on the GPU; `glowDiscScale` mirrors that scale, so ring and labels are placed off the dot as drawn. The fill test fails on the old drawer. Entity diamonds share the same plate helper. |
| UI-5 | pass | .dforge/ui-ux/graph-round-islands/final-hover-zoom-1920x1080-dark.png, .dforge/ui-ux/graph-round-islands/final-hover-zoom-1920x1080-light.png, .dforge/ui-ux/graph-round-islands/final-hover-zoom-1280x800-dark.png, .dforge/ui-ux/graph-round-islands/final-hover-zoom-1280x800-light.png, .dforge/ui-ux/graph-round-islands/before-hover-crop.png; tests "makes hover lighter than focus under accent/inverted", "fills no shape round the node under hover" | Before: hover filled a page-coloured disc of about 17 px radius round a 3 px dot. |
| OP-1 | pass | .dforge/ui-ux/graph-round-islands/final-run-1920x1080-dark.json, .dforge/ui-ux/graph-round-islands/final-run-1920x1080-light.json, .dforge/ui-ux/graph-round-islands/final-run-1280x800-dark.json, .dforge/ui-ux/graph-round-islands/final-run-1280x800-light.json; script .dforge/ui-ux/graph-round-islands/scripts/sel.mjs | Each run: `errors: []`, `blocked: 0`, `overflow: false`. |
| OP-2 | pass | test `cluster-layout.test.ts` "A12: layoutIslands takes 50 ms or less …" | 26.8, 27.3, 27.7, 28.8, 37.8 ms (median 27.7) at load average 33. An earlier run at load 14 missed the bar at a 50.1 ms median, and so did unchanged master in the same window (51.5 ms), so that miss was host contention. |

**Harness:** Vite dev on :3636 running this working tree and proxying `/api` to the production backend on :8000, which holds the cloned 192.168.0.199 corpus (1,000 memories in the default view). A session was minted inside the production container (a JWT mint, no write). Every request other than GET, HEAD and OPTIONS was routed to abort; none was attempted. Light runs answered `GET /api/v1/config/theme` with the stored settings plus `mode: "light"`. Chromium on SwiftShader, 20 s after the canvas appears; the hover target is found by walking the pointer outward from the canvas centre until the hover layer draws, then pressed to select.

## Automated checks

- console and page errors: 0 in all four live runs.
- attempted writes: 0.
- horizontal overflow: none at either viewport.
- `npm test`: 304 files, 2,437 tests, all passed; `npm run typecheck` clean.
- `ui-lint` on the five changed source files: no findings.
- eslint on the changed files: 5 errors and 1 warning, the same six on master (refs read during render in `graph-2d-renderer.tsx`, `no-useless-assignment` in `node-diamond-program.ts`); not introduced here.

## Not proven here

- The deployed image: these captures are of Vite dev against the live backend. Nothing is committed or deployed yet.
- The knowledge graph canvas shares the new plate drawer (`drawThemedDiscNodeHover`); its selection was not captured.
- Keyboard selection was not walked.
- Frame rate: not measured (SwiftShader; profile decision 2026-11-18).
