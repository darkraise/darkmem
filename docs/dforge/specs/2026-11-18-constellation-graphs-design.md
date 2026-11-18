# Constellation graphs — design

**Execution strategy:** sequential — inline execution
**Depth:** light — approach,intricate

The 2D memory graph and the code graph take on the arrangement and treatment of
the owner's reference image (`graph.jpg`, repo root, untracked): a dense,
colourful core, small tight clumps around it, and a wide sparse halo of faint
points, glowing on a dark nebula, with near-invisible edges. The arrangement is
the primary goal; the glow is how it is drawn.

## Decisions

- **Process:** full dforge flow. Owner: "Full dforge flow (Recommended)".
- **Which memory view:** owner: "Only the 2D view". The 3D view
  (`graph-3d-renderer.tsx`) is unchanged.
- **Elements taken from the reference:** owner: "Core + orbital halo layout,
  Nebula backdrop, Ambient motion, The arrangement of nodes in picture is the
  core and primary thing I want to adopt". No perspective floor grid, no
  "READY" label.
- **Code graph layouts:** owner: "Add as new default layout and remove all
  other layout, we will keep the graph simple". The code graph has one layout
  and no layout control.
- **Light theme:** owner: "Light variant". Both canvases follow the app theme;
  the light theme gets saturated points without additive glow on a pale
  backdrop with a faint tinted wash.
- **2D memory layout controls:** owner: "Remove layout sliders". Tightness and
  the 2D Spacing row go; Regions (hulls) stays; Spacing stays for the 3D view.
- **UI profile:** owner: "Yes, as drafted (Recommended)" —
  `docs/dforge/ui-ux/profile.md`.
- **State boards:** owner: "Yes, as Storybook stories (Recommended)".
- **Layout approach:** owner: "Hybrid: force core + placed rest
  (Recommended)" — ForceAtlas2 over the core only; satellites and halo placed
  directly.
- **Code graph renderer:** owner: "Move to WebGL (sigma.js)". The live code
  graph is an SVG (`features/code/components/code-canvas.tsx`) used by both
  `CodeGraphTab` (demo) and `RealCodeGraphView`; it is replaced by a sigma.js
  canvas sharing the memory graph's node program, backdrop and layout.
- **Ambient motion has no control** (my call; see A16): it follows the
  operating system's reduced-motion setting. The demo host's Play/Pause button,
  which drove the SVG drift animation, goes with the layout switch.
- **Not touched:** the demo-mode memory explorer
  (`memory-graph-explorer.tsx`, SVG, uses `demo/explore.ts`'s `layoutGraph`),
  which keeps its three layouts (see A22); and the sigma
  `features/graph/components/code-graph-renderer.tsx`, which nothing imports.
  It is reported as dead code, not deleted here.

- **Spec review (2026-11-18):** A16, A17, A18, A22 and A24 confirmed by the
  owner ("Right" to each); early CI declined ("No early run (Recommended)").

Early CI: none

Finish: merge

Worktree: in-place

## Architecture

Six units, each testable alone.

1. **`features/graph/lib/constellation-layout.ts`** (pure, no DOM, no
   graphology). `classify(nodeIds, edges)` returns each node's role and, for
   satellites, its component. `placeOuter(classification, coreRadius, ids)`
   returns positions for satellite and halo nodes. `fitCore(positions,
   targetRadius)` scales core positions uniformly about their centroid.
   - **Components** are found by union-find over the drawn edges (self-loops
     and edges to absent nodes ignored; direction ignored).
   - **Core**: every component of at least `CORE_MIN = 8` nodes. With none,
     the largest component of at least 2 nodes is the core.
   - **Satellites**: every other component of 2 or more nodes. Each is packed
     as a sunflower clump (node *i*, sorted by degree then id, at radius
     `r0·√i` and angle `i·golden angle`). Clumps sit on rings starting just
     outside the core (`1.15·R`), largest first, filled by arc length, a new
     ring outward when one is full.
   - **Halo**: every isolated node. Angle and radius come from two hashes of
     the node id (`seededUnit`, already in `code-graph-theme.ts`), radius drawn
     for uniform area density over an annulus from the outermost satellite
     ring plus a gap to at least `2.6·R`, widened so density stays sparse as
     the halo grows. A halo node's position depends only on its id and the two
     radii, so it does not jump when other nodes come and go.
   - **No core** (no edges at all): the halo fills a full disc. **No halo**:
     no outer ring.
   - `R`, the core's target radius, is `k·√(core node count)` in graph units.
     The halo's outer radius is `max(2.6·R, inner + c·√(halo count))`. `k`,
     `c` and `CORE_MIN` are named constants in this module, set in the
     plan's first task against the real graph (see Riskiest assumption).
2. **`features/graph/lib/constellation-runner.ts`**. Binds the layout to a
   rendered graphology graph. It builds a core-only layout graph, runs the
   existing ForceAtlas2 worker (`graphology-layout-forceatlas2/worker`) on it
   for the scale tier's `layoutMs`, and on each animation frame copies core
   positions into the rendered graph through `fitCore`, so the core never
   crosses into the satellite ring. Satellites and halo are placed once, at
   build. It exposes `start`, `stop`, `isRunning` and an `onStop` callback.
   Both renderers use it; the memory renderer's inline FA2 code goes.
3. **`features/graph/lib/node-glow-program.ts`**: an instanced sigma
   `NodeProgram`. Per node it reads position, size, colour, a `brightness`
   (core 1.0, satellite 0.8, halo 0.45) and a `phase` (hash of the id). The
   quad is three times the node's radius: a solid core disc with a soft edge
   plus a Gaussian falloff. In the dark theme its normal pass draws with
   additive blending (`gl.ONE, gl.ONE`) and restores sigma's
   `gl.ONE, gl.ONE_MINUS_SRC_ALPHA` afterwards. Its picking pass keeps
   sigma's blending and answers only inside the core disc. In the light theme
   it draws a crisp disc with a soft 1px edge and no glow, and halo nodes at
   55% opacity. Uniform `u_time` drives the twinkle (unit 5).
4. **`features/graph/lib/graph-backdrop.ts`**: a 2D canvas layer under
   sigma's (sigma's own background becomes transparent). It paints the
   `--graph-canvas` colour, then a radial gradient of `--graph-nebula`
   centred on the core's centroid, with a radius of 2.2× the core's on-screen
   radius. It is repainted on the camera's `updated` event, so the glow pans
   and zooms with the graph.
5. **`features/graph/lib/ambient-motion.ts`**: a frame loop that advances
   `u_time` and calls `sigma.scheduleRender()` (redraw only, no reducer pass)
   at most 30 times a second. It runs only while all of these hold:
   `prefers-reduced-motion` is not `reduce`, the graph has fewer than 2,000
   nodes (the small and medium tiers of `graph-scale.ts`), and the document is
   visible. Halo brightness varies ±30% with a per-node period of 3–7 s.
   Positions never move.
6. **`features/code/components/code-glow-canvas.tsx`**: a sigma canvas taking
   `CodeCanvas`'s props minus `layout` and `playing`. It keeps colour by kind
   or community (the `--chart-N` ramp resolved through `resolveGraphTokens`),
   dimming for `visibleIds` and `highlightCommunity`, removal for
   `hiddenKinds`, and the selection, blast and process rings, drawn on an
   overlay canvas as the memory renderer draws hulls. Labels show for
   selected, blast and process nodes as today, plus hubs (degree ≥ the memory
   renderer's `HUB_DEGREE`) once the camera ratio is below its
   `LABEL_ZOOM_RATIO`. Both
   hosts swap `CodeCanvas` for it and drop their Layout and Play/Pause
   controls. `code-canvas.tsx` keeps only `chartVar` and the canvas size
   constants the hosts still import.

**Theme tokens.** `--graph-canvas` and `--graph-nebula`, with light and dark
values in `frontend/src/styles/globals.css`, read by `resolveGraphTokens`
into `GraphThemeTokens`. Dark: near-black canvas and a violet nebula. Light: a
pale paper canvas and a faint lavender wash.

**Memory 2D renderer changes** (`graph-2d-renderer.tsx`). Memory nodes move
from `NodeCircleProgram` to the glow program; entities keep the diamond
program. FA2 goes through the runner, and component analysis counts every
drawn edge, membership edges included. At rest, edges draw at 8% (dark) or
12% (light) of their colour's opacity; `edgeEmphasis` still lifts the
selected or hovered neighbourhood. The backdrop and motion are attached, and
the `spacing` and `clusterTightness` props are removed. The page and toolbar
drop the Tightness row and show Spacing only in 3D mode.

**Data flow.** Data and filters → graphology graph (rendered) →
`classify` → core layout graph to the FA2 worker; `placeOuter` writes the
satellites and the halo → each frame, the runner mirrors fitted core
positions → sigma draws the backdrop layer, edges, glow nodes, diamonds, then
the overlay. A rebuild after a filter change keeps the existing
`positionsRef` seeding, so core nodes start where they were.

**Error handling.** If sigma cannot get a WebGL context (it throws at
construction), the canvas area shows "The graph needs WebGL, which this
browser has turned off." The code explorer and the memory toolbar stay usable.
Losing the worker leaves the core where it stopped, with no error state.
Today the memory 2D renderer has no WebGL failure state either; both canvases
gain this one.

## UI/UX contract

**UI/UX depth:** feature — two existing graph canvases change their layout and rendering

### UI

- **UI-1** — Canvas surface, both graphs: `--graph-canvas` background with a
  `--graph-nebula` radial glow centred on the core that pans and zooms with
  the graph; dark near-black and violet, light pale paper and faint lavender.
  Board: Storybook `Graph/Constellation/Memory` and `Graph/Constellation/Code`.
- **UI-2** — Nodes, both graphs: glow program. In the dark theme, a solid disc
  with a soft additive glow, where overlapping glows brighten. Role sets
  brightness: core 1.0, satellite 0.8, halo 0.45. Size follows the existing
  size rules. In the light theme, a crisp saturated disc with no glow, and
  halo nodes at 55% opacity.
- **UI-3** — Edges at rest at 8% (dark) or 12% (light) of their colour's
  opacity. The selected or hovered node's neighbourhood is emphasised as
  today.
- **UI-4** — Memory toolbar: in 2D mode there is no Tightness or Spacing row.
  In 3D mode Spacing remains. Every other row is unchanged.
- **UI-5** — Code canvas chrome: selection ring in `--primary`, blast ring
  dashed in `--destructive-solid`, process ring dashed in `--foreground`, as
  the SVG drew them. Labels in the mono font with a canvas-coloured halo.
- **UI-6** — Code hosts (`CodeGraphTab`, `RealCodeGraphView`): no Layout
  control and no Play/Pause control. Colour by, the legend and the counters
  stay.
- **UI-7** — Memory entity layer: entities keep their diamond shape and
  type-coloured border, and take core or satellite roles by component like
  memories.

### UX

- **UX-1** — Arrangement, both graphs: core, satellite and halo exactly as
  Architecture §1 defines them. Board states: one big component, all orphans,
  no orphans, many satellites, mixed.
- **UX-2** — Settling: satellites and halo are in place on the first frame;
  only the core animates, for the tier's `layoutMs`, and it never overlaps
  the satellite ring. After a filter change, nodes still drawn start where
  they were.
- **UX-3** — Coupling: raising the memory graph's Edges threshold moves
  memories that lose every edge into the halo. Lowering it pulls them into
  satellites or the core.
- **UX-4** — Ambient motion: halo twinkle as in Architecture §5. It is
  absent under reduced motion, at 2,000 nodes or more, and while the tab is
  hidden. Positions never move.
- **UX-5** — State matrix, memory 2D canvas:

  | State | Shows |
  |---|---|
  | loading, first | existing skeleton |
  | settling | core animating, satellites and halo still |
  | settled | the arrangement at rest, twinkle if eligible |
  | empty / empty filtered | existing empty states |
  | one node | a single glowing point at the centre |
  | all orphans | halo as a full disc |
  | worst case | 20,000 nodes, 110,000 edges (`Scale20k` data) |
  | selected / hovered | existing focus, halo ring and dimming |
  | entity layer on | diamonds in core and satellites |
  | WebGL unavailable | the WebGL message |

- **UX-6** — State matrix, code canvas: loading (existing), empty repository
  (existing), folded file-level graph with the LOD banner, search-narrowed
  subset, one node, selected, blast radius, active process, highlighted
  community, depth filter (demo), hidden kinds, worst case of 2,000 nodes,
  WebGL unavailable.
- **UX-7** — Code canvas pointer: wheel zoom and drag pan (new to the real
  host). Click selects; a click on empty canvas deselects. Hover shows
  `name · kind · file`. Selecting in the explorer, or arriving by a
  `?symbol=` / `?file=` deep link, animates the camera to the node in 400 ms
  (instant under reduced motion). The demo host's zoom buttons drive the
  camera.
- **UX-8** — Code canvas keyboard: the canvas is one tab stop with a
  visible focus ring and the label "Code graph — N nodes, M edges". `+` and
  `-` zoom, the arrow keys pan, `0` fits the view, and Escape clears the
  selection. Choosing a node by keyboard goes through the explorer tree,
  replacing the SVG's per-node tab stops.
- **UX-9** — Memory 2D interactions are otherwise unchanged: click, hover,
  dimming, labels, zoom, reset and the detail panel.

### Output promise

| ID | Promise |
|---|---|
| OP-1 | Built canvases match the Storybook boards in arrangement, colour roles and treatment; exact positions may differ. |
| OP-2 | Proven at 1280x800 and 1920x1080, light and dark themes. |
| OP-3 | `classify` plus `placeOuter` take ≤ 50 ms for 20,000 nodes and 110,000 edges in vitest on this host; the `Scale20k` story's time to first frame is within 20% of the pre-change time, both measured on this host in one session. |
| OP-4 | Code canvas focus ring visible; labels ≥ 4.5:1 contrast against the canvas in both themes; reduced motion honoured. |
| OP-5 | Declared deviations from graph.jpg: no 3D, no perspective floor grid, no "READY" label; the 3D memory view and the demo memory explorer are unchanged. |

## Acceptance

A1. [test, high] UX-1: A node with no drawn edge is classed halo; a component of 8 or more nodes is core; a component of 2–7 nodes is a satellite while any core exists.
A2. [test, high] UX-1: With no component of 8 or more, the largest component of 2 or more is the core; with no edges at all, every node is halo and the halo fills a full disc from the centre.
A3. [test, high] UX-1: A halo node's position is identical across two placements in which other nodes were added or removed but the core and satellite radii are the same.
A4. [test, high] UX-1: Every satellite node and every halo node lies farther from the centre than 1.15·R, and no two satellite clumps overlap.
A5. [test, high] UX-2: During the core's run, no core node is placed beyond R by `fitCore`.
A6. [test, high] OP-3: `classify` plus `placeOuter` complete in ≤ 50 ms for 20,000 nodes and 110,000 edges in vitest.
A7. [test, high] UI-2: The glow program's normal pass sets additive blending in the dark theme and restores `ONE, ONE_MINUS_SRC_ALPHA` after drawing; its picking pass never changes the blend function.
A8. [test, high] UX-4: The motion loop does not start when reduced motion is requested, when the graph has 2,000 or more nodes, or when the document is hidden, and stops when any of these becomes true.
A9. [test, neg, high] UX-4: The motion loop never writes node positions (`x`/`y` attributes stay unchanged across frames).
A10. [test, high] UI-4: In 2D mode the memory toolbar renders no Tightness or Spacing control; in 3D mode it renders Spacing.
A11. [test, high] UI-6: Neither code host renders a Layout control or a Play/Pause control.
A12. [test, high] UX-3: Raising the Edges threshold so a memory loses its last edge reclassifies it as halo on the next build.
A13. [demo, high] UI-1, UI-2, UI-3: The memory 2D canvas matches its board in both themes: dark nebula and glow, light paper and crisp points, faint edges at rest.
A14. [demo, high] UI-1, UI-2, UI-5, UX-6: The code canvas matches its board in both themes, with selection, blast and process rings and labels drawn as the SVG drew them.
A15. [demo, high] UX-2: On load, satellites and halo appear in place on the first frame and only the core animates; after a filter change, nodes still drawn do not jump.
A16. [demo, confirmed] UX-4: Halo points twinkle on graphs under 2,000 nodes with no on/off control; reduced motion turns it off.
A17. [demo, confirmed] UX-4: No twinkle at 2,000 nodes or more.
A18. [test, confirmed] UX-8: The code canvas is one tab stop; `+`/`-` zoom, arrows pan, `0` fits, Escape clears the selection; node choice by keyboard goes through the explorer.
A19. [demo, high] UX-7: In the real code host, wheel zooms, drag pans, and selecting a node in the explorer or by `?symbol=` deep link animates the camera to it.
A20. [demo, high] UX-5, UX-6: Each canvas shows "The graph needs WebGL, which this browser has turned off." when no WebGL context is available, and the explorer and toolbar stay usable.
A21. [test, neg, high] UI-7: Turning the entity layer on never changes an entity's diamond shape or border colour.
A22. [demo, neg, confirmed] OP-5: The 3D memory view and the demo-mode memory explorer look and behave exactly as before.
A23. [demo, high] OP-3: The `Scale20k` story reaches its first frame within 20% of the pre-change time on this host.
A24. [test, confirmed] UX-1: The core threshold is 8 nodes.

## Riskiest assumption

That your real memory graph, at the default Edges threshold of 0.5
(`real-memory-graph-page.tsx:63`), has a component distribution that reads
like the reference: a sizeable core, some satellites and a halo. If nearly
every memory sits in one component, there is no halo. If nearly every memory
is an orphan, the picture is just a starfield. The fallbacks in A2 keep both
cases drawable, but not attractive. The demo snapshot
(`demo/data/graph-snapshot.json`) is empty, so there is no in-repo evidence.
**Unverified — the plan's first task verifies it**, by computing component
sizes from a `/graph/unified` response of your instance (read-only, through
your session or a JSON you save from the browser) before the renderers are
built on it.

## Testing

- Vitest, pure: `constellation-layout.test.ts` (A1–A6, A24),
  `ambient-motion.test.ts` (A8, A9, with fake timers and a mocked
  `matchMedia`), `node-glow-program.test.ts` (A7, extending the mocked-GL
  pattern of `node-border-programs.test.ts`).
- Vitest, components, with renderers mocked as the existing tests do:
  toolbar rows (A10, extending the toolbar tests), code hosts without the
  Layout or Play/Pause controls (A11, extending `code-tabs.test.tsx` and
  `real-code-graph-view.test.tsx`), and the entity layer (A21).
- A12 runs `classify` on a fixture before and after raising the threshold.
- A18 is a Playwright spec on the demo Code Graph, added to
  `DEMO_FIXTURE_SPECS`, run through `run_playwright_e2e.py`.
- Demo statements are proven by the `ui-proof` walkthrough on the Storybook
  boards and in demo mode, at both viewports and in both themes.
