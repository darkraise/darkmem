# Cluster islands — design

**Execution strategy:** inline
**Depth:** light — intricate

The memory graph's 2D canvas drops the constellation's core, clump ring and
halo annulus for one island per cluster. It supersedes the memory-canvas
arrangement of `2026-11-18-constellation-graphs-design.md` (UX-1, UX-3) and
`2026-11-18-constellation-real-data-design.md` (roles by score cut, clump
placement, halo annulus, core fit); the glow, backdrop, motion, labels and
the code canvas's ring layout are unchanged.

## Decisions

- **Owner request (2026-11-19):** "group them by cluster", "make the
  connected nodes gather together, not strictly but at a loose threshold",
  "retire the circle shape"; Regions becomes a toggle, "when off, do not
  show the region, when on, show region by cluster".
- **Process:** bounded, decided inline (my call; the request named the
  behaviour and the files are enumerable).
- **State boards:** none new; the existing `Graph/Constellation/RealCorpus`
  stories gain a `Regions` story (my call; the canvas already has boards).
- **Unclustered memories** (my call): one with an edge to a clustered memory
  rides on the island of its highest-scored such neighbour; one with none
  joins a single sparse "loose" island, drawn dim and small as the halo was.
- **Region colour** is the cluster's colour in every colour mode, since a
  region is always a cluster now.
- **Code canvas:** unchanged; it keeps `classify`, `placeOuterRing` and
  `fitCoreToFarthest`. The memory-only score-cut path is deleted.

## Architecture

1. `features/graph/lib/cluster-layout.ts` (pure). `groupMemories` assigns
   islands as above. `placeIslands` runs a deterministic simulation over
   island discs (radius `ISLAND_K·√n`, loose `LOOSE_K·√n`): spiral start,
   pull between islands proportional to their shared edges normalised by
   `√(nₐ·n_b)`, weak gravity (a third for the loose island), collisions at
   `1.15·(rₐ+r_b)` plus a gap. `fitIsland` maps one island's simulated
   positions onto its disc (85th percentile at 0.8r, soft taper to 1.15r).
   `spreadPoints` enforces a minimum memory gap of `NODE_GAP` (0.4) of the
   even spacing, unbounded.
2. `features/graph/lib/cluster-runner.ts`. ForceAtlas2 over every clustered
   or riding memory with only intra-island edges, weighted by score from
   0.15 (weakest) to 1 (strongest); each frame refits every island and
   spreads. The loose island is placed once by sunflower and never
   simulated. Entities ride on the centroid of their memories.
3. Regions: `HullMode` is `"none" | "cluster"`; the toolbar shows a switch.

## UI/UX contract

**UI/UX depth:** feature — the memory graph's 2D arrangement and one setting change

### UI

- **UI-1** — Settings → Encoding: a "Regions" switch (accessible name
  "Cluster regions") replaces the None/Cluster/Tag/Source segment. Off draws
  no region; on draws one region per cluster in that cluster's colour, with
  its name chip when zoomed in. Default off; Reset returns it to off.
- **UI-2** — At rest an edge draws only between two memories of one island;
  hover or selection lights a node's other edges as before.
- **UI-3** — Loose-island memories keep the halo treatment: one small size
  and 0.45 brightness. Island members are 1.0, riders 0.8.

### UX

- **UX-1** — Arrangement: one island per cluster; islands sharing more
  edges sit closer; islands never overlap; no ring, annulus or circular
  silhouette is imposed.
- **UX-2** — Inside an island linked memories gather (a weighted force
  layout) but no two memories sit closer than the minimum gap.
- **UX-3** — Settling: islands are in place on the first frame; members
  animate within their island for the tier's `layoutMs`. A change of island
  membership at an unchanged memory set re-runs the layout; a rebuild with
  the same membership does not.
- **UX-4** — Entity layer: toggling it moves no memory; an entity sits on
  its memories' centroid and takes their highest role.

### Output promise

| ID | Promise |
|---|---|
| OP-1 | Proven in Storybook on the real-corpus fixtures and on the live page, 1280x800 and 1920x1080, light and dark. |
| OP-2 | `layoutIslands` takes ≤ 50 ms for 20,000 memories and 110,000 edges in vitest on this host. |

## Acceptance

A1. [test, high] UX-1: a clustered memory is on its cluster's island; an unclustered one joins its highest-scored clustered neighbour's island, else the loose island.
A2. [test, high] UX-1: on the 200, 1,000 and full fixtures no two islands come closer than 1.15·(rₐ+r_b).
A3. [test, medium] UX-1: an island sharing many edges with another sits closer to it than to one sharing none.
A4. [test, high] UX-2: `fitIsland` keeps every member within 1.15r of the centre, and `spreadPoints` leaves no pair closer than 90% of the gap.
A5. [test, medium] UX-2: on the 1,000 fixture after a ForceAtlas2 run and fit, linked memories of an island are on average closer than random member pairs of that island.
A6. [test, high] UI-1: the toolbar renders the "Cluster regions" switch and no Regions radiogroup; toggling reports "cluster" and "none"; Reset returns it off.
A7. [test, high] UI-1: `computeHullGroups` answers nothing when off and one group per non-negative cluster when on.
A8. [test, high] UI-2: on the 1,000 fixture an edge is hidden at rest exactly when its endpoints are on different islands, and hovering a node lights its edges.
A9. [test, high] UI-3: loose memories take one small size whatever their importance, at most 40% of the median island size.
A10. [test, high] UX-4: with the entity layer on, no memory moves or changes role, and an entity takes its memories' highest role.
A11. [test, high] UX-3: an island-membership change at an unchanged memory set starts a new layout run; an identical rebuild does not.
A12. [test, high] OP-2: `layoutIslands` at 20,000 memories and 110,000 edges takes ≤ 50 ms (median of 5).
A13. [demo, high] OP-1: screenshots of each UI and UX item in Storybook and on the live page, both themes, both viewports.
