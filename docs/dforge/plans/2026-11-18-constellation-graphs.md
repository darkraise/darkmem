# Constellation Graphs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dforge:subagent-driven-development for `subagent`, dforge:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 2D memory graph and the code graph the reference image's core/satellite/halo arrangement and its glowing, nebula-backed WebGL treatment.

**Architecture:** One pure layout module classifies nodes by connected component and places satellites and the halo directly; a runner simulates only the core with the existing ForceAtlas2 worker and fits it inside its radius every frame. Shared sigma.js pieces (a glow node program, a backdrop layer, an ambient-motion loop) are wired into the existing memory 2D renderer and into a new sigma-based code canvas that replaces the SVG one.

**Tech Stack:** React 19, TypeScript, sigma.js 3.0.3, graphology, graphology-layout-forceatlas2 (worker), vitest on happy-dom, Storybook, Playwright.

**Spec:** docs/dforge/specs/2026-11-18-constellation-graphs-design.md

**Execution:** inline — `claude --model opus --effort high` — the hardest self-implemented tasks (Task 8, total 7) maps to impl-opus-high

**Parallelism:** sequential — inline execution

**Task check:** `cd frontend && npx tsc -b && npx vitest run --changed chore/darkraise-ui-7` — rule 3: no gates.md and no suites.tsv timing, so vitest's impact selection against the run's base

**Integration check:** `cd frontend && npm run typecheck && npm test && npm run build`

**CI:** `.github/workflows/ci.yml .github/workflows/release.yml .github/workflows/cache-cleanup.yml` — platforms: uutils (ubuntu-latest), self-hosted darkmem-linux — local: `cd frontend && npm run typecheck`; `cd frontend && npm run lint`; `cd frontend && npx vite build`; `cd frontend && npx vitest run`; `cd backend && .venv/bin/ruff check app/ --select F` — uncovered: uutils (ubuntu-latest)

**Plan review:** 2026-11-18 — dforge:judge-opus — executability 10 / coherence 15 / coverage 13 / assumptions 11 (round 1)

## Global Constraints

- Only `frontend/` changes. `graph-3d-renderer.tsx`, `memory-graph-explorer.tsx` and `demo/explore.ts` must not change (A22).
- Core rule: a component of `CORE_MIN = 8` or more nodes is core; with none, the largest component of 2 or more is core; other components of 2+ are satellites; isolated nodes are halo.
- Placement constants: satellite rings start at `1.15·R`; the halo's outer radius is at least `2.6·R`; `R = k·√(core count)`.
- Brightness by role: core 1.0, satellite 0.8, halo 0.45. Light theme: no additive glow, halo nodes at 55% opacity.
- Glow quad: three times the node radius. Edges at rest: 8% (dark) or 12% (light) of their colour's opacity in the 2D memory graph and the code canvas only.
- Nebula radius: 2.2× the core's on-screen radius.
- Motion: only below 2,000 nodes, at most 30 frames a second, never under `prefers-reduced-motion: reduce`, never while the document is hidden; halo brightness ±30% with a per-node period of 3–7 s; positions never move.
- Camera animations: 400 ms, instant under reduced motion.
- WebGL failure copy, exactly: "The graph needs WebGL, which this browser has turned off."
- Code canvas accessible name, exactly: `Code graph — N nodes, M edges`.
- Colours come from `GraphThemeTokens`; no raw hex in renderers. The only new raw values are the four CSS token triplets in Task 2.
- Run the typecheck as `npm run typecheck` (`tsc -b`), never plain `tsc`. `Array.prototype.at` is unavailable under `tsc -b`'s lib setting.
- Never run a repo-wide `prettier --write`; the frontend is not prettier-clean.
- Playwright only through `backend/scripts/e2e/run_playwright_e2e.py <spec> --project=<project>`, never bare `npx playwright test` (it points `/api` at production on :8000).
- Every Storybook or vite server started for a check runs as a tracked background task and is killed when the check ends. Never `pkill node`.
- Check darkraise-ui (`frontend/node_modules/darkraise-ui/dist/components/`) before building any DOM control.
- Comments only for a non-obvious why. Commits `<type>(<scope>): <subject>`, ≤50 chars, no attribution lines.
- uutils (ubuntu-latest): A lock built on `mkdir` failing when the directory exists does not exclude a second process. Do instead: Create the lock file with `set -C` (noclobber), or use `flock`.
- uutils (ubuntu-latest): `timeout` signals only the command it started, so the command's children keep running. Do instead: Run the command in its own process group (`setsid`) and signal the group.

## Contracts

**C1 — `frontend/src/features/graph/lib/constellation-layout.ts`** (Task 1)

```ts
export type ConstellationRole = "core" | "satellite" | "halo"
export const CORE_MIN = 8
export const SATELLITE_RING_START = 1.15
export const HALO_MIN_OUTER = 2.6
export const ROLE_BRIGHTNESS: Record<ConstellationRole, number> // { core: 1, satellite: 0.8, halo: 0.45 }
export interface ConstellationEdge { source: string; target: string }
export interface Point { x: number; y: number }
export interface Classification {
  role: Map<string, ConstellationRole>
  core: string[]
  satellites: string[][] // one array per component, members sorted by degree desc then id
  halo: string[]
  degree: Map<string, number>
}
export interface OuterLayout {
  positions: Map<string, Point> // satellite and halo nodes only, centred on the origin
  satelliteOuter: number
  haloInner: number
  haloOuter: number
}
export function classify(nodeIds: readonly string[], edges: readonly ConstellationEdge[]): Classification
export function coreRadius(coreCount: number): number // k·√n; 0 for 0
export function placeOuter(c: Classification, R: number): OuterLayout
export function fitCore(positions: ReadonlyMap<string, Point>, R: number): Map<string, Point> // centroid to origin, farthest node at exactly R
```

**C2 — tokens** (Task 2): CSS custom properties `--graph-canvas` and `--graph-nebula` (HSL triplets, light under `:root`, dark under `[data-mode="dark"]`) in `frontend/src/styles/globals.css`; `GraphThemeTokens` gains `canvas: string` and `nebula: string` (hex), filled by `resolveGraphTokens` with fallbacks.

**C3 — `frontend/src/features/graph/lib/node-glow-program.ts`** (Task 3)

```ts
export const GLOW_SPREAD = 3
export interface GlowClock { time: number } // seconds, written by the motion loop
export function createNodeGlowProgram(opts: { additive: boolean; clock: GlowClock }): NodeProgramType
```

Reads `brightness` (default 1) and `phase` (default 0) from node display data. Uniform `u_time` comes from `clock.time`.

**C4 — `frontend/src/features/graph/lib/graph-backdrop.ts`** (Task 4)

```ts
export const NEBULA_SCALE = 2.2
export const NEBULA_MIN_PX = 120
export const WEBGL_UNAVAILABLE_MESSAGE = "The graph needs WebGL, which this browser has turned off."
export interface BackdropHost {
  getContainer(): HTMLElement
  getCamera(): { on(event: "updated", fn: () => void): unknown; off(event: "updated", fn: () => void): unknown }
  getDimensions(): { width: number; height: number }
}
export function nebulaGeometry(centre: Point, radiusPx: number): { x: number; y: number; r: number }
export function coreOnScreen(host: { graphToViewport(p: Point): Point }, R: number): { centre: Point; radiusPx: number }
export function attachBackdrop(
  host: BackdropHost,
  getCore: () => { centre: Point; radiusPx: number },
  colors: { canvas: string; nebula: string; isDark: boolean },
): () => void // detach
```

**C5 — `frontend/src/features/graph/lib/ambient-motion.ts`** (Task 5)

```ts
export const MOTION_NODE_LIMIT = 2000
export const MOTION_FPS = 30
export function motionAllowed(env: { reducedMotion: boolean; nodeCount: number; hidden: boolean }): boolean
export function startAmbientMotion(opts: { nodeCount: number; onFrame: (timeSec: number) => void }): () => void // stop
```

**C6 — `frontend/src/features/graph/lib/constellation-runner.ts`** (Task 6)

```ts
export interface ConstellationRunner {
  readonly classification: Classification
  readonly coreRadius: number
  readonly outer: OuterLayout
  start(): void
  stop(): void
  kill(): void
  isRunning(): boolean
}
export function createConstellationRunner(
  graph: Graph,
  opts: { layoutMs: number; fa2Settings: Record<string, unknown>; onStop?: () => void },
): ConstellationRunner
export function constellationFa2Settings(
  graph: Graph,
  tier: { slowDown: number; barnesHutOptimize: boolean },
): Record<string, unknown> // { ...inferSettings(graph), linLogMode: true, outboundAttractionDistribution: false, strongGravityMode: true, gravity: 1, scalingRatio: 10, slowDown, barnesHutOptimize }
```

On construction it writes `_role`, `brightness` and `phase` on every node, writes `x`/`y` for satellite and halo nodes, and fits the core inside `coreRadius`. It never writes `type`, `color` or `borderColor`.

**C7 — `frontend/src/features/code/components/code-glow-canvas.tsx`** (Task 10)

```ts
export interface CodeGlowCanvasProps {
  graph: DemoCodeGraph
  colorBy: "community" | "kind"
  selectedId: string | null
  onSelect: (id: string | null) => void
  visibleIds: Set<string> | null
  hiddenKinds?: ReadonlySet<CodeNodeKind>
  blastIds: Set<string> | null
  highlightCommunity: string | null
  processIds: Set<string> | null
  zoom: number // 1 = fitted view
}
export type CanvasKeyAction =
  | { type: "zoom"; factor: number }
  | { type: "pan"; dx: number; dy: number }
  | { type: "fit" }
  | { type: "clear" }
export function canvasKeyAction(key: string): CanvasKeyAction | null
export const KIND_CHART: Record<CodeNodeKind, 1 | 2 | 3>
export function drawnGraph(graph: DemoCodeGraph, hiddenKinds?: ReadonlySet<CodeNodeKind>): { nodes: DemoCodeNode[]; edges: DemoCodeEdge[] }
export function codeNodeColor(node: DemoCodeNode, colorBy: "community" | "kind", communities: DemoCodeCommunity[], chart: string[]): string
export function isDimmed(node: DemoCodeNode, visibleIds: Set<string> | null, highlightCommunity: string | null): boolean
export function showsLabel(o: { selected: boolean; blast: boolean; process: boolean; degree: number; cameraRatio: number }): boolean
export function CodeGlowCanvas(props: CodeGlowCanvasProps): JSX.Element
```

**C8 — `frontend/src/test/code-glow-canvas-stub.tsx`** (Task 12): `CodeGlowCanvasStub(props: CodeGlowCanvasProps)` names its group from `drawnGraph(graph, hiddenKinds)` (C7) and renders one `button` named `${name} (${kind})` per drawn node, calling `onSelect(id)`.

**C9 — `layoutSignature(memoryIds: string[], entityIds?: string[]): string`** in `frontend/src/features/graph/lib/graph-utils.ts` (Task 7), with the `spacing` and `clusterTightness` parameters removed.

**C10 — `restEdgeColor(hex: string, isDark: boolean): string`** in `frontend/src/features/graph/lib/graph-colors.ts` (Task 8): `hexToRgba(hex, isDark ? 0.08 : 0.12)`, the at-rest edge colour of both 2D canvases.

**C11 — the A23 measurement** (Tasks 7 and 8). Start Storybook as a tracked background task (`cd frontend && npx storybook dev -p 6006 --ci`, record its PID). Through the Playwright MCP tools at 1920x1080, load `http://localhost:6006/iframe.html?id=graph-graph2drenderer--scale20k&viewMode=story` (confirm the id in Storybook's sidebar) three times; after each load read the `graph-ready` mark that `ScaleHarness`'s `onReady` sets, with `browser_evaluate`:

```js
() => new Promise((resolve) => {
  const read = () => {
    const m = performance.getEntriesByName("graph-ready")[0]
    if (m) resolve(m.startTime)
    else setTimeout(read, 100)
  }
  read()
})
```

Take the median of the three. The ledger is the file `bash <plugin-root>/scripts/dforge-path ledger docs/dforge/plans/2026-11-18-constellation-graphs.md` prints. Kill Storybook when done (`pkill -P <pid>; kill <pid>`).

## Assumptions (evidence)

- sigma enables blending inside each program's `renderProgram` and sets `blendFunc(ONE, ONE_MINUS_SRC_ALPHA)` once per context, so a program can switch blending for its own draw: `frontend/node_modules/sigma/dist/index-5d7c4e29.cjs.dev.js:354-370`, `frontend/node_modules/sigma/dist/sigma.cjs.dev.js:2888` (sigma 3.0.3, read 2026-11-18). `ProgramInfo.isPicking` exists: `frontend/node_modules/sigma/dist/declarations/src/rendering/utils.d.ts:5`.
- `scheduleRender()` redraws without re-running reducers: `render()` processes only when `needToProcess` is set (`sigma.cjs.dev.js` around line 2430; `scheduleRender` at line 3327), read 2026-11-18.
- The graphology ForceAtlas2 worker honours a node `fixed` flag (`frontend/node_modules/graphology-layout-forceatlas2/helpers.js:144`), but the runner simulates a separate core-only graph instead, so no halo node costs simulation time.
- The live code graph is an SVG capped by the server at 2,000 nodes before folding to files: `backend/app/services/code_query.py` (`CODE_GRAPH_AUTO_LIMIT = 2000`), read 2026-11-18. Neither code host passes anything but `zoom` to steer the camera; the real host passes `zoom={1}`, `center={null}`, `playing={false}` (`real-code-graph-view.tsx:483-485`).
- `features/graph/components/code-graph-renderer.tsx` is imported by nothing (`rg -l "code-graph-renderer"`, 2026-11-18); it is left in place.
- Host tests click SVG nodes by label (`real-code-graph-view.test.tsx` "selecting a symbol node…", "runs blast radius…", and the filter test's `getByRole("button", { name: "rrf_fuse (function)" })`); Task 12 keeps them meaningful with the C8 stub. Both hosts label their layout control `aria-label="Graph layout"` (`code-graph-tab.tsx:441`, `real-code-graph-view.tsx:369`); the demo explorer starts with every folder collapsed (`code-explorer.tsx:53`).
- The Playwright MCP tools (`mcp__playwright__*`) are available in this session (2026-11-18) and drive Storybook for the A23 measurement and the board screenshots.
- `hexToRgba` returns `rgba(r,g,b,a)` without spaces (`graph-colors.ts:223-228`), which C10's test pins.
- Plan review round 1 (judge-opus, 2026-11-18) scored executability 10, assumptions 11: borderline. Every Critical and Important finding was fixed in place; the review cap at this depth is one round, so no second round ran.
- Ruling (judge-opus, `.dforge/rulings-preexec-1-report.md`, 2026-11-18): proceed without real-data verification; register row 3 holds the tuning; the run's final message names row 3, says the look on the 192.168.0.199 corpus is unchecked, and lists `CORE_MIN`, `CORE_K`, `CLUMP_R0`, `HALO_GAP`, `HALO_C` as the constants to tune.
- Theme mode is `data-mode` on `<html>` (`frontend/src/styles/globals.css`, `[data-mode="dark"]` selectors), read 2026-11-18.
- Storybook stories are not vitest tests: `frontend/vitest.config.ts` has no Storybook plugin.
- The spec's riskiest assumption (the real component split) is **unverified, and cannot be verified from this host**: this host's production database holds no memories (the `memories` COPY block of `/root/darkmem-backups/darkmem-20261118-033000.sql.gz` is empty, checked 2026-11-18), and the owner's corpus on 192.168.0.199 (4,837 memories per `memory_stats`, 2026-11-18) exposes no vectors over MCP. Task 1 proves the fallbacks (A2) and the placement invariants on every shape, including a k-nearest-neighbour graph built like `backend/app/utils/graph_knn.py` (top-5 above a threshold); `CORE_MIN` stays 8 (A24, confirmed). Tuning on the real corpus is a deferred register row.
- The Task check compares against `chore/darkraise-ui-7`, the run's base.

## Task index

1. Constellation layout module
2. Graph canvas tokens
3. Glow node program
4. Nebula backdrop
5. Ambient motion loop
6. Constellation runner
7. Memory renderer inputs without layout sliders
8. Memory 2D renderer on the constellation
9. Memory toolbar without layout sliders
10. Code glow canvas
11. Constellation state boards
12. Code hosts on the glow canvas

---

### Task 1: Constellation layout module

**Files:**
- Create: `frontend/src/features/graph/lib/constellation-layout.ts`
- Test: `frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts`

**Interfaces:**
- Consumes: `seededUnit` from `frontend/src/features/graph/lib/code-graph-theme.ts` (existing).
- Produces: C1.

**UI/UX:** UX-1

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest"
import {
  classify,
  coreRadius,
  fitCore,
  placeOuter,
  CORE_MIN,
  HALO_MIN_OUTER,
  SATELLITE_RING_START,
  type ConstellationEdge,
  type Point,
} from "../constellation-layout"

const ids = (prefix: string, n: number) =>
  Array.from({ length: n }, (_, i) => `${prefix}${i}`)
const chain = (nodes: string[]): ConstellationEdge[] =>
  nodes.slice(1).map((id, i) => ({ source: nodes[i]!, target: id }))
const dist = (p: Point) => Math.hypot(p.x, p.y)

// A deterministic stand-in for Math.random, so failures reproduce.
function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 2 ** 32
  }
}

// Built the way backend/app/utils/graph_knn.py builds similarity edges: each
// node keeps its top-5 neighbours by cosine similarity above a threshold.
function knnGraph(n: number, clusters: number, outliers: number, threshold: number) {
  const rand = rng(7)
  const dim = 16
  const centres = Array.from({ length: clusters }, () =>
    Array.from({ length: dim }, () => rand() * 2 - 1),
  )
  const vecs: number[][] = []
  for (let i = 0; i < n; i++) {
    const c = centres[i % clusters]!
    vecs.push(c.map((v) => v + (rand() - 0.5) * 0.6))
  }
  for (let i = 0; i < outliers; i++) vecs.push(Array.from({ length: dim }, () => rand() * 2 - 1))
  const unit = vecs.map((v) => {
    const len = Math.hypot(...v)
    return v.map((x) => x / len)
  })
  const nodeIds = unit.map((_, i) => `k${i}`)
  const edges: ConstellationEdge[] = []
  unit.forEach((a, i) => {
    const sims = unit
      .map((b, j) => ({ j, s: j === i ? -2 : a.reduce((t, x, d) => t + x * b[d]!, 0) }))
      .sort((p, q) => q.s - p.s)
      .slice(0, 5)
      .filter((p) => p.s >= threshold)
    for (const p of sims) edges.push({ source: nodeIds[i]!, target: nodeIds[p.j]! })
  })
  return { nodeIds, edges }
}

describe("classify", () => {
  it("puts components of CORE_MIN or more in the core, smaller ones in satellites, lone nodes in the halo", () => {
    const big = ids("c", CORE_MIN)
    const small = ids("s", CORE_MIN - 1)
    const pair = ids("p", 2)
    const lone = ids("h", 3)
    const c = classify(
      [...big, ...small, ...pair, ...lone],
      [...chain(big), ...chain(small), ...chain(pair)],
    )
    expect(CORE_MIN).toBe(8)
    for (const id of big) expect(c.role.get(id)).toBe("core")
    for (const id of [...small, ...pair]) expect(c.role.get(id)).toBe("satellite")
    for (const id of lone) expect(c.role.get(id)).toBe("halo")
    expect(c.satellites).toHaveLength(2)
  })

  it("promotes the largest component to the core when none reaches CORE_MIN", () => {
    const a = ids("a", 5)
    const b = ids("b", 3)
    const c = classify([...a, ...b, "x"], [...chain(a), ...chain(b)])
    expect(a.every((id) => c.role.get(id) === "core")).toBe(true)
    expect(b.every((id) => c.role.get(id) === "satellite")).toBe(true)
    expect(c.role.get("x")).toBe("halo")
  })

  it("makes every node halo when there are no edges", () => {
    const c = classify(ids("n", 10), [])
    expect(c.core).toHaveLength(0)
    expect(c.satellites).toHaveLength(0)
    expect(c.halo).toHaveLength(10)
  })

  it("ignores self-loops and edges to absent nodes", () => {
    const c = classify(["a", "b"], [
      { source: "a", target: "a" },
      { source: "a", target: "ghost" },
    ])
    expect(c.role.get("a")).toBe("halo")
    expect(c.role.get("b")).toBe("halo")
  })

  it("moves a memory to the halo once its last edge is filtered out", () => {
    const core = ids("c", CORE_MIN)
    const before = classify([...core, "m"], [...chain(core), { source: "m", target: "c0" }])
    expect(before.role.get("m")).toBe("core")
    const after = classify([...core, "m"], chain(core))
    expect(after.role.get("m")).toBe("halo")
  })

  it("assigns every node of a k-nearest-neighbour graph exactly one role", () => {
    const { nodeIds, edges } = knnGraph(200, 8, 30, 0.5)
    const c = classify(nodeIds, edges)
    expect(c.core.length + c.satellites.flat().length + c.halo.length).toBe(nodeIds.length)
    expect(new Set([...c.core, ...c.satellites.flat(), ...c.halo]).size).toBe(nodeIds.length)
  })
})

describe("placeOuter", () => {
  const scene = () => {
    const core = ids("c", 40)
    const sats = Array.from({ length: 40 }, (_, k) => ids(`s${k}_`, 2 + (k % 6)))
    const halo = ids("h", 300)
    const c = classify([...core, ...sats.flat(), ...halo], [...chain(core), ...sats.flatMap(chain)])
    return { c, sats, halo, R: coreRadius(c.core.length) }
  }

  it("keeps every satellite and halo node beyond the satellite ring start", () => {
    const { c, sats, halo, R } = scene()
    const out = placeOuter(c, R)
    for (const id of [...sats.flat(), ...halo]) {
      expect(dist(out.positions.get(id)!)).toBeGreaterThan(SATELLITE_RING_START * R)
    }
    expect(out.haloOuter).toBeGreaterThanOrEqual(HALO_MIN_OUTER * R)
    expect(out.haloInner).toBeGreaterThanOrEqual(out.satelliteOuter)
  })

  it("never overlaps two satellite clumps", () => {
    const { c, R } = scene()
    const out = placeOuter(c, R)
    const discs = c.satellites.map((members) => {
      const pts = members.map((id) => out.positions.get(id)!)
      const cx = pts.reduce((t, p) => t + p.x, 0) / pts.length
      const cy = pts.reduce((t, p) => t + p.y, 0) / pts.length
      const r = Math.max(...pts.map((p) => Math.hypot(p.x - cx, p.y - cy)))
      return { cx, cy, r }
    })
    for (let i = 0; i < discs.length; i++) {
      for (let j = i + 1; j < discs.length; j++) {
        const a = discs[i]!
        const b = discs[j]!
        expect(Math.hypot(a.cx - b.cx, a.cy - b.cy)).toBeGreaterThan(a.r + b.r)
      }
    }
  })

  it("places a halo node by its id alone", () => {
    const core = ids("c", 20)
    const a = classify([...core, "h1", "h2", "h3"], chain(core))
    const b = classify([...core, "h1", "h9"], chain(core))
    const R = coreRadius(core.length)
    const pa = placeOuter(a, R)
    const pb = placeOuter(b, R)
    expect(pa.haloInner).toBe(pb.haloInner)
    expect(pa.haloOuter).toBe(pb.haloOuter)
    expect(pa.positions.get("h1")).toEqual(pb.positions.get("h1"))
  })

  it("fills a full disc from the centre when there is no core", () => {
    const c = classify(ids("n", 50), [])
    const out = placeOuter(c, coreRadius(0))
    expect(coreRadius(0)).toBe(0)
    expect(out.haloInner).toBe(0)
    expect(out.positions.size).toBe(50)
    for (const p of out.positions.values()) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true)
      expect(dist(p)).toBeLessThanOrEqual(out.haloOuter)
    }
  })

  it("keeps every other clump in place when the last-placed clump goes", () => {
    const core = ids("c", 30)
    const sats = Array.from({ length: 12 }, (_, k) => ids(`s${k}_`, 7 - (k % 5)))
    const withAll = classify([...core, ...sats.flat()], [...chain(core), ...sats.flatMap(chain)])
    const last = withAll.satellites[withAll.satellites.length - 1]!
    const keptSats = sats.filter((s) => !s.some((id) => last.includes(id)))
    const without = classify([...core, ...keptSats.flat()], [...chain(core), ...keptSats.flatMap(chain)])
    const R = coreRadius(core.length)
    const a = placeOuter(withAll, R)
    const b = placeOuter(without, R)
    for (const id of keptSats.flat()) expect(b.positions.get(id)).toEqual(a.positions.get(id))
  })

  it("is deterministic", () => {
    const { c, R } = scene()
    expect([...placeOuter(c, R).positions]).toEqual([...placeOuter(c, R).positions])
  })

  it("classifies and places 20,000 nodes and 110,000 edges within 50 ms", () => {
    const rand = rng(11)
    const n = 20_000
    const nodeIds = ids("n", n)
    const edges: ConstellationEdge[] = []
    for (let i = 0; i < 110_000; i++) {
      edges.push({ source: nodeIds[Math.floor(rand() * 12_000)]!, target: nodeIds[Math.floor(rand() * 12_000)]! })
    }
    const run = () => {
      const t0 = performance.now()
      const c = classify(nodeIds, edges)
      placeOuter(c, coreRadius(c.core.length))
      return performance.now() - t0
    }
    run()
    expect(Math.min(run(), run(), run())).toBeLessThanOrEqual(50)
  })
})

describe("fitCore", () => {
  it("centres the core on the origin with its farthest node at R", () => {
    const pos = new Map<string, Point>([
      ["a", { x: 100, y: 100 }],
      ["b", { x: 300, y: -50 }],
      ["c", { x: -20, y: 400 }],
    ])
    const fitted = [...fitCore(pos, 10).values()]
    const cx = fitted.reduce((t, p) => t + p.x, 0) / fitted.length
    const cy = fitted.reduce((t, p) => t + p.y, 0) / fitted.length
    expect(Math.abs(cx)).toBeLessThan(1e-9)
    expect(Math.abs(cy)).toBeLessThan(1e-9)
    for (const p of fitted) expect(dist(p)).toBeLessThanOrEqual(10 + 1e-9)
    expect(Math.max(...fitted.map(dist))).toBeCloseTo(10)
  })

  it("leaves a single node at the origin", () => {
    expect(fitCore(new Map([["a", { x: 5, y: 9 }]]), 10).get("a")).toEqual({ x: 0, y: 0 })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts`
Expected: FAIL — cannot resolve `../constellation-layout`.

- [ ] **Step 3: Implement**

1. `classify(nodeIds, edges)`: union-find with path compression over the node set; skip self-loops and edges whose endpoint is not in `nodeIds`; count degree over kept edges. Components of size ≥ `CORE_MIN` form the core; if none, the largest component of size ≥ 2 does (ties by the smallest member id). Remaining components of size ≥ 2 are satellites, ordered by size desc then smallest member id; members sorted by degree desc then id. Size-1 components are halo. Every node appears in exactly one role.
2. `coreRadius(n)`: `0` for `n === 0`, else `CORE_K * Math.sqrt(n)` with a named constant `CORE_K` (start at 10).
3. Named constants with these starting values: `CORE_K = 10`, `CLUMP_R0 = 3`, `HALO_GAP = 0.25`, `HALO_C = 6`. With them the `HALO_MIN_OUTER · R` floor dominates small halos (for `R = 10·√20`, `haloInner + 6·√3 < 2.6·R`), which is what keeps a halo node's radii, and so its position, fixed when a few halo nodes come and go (A3); a large halo widens the annulus instead.
4. `placeOuter(c, R)`: satellite clump *j* is a sunflower: member *i* (in `c.satellites[j]` order) at radius `CLUMP_R0 * Math.sqrt(i)` and angle `i * GOLDEN_ANGLE`; the clump radius is its largest member radius plus `CLUMP_R0`. Clumps are placed one by one in `c.satellites` order. Each starts at angle `seededUnit(firstMemberId, 3) * 2π` and centre radius `SATELLITE_RING_START * R + clumpRadius + CLUMP_R0` (with `R = 0`: `CLUMP_R0 + clumpRadius`). While it overlaps an already placed clump (centre distance ≤ sum of radii + `CLUMP_R0`), its centre radius grows by `clumpRadius + CLUMP_R0`. A clump therefore never depends on clumps placed after it. `satelliteOuter` is the largest `centre radius + clump radius`, or `SATELLITE_RING_START * R` when there are no satellites. `haloInner = 0` when `R === 0` and there are no satellites, else `satelliteOuter + HALO_GAP · R`. `haloOuter = max(HALO_MIN_OUTER * R, haloInner + HALO_C * Math.sqrt(halo count))`. A halo node sits at angle `seededUnit(id, 1) * 2π` and radius `Math.sqrt(haloInner² + seededUnit(id, 2) * (haloOuter² − haloInner²))`. Output is centred on the origin.
5. `fitCore(positions, R)`: translate the centroid to the origin, then scale uniformly so the farthest node lies at exactly `R`; a single node, or all nodes coincident, lands on the origin.
6. Export the C1 names exactly; no DOM, graphology or sigma imports. The k-nearest-neighbour test proves only that every node gets one role; it is not evidence of how the real corpus splits (ruling, see Assumptions).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/constellation-layout.ts frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts
git commit -m "feat(graph): add the constellation layout"
```

### Task 2: Graph canvas tokens

**Files:**
- Modify: `frontend/src/styles/globals.css` (beside the existing `:root` / `[data-mode="dark"]` `--primary-text` block)
- Modify: `frontend/src/features/graph/lib/code-graph-theme.ts` (`GraphThemeTokens`, `FALLBACK`, `resolveGraphTokens`)
- Test: `frontend/src/features/graph/lib/__tests__/code-graph-theme.test.tsx`

**Interfaces:**
- Consumes: none.
- Produces: C2.

**UI/UX:** UI-1

**Implementer:** dforge:impl-sonnet-medium
**Evaluation:** files 1 - spec 1 - coupling 2 - risk 0 = 4

- [ ] **Step 1: Extend the test `frontend/src/features/graph/lib/__tests__/code-graph-theme.test.tsx::resolveGraphTokens`**

Add to `DARK_TOKENS`:

```ts
  "--graph-canvas": "258 35% 4%",
  "--graph-nebula": "266 75% 42%",
```

Add to the "resolves dark tokens to hex with primaryHue and isDark" case:

```ts
    expect(t.canvas).toBe(hslToHex(258, 35, 4))
    expect(t.nebula).toBe(hslToHex(266, 75, 42))
```

Add to the "falls back to sane defaults on empty values (no NaN)" case:

```ts
    expect(t.canvas).toMatch(HEX)
    expect(t.nebula).toMatch(HEX)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/code-graph-theme.test.tsx`
Expected: FAIL — `t.canvas` is undefined.

- [ ] **Step 3: Implement**

1. In `globals.css`, add (configuration values, verbatim):

```css
:root {
  --graph-canvas: 40 33% 98%;
  --graph-nebula: 262 70% 88%;
}
[data-mode="dark"] {
  --graph-canvas: 258 35% 4%;
  --graph-nebula: 266 75% 42%;
}
```

2. In `code-graph-theme.ts`, add `canvas` and `nebula` to `GraphThemeTokens`, add fallbacks to `FALLBACK` (light values above), and fill both in `resolveGraphTokens` through the existing `triplet()` helper. Every other field is unchanged; `isDark` still derives from `--background`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/code-graph-theme.test.tsx && npx tsc -b`
Expected: PASS, typecheck clean (any object literal typed `GraphThemeTokens` elsewhere gains the two fields).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/globals.css frontend/src/features/graph/lib/code-graph-theme.ts frontend/src/features/graph/lib/__tests__/code-graph-theme.test.tsx
git commit -m "feat(graph): add graph canvas and nebula tokens"
```

### Task 3: Glow node program

**Files:**
- Create: `frontend/src/features/graph/lib/node-glow-program.ts`
- Test: `frontend/src/features/graph/lib/__tests__/node-glow-program.test.ts`

**Interfaces:**
- Consumes: none (sigma's `NodeCircleProgram`, as `node-circle-bordered-program.ts` extends it).
- Produces: C3.

**UI/UX:** UI-2

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi } from "vitest"

// sigma reads WebGL enums off the global constructors at module load; the test
// DOM ships neither. Real GL constant values.
const GL = {
  FLOAT: 0x1406,
  UNSIGNED_BYTE: 0x1401,
  TRIANGLES: 0x0004,
  ONE: 1,
  ONE_MINUS_SRC_ALPHA: 0x0303,
  BLEND: 0x0be2,
}
Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })

type Attr = { name: string; size: number; type: number }
type Proto = {
  renderProgram: (params: unknown, info: unknown) => void
  getDefinition: () => { ATTRIBUTES: Attr[] }
  processVisibleItem: (nodeIndex: number, start: number, data: unknown) => void
  setUniforms: (params: unknown, info: unknown) => void
}

const load = async (additive: boolean, time = 0) => {
  const { createNodeGlowProgram } = await import("../node-glow-program")
  const Program = createNodeGlowProgram({ additive, clock: { time } })
  return Program.prototype as unknown as Proto
}
const fakeGl = () => ({
  ...GL,
  enable: vi.fn(),
  useProgram: vi.fn(),
  blendFunc: vi.fn(),
  uniform1f: vi.fn(),
  uniform2f: vi.fn(),
  uniformMatrix3fv: vi.fn(),
})
const fakeThis = () => ({ setUniforms: vi.fn(), drawWebGL: vi.fn(), METHOD: GL.TRIANGLES })

describe("node glow program", () => {
  it("draws its normal pass additively in the dark theme and restores sigma's blending", async () => {
    const proto = await load(true)
    const gl = fakeGl()
    const self = fakeThis()
    proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: false })
    expect(gl.blendFunc.mock.calls).toEqual([
      [GL.ONE, GL.ONE],
      [GL.ONE, GL.ONE_MINUS_SRC_ALPHA],
    ])
    expect(self.drawWebGL).toHaveBeenCalledTimes(1)
    const [first, second] = gl.blendFunc.mock.invocationCallOrder
    const draw = self.drawWebGL.mock.invocationCallOrder[0]!
    expect(first!).toBeLessThan(draw)
    expect(draw).toBeLessThan(second!)
  })

  it("never touches the blend function on the picking pass", async () => {
    const proto = await load(true)
    const gl = fakeGl()
    const self = fakeThis()
    proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: true })
    expect(gl.blendFunc).not.toHaveBeenCalled()
    expect(self.drawWebGL).toHaveBeenCalledTimes(1)
  })

  it("never draws additively in the light theme", async () => {
    const proto = await load(false)
    const gl = fakeGl()
    proto.renderProgram.call(fakeThis(), {}, { gl, program: {}, isPicking: false })
    expect(gl.blendFunc).not.toHaveBeenCalled()
  })

  it("packs brightness and phase per node, defaulting brightness to 1", async () => {
    const proto = await load(true)
    const attrs = proto.getDefinition.call({}).ATTRIBUTES
    const slots = attrs.flatMap((a) =>
      a.type === GL.UNSIGNED_BYTE ? [a.name] : (Array(a.size).fill(a.name) as string[]),
    )
    expect(slots).toEqual(expect.arrayContaining(["a_position", "a_size", "a_color", "a_id", "a_brightness", "a_phase"]))
    const self = { array: new Float32Array(slots.length * 2) }
    proto.processVisibleItem.call(self, 0, 0, { x: 1, y: 2, size: 3, color: "#ff0000", brightness: 0.45, phase: 0.25 })
    proto.processVisibleItem.call(self, 1, slots.length, { x: 0, y: 0, size: 1, color: "#00ff00" })
    expect(self.array[slots.indexOf("a_brightness")]).toBeCloseTo(0.45)
    expect(self.array[slots.indexOf("a_phase")]).toBeCloseTo(0.25)
    expect(self.array[slots.length + slots.indexOf("a_brightness")]).toBe(1)
  })

  it("feeds the shared clock to u_time", async () => {
    const proto = await load(true, 12.5)
    const gl = fakeGl()
    proto.setUniforms.call(
      {},
      { matrix: new Float32Array(9), sizeRatio: 1, correctionRatio: 1, pixelRatio: 1, zoomRatio: 1, width: 10, height: 10, downSizingRatio: 1 },
      { gl, uniformLocations: { u_time: "T", u_matrix: "M", u_sizeRatio: "S", u_correctionRatio: "C" } },
    )
    expect(gl.uniform1f).toHaveBeenCalledWith("T", 12.5)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/node-glow-program.test.ts`
Expected: FAIL — cannot resolve `../node-glow-program`.

- [ ] **Step 3: Implement**

1. `createNodeGlowProgram({ additive, clock })` returns a class extending sigma's `NodeCircleProgram` (as `NodeCircleBorderedProgram` does).
2. `getDefinition()`: the parent's definition with its own shaders, `UNIFORMS` extended by `u_time`, and `ATTRIBUTES` `a_position` (2 FLOAT), `a_size` (1 FLOAT), `a_color` (4 UNSIGNED_BYTE normalised), `a_id` (4 UNSIGNED_BYTE normalised), `a_brightness` (1 FLOAT), `a_phase` (1 FLOAT).
3. Vertex shader: the quad radius is the node radius times `GLOW_SPREAD` (3). Fragment shader: a solid core disc of the node radius with a soft one-pixel edge plus a Gaussian falloff to the quad edge. Colour alpha is multiplied by `a_brightness`; a halo node (`a_brightness < 0.5`) varies by ±30% as `sin(2π·(u_time / period + a_phase))`, with `period = 3.0 + 4.0·a_phase` seconds. In `PICKING_MODE`, output the id colour inside the core disc only and transparent elsewhere. When built with `additive: false`, compile with a `LIGHT_MODE` define: no falloff beyond the soft edge, and halo nodes at alpha 0.55.
4. `processVisibleItem`: write position, size, packed colour, packed id (as the bordered program does), then `brightness ?? 1` and `phase ?? 0` from the display data.
5. `setUniforms(params, info)`: call the parent's, then `gl.uniform1f(uniformLocations.u_time, clock.time)`.
6. `renderProgram(params, info)`: when `additive && !info.isPicking`, set `gl.blendFunc(gl.ONE, gl.ONE)`, call the parent's, then restore `gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)`. Otherwise call the parent's only.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/node-glow-program.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/node-glow-program.ts frontend/src/features/graph/lib/__tests__/node-glow-program.test.ts
git commit -m "feat(graph): add a glow node program"
```

### Task 4: Nebula backdrop

**Files:**
- Create: `frontend/src/features/graph/lib/graph-backdrop.ts`
- Test: `frontend/src/features/graph/lib/__tests__/graph-backdrop.test.ts`

**Interfaces:**
- Consumes: C1's `Point` type.
- Produces: C4.

**UI/UX:** UI-1

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi, afterEach } from "vitest"
import {
  attachBackdrop,
  coreOnScreen,
  nebulaGeometry,
  NEBULA_MIN_PX,
  NEBULA_SCALE,
} from "../graph-backdrop"

afterEach(() => vi.restoreAllMocks())

function fakeCtx() {
  const gradient = { addColorStop: vi.fn() }
  const fills: string[] = []
  const ctx = {
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    createRadialGradient: vi.fn(() => gradient),
    set fillStyle(v: string | object) {
      if (typeof v === "string") fills.push(v)
    },
  }
  return { ctx, gradient, fills }
}

function fakeHost() {
  const container = document.createElement("div")
  const sigmaLayer = document.createElement("canvas")
  container.appendChild(sigmaLayer)
  const handlers = new Set<() => void>()
  const camera = {
    on: vi.fn((_: "updated", fn: () => void) => handlers.add(fn)),
    off: vi.fn((_: "updated", fn: () => void) => handlers.delete(fn)),
  }
  return {
    container,
    sigmaLayer,
    handlers,
    camera,
    host: {
      getContainer: () => container,
      getCamera: () => camera,
      getDimensions: () => ({ width: 400, height: 300 }),
    },
  }
}

describe("nebulaGeometry", () => {
  it("centres on the core and spans NEBULA_SCALE times its on-screen radius", () => {
    expect(NEBULA_SCALE).toBe(2.2)
    expect(nebulaGeometry({ x: 120, y: 80 }, 100)).toEqual({ x: 120, y: 80, r: 220 })
  })

  it("keeps a visible glow when the core is tiny or absent", () => {
    expect(nebulaGeometry({ x: 0, y: 0 }, 0).r).toBe(NEBULA_MIN_PX)
  })
})

describe("coreOnScreen", () => {
  it("measures the core from the graph origin, where the runner centres it", () => {
    const host = {
      graphToViewport: (p: { x: number; y: number }) => ({ x: 200 + 2 * p.x, y: 150 - 2 * p.y }),
    }
    expect(coreOnScreen(host, 30)).toEqual({ centre: { x: 200, y: 150 }, radiusPx: 60 })
  })
})

describe("attachBackdrop", () => {
  it("puts one canvas beneath sigma's layers and paints the canvas colour, then the nebula", () => {
    const { ctx, gradient, fills } = fakeCtx()
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as never)
    const { container, sigmaLayer, host } = fakeHost()
    attachBackdrop(host, () => ({ centre: { x: 200, y: 150 }, radiusPx: 100 }), {
      canvas: "#0a0810",
      nebula: "#6a2bd1",
      isDark: true,
    })
    expect(container.firstElementChild).not.toBe(sigmaLayer)
    expect(container.querySelectorAll("canvas")).toHaveLength(2)
    expect(fills[0]).toBe("#0a0810")
    expect(ctx.createRadialGradient).toHaveBeenCalledWith(200, 150, 0, 200, 150, 220)
    expect(gradient.addColorStop).toHaveBeenCalled()
  })

  it("repaints when the camera moves and cleans up on detach", () => {
    const { ctx } = fakeCtx()
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as never)
    const { container, handlers, camera, host } = fakeHost()
    let r = 100
    const detach = attachBackdrop(host, () => ({ centre: { x: 0, y: 0 }, radiusPx: r }), {
      canvas: "#ffffff",
      nebula: "#ccbbff",
      isDark: false,
    })
    r = 200
    for (const fn of handlers) fn()
    expect(ctx.createRadialGradient).toHaveBeenLastCalledWith(0, 0, 0, 0, 0, 440)
    detach()
    expect(camera.off).toHaveBeenCalled()
    expect(container.querySelectorAll("canvas")).toHaveLength(1)
  })

  it("does nothing harmful where 2D canvas is unavailable", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null)
    const { host } = fakeHost()
    expect(() =>
      attachBackdrop(host, () => ({ centre: { x: 0, y: 0 }, radiusPx: 0 }), {
        canvas: "#000000",
        nebula: "#000000",
        isDark: true,
      })(),
    ).not.toThrow()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/graph-backdrop.test.ts`
Expected: FAIL — cannot resolve `../graph-backdrop`.

- [ ] **Step 3: Implement**

1. `nebulaGeometry(centre, radiusPx)` returns `{ x, y, r: max(NEBULA_MIN_PX, NEBULA_SCALE · radiusPx) }`.
2. `attachBackdrop(host, getCore, colors)`: create a `canvas` absolutely positioned at inset 0 with `pointer-events: none`, insert it as the container's first child, and size it to `getDimensions()` times `devicePixelRatio` on each paint. Paint: `setTransform(dpr,…)`, `clearRect`, fill the whole canvas with `colors.canvas`, then a radial gradient from `nebulaGeometry(getCore())` with stops: centre `colors.nebula` at alpha 0.55 (dark) or 0.35 (light), mid (0.5) at a third of that alpha, edge transparent. Paint once on attach and on every camera `updated` event. With a null 2D context, skip painting but still attach and detach cleanly. The returned function detaches: `camera.off`, remove the canvas.
3. `coreOnScreen(host, R)`: `centre = host.graphToViewport({ x: 0, y: 0 })`, `radiusPx` = the distance from it to `host.graphToViewport({ x: R, y: 0 })`.
4. Export `WEBGL_UNAVAILABLE_MESSAGE` with the exact Global Constraints copy (the renderer tests assert the rendered string).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/graph-backdrop.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-backdrop.ts frontend/src/features/graph/lib/__tests__/graph-backdrop.test.ts
git commit -m "feat(graph): add the nebula backdrop layer"
```

### Task 5: Ambient motion loop

**Files:**
- Create: `frontend/src/features/graph/lib/ambient-motion.ts`
- Test: `frontend/src/features/graph/lib/__tests__/ambient-motion.test.ts`

**Interfaces:**
- Consumes: none.
- Produces: C5.

**UI/UX:** UX-4

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  motionAllowed,
  startAmbientMotion,
  MOTION_FPS,
  MOTION_NODE_LIMIT,
} from "../ambient-motion"

let reduce = false
let mediaListener: ((e: { matches: boolean }) => void) | null = null
let visibility: DocumentVisibilityState = "visible"

beforeEach(() => {
  reduce = false
  mediaListener = null
  visibility = "visible"
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"],
  })
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: query.includes("reduce") ? reduce : false,
        media: query,
        onchange: null,
        addEventListener: (_: string, fn: (e: { matches: boolean }) => void) => {
          mediaListener = fn
        },
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as unknown as MediaQueryList,
  )
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => visibility })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe("motionAllowed", () => {
  it.each([
    [{ reducedMotion: false, nodeCount: 10, hidden: false }, true],
    [{ reducedMotion: true, nodeCount: 10, hidden: false }, false],
    [{ reducedMotion: false, nodeCount: 2000, hidden: false }, false],
    [{ reducedMotion: false, nodeCount: 1999, hidden: false }, true],
    [{ reducedMotion: false, nodeCount: 10, hidden: true }, false],
  ])("%o → %s", (env, expected) => {
    expect(motionAllowed(env)).toBe(expected)
  })

  it("caps at 2,000 nodes and 30 frames a second", () => {
    expect(MOTION_NODE_LIMIT).toBe(2000)
    expect(MOTION_FPS).toBe(30)
  })
})

describe("startAmbientMotion", () => {
  it("emits frames at no more than MOTION_FPS and stops when told", () => {
    const onFrame = vi.fn()
    const stop = startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBeGreaterThan(0)
    expect(onFrame.mock.calls.length).toBeLessThanOrEqual(MOTION_FPS)
    stop()
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("never starts under reduced motion", () => {
    reduce = true
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame).not.toHaveBeenCalled()
  })

  it("never starts at MOTION_NODE_LIMIT nodes", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: MOTION_NODE_LIMIT, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame).not.toHaveBeenCalled()
  })

  it("stops when the tab is hidden", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(200)
    visibility = "hidden"
    document.dispatchEvent(new Event("visibilitychange"))
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("stops when reduced motion turns on mid-run", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(200)
    reduce = true
    mediaListener?.({ matches: true })
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("hands each frame the time alone, so a frame cannot move a node", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(500)
    expect(onFrame.mock.calls.length).toBeGreaterThan(0)
    for (const call of onFrame.mock.calls) {
      expect(call).toHaveLength(1)
      expect(typeof call[0]).toBe("number")
    }
    const times = onFrame.mock.calls.map((c) => c[0] as number)
    expect(times).toEqual([...times].sort((a, b) => a - b))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/ambient-motion.test.ts`
Expected: FAIL — cannot resolve `../ambient-motion`.

- [ ] **Step 3: Implement**

1. `motionAllowed(env)`: true only when `!reducedMotion && nodeCount < MOTION_NODE_LIMIT && !hidden`.
2. `startAmbientMotion({ nodeCount, onFrame })`: read `matchMedia("(prefers-reduced-motion: reduce)")` and `document.visibilityState`; if not allowed, return a no-op stop. Otherwise run a `requestAnimationFrame` loop that calls `onFrame(seconds since start)` only when at least `1000 / MOTION_FPS` ms (from `performance.now()`) have passed since the last call. Listen for the media query's `change` (read the event's `matches`, never re-query the list) and the document's `visibilitychange`; pause while disallowed and resume when allowed again. The returned stop cancels the frame and removes both listeners. `onFrame` receives exactly one argument.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/ambient-motion.test.ts`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/ambient-motion.ts frontend/src/features/graph/lib/__tests__/ambient-motion.test.ts
git commit -m "feat(graph): add the ambient motion loop"
```

### Task 6: Constellation runner

**Files:**
- Create: `frontend/src/features/graph/lib/constellation-runner.ts`
- Test: `frontend/src/features/graph/lib/__tests__/constellation-runner.test.ts`

**Interfaces:**
- Consumes: C1 (`classify`, `coreRadius`, `placeOuter`, `fitCore`, `ROLE_BRIGHTNESS`), `seededUnit` from `code-graph-theme.ts`.
- Produces: C6.

**UI/UX:** UX-2, UI-7

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import Graph from "graphology"

const fa2 = vi.hoisted(() => ({
  instances: [] as Array<{ graph: import("graphology").default; running: boolean }>,
}))

vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    running = false
    constructor(public graph: import("graphology").default) {
      fa2.instances.push(this)
    }
    start() {
      this.running = true
    }
    stop() {
      this.running = false
    }
    kill() {
      this.running = false
    }
    isRunning() {
      return this.running
    }
  },
}))

import { constellationFa2Settings, createConstellationRunner } from "../constellation-runner"
import { CORE_MIN, ROLE_BRIGHTNESS } from "../constellation-layout"

function buildGraph() {
  const g = new Graph()
  for (let i = 0; i < CORE_MIN; i++) {
    g.addNode(`c${i}`, { x: i * 50, y: (i % 3) * 40, type: "glow", color: "#abcdef" })
  }
  for (let i = 1; i < CORE_MIN; i++) g.addEdge(`c${i - 1}`, `c${i}`)
  g.addNode("s0", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addNode("s1", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addEdge("s0", "s1")
  g.addNode("h0", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addNode("entity:e1", { x: 0, y: 0, type: "diamond", color: "#222222", borderColor: "#123456" })
  g.addEdge("entity:e1", "c0")
  return g
}

const opts = (extra: Partial<{ onStop: () => void }> = {}) => ({
  layoutMs: 1000,
  fa2Settings: { gravity: 1 },
  ...extra,
})

beforeEach(() => {
  fa2.instances.length = 0
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame"],
  })
})
afterEach(() => vi.useRealTimers())

describe("createConstellationRunner", () => {
  it("writes each node's role and brightness, entities included", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts())
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("entity:e1", "_role")).toBe("core")
    expect(g.getNodeAttribute("s0", "_role")).toBe("satellite")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
    expect(g.getNodeAttribute("c0", "brightness")).toBe(ROLE_BRIGHTNESS.core)
    expect(g.getNodeAttribute("h0", "brightness")).toBe(ROLE_BRIGHTNESS.halo)
    expect(typeof g.getNodeAttribute("h0", "phase")).toBe("number")
  })

  it("simulates the core only", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts()).start()
    const sim = fa2.instances[0]!.graph
    expect(sim.order).toBe(CORE_MIN + 1)
    expect(sim.hasNode("h0")).toBe(false)
    expect(sim.hasNode("s0")).toBe(false)
  })

  it("places satellites and the halo before the run and never moves them", () => {
    const g = buildGraph()
    const r = createConstellationRunner(g, opts())
    const s0 = { x: g.getNodeAttribute("s0", "x"), y: g.getNodeAttribute("s0", "y") }
    const h0 = { x: g.getNodeAttribute("h0", "x"), y: g.getNodeAttribute("h0", "y") }
    expect(Math.hypot(h0.x, h0.y)).toBeGreaterThan(r.coreRadius)
    r.start()
    fa2.instances[0]!.graph.updateEachNodeAttributes((_, a) => ({
      ...a,
      x: (a.x as number) * 7 + 900,
      y: -(a.y as number) * 5,
    }))
    vi.advanceTimersByTime(1100)
    expect({ x: g.getNodeAttribute("s0", "x"), y: g.getNodeAttribute("s0", "y") }).toEqual(s0)
    expect({ x: g.getNodeAttribute("h0", "x"), y: g.getNodeAttribute("h0", "y") }).toEqual(h0)
  })

  it("keeps every core node within the core radius while running", () => {
    const g = buildGraph()
    const r = createConstellationRunner(g, opts())
    r.start()
    let i = 0
    fa2.instances[0]!.graph.updateEachNodeAttributes((_, a) => ({
      ...a,
      x: 10_000 + 400 * i++,
      y: -8_000 + 90 * i,
    }))
    vi.advanceTimersByTime(100)
    g.forEachNode((_, a) => {
      if (a._role === "core") {
        expect(Math.hypot(a.x as number, a.y as number)).toBeLessThanOrEqual(r.coreRadius + 1e-6)
      }
    })
  })

  it("stops after layoutMs and calls onStop once", () => {
    const onStop = vi.fn()
    const r = createConstellationRunner(buildGraph(), opts({ onStop }))
    r.start()
    expect(r.isRunning()).toBe(true)
    vi.advanceTimersByTime(999)
    expect(onStop).not.toHaveBeenCalled()
    vi.advanceTimersByTime(2)
    expect(onStop).toHaveBeenCalledTimes(1)
    expect(r.isRunning()).toBe(false)
  })

  it("gives every caller the same force settings", () => {
    expect(constellationFa2Settings(buildGraph(), { slowDown: 5, barnesHutOptimize: true })).toMatchObject({
      linLogMode: true,
      outboundAttractionDistribution: false,
      strongGravityMode: true,
      gravity: 1,
      scalingRatio: 10,
      slowDown: 5,
      barnesHutOptimize: true,
    })
  })

  it("never changes a node's type, colour or border", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts()).start()
    vi.advanceTimersByTime(1100)
    expect(g.getNodeAttribute("entity:e1", "type")).toBe("diamond")
    expect(g.getNodeAttribute("entity:e1", "borderColor")).toBe("#123456")
    expect(g.getNodeAttribute("entity:e1", "color")).toBe("#222222")
    expect(g.getNodeAttribute("c0", "type")).toBe("glow")
    expect(g.getNodeAttribute("c0", "color")).toBe("#abcdef")
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-runner.test.ts`
Expected: FAIL — cannot resolve `../constellation-runner`.

- [ ] **Step 3: Implement**

1. Construction: `classify` the graph's node ids and edges (every edge, membership edges included); `R = coreRadius(core count)`; `placeOuter(c, R)`. Through one `graph.updateEachNodeAttributes` pass, merge `_role`, `brightness` (`ROLE_BRIGHTNESS[role]`), `phase` (`seededUnit(id, 7)`), and, for satellite and halo nodes, `x`/`y` from the outer layout. For core nodes, merge `x`/`y` from `fitCore` of their current positions. Spread the existing attributes so `type`, `color` and `borderColor` survive.
2. `start()`: build a core-only `Graph` holding the core nodes at their current positions and the edges between them (`mergeEdge`, so duplicates and both directions collapse); create `new FA2Layout(coreGraph, { settings: opts.fa2Settings })` and start it. Run a `requestAnimationFrame` loop that, while running, reads the core graph's positions, applies `fitCore(…, R)`, and merges the fitted `x`/`y` into the rendered graph in one `updateEachNodeAttributes` pass over core nodes. After `opts.layoutMs` (one `setTimeout`), stop the worker, do one final mirror, cancel the loop and call `onStop` once.
3. `constellationFa2Settings(graph, tier)` returns exactly the C6 object; both renderers pass it as `fa2Settings`.
4. `stop()` stops early without calling `onStop`; `kill()` also kills the worker; `isRunning()` reports the worker state. A runner that is never started has already fitted the core (used when the layout signature is unchanged).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-runner.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/constellation-runner.ts frontend/src/features/graph/lib/__tests__/constellation-runner.test.ts
git commit -m "feat(graph): add the constellation runner"
```

### Task 7: Memory renderer inputs without layout sliders

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-utils.ts` (`layoutSignature`)
- Test: `frontend/src/features/graph/lib/__tests__/layout-signature.test.ts`
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (`Graph2DRendererProps`, the `layoutSignature` call, the FA2 settings block, the build callback's dependency list)
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.stories.tsx` (`ScaleHarness`)
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (the `<Graph2DRenderer>` call site only)

**Interfaces:**
- Consumes: none.
- Produces: C9; the `graph-ready` performance mark in `ScaleHarness` that C11 reads.

**Items:** 1

**UI/UX:** UX-3

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 1 = 6

- [ ] **Step 1: Extend the test `frontend/src/features/graph/lib/__tests__/layout-signature.test.ts::changes when the memory set does`**

Rewrite every `layoutSignature(<spacing>, <tightness>, MEM_OR_ARRAY, ENT_OR_ARRAY)` call in the file as `layoutSignature(MEM_OR_ARRAY, ENT_OR_ARRAY)`. Delete the `it.each([["spacing", 200, 300], ["tightness", 100, 120]])("changes when %s does", …)` case: it asserts the behaviour this task removes. In "changes when the memory set does", add:

```ts
    expect(layoutSignature.length).toBeLessThanOrEqual(2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/layout-signature.test.ts`
Expected: FAIL — the four-parameter signature receives the id arrays in its number slots and throws spreading `undefined`.

- [ ] **Step 3: Implement**

1. `layoutSignature(memoryIds, entityIds = [])`: drop the `spacing` and `clusterTightness` parameters; nothing else changes.
2. Remove `spacing` and `clusterTightness` from `Graph2DRendererProps`, the destructuring, the `layoutSignature` call and the build callback's dependency list. In the FA2 settings block, replace the two slider-driven lines with `gravity: 1` and `scalingRatio: 10` (the values the sliders' defaults produced) and delete the comment that described the sliders.
3. Page: stop passing `spacing` and `clusterTightness` to `<Graph2DRenderer>`; the toolbar keeps its props until Task 9.
4. Stories: drop the two props from `ScaleHarness`, and make its `onReady` call `performance.mark("graph-ready")` (a stable callback defined at module level, as `noop` is today), so the A23 measurement reads a mark the renderer itself triggers.
5. Record the A23 baseline now, before Task 8 changes the renderer: run C11 and write `Task 7: baseline Scale20k graph-ready <median> ms (3 loads: <a>, <b>, <c>)` to the ledger.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/layout-signature.test.ts src/features/memory-graph && npx tsc -b`
Expected: PASS; the memory-graph page tests (which mock the renderer) still pass; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-utils.ts frontend/src/features/graph/lib/__tests__/layout-signature.test.ts frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/graph/components/graph-2d-renderer.stories.tsx frontend/src/features/memory-graph/components/real-memory-graph-page.tsx
git commit -m "refactor(graph): key the 2D layout on ids alone"
```

### Task 8: Memory 2D renderer on the constellation

**Files:**
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (`buildGraph`, the sigma settings block, the edge reducer, the hull `afterRender` handler, the build effect's cleanup, the rendered container)
- Modify: `frontend/src/features/graph/lib/graph-colors.ts` (new `restEdgeColor`)
- Test: `frontend/src/features/graph/lib/__tests__/graph-colors.test.ts`
- Test: `frontend/src/features/graph/components/__tests__/graph-2d-renderer.test.tsx`

**Interfaces:**
- Consumes: C1–C6, C9.
- Produces: C10.

**Items:** 1

**UI/UX:** UI-1, UI-2, UI-3, UI-7, UX-1, UX-2, UX-4, UX-5, UX-9

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

Add to `graph-colors.test.ts` (import `restEdgeColor` beside the file's existing imports from `../graph-colors`):

```ts
describe("restEdgeColor", () => {
  it("fades an edge to 8% on a dark canvas and 12% on a light one", () => {
    expect(restEdgeColor("#ff0000", true)).toBe("rgba(255,0,0,0.08)")
    expect(restEdgeColor("#00ff00", false)).toBe("rgba(0,255,0,0.12)")
  })
})
```

Create `frontend/src/features/graph/components/__tests__/graph-2d-renderer.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { useMemo } from "react"

// sigma's programs read WebGL enums off the global constructors at module
// load; happy-dom ships neither. Real GL constant values.
const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004 }
Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })

vi.mock("sigma", () => ({
  default: class {
    constructor() {
      throw new Error("WebGL unavailable")
    }
  },
}))
vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    start() {}
    stop() {}
    kill() {}
    isRunning() {
      return false
    }
  },
}))
const motion = vi.hoisted(() => ({ start: vi.fn(() => vi.fn()) }))
vi.mock("@/features/graph/lib/ambient-motion", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/graph/lib/ambient-motion")>()),
  startAmbientMotion: motion.start,
}))

import { Graph2DRenderer } from "../graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"

const noopSelect = (_id: string | null) => {}

function Harness({ onReady }: { onReady: () => void }) {
  const { tokens, palette } = useMemoryGraphTheme()
  const graph = useMemo(() => syntheticMemoryGraph(30, 3, 2), [])
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={onReady}
        sizeMode="connections"
        colorMode="cluster"
        hullMode="none"
        entityLayerEnabled={false}
        entities={[]}
        entityRelations={[]}
        tokens={tokens}
        palette={palette}
        clusterNames={graph.clusterNames}
      />
    </div>
  )
}

describe("Graph2DRenderer without WebGL", () => {
  it("says so, still reports ready, and starts no motion", async () => {
    const onReady = vi.fn()
    render(<Harness onReady={onReady} />)
    expect(
      await screen.findByText("The graph needs WebGL, which this browser has turned off."),
    ).toBeInTheDocument()
    expect(onReady).toHaveBeenCalled()
    expect(motion.start).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/graph-colors.test.ts src/features/graph/components/__tests__/graph-2d-renderer.test.tsx`
Expected: FAIL — `restEdgeColor` is not exported, and the renderer lets sigma's error escape instead of showing the message.

- [ ] **Step 3: Implement**

1. `graph-colors.ts`: add `restEdgeColor(hex, isDark)` returning `hexToRgba(hex, isDark ? 0.08 : 0.12)`. Do not change any existing export: the 3D view uses them.
2. Memory nodes use `type: "glow"`; register `nodeProgramClasses: { diamond: NodeDiamondProgram, glow: createNodeGlowProgram({ additive: tokens.isDark, clock }) }`, keeping diamonds registered first, as today. `clock` is one `GlowClock` per mounted renderer (a `useRef`). Entities keep the diamond program and their current colours.
3. Replace the inline `FA2Layout` (`fa2Ref`, `fa2StopTimerRef` and their cleanups) with `createConstellationRunner(graph, { layoutMs: scale.layoutMs, fa2Settings: constellationFa2Settings(graph, scale), onStop: () => { hullCache.invalidate(); sigmaRef.current?.refresh() } })`, created after nodes and edges are added and before sigma is constructed, so the first frame already shows satellites and the halo. Call `runner.start()` only after sigma was constructed and only when `layoutChanged`. The hull cache reads `runner.isRunning()`. Kill the runner wherever FA2 was killed.
4. Edges: keep each edge's full-strength colour (today's `edgeBaseColor` result) as `_fullColor` and set `color` to `restEdgeColor(_fullColor-as-hex, tokens.isDark)`. For an rgba full colour, take the endpoint hex it was derived from. In the edge reducer, an edge that `edgeEmphasis` lifts (the selected or hovered neighbourhood) uses `_fullColor`.
5. Make the sigma container's background transparent, then `attachBackdrop(sigma, () => coreOnScreen(sigma, runner.coreRadius), { canvas: tokens.canvas, nebula: tokens.nebula, isDark: tokens.isDark })`. Detach on sigma's `kill`.
6. After sigma is built, `const stopMotion = startAmbientMotion({ nodeCount: graph.order, onFrame: (t) => { clock.current.time = t; sigma.scheduleRender() } })`; call `stopMotion` in the build effect's cleanup, before sigma is killed.
7. Wrap `new Sigma(...)` in a try/catch. On failure: kill the runner, set a `webglFailed` state that renders `WEBGL_UNAVAILABLE_MESSAGE` centred over the canvas area through darkraise-ui's `empty-state` (read `frontend/node_modules/darkraise-ui/dist/components/empty-state.d.ts` for its props), start no motion, attach no backdrop, and still call `onReady()`.
8. Nothing else changes: hover, selection, dimming, labels, hulls, zoom, reset and the entity overlay keep their current code paths.
9. Run C11 and write `Task 8: Scale20k graph-ready <median> ms, baseline <b> ms (<±x%>)` to the ledger, `<b>` being the ledger's `Task 7: baseline` value; A23 holds within 20%. Before killing Storybook, screenshot the `Scale2k` story in dark and in light at 1920x1080 into `.dforge/sdd/2026-11-18-constellation-graphs/boards/` (A13, A15).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph src/features/memory-graph && npx tsc -b`
Expected: PASS; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/graph/lib/graph-colors.ts frontend/src/features/graph/lib/__tests__/graph-colors.test.ts frontend/src/features/graph/components/__tests__/graph-2d-renderer.test.tsx
git commit -m "feat(graph): draw the 2D memory graph as a constellation"
```

### Task 9: Memory toolbar without layout sliders

**Files:**
- Modify: `frontend/src/features/graph/components/graph-toolbar.tsx` (`GraphToolbarProps`, the Layout section's `Tightness` and `Spacing` rows)
- Modify: `frontend/src/features/graph/components/graph-toolbar.stories.tsx`
- Modify: `frontend/src/features/graph/hooks/use-graph-layout.ts`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (the `<GraphToolbar>` props)
- Test: `frontend/src/features/graph/components/__tests__/graph-toolbar.test.tsx`

**Interfaces:**
- Consumes: C9 and Task 7's renderer, which no longer takes `spacing` or `clusterTightness`.
- Produces: none.

**Items:** 1

**UI/UX:** UI-4

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { GraphToolbar } from "../graph-toolbar"

const base = {
  viewMode: "2d" as const,
  onViewModeChange: vi.fn(),
  colorMode: "cluster" as const,
  onColorModeChange: vi.fn(),
  hullMode: "none" as const,
  onHullModeChange: vi.fn(),
  entityLayer: false,
  onEntityLayerChange: vi.fn(),
  sharedEntitiesOnly: false,
  onSharedEntitiesOnlyChange: vi.fn(),
  sizeMode: "importance" as const,
  onSizeModeChange: vi.fn(),
  similarityThreshold: 0.5,
  onSimilarityChange: vi.fn(),
  minClusterSize: 3,
  onMinClusterSizeChange: vi.fn(),
  spacing: 50,
  onSpacingChange: vi.fn(),
  onReset: vi.fn(),
}

async function openSettings() {
  await userEvent.click(screen.getByRole("button", { name: "Toggle graph settings" }))
}

describe("GraphToolbar layout rows", () => {
  it("offers no Tightness or Spacing control in 2D", async () => {
    render(<GraphToolbar {...base} viewMode="2d" />)
    await openSettings()
    expect(screen.getByText("Edges")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
    expect(screen.queryByText("Spacing")).toBeNull()
  })

  it("keeps Spacing, and only Spacing, in 3D", async () => {
    render(<GraphToolbar {...base} viewMode="3d" />)
    await openSettings()
    expect(screen.getByText("Spacing")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/components/__tests__/graph-toolbar.test.tsx`
Expected: FAIL — the 2D case still finds "Tightness" and "Spacing".

- [ ] **Step 3: Implement**

1. `GraphToolbar`: delete the `clusterTightness` / `onClusterTightnessChange` props and the `Tightness` row; render the `Spacing` row only when `viewMode === "3d"`, with the 3D range (min 30, max 200, step 10) only.
2. `useGraphLayout`: remove `nodeSpacing`, `clusterTightness`, their setters and the two debounced values; keep `spacing3D` and the rest.
3. Page: pass `spacing={layout.spacing3D}` and `onSpacingChange={layout.setSpacing3D}` to the toolbar; drop the tightness props.
4. Stories: drop the removed args.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph src/features/memory-graph && npx tsc -b`
Expected: PASS (including `graph-defaults.test.ts`); typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/components/graph-toolbar.tsx frontend/src/features/graph/components/graph-toolbar.stories.tsx frontend/src/features/graph/hooks/use-graph-layout.ts frontend/src/features/memory-graph/components/real-memory-graph-page.tsx frontend/src/features/graph/components/__tests__/graph-toolbar.test.tsx
git commit -m "feat(graph): drop the 2D layout sliders"
```

### Task 10: Code glow canvas

**Files:**
- Create: `frontend/src/features/code/components/code-glow-canvas.tsx`
- Test: `frontend/src/features/code/__tests__/code-glow-canvas.test.tsx`

**Interfaces:**
- Consumes: C1–C6, C10; `useGraphThemeTokens` (`code-graph-theme.ts`); `scaleSettings` (`graph-scale.ts`); `DemoCodeGraph`, `DemoCodeNode`, `DemoCodeEdge`, `DemoCodeCommunity`, `CodeNodeKind` (`features/code/types.ts`).
- Produces: C7.

**Items:** 2

**UI/UX:** UI-1, UI-2, UI-3, UI-5, UX-1, UX-6, UX-7, UX-8

**Implementer:** dforge:impl-sonnet-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 0 = 5

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

// sigma's programs read WebGL enums off the global constructors at module
// load; happy-dom ships neither. Real GL constant values.
const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004 }
Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })

vi.mock("sigma", () => ({
  default: class {
    constructor() {
      throw new Error("WebGL unavailable")
    }
  },
}))
vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    start() {}
    stop() {}
    kill() {}
    isRunning() {
      return false
    }
  },
}))

import {
  canvasKeyAction,
  codeNodeColor,
  CodeGlowCanvas,
  drawnGraph,
  isDimmed,
  KIND_CHART,
  showsLabel,
} from "../components/code-glow-canvas"

const GRAPH = {
  repo_id: "r1",
  nodes: [
    { id: "a", name: "main.py", kind: "file" as const, file: "main.py", community: "c1" },
    { id: "b", name: "run", kind: "function" as const, file: "main.py", community: "c1" },
  ],
  edges: [{ source: "a", target: "b", type: "CONTAINS" }],
  communities: [{ id: "c1", label: "core", chart: 1 as const }],
  processes: [],
}

const renderCanvas = (onSelect = vi.fn(), hiddenKinds?: ReadonlySet<"file">) =>
  render(
    <CodeGlowCanvas
      graph={GRAPH}
      colorBy="kind"
      selectedId="b"
      onSelect={onSelect}
      visibleIds={null}
      hiddenKinds={hiddenKinds}
      blastIds={null}
      highlightCommunity={null}
      processIds={null}
      zoom={1}
    />,
  )

describe("canvasKeyAction", () => {
  it.each([
    ["+", { type: "zoom", factor: 1.25 }],
    ["=", { type: "zoom", factor: 1.25 }],
    ["-", { type: "zoom", factor: 0.8 }],
    ["ArrowLeft", { type: "pan", dx: -1, dy: 0 }],
    ["ArrowRight", { type: "pan", dx: 1, dy: 0 }],
    ["ArrowUp", { type: "pan", dx: 0, dy: -1 }],
    ["ArrowDown", { type: "pan", dx: 0, dy: 1 }],
    ["0", { type: "fit" }],
    ["Escape", { type: "clear" }],
    ["a", null],
    ["Tab", null],
  ])("%s → %o", (key, action) => {
    expect(canvasKeyAction(key)).toEqual(action)
  })
})

describe("drawnGraph", () => {
  it("drops hidden kinds and every edge touching them", () => {
    const d = drawnGraph(GRAPH, new Set(["file"]))
    expect(d.nodes.map((n) => n.id)).toEqual(["b"])
    expect(d.edges).toHaveLength(0)
  })

  it("keeps everything when nothing is hidden", () => {
    const d = drawnGraph(GRAPH)
    expect(d.nodes).toHaveLength(2)
    expect(d.edges).toHaveLength(1)
  })
})

describe("codeNodeColor", () => {
  const chart = ["#111111", "#222222", "#333333", "#444444", "#555555"]

  it("colours by community through its chart slot", () => {
    expect(codeNodeColor(GRAPH.nodes[1]!, "community", GRAPH.communities, chart)).toBe("#111111")
  })

  it("colours by kind through the kind tiers", () => {
    expect(KIND_CHART.file).not.toBe(KIND_CHART.function)
    expect(codeNodeColor(GRAPH.nodes[0]!, "kind", GRAPH.communities, chart)).toBe(chart[KIND_CHART.file - 1])
    expect(codeNodeColor(GRAPH.nodes[1]!, "kind", GRAPH.communities, chart)).toBe(chart[KIND_CHART.function - 1])
  })
})

describe("isDimmed", () => {
  it.each([
    [null, null, false],
    [new Set(["b"]), null, true],
    [new Set(["a"]), null, false],
    [null, "c2", true],
    [null, "c1", false],
  ])("visible %o, community %s → %s", (visible, community, dimmed) => {
    expect(isDimmed(GRAPH.nodes[0]!, visible, community)).toBe(dimmed)
  })
})

describe("showsLabel", () => {
  const base = { selected: false, blast: false, process: false, degree: 0, cameraRatio: 1 }
  it.each([
    [{}, false],
    [{ selected: true }, true],
    [{ blast: true }, true],
    [{ process: true }, true],
    [{ degree: 5 }, false],
    [{ degree: 5, cameraRatio: 0.5 }, true],
    [{ degree: 4, cameraRatio: 0.5 }, false],
  ])("%o → %s", (over, shown) => {
    expect(showsLabel({ ...base, ...over })).toBe(shown)
  })
})

describe("CodeGlowCanvas", () => {
  it("is one named, focusable stop", () => {
    renderCanvas()
    const canvas = screen.getByRole("group", { name: "Code graph — 2 nodes, 1 edges" })
    expect(canvas.tabIndex).toBe(0)
    expect(screen.queryAllByRole("button")).toHaveLength(0)
  })

  it("counts only what it draws", () => {
    renderCanvas(vi.fn(), new Set(["file"]))
    expect(screen.getByRole("group", { name: "Code graph — 1 nodes, 0 edges" })).toBeInTheDocument()
  })

  it("says so when the browser has no WebGL", () => {
    renderCanvas()
    expect(
      screen.getByText("The graph needs WebGL, which this browser has turned off."),
    ).toBeInTheDocument()
  })

  it("clears the selection on Escape", () => {
    const onSelect = vi.fn()
    renderCanvas(onSelect)
    fireEvent.keyDown(screen.getByRole("group", { name: /^Code graph/ }), { key: "Escape" })
    expect(onSelect).toHaveBeenCalledWith(null)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/code/__tests__/code-glow-canvas.test.tsx`
Expected: FAIL — cannot resolve `../components/code-glow-canvas`.

- [ ] **Step 3: Implement**

1. Pure exports (C7): `canvasKeyAction` (`+`/`=` zoom 1.25, `-` zoom 0.8, arrows pan one unit, `0` fit, `Escape` clear, else `null`); `KIND_CHART`, a copy of `code-canvas.tsx`'s kind-to-tier map (Task 12 deletes the original); `drawnGraph(graph, hiddenKinds)` (nodes whose kind is not hidden, edges whose both ends survive); `codeNodeColor(node, colorBy, communities, chart)` (community → `chart[community.chart - 1]`, unknown community → `chart[0]`; kind → `chart[KIND_CHART[kind] - 1]`); `isDimmed(node, visibleIds, highlightCommunity)` (outside `visibleIds`, or not in `highlightCommunity`); `showsLabel({ selected, blast, process, degree, cameraRatio })` (any of the three flags, or `degree >= 5 && cameraRatio < 0.72`, the memory renderer's `HUB_DEGREE` and `LABEL_ZOOM_RATIO`).
2. `CodeGlowCanvas`: a `div` with `role="group"`, `tabIndex={0}`, `aria-label` `Code graph — ${nodes} nodes, ${edges} edges` from `drawnGraph`, a visible `focus-visible` ring from the `ring` token, and `onKeyDown` dispatching `canvasKeyAction`: zoom through `camera.animatedZoom`/`animatedUnzoom`, pan by 10% of the viewport through `camera.animate`, fit through `camera.animatedReset`, clear through `onSelect(null)` (clear works even when sigma failed); `preventDefault` only for handled keys.
3. Build a graphology graph from `drawnGraph`: each node gets `color` from `codeNodeColor(…, tokens.chart)`, `type: "glow"`, `size: 3 + 0.5 * Math.min(degree, 12)`, and `name`/`kind`/`file` attributes; each edge keeps its full-strength colour as `_fullColor` (`tokens.border` across communities, the source node's colour within one) and `color: restEdgeColor(_fullColor, tokens.isDark)` (C10). Create `createConstellationRunner(graph, { layoutMs: scaleSettings(graph.order, graph.size).layoutMs, fa2Settings: constellationFa2Settings(graph, scaleSettings(graph.order, graph.size)) })`.
4. `new Sigma(graph, container, { nodeProgramClasses: { glow: createNodeGlowProgram({ additive: tokens.isDark, clock }) }, defaultNodeType: "glow", renderEdgeLabels: false, labelFont: tokens.fontMono, zIndex: true, defaultDrawNodeLabel, defaultDrawNodeHover })` in a try/catch. On failure: kill the runner, render `WEBGL_UNAVAILABLE_MESSAGE` inside the group through darkraise-ui's `empty-state`, start no motion, attach no backdrop. On success: `runner.start()`.
5. `defaultDrawNodeLabel` writes the label in `tokens.fontMono` at 12px in `tokens.foreground`, stroked first with a 3px `tokens.canvas` outline (`strokeText` then `fillText`), so a label stays legible over edges and nodes. `defaultDrawNodeHover` draws `${name} · ${kind} · ${file}` from the node's attributes the same way. The node reducer sets `label` to the node's `name` when `showsLabel` holds, else `""`.
6. Reducers: a dimmed node (`isDimmed`) takes its colour at alpha 0.18 over `tokens.canvas`; an edge with either end dimmed draws at alpha 0.08; an edge touching the selected node draws `_fullColor`.
7. An overlay canvas drawn on `afterRender` (as `graph-2d-renderer.tsx` draws hulls): selection ring in `tokens.primary`, blast ring dashed `[3, 2]` in `tokens.destructive`, process ring dashed `[2, 2]` in `tokens.foreground` at 0.7 alpha, radius from `sigma.scaleSize(displayData.size)` plus 4px.
8. Pointer: click node → `onSelect(id)`; click stage → `onSelect(null)`. When `selectedId` changes to a drawn node, animate the camera to it at ratio 0.15 over 400 ms, or set it instantly under `prefers-reduced-motion: reduce`. `zoom` maps to camera ratio `1 / zoom`, animated over 200 ms.
9. After sigma is built: `attachBackdrop(sigma, () => coreOnScreen(sigma, runner.coreRadius), { canvas: tokens.canvas, nebula: tokens.nebula, isDark: tokens.isDark })` and `startAmbientMotion({ nodeCount: graph.order, onFrame: (t) => { clock.current.time = t; sigma.scheduleRender() } })`. Rebuild on `graph`, `colorBy`, `hiddenKinds` or theme change; on rebuild and unmount stop motion, detach the backdrop, kill the runner and sigma, in that order.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/code/__tests__/code-glow-canvas.test.tsx && npx tsc -b`
Expected: PASS (31 tests); typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/code/components/code-glow-canvas.tsx frontend/src/features/code/__tests__/code-glow-canvas.test.tsx
git commit -m "feat(code): add a WebGL constellation canvas"
```

### Task 11: Constellation state boards

**Files:**
- Modify: `frontend/src/features/graph/lib/synthetic-graph.ts`
- Test: `frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts`
- Create: `frontend/src/features/graph/components/constellation-board.stories.tsx`
- Create: `frontend/src/features/code/components/code-glow-canvas.stories.tsx`

**Interfaces:**
- Consumes: Task 8's `Graph2DRenderer`, C7, `syntheticMemoryGraph` (existing).
- Produces: none.

**UI/UX:** UX-5, UX-6

**Implementer:** dforge:impl-sonnet-medium
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 0 = 4

- [ ] **Step 1: Extend the test `frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts`**

Add:

```ts
import { classify } from "../constellation-layout"
import { syntheticShape } from "../synthetic-graph"

describe("syntheticShape", () => {
  const roles = (shape: Parameters<typeof syntheticShape>[0]) => {
    const g = syntheticShape(shape, 300)
    const c = classify(g.memories.map((m) => m.id), g.edges)
    return { core: c.core.length, sats: c.satellites.length, halo: c.halo.length, n: g.memories.length }
  }

  it.each([
    ["one-component", (r: ReturnType<typeof roles>) => r.core === r.n],
    ["all-orphans", (r: ReturnType<typeof roles>) => r.halo === r.n],
    ["no-orphans", (r: ReturnType<typeof roles>) => r.halo === 0 && r.core > 0],
    ["many-satellites", (r: ReturnType<typeof roles>) => r.sats >= 20],
    ["mixed", (r: ReturnType<typeof roles>) => r.core > 0 && r.sats > 0 && r.halo > 0],
  ] as const)("%s", (shape, holds) => {
    expect(holds(roles(shape))).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/synthetic-graph.test.ts`
Expected: FAIL — `syntheticShape` is not exported.

- [ ] **Step 3: Implement**

1. `syntheticShape(shape: "one-component" | "all-orphans" | "no-orphans" | "many-satellites" | "mixed", n: number)` in `synthetic-graph.ts`, returning the same `{ memories, edges, clusterNames }` shape as `syntheticMemoryGraph`, deterministic (seeded): one chain-connected component; no edges; several core components plus satellites and no lone nodes; one core plus at least 20 components of 2–7; roughly 50% core, 20% satellites, 30% halo.
2. `constellation-board.stories.tsx`, title `Graph/Constellation/Memory`: one story per state of UX-5 that Storybook can force — `OneComponent`, `AllOrphans`, `NoOrphans`, `ManySatellites`, `Mixed`, `OneNode`, `Selected` (mixed, a core node selected), `EntityLayer` (mixed with a few entities), `WebGLUnavailable`, `Scale20k` (`syntheticMemoryGraph(20000, 60, 6)`) — each through `Graph2DRenderer` with stable callbacks, as `graph-2d-renderer.stories.tsx` does. Theme via the existing Storybook theme toolbar.
3. `code-glow-canvas.stories.tsx`, title `Graph/Constellation/Code`: `Mixed`, `OneNode`, `Selected`, `BlastRadius`, `ActiveProcess`, `HighlightedCommunity`, `DepthFilter`, `HiddenKinds`, `WebGLUnavailable`, `Worst2000`, from a deterministic code graph generator inside the story file (nodes with kinds and communities, `CONTAINS` / `CALLS` edges).

4. Both `WebGLUnavailable` stories use a decorator that, while mounted, makes `HTMLCanvasElement.prototype.getContext` return `null` for `"webgl"`, `"webgl2"` and `"experimental-webgl"` and restores the original on unmount, so sigma's constructor fails as on a browser with WebGL off.
5. The host-level states of UX-6 (empty repository, folded file-level graph with the LOD banner, search-narrowed subset) live in the host pages, not the canvas: they get no story and are proven in demo mode during the walkthrough.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/synthetic-graph.test.ts && npx tsc -b`
Expected: PASS; typecheck clean. Start Storybook as a tracked background task, open each new story once through Playwright MCP to confirm it renders, screenshot each at 1920x1080 in dark and light to `.dforge/sdd/2026-11-18-constellation-graphs/boards/`, then kill Storybook.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/synthetic-graph.ts frontend/src/features/graph/lib/__tests__/synthetic-graph.test.ts frontend/src/features/graph/components/constellation-board.stories.tsx frontend/src/features/code/components/code-glow-canvas.stories.tsx
git commit -m "feat(graph): add constellation state boards"
```

### Task 12: Code hosts on the glow canvas

**Files:**
- Modify: `frontend/src/features/code/components/code-graph-tab.tsx` (imports, `layout`/`playing`/`center` state, the Layout and Play/Pause controls, the `positions` memo, the `<CodeCanvas>` call)
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx` (imports, `LAYOUTS`, `layout` state, the Layout control, the `<CodeCanvas>` call)
- Modify: `frontend/src/features/code/components/code-canvas.tsx` (keep only `chartVar`)
- Delete: `frontend/src/features/code/__tests__/code-canvas.test.tsx`
- Create: `frontend/src/test/code-glow-canvas-stub.tsx`
- Modify: `frontend/src/features/code/types.ts` (the comment above `CodeNodeKind` naming `code-canvas.tsx`)
- Modify: `frontend/src/features/code/lib/graph-derive.ts` (the doc comment naming `CodeCanvas`)
- Test: `frontend/src/features/code/__tests__/real-code-graph-view.test.tsx`, `frontend/src/features/code/__tests__/code-tabs.test.tsx`
- Create: `frontend/tests/code-graph-keyboard.spec.ts`
- Modify: `frontend/playwright.config.ts` (`DEMO_FIXTURE_SPECS`)

**Interfaces:**
- Consumes: C7.
- Produces: C8.

**Items:** 2

**UI/UX:** UI-6, UX-7, UX-8

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

This extends `real-code-graph-view.test.tsx` (its "spells out the counter and stacks its panes below lg" case) and `code-tabs.test.tsx` (`describe("CodeGraphTab")`), and adds one browser spec.

Create the stub (C8):

```tsx
import {
  drawnGraph,
  type CodeGlowCanvasProps,
} from "@/features/code/components/code-glow-canvas"

export function CodeGlowCanvasStub({ graph, hiddenKinds, onSelect }: CodeGlowCanvasProps) {
  const { nodes, edges } = drawnGraph(graph, hiddenKinds)
  return (
    <div
      role="group"
      aria-label={`Code graph — ${nodes.length} nodes, ${edges.length} edges`}
    >
      {nodes.map((n) => (
        <button
          key={n.id}
          type="button"
          aria-label={`${n.name} (${n.kind})`}
          onClick={() => onSelect(n.id)}
        />
      ))}
    </div>
  )
}
```

At the top of both test files, after the existing `vi.mock` calls:

```ts
vi.mock("@/features/code/components/code-glow-canvas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/code/components/code-glow-canvas")>()),
  CodeGlowCanvas: (await import("@/test/code-glow-canvas-stub")).CodeGlowCanvasStub,
}))
```

In `real-code-graph-view.test.tsx`, replace `expect(screen.getByText("Layout")).toBeInTheDocument()` with:

```ts
    expect(screen.queryByText("Layout")).toBeNull()
    expect(screen.queryByRole("group", { name: "Graph layout" })).toBeNull()
```

In `code-tabs.test.tsx`, add to `describe("CodeGraphTab")`:

```tsx
  it("offers one layout: no Layout switch and no Play/Pause", () => {
    render(
      <CodeGraphTab
        repoId="repo-backend"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    expect(screen.queryByRole("group", { name: "Graph layout" })).toBeNull()
    expect(screen.queryByRole("button", { name: /Play layout|Pause layout/ })).toBeNull()
    expect(screen.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })).toBeInTheDocument()
  })
```

Create `frontend/tests/code-graph-keyboard.spec.ts` (A18, against the demo Code Graph):

```ts
import { test, expect } from "@playwright/test"

test("the code graph canvas is one keyboard stop, and node choice goes through the explorer", async ({ page }) => {
  await page.goto("/code/graph")
  const canvas = page.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })
  await expect(canvas).toBeVisible()
  await expect(canvas.getByRole("button")).toHaveCount(0)

  await canvas.focus()
  await expect(canvas).toBeFocused()
  await page.keyboard.press("Tab")
  await expect(canvas).not.toBeFocused()

  // The demo explorer opens with every folder collapsed (code-explorer.tsx
  // starts `expanded` empty); open folders and files by keyboard until a
  // symbol row (a titled button with no aria-expanded) appears.
  const explorer = page.getByRole("tabpanel", { name: "Explorer" })
  const symbols = explorer.locator("button[title]:not([aria-expanded])")
  for (let i = 0; i < 8 && (await symbols.count()) === 0; i++) {
    await explorer.locator('button[aria-expanded="false"]').first().focus()
    await page.keyboard.press("Enter")
  }
  const symbol = symbols.first()
  const name = (await symbol.getAttribute("title"))!
  await symbol.focus()
  await page.keyboard.press("Enter")
  const panel = page.getByText("Selected symbol").locator("xpath=../..")
  await expect(panel.getByText(name, { exact: true })).toBeVisible()

  await canvas.focus()
  await page.keyboard.press("+")
  await page.keyboard.press("ArrowLeft")
  await page.keyboard.press("0")
  await page.keyboard.press("Escape")
  await expect(panel.getByText(name, { exact: true })).toHaveCount(0)
})
```

Add `"code-graph-keyboard.spec.ts",` to `DEMO_FIXTURE_SPECS` in `frontend/playwright.config.ts`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/code/__tests__/real-code-graph-view.test.tsx src/features/code/__tests__/code-tabs.test.tsx; python3 ../backend/scripts/e2e/run_playwright_e2e.py tests/code-graph-keyboard.spec.ts --project=demo-fixture`
Expected: FAIL — both hosts still render the Layout control and the SVG canvas, whose accessible name ends in `, force layout` and which holds node buttons.

- [ ] **Step 3: Implement**

1. Both hosts import `CodeGlowCanvas` and pass `graph`, `colorBy`, `selectedId`, `onSelect`, `visibleIds`, `hiddenKinds`, `blastIds`, `highlightCommunity`, `processIds` as they did, plus `zoom` (the demo host's zoom state; the real host `1`).
2. Remove the Layout control, the `layout` state and `LAYOUTS` from both hosts; remove the demo host's Play/Pause button and `playing` state, and its `center` state and the `positions` memo that fed it (the canvas centres on `selectedId` itself). The zoom buttons and the reset keep driving `zoom`.
3. `code-canvas.tsx` keeps only `chartVar`; `code-filters.tsx` and `code-explorer.tsx` keep importing it. Delete `CodeCanvas`, `CANVAS_W`, `CANVAS_H` and `code-canvas.test.tsx`, whose behaviours (per-node buttons, per-node focus ring) the spec retires (A18).
4. Update the two stale comments: `types.ts` names `KIND_CHART in code-canvas.tsx`, now in `code-glow-canvas.tsx`; `graph-derive.ts` names `CodeCanvas`, now `CodeGlowCanvas`.
5. The rest of both hosts (legend, counters, LOD banner, explorer, filters, analysis panel, deep links) is unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/code && npx tsc -b && npm run lint && python3 ../backend/scripts/e2e/run_playwright_e2e.py tests/code-graph-keyboard.spec.ts --project=demo-fixture`
Expected: PASS (every existing host test, with the stub standing in for WebGL, and the keyboard spec); typecheck clean; lint advisory only. Confirm the runner's vite server is gone afterwards.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/code frontend/src/test/code-glow-canvas-stub.tsx frontend/tests/code-graph-keyboard.spec.ts frontend/playwright.config.ts
git commit -m "feat(code): put both code hosts on the glow canvas"
```
