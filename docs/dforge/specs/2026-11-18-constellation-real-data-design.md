# Constellation graphs on real data — design

**Execution strategy:** sequential — inline execution
**Depth:** light — approach,intricate

The 2D memory graph shipped by
`docs/dforge/specs/2026-11-18-constellation-graphs-design.md` passed every
check on synthetic graphs and failed on the owner's real corpus (4,759
memories cloned from 192.168.0.199 to this host on 2026-11-18). This spec
makes the memory canvas read like the reference (`graph.jpg`, repo root,
untracked) on that corpus: a dense multi-coloured core with a soft edge,
small clumps scattered around it, and a wide sparse field of faint halo
points, with nothing saturating to white. It also gives the work real-shaped
proof data so this cannot recur unseen.

## Measured on the real corpus (2026-11-18)

Against `GET /api/v1/graph/unified` on this host's cloned data:

- Every memory has at least 2 edges (kNN graph, `EDGE_K = 5` either way,
  `backend/app/utils/graph_knn.py`); the median degree is 6. At the page's
  default Edges threshold of 0.5 the whole corpus is one connected component
  at 200, 1,000 and 4,759 memories, so every memory is core.
- A fixed threshold does not port across sizes, because kNN edge scores rise
  with the number of memories (median edge score 0.64 at 200, 0.74 at
  4,759). At 0.75: 65% core / 10% satellite / 25% halo for all 4,759, but
  16% / 24% / 60% for 200.
- The cut rule of Architecture §1 (core at most 45%) gives 44/22/35 at 200
  (cut 0.691), 44/17/38 at 1,000 (0.764) and 44/15/41 at 4,759 (0.778).
- Louvain labels (`cluster`) carry no noise label and no cluster below 8
  members at these sizes, so they cannot supply satellites or halo on their
  own.
- At Edges 0.75 with every memory loaded, the halo (1,211 nodes) renders as
  a solid white ring: `densityStyle` governs only the core and satellite
  roles (`features/graph/lib/node-glow-program.ts`), so overlapping halo
  glows sum past white. The core is a uniform hard-edged disc; satellites
  sit on one packed ring and read as a dotted arc.
- Labels show on nearly every node: a hub is `_degree >= HUB_DEGREE` (5),
  and the median memory has 6 edges.
- Load time of `/graph/unified` here: 200 in 1.3 s, 1,000 in 2.6 s, 4,759 in
  5.0 s.
- Re-measured 2026-11-19, after the first fix wave: the core's force layout
  keeps contracting each community toward a point for as long as it runs.
  On the 1,000-memory core the median nearest-neighbour distance after the
  fit falls from 10.4 to 3.8 units between 100 and 2,000 iterations, against
  17.7 for an even disc, under every FA2 setting tried. The look therefore
  depended on how long the layout ran: a loaded host showed lobes, a quiet
  one a few white-hot stacks. With the entity layer on, entities in the
  core's simulation pulled the memories sharing them into tighter stacks.

## Decisions

- **Process:** full dforge flow. Owner: "Full dforge flow (Recommended)".
- **Role assignment:** owner: "Adaptive cut (Recommended)" — roles use their
  own similarity cut, chosen per graph so the core is about 45%; the Edges
  slider still controls which links are drawn. Rejected: a fixed cut (raise
  the Edges default to 0.75; the split depends on how many memories are
  shown) and per-memory strength ranking (clusters stop being connected
  groups).
- **Proof data:** owner: "Fixture + live (Recommended)" — an anonymised
  snapshot of the cloned corpus committed as a Storybook fixture, and the
  read-only memory graph page on this host's :8000 with the cloned data. The
  UI profile gains that exception.
- **Default node limit:** owner: "1,000 (Recommended)".
- **State boards:** owner: "Yes, Storybook (Recommended)".
- **UI profile:** unchanged apart from the live-page exception above.
- **Scope** (my call): the memory 2D canvas. The code canvas keeps its
  classification (its edges carry no score) and gains only the shared halo
  rendering of UI-2 and UI-3. The 3D view and the demo memory explorer are
  untouched.
- **Signing in for the live proof** (my call): the proof session uses a
  short-lived admin token minted inside the app container with the app's own
  `create_access_token`, as on 2026-11-18; it writes nothing.
- **Inherited register rows**
  (`docs/dforge/registers/2026-11-18-constellation-graphs.md`): row 3
  (measure the split on the .199 corpus and tune the constants) is delivered
  here; row 4 (the dark theme's density dimming) is settled by UI-2, which
  states the dimming in the contract.

- **Fix wave (2026-11-19)** (my calls, under the owner's "continue to
  resolve all remaining items"): the UI proof's judge found the boards
  differing from `graph.jpg` in three ways (a blob-like core, speck clumps,
  a web of rest edges across the halo) and the entity layer summing to
  white. These are fixed rather than recorded as deviations: Architecture
  §2, §3, §5, §7 and §11.
- **Spec review (2026-11-18):** A9 and A10 confirmed by the owner ("Right"
  to each); early CI declined ("No early run (Recommended)"); approved with
  "Approve and run unattended".

Early CI: none

Finish: merge

Worktree: in-place

## Architecture

1. **Role cut** (`features/graph/lib/constellation-layout.ts`, pure).
   `roleCut(nodeIds, scoredEdges, share = CORE_SHARE)` sorts edges by score,
   highest first, and adds them to a union-find one score at a time (equal
   scores together), tracking how many nodes sit in components of at least
   `CORE_MIN`. The cut is the lowest score whose addition keeps that count at
   or below `share` of the nodes. When every edge keeps it at or below, the
   cut is the lowest edge score, so every drawn edge counts. The highest score group is always kept, so when it alone passes `share` the cut is the highest score. Under about 18 nodes, where `share` of the nodes is fewer than `CORE_MIN`, groups are kept until the first core forms, so a small graph keeps a core. `CORE_SHARE` is
   0.45. `classify` then runs, unchanged, on the edges at or above the cut.
   Because the server sends only edges at or above the Edges threshold, the
   effective cut is never below the slider.
2. **Who is classified.** On the memory canvas only memory-to-memory
   similarity edges feed `roleCut` and `classify`; the renderer keeps each
   one's `score` as an edge attribute. With the entity layer on, an entity
   takes the highest role among the memories it links to
   (core > satellite > halo). A core entity rides on the core: it stays out
   of the core's simulation and of `R`, and sits at the centre of its linked
   core memories, offset by at most a quarter of `CORE_K` on each axis, so
   toggling the entity layer never moves a core memory; a
   satellite entity joins the clump of its first linked satellite memory (by
   id); an entity linking only halo memories is halo. Membership and
   relation edges never merge two memory groups. The code canvas passes
   unscored edges and keeps today's classification.
3. **Satellite placement.** Each clump keeps its sunflower packing, at
   `MEMORY_CLUMP_R0` (6) between neighbours on the memory canvas, twice the
   code canvas's `CLUMP_R0`, so a clump of a few memories reads as a group
   of points rather than a speck. Clump
   centres are scattered rather than ringed: clumps are taken largest first,
   and each tries up to 24 candidate centres, angle and radius from
   `seededUnit` hashes of the clump's smallest member id, radius within
   `[1.15·R + clump radius, SATELLITE_BAND·R]` (`SATELLITE_BAND` 2.0). It
   takes the first candidate that clears every placed clump by
   `MEMORY_CLUMP_R0`.
   When all 24 fail, it takes the clear position nearest the band's outer
   edge, found by stepping outward from the last candidate.
4. **Halo placement.** Angle from a `seededUnit` hash; radius uniform in
   distance rather than area between `haloInner = 1.15·R` and
   `haloOuter = max(HALO_MIN_OUTER·R, satellite band outer + HALO_C·√(halo count))`
   (`HALO_MIN_OUTER` 3.0). Density therefore falls with distance, the field
   reaches in between the clumps, and a halo node's position depends only on
   its id and the two radii. With no core, the halo fills a full disc from
   the centre, as before.
5. **Core shape.** FA2 on the core drops `strongGravityMode` and runs
   LinLog with `gravity` 0.05, so communities pull apart into lobes rather
   than a uniform disc. `fitCore` scales uniformly about the centroid so the
   90th-percentile node distance lands at `0.85·R`. A node whose scaled
   distance `d` exceeds `0.85·R` moves radially to
   `0.85·R + 0.15·R·tanh((d − 0.85·R) / (0.15·R))`, so the edge stays soft
   and no node passes `R`. On the memory canvas `spreadCore` then pushes
   apart any two core nodes closer than `CORE_GAP` (0.8) of an even disc's
   spacing, `R·√(π/n)`, keeping each inside `R`. It is warm-started from the
   previous frame's corrections and runs 2 passes per frame and 40 when the
   layout stops: about 3 ms a frame for the 2,115-node all-memories core and
   10 ms at 9,000, measured in vitest on this host.
6. **Sizes.** On the memory 2D canvas a memory's `size` is
   `computeSize(...) × MEMORY_SIZE_SCALE` (0.25, from today's 0.5). Halo
   nodes ignore size mode, importance and degree and take `HALO_SIZE`, at
   most 40% of the median core size. The code canvas's halo takes the same size (UI-3, OP-5); its other sizes are unchanged.
7. **Density control on the halo.** `trackDensityGain` adds a halo style.
   Spacing is the mean distance between halo points over the annulus
   (`√(π·(outer² − inner²)/count)` in pixels), the overlap ceiling the halo's
   count, the gain floor 0.1. The glow program applies `u_haloGain` and
   `u_haloScale` to halo fragments before the twinkle, in the dark theme. On
   the memory canvas the core's spacing is measured from its fitted positions
   (`localSpacing`: the spacing its densest 2% of nodes see, at most
   `CORE_K`), because weak gravity and the percentile fit pack it into lobes
   denser than an even disc. Every role is then
   held under `COVERAGE_TARGET`, so no part of the canvas sums to white at
   the fit view. On the memory canvas a core or clump disc is also drawn no
   wider than `CRISP_RATIO` (0.3) of its role's spacing on screen and no
   narrower than 1.5 px (`crispStyle`), so neighbours stay separate points;
   the light theme, which draws no glow, allows 1.5 times that. Zooming in
   widens the spacing and lifts the cap. The memory canvas's glow pass
   screen-blends (`ONE, ONE_MINUS_SRC_COLOR`) instead of summing, so an
   overlap never passes its brighter colour, a glow drawn over an entity
   outline included. Entity diamonds count in no role's density.
8. **Labels.** Hubs are the top 2% of drawn memories (rounded down, at least
   one when any memory has `HUB_DEGREE` or more edges), ranked by degree then
   id, and only among memories with at least `HUB_DEGREE` edges. In the rest
   tier (nothing selected) a memory's label shows only when it is hovered, or
   when it is a hub and the camera is zoomed past `LABEL_ZOOM_RATIO`; the
   focus and adjacent tiers of a selection keep their labels. The memory
   renderer applies this itself. The shared `labelVisible`
   (`features/graph/lib/focus-model.ts`), which today labels every node once
   zoomed in and hubs at rest, is unchanged, because the code canvas uses it.
9. **Default node limit.** `NODE_LIMIT_DEFAULT` becomes 1,000.
   `darkmem-graph-prefs` gains persist `version: 1` with a `migrate` that
   turns a stored `nodeLimit` of exactly 200 (the old default) into 1,000 and
   keeps every other stored value.
10. **Real-corpus fixture.** `frontend/scripts/anonymise-graph-fixture.mjs
    <in.json> <out.json>` reads a saved `/graph/unified` response and writes
    `frontend/src/features/graph/fixtures/real-corpus-<n>.json` for n = 200,
    1,000 and all memories. Ids become the first 12 hex digits of their
    SHA-256, content becomes `Memory <i>`, cluster names `Cluster <k>`, and
    tags and project are dropped. Cluster numbers, `memory_type`,
    `importance`, order and edge scores (rounded to 3 places) are kept. The
    boards (`Graph/Constellation/RealCorpus`) render these through the real
    `Graph2DRenderer`.
11. **Rest edges.** With nothing hovered or selected, the memory canvas
    draws an edge only when both its ends sit in the core or in one clump;
    hover or selection lights every edge of its node. Light-theme rest edges
    draw at 0.4 of their alpha, so the core's mesh does not outweigh its
    points.

**Data flow.** `/graph/unified` → page filters → renderer builds the
graphology graph with memory edges carrying `score` → runner: `roleCut` over
memory edges → `classify` over edges ≥ cut → entity roles → `placeOuter`
(scattered clumps, falling halo) → FA2 on the core's memories, mirrored
through `fitCore` and `spreadCore`, core entities placed on their memories →
sigma draws with per-role density control and the rest-edge rule.

**Error handling.** A memory edge without a numeric score counts as above
every cut, so the graph never loses an edge silently. Nothing else changes:
the WebGL failure state, empty states and worker-loss behaviour are as
shipped.

## UI/UX contract

**UI/UX depth:** feature — the memory 2D canvas changes its role assignment, placement and rendering on real data

### UI

- **UI-1** — Memory 2D canvas at rest, dark theme, on the real corpus: a
  multi-coloured core of crisp, separate points with a soft, irregular edge;
  small clumps scattered around it at varying distances; a sparse field of
  faint, cluster-tinted halo points thinning outward; no lines cross the
  halo at rest. Board: `Graph/Constellation/RealCorpus`.
- **UI-2** — Density, dark theme: core and clump points are drawn no wider
  than a share of their spacing, the glow pass screen-blends, and core,
  satellite and halo glows are dimmed, and below the gain floor shrunk, so
  overlapping discs never sum to white
  at the fit view (the camera after load or "Reset graph view"). Zooming in restores full brightness and size. Role order
  holds: core ≥ satellite ≥ halo brightness.
- **UI-3** — Halo points are small and uniform: `HALO_SIZE` regardless of
  importance or degree, on both canvases.
- **UI-4** — Light theme: crisp saturated points, halo at 55% opacity, as
  shipped, with the new arrangement and sizes; the core's rest edges recede
  behind its points.
- **UI-5** — Labels: none at the fit view except hovered or selected nodes;
  hub labels (top 2% of memories by degree) appear once zoomed in.

### UX

- **UX-1** — Roles on real data follow Architecture §1–2: about 45% core,
  the rest in clumps and halo, at any node limit.
- **UX-2** — Edges slider: raising it never pulls a memory inward (halo to
  satellite or core, satellite to core) while any component of `CORE_MIN`
  remains; lowering it never pushes one outward.
- **UX-3** — Default view: the page opens on 1,000 memories; an owner who
  never changed the limit sees 1,000, one who chose another value keeps it.
- **UX-4** — Settling, interactions, twinkle and the WebGL state behave as
  shipped (prior spec UX-2, UX-4, UX-9).
- **UX-5** — State matrix, memory 2D canvas on real data:

  | State | Shows |
  |---|---|
  | default | 1,000 memories, arrangement of UI-1 |
  | all memories | 4,759, no twinkle, no saturation |
  | small | 200 memories |
  | high Edges | Edges 0.8: smaller core, more clumps and halo |
  | entity layer on | diamonds placed with their memories' roles |
  | selected / hovered | existing focus, ring and dimming, label shown |
  | light theme | each of the above that the proof walks in light |

### Output promise

| ID | Promise |
|---|---|
| OP-1 | The live page at the default view reads as `graph.jpg`'s arrangement: core, scattered clumps, sparse halo, no white saturation. Exact positions and colours may differ. |
| OP-2 | Proven at 1280x800 and 1920x1080, light and dark, on the live page with the cloned corpus and on the boards. |
| OP-3 | `roleCut` + `classify` + `placeOuter` ≤ 50 ms for 20,000 nodes and 110,000 scored edges in vitest on this host. |
| OP-4 | No real memory content, tag, project name or id is committed. |
| OP-5 | The 3D view and the demo memory explorer are unchanged; the code canvas changes only by UI-2's halo dimming and UI-3's halo size. |

## Acceptance

A1. [test, high] UX-1: `roleCut` returns the lowest edge score at which components of `CORE_MIN` or more hold at most 45% of the nodes, adding equal scores together; when every edge keeps them at or below 45%, it returns the lowest edge score; when the highest score group alone passes 45%, it returns the highest score.
A2. [test, high] UX-1: On the real-corpus fixtures at 200, 1,000 and all memories, the core holds 35–50%, satellites 10–25% and the halo 25–45% of the memories.
A3. [test, high] UX-2: On the 1,000-memory fixture, raising the Edges threshold from 0.5 to 0.8 in steps of 0.05 never moves a memory from halo to satellite or core, or from satellite to core, while a component of `CORE_MIN` or more remains.
A4. [test, high] UX-1: With the entity layer on, an entity takes the highest role among its linked memories, and adding membership and relation edges never changes any memory's role.
A5. [test, high] UX-1: No two satellite clumps overlap, every clump centre lies at least `1.15·R` plus its radius from the centre, and on the real-corpus fixtures every clump centre lies within `2.0·R` and no 90° sector holds more than half of the clumps.
A6. [test, high] UX-1: Every halo node lies between `1.15·R` and the halo's outer radius; halo nodes per unit area are denser in the inner half of that span than in the outer half; a halo node's position is identical across placements with equal radii.
A7. [test, high] UX-1: `fitCore` places no core node beyond `R` and at most 10% of core nodes beyond `0.85·R`.
A8. [test, high] UI-2: For the all-memories fixture's halo at the fit view, `trackDensityGain`'s halo gain times the halo's coverage (scaled disc radius squared over spacing squared) stays at or below `COVERAGE_TARGET` for halo sizes of 1.5 and 20; the program feeds `u_haloGain` and `u_haloScale` from the clock, and its dark-theme shader scales halo brightness and radius by them.
A9. [test, confirmed] UI-3: Every halo node's `size` equals `HALO_SIZE`, at most 40% of the median core size, whatever its importance or degree.
A10. [test, confirmed] UI-5: On the 1,000-memory fixture at most 2% of memories are hubs, and at the fit view only hovered or selected nodes carry a label.
A11. [test, high] UX-3: The default node limit is 1,000; a stored preference of 200 from before this change loads as 1,000, and any other stored value loads unchanged.
A12. [test, neg, high] OP-5: The code canvas's roles for a fixture graph are identical before and after this change.
A13. [test, neg, high] OP-4: The committed fixtures contain no `content` other than `Memory <i>`, no `tags` or `project` key, no cluster name other than `Cluster <k>`, and no id matching the UUID pattern.
A14. [test, high] OP-3: `roleCut` + `classify` + `placeOuter` complete in ≤ 50 ms for 20,000 nodes and 110,000 scored edges in vitest (median of 5).
A15. [demo, high] UI-1, UI-2, OP-1: The live memory graph page on this host, at the default 1,000 memories in the dark theme, shows a multi-coloured core with a soft edge, scattered clumps and a sparse halo with no white saturation, beside `graph.jpg`, at both viewports.
A16. [demo, high] UI-2, UX-5: The live page with all 4,759 memories and with 200 shows the same arrangement and no saturation; Edges 0.8 shows a smaller core with more clumps and halo.
A17. [demo, high] UI-4, UI-5: In the light theme the live page shows crisp points and a 55% halo; at the fit view no labels show until a node is hovered.
A18. [demo, high] UX-5: The `Graph/Constellation/RealCorpus` boards match the live page's arrangement for 200, 1,000, all memories, Edges 0.8 and the entity layer.
A19. [demo, neg, high] OP-5: The 3D memory view and the demo memory explorer look and behave as before; the code canvas differs only in halo size and dimming.

A20. [test, high] UI-1: At rest an edge of the 1,000-memory board is hidden exactly when its ends are not both in the core or both in one clump; hovering a halo memory shows every edge it has.
A21. [test, high] UX-5: Turning the entity layer on leaves every core memory's position unchanged, and every core entity lies within `0.25·CORE_K` of its linked core memories' centre.
A22. [test, high] UI-1, UI-2: After a 2,000-iteration run of the core's force layout on the 1,000-memory fixture, `spreadCore`'s 40 settle passes leave no two core nodes closer than 0.7 of the `CORE_GAP` distance and every node inside `R`; 100 frames of 2 warm-started passes reach 0.85.
A23. [test, high] UI-2, UI-4: On the memory canvas a packed core's discs are drawn at `max(1.5 px, CRISP_RATIO × spacing)` at full gain, the glow pass screen-blends, and only the memory canvas applies the cap in the light theme; the code canvas keeps `densityStyle` at `CORE_K` and additive blending.

## Riskiest assumption

That arrangement plus per-role density control is what makes the reference
read as it does, so the live page will look like `graph.jpg` once A1–A10
hold. The role split is evidenced (the cut measurements above, run against
`/graph/unified` on 2026-11-18). How the rendered result looks is
unverified — the plan's first task that can render the real-corpus board
(after the cut, the placement, the halo density and the renderer wiring)
screenshots the 1,000-memory board beside `graph.jpg`, before sizes,
labels and the default limit are built on it.

## Testing

- Vitest, pure: `constellation-layout.test.ts` extended for A1, A5, A6, A7,
  A14; a new `real-corpus-roles.test.ts` loads the three fixtures for A2, A3,
  A4 and A10's hub count; `node-glow-program.test.ts` extended for A8;
  renderer tests extended for A9 and A10's label rule; `graph-prefs.test.ts`
  for A11; a fixture scan test for A13; the code canvas's existing role tests
  pinned for A12.
- Demo statements are proven by the `ui-proof` walkthrough on the live page
  at :8000 with the cloned corpus and on the Storybook boards, at both
  viewports and in both themes, side by side with `graph.jpg`.
