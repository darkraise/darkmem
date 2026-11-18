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
   cut is the lowest edge score, so every drawn edge counts. `CORE_SHARE` is
   0.45. `classify` then runs, unchanged, on the edges at or above the cut.
   Because the server sends only edges at or above the Edges threshold, the
   effective cut is never below the slider.
2. **Who is classified.** On the memory canvas only memory-to-memory
   similarity edges feed `roleCut` and `classify`; the renderer keeps each
   one's `score` as an edge attribute. With the entity layer on, an entity
   takes the highest role among the memories it links to
   (core > satellite > halo). A core entity joins the core layout; a
   satellite entity joins the clump of its first linked satellite memory (by
   id); an entity linking only halo memories is halo. Membership and
   relation edges never merge two memory groups. The code canvas passes
   unscored edges and keeps today's classification.
3. **Satellite placement.** Each clump keeps its sunflower packing. Clump
   centres are scattered rather than ringed: clumps are taken largest first,
   and each tries up to 24 candidate centres, angle and radius from
   `seededUnit` hashes of the clump's smallest member id, radius within
   `[1.15·R + clump radius, SATELLITE_BAND·R]` (`SATELLITE_BAND` 2.0). It
   takes the first candidate that clears every placed clump by `CLUMP_R0`.
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
   and no node passes `R`.
6. **Sizes.** On the memory 2D canvas a memory's `size` is
   `computeSize(...) × MEMORY_SIZE_SCALE` (0.25, from today's 0.5). Halo
   nodes ignore size mode, importance and degree and take `HALO_SIZE`, at
   most 40% of the median core size. The code canvas keeps its sizes.
7. **Density control on the halo.** `trackDensityGain` adds a halo style.
   Spacing is the mean distance between halo points over the annulus
   (`√(π·(outer² − inner²)/count)` in pixels), the overlap ceiling 1, the
   gain floor 0.1. The glow program applies `u_haloGain` and `u_haloScale` to
   halo fragments before the twinkle, in the dark theme. Every role is then
   held under `COVERAGE_TARGET`, so no part of the canvas sums to white at
   the fit view.
8. **Labels.** Hubs are the top 2% of drawn memories (rounded down, at least
   one when any memory has `HUB_DEGREE` or more edges), ranked by degree then
   id, and only among memories with at least `HUB_DEGREE` edges. Labels otherwise
   follow `labelVisible` as today: hovered or selected nodes always, hubs
   once zoomed past `LABEL_ZOOM_RATIO`.
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

**Data flow.** `/graph/unified` → page filters → renderer builds the
graphology graph with memory edges carrying `score` → runner: `roleCut` over
memory edges → `classify` over edges ≥ cut → entity roles → `placeOuter`
(scattered clumps, falling halo) → FA2 on the core, mirrored through the new
`fitCore` → sigma draws with per-role density control.

**Error handling.** A memory edge without a numeric score counts as above
every cut, so the graph never loses an edge silently. Nothing else changes:
the WebGL failure state, empty states and worker-loss behaviour are as
shipped.

## UI/UX contract

**UI/UX depth:** feature — the memory 2D canvas changes its role assignment, placement and rendering on real data

### UI

- **UI-1** — Memory 2D canvas at rest, dark theme, on the real corpus: a
  multi-coloured core with a soft, irregular edge; small clumps scattered
  around it at varying distances; a sparse field of faint, cluster-tinted
  halo points thinning outward. Board: `Graph/Constellation/RealCorpus`.
- **UI-2** — Density, dark theme: core, satellite and halo glows are dimmed,
  and below the gain floor shrunk, so overlapping discs never sum to white
  at the fit view (the camera after load or "Reset graph view"). Zooming in restores full brightness and size. Role order
  holds: core ≥ satellite ≥ halo brightness.
- **UI-3** — Halo points are small and uniform: `HALO_SIZE` regardless of
  importance or degree, on both canvases.
- **UI-4** — Light theme: crisp saturated points, halo at 55% opacity, as
  shipped, with the new arrangement and sizes.
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

A1. [test, high] UX-1: `roleCut` returns the lowest edge score at which components of `CORE_MIN` or more hold at most 45% of the nodes, adding equal scores together; when every edge keeps them at or below 45%, it returns the lowest edge score.
A2. [test, high] UX-1: On the real-corpus fixtures at 200, 1,000 and all memories, the core holds 35–50%, satellites 10–25% and the halo 25–45% of the memories.
A3. [test, high] UX-2: On the 1,000-memory fixture, raising the Edges threshold from 0.5 to 0.8 in steps of 0.05 never moves a memory from halo to satellite or core, or from satellite to core, while a component of `CORE_MIN` or more remains.
A4. [test, high] UX-1: With the entity layer on, an entity takes the highest role among its linked memories, and adding membership and relation edges never changes any memory's role.
A5. [test, high] UX-1: No two satellite clumps overlap, every clump centre lies at least `1.15·R` plus its radius from the centre, and on the real-corpus fixtures every clump centre lies within `2.0·R` and no 90° sector holds more than half of the clumps.
A6. [test, high] UX-1: Every halo node lies between `1.15·R` and the halo's outer radius; the inner half of that span holds more halo nodes than the outer half; a halo node's position is identical across placements with equal radii.
A7. [test, high] UX-1: `fitCore` places no core node beyond `R` and at most 10% of core nodes beyond `0.85·R`.
A8. [test, high] UI-2: `trackDensityGain` sets a halo gain below 1 for the all-memories fixture's halo at the fit view, and the glow program's dark-theme shader scales halo brightness by `u_haloGain` and halo radius by `u_haloScale`.
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

## Riskiest assumption

That arrangement plus per-role density control is what makes the reference
read as it does, so the live page will look like `graph.jpg` once A1–A10
hold. The role split is evidenced (the cut measurements above, run against
`/graph/unified` on 2026-11-18). How the rendered result looks is
unverified — the plan's first task builds the cut, the placement and the
halo density on the real-corpus fixture and screenshots the 1,000-memory
board beside `graph.jpg` before anything else is built on it.

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
