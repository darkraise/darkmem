# Constellation Graphs on Real Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dforge:subagent-driven-development for `subagent`, dforge:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 2D memory graph read like `graph.jpg` on the real 4,759-memory corpus: an adaptive role cut, scattered clumps, a thinning halo of small dots, a soft-edged core, no white saturation, hub-only labels and a 1,000-memory default.

**Architecture:** A pure role cut and placement in `constellation-layout.ts`, selected by an optional `roles` input to the shared constellation runner, which only the memory renderer passes; the code canvas keeps classifying over every edge. Per-role density control gains a halo style in the glow program. An anonymised snapshot of the cloned corpus drives the tests and the Storybook boards.

**Tech Stack:** React 19, TypeScript, sigma.js 3.0.3, graphology, graphology-layout-forceatlas2 (worker), zustand persist, vitest on happy-dom, Storybook 10, Playwright MCP for the proof.

**Spec:** docs/dforge/specs/2026-11-18-constellation-real-data-design.md

**Execution:** inline — `claude --model opus --effort high` — the hardest self-implemented task (Task 1, total 7) maps to impl-opus-high

**Parallelism:** sequential — inline execution

**Task check:** `cd frontend && npx tsc -b && npx vitest run --changed master` — rule 3: no gates.md and no suites.tsv timing, so vitest's impact selection against the run's base

**Integration check:** `cd frontend && npm run typecheck && npm test && npm run build`

**CI:** `.github/workflows/ci.yml .github/workflows/release.yml .github/workflows/cache-cleanup.yml` — platforms: uutils (ubuntu-latest), self-hosted darkmem-linux — local: `cd frontend && npm run typecheck`; `cd frontend && npm run lint`; `cd frontend && npx vite build`; `cd frontend && npx vitest run`; `cd backend && .venv/bin/ruff check app/ --select F` — uncovered: uutils (ubuntu-latest)

**Plan review:** 2026-11-18 — dforge:judge-opus — executability 11 / coherence 15 / coverage 16 / assumptions 12 (round 1)

## Global Constraints

- Only `frontend/` and `docs/dforge/ui-ux/profile.md` change. No backend change.
- Unchanged files: `graph-3d-renderer.tsx`, `memory-graph-explorer.tsx`, `demo/explore.ts`, and `labelVisible` in `features/graph/lib/focus-model.ts` (the code canvas uses it).
- Constants, verbatim from the spec: `CORE_SHARE = 0.45`; satellite band outer `SATELLITE_BAND = 2.0` (×R); 24 candidate centres per clump; halo inner `1.15·R`; `HALO_MIN_OUTER = 3.0`; FA2 core `linLogMode` on, `strongGravityMode` off, `gravity` 0.05; `fitCore` puts the 90th-percentile distance at `0.85·R` and maps `d > 0.85·R` to `0.85·R + 0.15·R·tanh((d − 0.85·R)/(0.15·R))`; `MEMORY_SIZE_SCALE = 0.25`; halo size `min(HALO_SIZE, 0.4 × median core size)` with `HALO_SIZE = 1.5`; hubs are the top 2% of memories with at least `HUB_DEGREE` (5) edges, by degree then id, at least one when any memory qualifies; `NODE_LIMIT_DEFAULT = 1000`; graph prefs persist `version: 1`, migrating a stored `nodeLimit` of exactly 200 to 1000.
- A memory edge without a numeric score counts as above every cut.
- Committed fixtures carry no memory content, tags, project names, real entity names or real ids (A13).
- A test in `features/graph/__tests__/constellation-graphs.acceptance.test.tsx` or `features/graph/lib/__tests__/*.test.ts` that pins a rule this plan replaces is rewritten to the new rule in the task that replaces it, and that task names it; no test is deleted without its replacement.
- The live page proof uses `http://127.0.0.1:8000/memory-graph` read-only with the cloned corpus. Sign in by minting a session inside the container (`docker exec darkmem-prod-darkmem-1 python -c "from datetime import timedelta; from app.api.auth import create_access_token; print(create_access_token({'sub':'admin'}, timedelta(hours=2)))"`), setting it as the `darkmem_session` cookie and `localStorage['darkmem-auth'] = '{"state":{"isAuthenticated":true},"version":0}'`. Never write through the live page, and never run Playwright specs against :8000.
- Run the typecheck as `npm run typecheck` (`tsc -b`), never plain `tsc`. `Array.prototype.at` is unavailable under `tsc -b`'s lib setting.
- Never run a repo-wide `prettier --write`; the frontend is not prettier-clean.
- Every Storybook server started for a check runs as a tracked background task and is killed when the check ends. Never `pkill node`.
- Colours come from `GraphThemeTokens`; no raw hex in renderers.
- Comments only for a non-obvious why. Commits `<type>(<scope>): <subject>`, ≤50 chars, no attribution lines.
- uutils (ubuntu-latest): A lock built on `mkdir` failing when the directory exists does not exclude a second process. Do instead: Create the lock file with `set -C` (noclobber), or use `flock`.
- uutils (ubuntu-latest): `timeout` signals only the command it started, so the command's children keep running. Do instead: Run the command in its own process group (`setsid`) and signal the group.

## Contracts

**C1 — real-corpus fixtures** (Task 1)

- Files: `frontend/src/features/graph/fixtures/real-corpus-200.json`, `real-corpus-1000.json`, `real-corpus-all.json`, each:

```ts
interface RealCorpusFixture {
  memories: { id: string; cluster: number; memory_type: string | null; importance: number }[] // server order, newest first
  edges: { source: string; target: string; score: number }[] // score rounded to 3 places
  clusterNames: Record<string, string> // values "Cluster <k>"
  entities?: { id: string; name: string; entity_type: string; memory_ids: string[] }[] // 1000 only; name "Entity <k>"
  entityRelations?: { source: string; target: string; type: string; weight: number }[] // 1000 only
}
```

- Ids are the first 12 hex digits of the SHA-256 of the original id (memories and entities alike).
- Loader `frontend/src/features/graph/fixtures/real-corpus.ts`:

```ts
export type RealCorpusSize = 200 | 1000 | "all"
export interface RealCorpus {
  memories: UnifiedMemory[] // content "Memory <i>" (1-based), source "fixture", tags [], status "active"
  edges: SimilarityEdge[]
  clusterNames: Record<string, string>
  entities: GraphEntity[] // properties {}
  entityRelations: EntityRelation[]
}
export function loadRealCorpus(size: RealCorpusSize): RealCorpus
```

- Anonymiser `frontend/scripts/anonymise-graph-fixture.mjs <in.json> <out.json>` reads a saved `/api/v1/graph/unified` response.

**C2 — role cut** (Task 2), in `frontend/src/features/graph/lib/constellation-layout.ts`:

```ts
export const CORE_SHARE = 0.45
export interface ScoredEdge { source: string; target: string; score?: number }
export interface Attachment { id: string; linked: readonly string[] }
export function roleCut(nodeIds: readonly string[], edges: readonly ScoredEdge[], share?: number): number
export function classifyWithCut(
  nodeIds: readonly string[],
  edges: readonly ScoredEdge[],
  attachments?: readonly Attachment[],
  share?: number,
): Classification & { cut: number }
```

`roleCut` returns `-Infinity` when no edge carries a score. The highest score group is always kept: when it alone (with the unscored edges) puts more than `share` of the nodes in 8+ components, the cut is that highest score, so a small graph still has a core. `classifyWithCut` runs `classify` on the edges with `score >= cut` or no score, then gives each attachment the highest role among its linked ids present in `nodeIds` (core > satellite > halo; none present is halo): a core attachment is appended to `core`, a satellite one to the `satellites` group holding its smallest-id linked satellite, a halo one to `halo`; its `degree` is its linked count.

**C3 — placement** (Task 3): `placeOuter(c, R): OuterLayout` and `fitCore(positions, R)` keep their signatures. New exports `SATELLITE_BAND = 2.0`; `HALO_MIN_OUTER` becomes 3.0. `OuterLayout.haloInner` is `1.15·R` when `R > 0` (0 with no core and no satellites); `haloOuter` is `max(HALO_MIN_OUTER·R, SATELLITE_BAND·R + HALO_C·√(halo count))`; `satelliteOuter` is the farthest clump edge. A clump's first member (sunflower index 0) sits at its centre.

**C4 — halo density** (Task 4), in `frontend/src/features/graph/lib/node-glow-program.ts`: `GlowClock` gains `haloGain?: number; haloScale?: number`; `trackDensityGain(sigma, graph, classification: Pick<Classification, "core" | "satellites" | "halo">, clock, outer?: Pick<OuterLayout, "haloInner" | "haloOuter">)`; the program declares uniforms `u_haloGain`, `u_haloScale`.

**C5 — runner roles** (Task 5), in `frontend/src/features/graph/lib/constellation-runner.ts`: `createConstellationRunner(graph, opts: { layoutMs: number; fa2Settings: Record<string, unknown>; onStop?: () => void; roles?: { nodeIds: readonly string[]; edges: readonly ScoredEdge[]; attachments: readonly Attachment[] } })`. With `roles`, classification is `classifyWithCut(roles.nodeIds, roles.edges, roles.attachments)` and any graph node it does not name is halo; without it, `classify` over every graph edge as today. Each node gets `_role` as today.

**C6 — memory renderer wiring** (Task 6): each memory-to-memory edge in the rendered graph carries a numeric `score` attribute; the renderer passes `roles` with memory ids, memory edges and one attachment per entity node (`id: "entity:<id>"`, `linked`: its memory ids).

**C7 — sizes and hubs** (Task 8): `frontend/src/features/graph/lib/hubs.ts` exports `topHubs(degrees: ReadonlyMap<string, number>, share = 0.02, minDegree = 5): Set<string>`; `constellation-layout.ts` exports `HALO_SIZE = 1.5`; the runner sets every halo node's `size` to `min(HALO_SIZE, 0.4 × median core size)` (`HALO_SIZE` with no core).

**C8 — node limit** (Task 9): `NODE_LIMIT_DEFAULT = 1000` in `graph-prefs.ts`; persist options `{ name: "darkmem-graph-prefs", version: 1, migrate }`.

## Assumptions (evidence)

- Every memory has ≥ 2 edges and the corpus is one component at Edges 0.5 — measured against `/api/v1/graph/unified` on 2026-11-18 (spec §Measured).
- The exact cut rule gives 44/22/35 (200), 44/17/38 (1,000), 44/15/41 (4,759) core/satellite/halo percent — Python check of the rule on the saved responses, 2026-11-18.
- Entities: the 1,000-memory response with `include_entities=true` carries 2,378 entities and 1,840 relations (2026-11-18).
- Entity nodes are keyed `entity:<id>` in the rendered graph (`graph-2d-renderer.tsx`, the membership-edge block); memory edges carry no `score` attribute today.
- JSON imports type-check (`tsconfig.app.json` `resolveJsonModule: true`); `src/demo/store.ts` already imports JSON.
- The shared `labelVisible` labels every node once zoomed in and hubs at rest (`focus-model.ts`, `return isHub || zoomedIn`).
- The look on the real corpus — unverified — Task 7 verifies it on the 1,000-memory board beside `graph.jpg`.
- Satellite clumps under the cut: 15 (200), 63 (1,000) and 271 (4,759) components of 2–7 memories — Python check on the saved responses, 2026-11-18; A5's sector test relies on at least 8.
- Role order under dimming (UI-2) holds by construction: the satellite gain floor is 0.45/0.8 (`SATELLITE_GAIN_FLOOR`), so a dimmed satellite never drops below the halo's 0.45 base, and halo gain is at most 1.
- The demo statements A15–A19 are proven after the plan by the ui-proof walkthrough of the final review (live page and boards, both viewports and themes); Task 7 runs only the early look check.
- Plan review round 1 (cap 1) scored executability 11, borderline: its six Important findings were fixed in place (overflow rule, A12/UX-3 fixtures, A7 formula, A8 size 40, test cast, golden-angle spread), so the plan proceeds without another round.

## Task index

1. Real-corpus fixtures
2. Role cut
3. Scattered clumps, thinning halo, soft core
4. Halo density control
5. Runner roles input and core forces
6. Memory renderer wiring
7. Real-corpus boards and the look check
8. Halo size and hub labels
9. Default of 1,000 memories

---

### Task 1: Real-corpus fixtures

**Files:**
- Create: `frontend/scripts/anonymise-graph-fixture.mjs`
- Create: `frontend/src/features/graph/fixtures/real-corpus-200.json`, `real-corpus-1000.json`, `real-corpus-all.json`
- Create: `frontend/src/features/graph/fixtures/real-corpus.ts`
- Test: `frontend/src/features/graph/__tests__/real-corpus-fixture.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces: C1

**Items:** 7

**UI/UX:** UX-5

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest"
import small from "../fixtures/real-corpus-200.json"
import mid from "../fixtures/real-corpus-1000.json"
import all from "../fixtures/real-corpus-all.json"
import { loadRealCorpus } from "../fixtures/real-corpus"

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
const fixtures = [
  ["200", small],
  ["1000", mid],
  ["all", all],
] as const

describe("real-corpus fixtures", () => {
  for (const [name, fx] of fixtures) {
    it(`A13: the ${name} fixture carries no content, tags, project, real names or UUIDs`, () => {
      const text = JSON.stringify(fx)
      expect(text).not.toMatch(UUID)
      expect(text).not.toMatch(/"(content|tags|project|properties)"\s*:/)
      for (const label of Object.values(fx.clusterNames)) expect(label).toMatch(/^Cluster \d+$/)
      for (const e of ("entities" in fx ? fx.entities : []) ?? []) expect(e.name).toMatch(/^Entity \d+$/)
      for (const m of fx.memories) {
        expect(Object.keys(m).sort()).toEqual(["cluster", "id", "importance", "memory_type"])
        expect(m.id).toMatch(/^[0-9a-f]{12}$/)
      }
    })
  }

  it("holds 200, 1,000 and every memory, with edges between fixture memories at 0.5 or more", () => {
    expect(small.memories).toHaveLength(200)
    expect(mid.memories).toHaveLength(1000)
    expect(all.memories.length).toBeGreaterThan(4000)
    for (const [, fx] of fixtures) {
      const ids = new Set(fx.memories.map((m) => m.id))
      for (const e of fx.edges) {
        expect(ids.has(e.source) && ids.has(e.target)).toBe(true)
        expect(e.score).toBeGreaterThanOrEqual(0.5)
      }
    }
  })

  it("loadRealCorpus fills placeholder content in server order and empty tags", () => {
    const c = loadRealCorpus(200)
    expect(c.memories[0]!.content).toBe("Memory 1")
    expect(c.memories[199]!.content).toBe("Memory 200")
    expect(c.memories.every((m) => m.tags.length === 0 && m.source === "fixture")).toBe(true)
    expect(c.edges).toHaveLength(small.edges.length)
    expect(c.entities).toEqual([])
  })

  it("the 1,000 fixture carries entities whose memory ids are fixture memories", () => {
    const c = loadRealCorpus(1000)
    const ids = new Set(c.memories.map((m) => m.id))
    expect(c.entities.length).toBeGreaterThan(0)
    for (const e of c.entities) {
      expect(e.id).toMatch(/^[0-9a-f]{12}$/)
      for (const id of e.memory_ids) expect(ids.has(id)).toBe(true)
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/__tests__/real-corpus-fixture.test.ts`
Expected: FAIL — the fixture modules do not exist.

- [ ] **Step 3: Implement**

1. `anonymise-graph-fixture.mjs` (Node, no dependencies beyond `node:crypto` and `node:fs`): read `<in.json>`; map every memory id and entity id through `sha256(id).hex.slice(0, 12)`; keep each memory's `cluster`, `memory_type`, `importance` in input order and drop every other field; keep `similarity_edges` whose ends are both kept memories as `edges` with `score` rounded to 3 places; rewrite `cluster_names` values to `Cluster <k>` (k = the key); when the input has `entities`, write each as `{ id, name: "Entity <k>" (1-based input order), entity_type, memory_ids }` with memory ids hashed and filtered to kept memories (drop an entity left with none), and `entity_relations` as `entityRelations` with hashed ends, dropping relations whose ends were dropped; write compact JSON to `<out.json>`. Exit 1 with a message when an argument is missing.
2. Fetch the three responses from the live instance into the session scratchpad (never the repo) with curl, sending `Cookie: darkmem_session=<token>` for a token minted as Global Constraints says: `/api/v1/graph/unified?similarity_threshold=0.5&min_cluster_size=3&include_entities=false&limit=200`, the same with `include_entities=true&limit=1000`, and with `include_entities=false&all=true`. Run the script on each to write the three fixtures.
3. `real-corpus.ts` implements C1's loader over static JSON imports.
4. Search the three fixtures for any word of real content before committing: `rg -c "darkraise|darkmem|claude" frontend/src/features/graph/fixtures/` must print nothing.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/__tests__/real-corpus-fixture.test.ts && npm run typecheck`
Expected: PASS; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/anonymise-graph-fixture.mjs frontend/src/features/graph/fixtures frontend/src/features/graph/__tests__/real-corpus-fixture.test.ts
git commit -m "test(graph): add anonymised real-corpus fixtures"
```

### Task 2: Role cut

**Files:**
- Modify: `frontend/src/features/graph/lib/constellation-layout.ts` (new exports beside `classify`)
- Test: `frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts`
- Create: `frontend/src/features/graph/lib/__tests__/real-corpus-roles.test.ts`

**Interfaces:**
- Consumes: C1
- Produces: C2

**Items:** 1

**UI/UX:** UX-1, UX-2

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

Append to `constellation-layout.test.ts` (add `roleCut`, `classifyWithCut` to its import from `../constellation-layout`):

```ts
const ring = (p: string, n: number, score: number) =>
  Array.from({ length: n }, (_, i) => ({ source: `${p}${i}`, target: `${p}${(i + 1) % n}`, score }))
const named = (p: string, n: number) => Array.from({ length: n }, (_, i) => `${p}${i}`)

describe("roleCut", () => {
  it("A1: returns the lowest score that keeps 8+ components at or below 45% of nodes", () => {
    const ids = [...named("a", 9), ...named("b", 11)]
    const edges = [...ring("a", 9, 0.9), ...ring("b", 11, 0.8), { source: "a0", target: "b0", score: 0.7 }]
    expect(roleCut(ids, edges)).toBe(0.9)
  })
  it("A1: adds equal scores together", () => {
    const ids = [...named("a", 8), ...named("b", 8), ...named("z", 14)]
    const edges = [...ring("a", 8, 0.85), ...ring("b", 8, 0.85), { source: "z0", target: "z1", score: 0.95 }]
    expect(roleCut(ids, edges)).toBe(0.95)
  })
  it("A1: is the lowest score when every edge keeps the core at or below 45%", () => {
    const ids = named("n", 40)
    expect(roleCut(ids, [...ring("n", 8, 0.9), { source: "n20", target: "n21", score: 0.55 }])).toBe(0.55)
  })
  it("A1: keeps the highest score group even when it alone passes 45%", () => {
    const ids = named("a", 10)
    expect(roleCut(ids, [...ring("a", 9, 0.9), { source: "a8", target: "a9", score: 0.5 }])).toBe(0.9)
  })
  it("A1: is -Infinity when no edge carries a score", () => {
    expect(roleCut(named("n", 4), [{ source: "n0", target: "n1" }])).toBe(-Infinity)
  })
  it("an edge without a score counts at every cut", () => {
    const c = classifyWithCut(named("n", 20), [{ source: "n18", target: "n19" }, ...ring("n", 8, 0.9)])
    expect(c.role.get("n18")).toBe("satellite")
    expect(c.cut).toBe(0.9)
  })
  it("A4: an attachment takes the highest linked role and never changes a memory's role", () => {
    const ids = [...named("c", 8), "s0", "s1", "h0", ...named("z", 10)]
    const edges = [...ring("c", 8, 0.9), { source: "s0", target: "s1", score: 0.9 }]
    const attachments = [
      { id: "e:core", linked: ["h0", "c3"] },
      { id: "e:sat", linked: ["s1", "h0"] },
      { id: "e:halo", linked: ["h0"] },
      { id: "e:bridge", linked: ["s0", "h0", "z1"] },
      { id: "e:none", linked: ["missing"] },
    ]
    const c = classifyWithCut(ids, edges, attachments)
    const plain = classifyWithCut(ids, edges)
    expect(c.role.get("e:core")).toBe("core")
    expect(c.core).toContain("e:core")
    expect(c.role.get("e:sat")).toBe("satellite")
    expect(c.satellites.find((g) => g.includes("s1"))).toContain("e:sat")
    expect(c.role.get("e:halo")).toBe("halo")
    expect(c.role.get("e:none")).toBe("halo")
    for (const id of ids) expect(c.role.get(id)).toBe(plain.role.get(id))
  })
})
```

Create `real-corpus-roles.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { loadRealCorpus, type RealCorpusSize } from "../../fixtures/real-corpus"
import { classifyWithCut, CORE_MIN } from "../constellation-layout"

const RANK = { halo: 0, satellite: 1, core: 2 } as const

describe("roles on the real corpus", () => {
  for (const size of [200, 1000, "all"] as RealCorpusSize[]) {
    it(`A2: the ${size} fixture splits about 45% core, then clumps and halo`, () => {
      const c = loadRealCorpus(size)
      const r = classifyWithCut(c.memories.map((m) => m.id), c.edges)
      const n = c.memories.length
      const core = r.core.length / n
      const sat = r.satellites.flat().length / n
      const halo = r.halo.length / n
      expect(core).toBeGreaterThanOrEqual(0.35)
      expect(core).toBeLessThanOrEqual(0.5)
      expect(sat).toBeGreaterThanOrEqual(0.1)
      expect(sat).toBeLessThanOrEqual(0.25)
      expect(halo).toBeGreaterThanOrEqual(0.25)
      expect(halo).toBeLessThanOrEqual(0.45)
    })
  }

  it("A3: raising Edges from 0.5 to 0.8 never pulls a memory inward while an 8+ core remains", () => {
    const c = loadRealCorpus(1000)
    const ids = c.memories.map((m) => m.id)
    let prev = classifyWithCut(ids, c.edges)
    for (let step = 1; step <= 6; step++) {
      const t = 0.5 + step * 0.05
      const next = classifyWithCut(ids, c.edges.filter((e) => e.score >= t - 1e-9))
      if (next.core.length >= CORE_MIN) {
        for (const id of ids) expect(RANK[next.role.get(id)!]).toBeLessThanOrEqual(RANK[prev.role.get(id)!])
      }
      prev = next
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts src/features/graph/lib/__tests__/real-corpus-roles.test.ts`
Expected: FAIL — `roleCut` and `classifyWithCut` are not exported.

- [ ] **Step 3: Implement**

1. `roleCut(nodeIds, edges, share = CORE_SHARE)`: union every unscored edge first; then take scored edges in descending score, a whole score group at a time, through a union-find that tracks the node count in components of `CORE_MIN` or more (subtract both roots' contributions on a merge, add the merged one). Before a group, snapshot the parent and size arrays; if after the group the count exceeds `share × nodeIds.length`, restore the snapshot and stop — except for the first (highest) group, which is always kept. The answer is the last group's score that was kept, or the lowest score when every group was kept, or `-Infinity` when there are no scored edges. Scores carry 3 decimals, so a bucket order by `Math.round(score × 1000)` can replace a comparator sort. A snapshot per group is O(n) per distinct score; when A14 (Task 3) runs over budget, replace it with an undo log of the group's merges.
2. `classifyWithCut` as C2 says, reusing `classify`; `cut` is `roleCut`'s answer.
3. `classify`, `placeOuter`, `fitCore` and `coreRadius` are unchanged in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts src/features/graph/lib/__tests__/real-corpus-roles.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/constellation-layout.ts frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts frontend/src/features/graph/lib/__tests__/real-corpus-roles.test.ts
git commit -m "feat(graph): choose the role cut per graph"
```

### Task 3: Scattered clumps, thinning halo, soft core

**Files:**
- Modify: `frontend/src/features/graph/lib/constellation-layout.ts` (`placeOuter`, `fitCore`, constants)
- Test: `frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts`

**Interfaces:**
- Consumes: C1, C2
- Produces: C3

**Items:** 2, 3, 4

**UI/UX:** UI-1, UX-1

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

Append to `constellation-layout.test.ts` (add `SATELLITE_BAND` to its existing import from `../constellation-layout`, which already names `classify`, `coreRadius`, `fitCore` and `placeOuter`, and `import { loadRealCorpus, type RealCorpusSize } from "../../fixtures/real-corpus"`):

```ts
const layoutOf = (size: RealCorpusSize) => {
  const c = loadRealCorpus(size)
  const cls = classifyWithCut(c.memories.map((m) => m.id), c.edges)
  const R = coreRadius(cls.core.length)
  return { cls, R, out: placeOuter(cls, R) }
}

describe("placement on the real corpus", () => {
  it("A5: clumps never overlap, sit beyond 1.15R plus their radius, stay within 2R and spread around the core", () => {
    for (const size of [200, 1000, "all"] as RealCorpusSize[]) {
      const { cls, R, out } = layoutOf(size)
      const clumps = cls.satellites.map((g) => {
        const c = out.positions.get(g[0]!)!
        const r = Math.max(...g.map((id) => {
          const p = out.positions.get(id)!
          return Math.hypot(p.x - c.x, p.y - c.y)
        }))
        return { x: c.x, y: c.y, r }
      })
      for (let i = 0; i < clumps.length; i++) {
        const a = clumps[i]!
        const d = Math.hypot(a.x, a.y)
        expect(d).toBeGreaterThanOrEqual(1.15 * R + a.r - 1e-6)
        expect(d).toBeLessThanOrEqual(SATELLITE_BAND * R + 1e-6)
        for (let j = i + 1; j < clumps.length; j++) {
          const b = clumps[j]!
          expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(a.r + b.r)
        }
      }
      expect(clumps.length).toBeGreaterThanOrEqual(8)
      const angles = clumps.map((c) => (Math.atan2(c.y, c.x) + 2 * Math.PI) % (2 * Math.PI))
      for (let k = 0; k < 24; k++) {
        const start = (k * Math.PI) / 12
        const inSector = angles.filter((a) => ((a - start + 2 * Math.PI) % (2 * Math.PI)) < Math.PI / 2).length
        expect(inSector).toBeLessThanOrEqual(clumps.length / 2)
      }
    }
  })

  it("A6: the halo fills 1.15R to its outer radius, thins outward, and depends only on id and radii", () => {
    const { cls, R, out } = layoutOf(1000)
    expect(out.haloInner).toBeCloseTo(1.15 * R)
    expect(out.haloOuter).toBeGreaterThanOrEqual(3 * R)
    const mid = (out.haloInner + out.haloOuter) / 2
    let inner = 0
    let outer = 0
    for (const id of cls.halo) {
      const p = out.positions.get(id)!
      const d = Math.hypot(p.x, p.y)
      expect(d).toBeGreaterThanOrEqual(out.haloInner - 1e-6)
      expect(d).toBeLessThanOrEqual(out.haloOuter + 1e-6)
      if (d < mid) inner++
      else outer++
    }
    const ring = (a: number, b: number) => Math.PI * (b * b - a * a)
    expect(inner / ring(out.haloInner, mid)).toBeGreaterThan(outer / ring(mid, out.haloOuter))
    // Same halo count and R, other halo ids and no satellites: shared ids do not move.
    const kept = cls.halo.slice(0, Math.floor(cls.halo.length / 2))
    const swapped = { ...cls, satellites: [], halo: [...kept, ...cls.halo.slice(kept.length).map((id) => `x${id}`)] }
    const again = placeOuter(swapped, R)
    expect(again.haloOuter).toBeCloseTo(out.haloOuter)
    for (const id of kept) expect(again.positions.get(id)).toEqual(out.positions.get(id))
  })

  it("A7: fitCore puts the 90th percentile at 0.85R and softens the tail inside R", () => {
    const pts = new Map<string, { x: number; y: number }>()
    for (let i = 0; i < 450; i++) pts.set(`n${i}`, { x: Math.cos(i), y: Math.sin(i * 1.3) })
    for (let i = 0; i < 50; i++) pts.set(`f${i}`, { x: 50 * Math.cos(i), y: 50 * Math.sin(i) })
    const all = [...pts.values()]
    const cx = all.reduce((s, p) => s + p.x, 0) / all.length
    const cy = all.reduce((s, p) => s + p.y, 0) / all.length
    const raw = [...pts.keys()].map((id) => Math.hypot(pts.get(id)!.x - cx, pts.get(id)!.y - cy))
    const p90 = [...raw].sort((a, b) => a - b)[449]!
    const out = fitCore(pts, 100)
    const d = [...pts.keys()].map((id) => Math.hypot(out.get(id)!.x, out.get(id)!.y))
    expect(Math.max(...d)).toBeLessThan(100)
    expect(d.filter((x) => x > 85 + 1e-9).length).toBeLessThanOrEqual(50)
    raw.forEach((r, i) => {
      const scaled = (r * 85) / p90
      const want = scaled <= 85 ? scaled : 85 + 15 * Math.tanh((scaled - 85) / 15)
      expect(d[i]!).toBeCloseTo(want, 6)
    })
  })

  it("A14: roleCut + classify + placeOuter take 50 ms or less for 20,000 nodes and 110,000 scored edges", () => {
    const ids = named("n", 20000)
    let seed = 7
    const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648)
    const edges = Array.from({ length: 110000 }, () => ({
      source: ids[Math.floor(rnd() * ids.length)]!,
      target: ids[Math.floor(rnd() * ids.length)]!,
      score: Math.round((0.5 + rnd() * 0.45) * 1000) / 1000,
    }))
    const runs: number[] = []
    for (let i = 0; i < 5; i++) {
      const t0 = performance.now()
      const cls = classifyWithCut(ids, edges)
      placeOuter(cls, coreRadius(cls.core.length))
      runs.push(performance.now() - t0)
    }
    runs.sort((a, b) => a - b)
    expect(runs[2]!).toBeLessThanOrEqual(50)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts`
Expected: FAIL on A5 (`SATELLITE_BAND` is undefined), A6 (inner radius and `HALO_MIN_OUTER`) and A7 (today's fit puts the farthest node at R, so the 90th-percentile node lands near 3, not 85).

- [ ] **Step 3: Implement**

1. Constants: export `SATELLITE_BAND = 2.0`; `HALO_MIN_OUTER = 3.0`.
2. `placeOuter`: keep each clump's sunflower packing and member order. Replace the ring fill: take clumps largest first; for clump radius `cr = CLUMP_R0·√(n−1) + CLUMP_R0`, try 24 candidates `k = 0..23` with angle `(j·GOLDEN_ANGLE + k·2π/24) mod 2π`, `j` being the clump's index in largest-first order (so angles spread evenly around the core by construction), and radius between `1.15·R + cr` and `SATELLITE_BAND·R` (taken uniform from `seededUnit(minId, 11 + 2k)`, `minId` being the clump's smallest member id; when the band is narrower than zero, use `1.15·R + cr`), and take the first whose distance to every placed clump centre is at least `cr + other cr + CLUMP_R0`. When all 24 fail, step outward from the last candidate's angle in increments of `CLUMP_R0` until clear. `minId` is the clump's smallest member id. `satelliteOuter` is the largest `centre distance + cr`.
3. Halo: `haloInner = 1.15·R` when `R > 0` (0 with no core and no satellites), `haloOuter` per C3, angle `seededUnit(id, 1)·2π`, radius `haloInner + seededUnit(id, 2)·(haloOuter − haloInner)` (uniform in distance).
4. `fitCore`: scale about the centroid so the 90th-percentile distance (nearest-rank) lands at `0.85·R` (scale 0 when that distance is 0), then remap any `d > 0.85·R` as Global Constraints says.
5. Rewrite the tests this replaces, naming them in the commit body: in `constellation-graphs.acceptance.test.tsx`, `A3: a halo node's position does not move…` (inner radius set by the satellite ring, outer by `2.6·R`) and `A4: satellites and halo lie beyond 1.15R…` keep their intent against the new radii; in `constellation-layout.test.ts`, any assertion of `HALO_MIN_OUTER = 2.6`, ring-ordered clump centres, or the farthest core node at exactly `R`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/constellation-layout.ts frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts frontend/src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx
git commit -m "feat(graph): scatter clumps and thin the halo"
```

### Task 4: Halo density control

**Files:**
- Modify: `frontend/src/features/graph/lib/node-glow-program.ts` (`GlowClock`, `trackDensityGain`, vertex shader, uniforms)
- Test: `frontend/src/features/graph/lib/__tests__/node-glow-program.test.ts`

**Interfaces:**
- Consumes: C2, C3
- Produces: C4

**Items:** 2

**UI/UX:** UI-2

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

Append to `node-glow-program.test.ts`:

```ts
describe("halo density", () => {
  it("A8: halo gain times coverage stays at or below the target at the fit view, for small and large halo sizes", async () => {
    const { trackDensityGain, COVERAGE_TARGET } = await import("../node-glow-program")
    const { loadRealCorpus } = await import("../../fixtures/real-corpus")
    const { classifyWithCut, coreRadius, placeOuter } = await import("../constellation-layout")
    const c = loadRealCorpus("all")
    const cls = classifyWithCut(c.memories.map((m) => m.id), c.edges)
    const outer = placeOuter(cls, coreRadius(cls.core.length))
    const scale = 800 / outer.haloOuter
    for (const haloSize of [1.5, 20, 40]) {
      let onRender = () => {}
      const sigma = {
        on: (_e: string, f: () => void) => {
          onRender = f
        },
        graphToViewport: (p: { x: number; y: number }) => ({ x: p.x * scale, y: p.y * scale }),
        scaleSize: (s: number) => s,
      }
      const graph = {
        getNodeAttribute: (id: string) => (cls.role.get(id) === "halo" ? haloSize : 6),
      }
      const clock: { time: number; haloGain?: number; haloScale?: number } = { time: 0 }
      trackDensityGain(sigma as never, graph, cls, clock, outer)
      onRender()
      const spacing =
        Math.sqrt((Math.PI * (outer.haloOuter ** 2 - outer.haloInner ** 2)) / cls.halo.length) * scale
      const radius = haloSize * (clock.haloScale ?? 1)
      const coverage = Math.min(1, (radius * radius) / (spacing * spacing))
      expect((clock.haloGain ?? 1) * coverage).toBeLessThanOrEqual(COVERAGE_TARGET + 1e-9)
    }
  })

  it("A8: feeds u_haloGain and u_haloScale from the clock and applies them in the dark-theme shader", async () => {
    const { createNodeGlowProgram } = await import("../node-glow-program")
    const Program = createNodeGlowProgram({ additive: true, clock: { time: 0, haloGain: 0.3, haloScale: 0.6 } })
    const proto = Program.prototype as unknown as Proto
    const def = proto.getDefinition.call(proto) as unknown as { VERTEX_SHADER_SOURCE: string; UNIFORMS: string[] }
    expect(def.UNIFORMS).toEqual(expect.arrayContaining(["u_haloGain", "u_haloScale"]))
    expect(def.VERTEX_SHADER_SOURCE).toMatch(/a_brightness < 0\.5\)[^;]*radius \*= u_haloScale/)
    expect(def.VERTEX_SHADER_SOURCE).toMatch(/brightness \*= u_haloGain/)
    const gl = fakeGl()
    proto.setUniforms.call(
      {},
      { matrix: new Float32Array(9), sizeRatio: 1, correctionRatio: 1, pixelRatio: 1, zoomRatio: 1, width: 10, height: 10, downSizingRatio: 1 },
      { gl, uniformLocations: { u_time: "T", u_haloGain: "HG", u_haloScale: "HS", u_matrix: "M", u_sizeRatio: "S", u_correctionRatio: "C" } },
    )
    expect(gl.uniform1f).toHaveBeenCalledWith("HG", 0.3)
    expect(gl.uniform1f).toHaveBeenCalledWith("HS", 0.6)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/node-glow-program.test.ts`
Expected: FAIL — at size 40 coverage clamps to 1 with `haloGain` unset, and the uniforms are absent.

- [ ] **Step 3: Implement**

1. `GlowClock` gains `haloGain?`, `haloScale?`.
2. `trackDensityGain` takes optional `outer` (C4). When given and the halo is non-empty, each `beforeRender` computes the halo style with `densityStyle(sigma.scaleSize(meanHaloSize), √(π·(outer² − inner²)/haloCount)·pxPerUnit, 1)` and writes `clock.haloGain` / `clock.haloScale`; without `outer`, both stay unset (1).
3. Vertex shader, dark theme only (inside the existing `#ifndef LIGHT_MODE` blocks): `else if (a_brightness < 0.5) radius *= u_haloScale;` beside the core and satellite scales, and `brightness *= u_haloGain` for halo fragments before the twinkle. Add both uniforms to `UNIFORMS` and feed them in `setUniforms` with a default of 1.
4. Pass `runner.outer` from both callers of `trackDensityGain` (`graph-2d-renderer.tsx` and `code-glow-canvas.tsx`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/node-glow-program.test.ts && npm run typecheck`
Expected: PASS; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/node-glow-program.ts frontend/src/features/graph/lib/__tests__/node-glow-program.test.ts frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/code/components/code-glow-canvas.tsx
git commit -m "feat(graph): hold the halo under the glow target"
```

### Task 5: Runner roles input and core forces

**Files:**
- Modify: `frontend/src/features/graph/lib/constellation-runner.ts` (`createConstellationRunner`, `constellationFa2Settings`)
- Test: `frontend/src/features/graph/lib/__tests__/constellation-runner.test.ts`

**Interfaces:**
- Consumes: C2
- Produces: C5

**Items:** 1, 3

**UI/UX:** UX-4

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

Append to `constellation-runner.test.ts` (it already mocks the FA2 worker; add `classify` from `../constellation-layout` and `Graph` from `graphology` to its imports if absent):

```ts
describe("runner roles", () => {
  const build = (withScores: boolean) => {
    const g = new Graph({ type: "undirected" })
    const ids = [...Array.from({ length: 8 }, (_, i) => `c${i}`), "s0", "s1", ...Array.from({ length: 9 }, (_, i) => `h${i}`)]
    for (const id of ids) g.addNode(id, { x: 0, y: 0, size: 6 })
    g.addNode("entity:e1", { x: 0, y: 0, size: 6 })
    const add = (a: string, b: string, score: number) => g.addEdge(a, b, withScores ? { score } : {})
    for (let i = 0; i < 8; i++) add(`c${i}`, `c${(i + 1) % 8}`, 0.9)
    add("s0", "s1", 0.9)
    add("h0", "c0", 0.6)
    g.addEdge("entity:e1", "s1", {})
    return { g, ids }
  }

  it("A12: without roles the runner classifies over every drawn edge, as before", () => {
    const { g } = build(false)
    const edges: { source: string; target: string }[] = []
    g.forEachEdge((_e, _a, source, target) => edges.push({ source, target }))
    const runner = createConstellationRunner(g, { layoutMs: 10, fa2Settings: {} })
    const plain = classify(g.nodes(), edges)
    expect([...runner.classification.role.entries()]).toEqual([...plain.role.entries()])
    expect(g.getNodeAttribute("h0", "_role")).toBe("core")
  })

  it("UX-1: with roles the runner classifies by the cut and gives attachments their linked role", () => {
    const { g, ids } = build(true)
    const edges: { source: string; target: string; score?: number }[] = []
    g.forEachEdge((_e, a, source, target) => {
      if (!source.startsWith("entity:") && !target.startsWith("entity:")) edges.push({ source, target, score: a.score as number })
    })
    createConstellationRunner(g, {
      layoutMs: 10,
      fa2Settings: {},
      roles: { nodeIds: ids, edges, attachments: [{ id: "entity:e1", linked: ["s1"] }] },
    })
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
    expect(g.getNodeAttribute("entity:e1", "_role")).toBe("satellite")
  })

  it("UX-1: core forces pull communities into lobes rather than a gravity-packed disc", () => {
    const { g } = build(false)
    expect(constellationFa2Settings(g, { slowDown: 1, barnesHutOptimize: false })).toMatchObject({
      linLogMode: true,
      strongGravityMode: false,
      gravity: 0.05,
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-runner.test.ts`
Expected: FAIL — `h0` is core with roles (the option is ignored) and the FA2 settings still have strong gravity at 1.

- [ ] **Step 3: Implement**

1. `createConstellationRunner` reads `opts.roles` (C5): with it, classification is `classifyWithCut(...)`, and a graph node it does not name is set to halo (added to `halo` and `role`); without it, today's path is unchanged.
2. `constellationFa2Settings`: `strongGravityMode: false`, `gravity: 0.05`; the rest unchanged.
3. Rewrite `constellation-runner.test.ts::gives every caller the same force settings` to `strongGravityMode: false` and `gravity: 0.05` (every other key unchanged), naming it in the commit body.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/constellation-runner.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/constellation-runner.ts frontend/src/features/graph/lib/__tests__/constellation-runner.test.ts
git commit -m "feat(graph): let the runner take scored roles"
```

### Task 6: Memory renderer wiring

**Files:**
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (memory-edge block, entity membership block, the `createConstellationRunner` call)
- Test: `frontend/src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx` (the `memory 2D renderer` describe)
- Test: `frontend/src/features/graph/components/__tests__/graph-2d-renderer.test.tsx` (run; edit only an assertion that pins edge attributes or roles the cut replaces)

**Interfaces:**
- Consumes: C5
- Produces: C6

**Items:** 1

**UI/UX:** UI-1, UX-1

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: Extend the test `constellation-graphs.acceptance.test.tsx::memory 2D renderer`**

Add inside `describe("memory 2D renderer", …)`:

```ts
  it("UX-1: memory edges carry their score, and roles follow the cut rather than every drawn edge", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const rest = ["s0", "s1", ...ids("h", 9)].map((id) => memory(id))
    const memories = [...ring, ...rest]
    const edges = [
      ...path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target, 0.9)),
      edge("s0", "s1", 0.9),
      edge("h0", "c0", 0.6),
    ]
    render(<Scene memories={memories} edges={edges} />)
    advance(50)
    const g = lastSigma().graph
    expect(g.getEdgeAttribute(g.edge("c0", "c1")!, "score")).toBe(0.9)
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
  })

  it("A4: with the entity layer on, an entity takes its memories' highest role and memory roles do not change", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const rest = ["s0", "s1", ...ids("h", 10)].map((id) => memory(id))
    const memories = [...ring, ...rest]
    const edges = [...path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target)), edge("s0", "s1")]
    const entity = (id: string, memory_ids: string[]): GraphEntity => ({
      id,
      name: id,
      entity_type: "tool",
      properties: {},
      memory_ids,
    })
    const roles = (layer: boolean) => {
      render(
        <Scene
          memories={memories}
          edges={edges}
          entityLayer={layer}
          entities={[entity("x", ["s1", "h1"]), entity("y", ["c2", "h2"]), entity("z", ["h3", "h4"])]}
        />,
      )
      advance(50)
      const g = lastSigma().graph
      return (id: string) => g.getNodeAttribute(id, "_role")
    }
    const off = roles(false)
    const offRoles = memories.map((m) => off(m.id))
    const on = roles(true)
    expect(on("entity:x")).toBe("satellite")
    expect(on("entity:y")).toBe("core")
    expect(on("entity:z")).toBe("halo")
    expect(memories.map((m) => on(m.id))).toEqual(offRoles)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx -t "memory 2D renderer"`
Expected: FAIL — no `score` attribute, `h0` classified core, and the entity `entity:z` merges `h3`/`h4` into one component.

- [ ] **Step 3: Implement**

1. Memory-edge block: add `score: e.score` to each memory edge's attributes.
2. Collect `roles` while building: memory ids, memory edges `{ source, target, score }`, and for each entity node added, `{ id: "entity:<id>", linked: <its memory ids present in the graph> }`. Pass `roles` to `createConstellationRunner`.
3. Rewrite two tests whose 11-memory fixture (10-node core plus `x`) sits above 45% under the cut, so `x` would stay halo at Edges 0.5: in `A12: raising the Edges threshold so a memory loses its last edge…` and `UX-3: a core-membership change at an unchanged node set…`, change `const memories = [...coreMemories, x]` to `const memories = [...coreMemories, x, ...ids("o", 16).map((id) => memory(id))]` (27 memories: the core plus `x` is 11/27 ≈ 41%, so the 0.6 edge lies above the cut at Edges 0.5). Every assertion stays as written. Name both in the commit body. `A21` keeps passing (its first score group is always kept).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx src/features/graph/components/__tests__/graph-2d-renderer.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx frontend/src/features/graph/components/__tests__/graph-2d-renderer.test.tsx
git commit -m "feat(graph): classify memories by their scored edges"
```

### Task 7: Real-corpus boards and the look check

**Files:**
- Create: `frontend/src/features/graph/components/real-corpus-board.stories.tsx`
- Modify: `docs/dforge/ui-ux/profile.md` (Harness line, Decisions)

**Interfaces:**
- Consumes: C1, C6
- Produces: the `Graph/Constellation/RealCorpus` stories (Default1000, All, Small200, HighEdges, EntityLayer, Selected)

**Items:** 7, 1

**UI/UX:** UX-5, UI-1

**Implementer:** dforge:impl-sonnet-medium
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 0 = 4

- [ ] **Step 1: No new test, because stories are proven by the ui-proof walkthrough (A18) and a type error is caught by `npm run typecheck`**

- [ ] **Step 2: Write the boards**

1. Follow `constellation-board.stories.tsx`'s wrapper: `useMemoryGraphTheme()`, module-level stable callbacks, a full-size container. Stories render `Graph2DRenderer` with `loadRealCorpus(size)`:
   - `Default1000` — 1000; `All` — `"all"`; `Small200` — 200;
   - `HighEdges` — 1000 with edges `score >= 0.8`;
   - `EntityLayer` — 1000, entity layer on, the fixture's entities and relations;
   - `Selected` — 1000 with the highest-degree memory selected.
2. `sizeMode` `connections`, `colorMode` `cluster`, `hullMode` `none`, `clusterNames` from the fixture.

- [ ] **Step 3: Amend the profile**

In `docs/dforge/ui-ux/profile.md`, extend the Harness line with: the live memory graph page at `http://127.0.0.1:8000/memory-graph` with the cloned 192.168.0.199 corpus, read-only, signed in as Global Constraints says. Remove "Never the live instance on :8000." from that line, and add the Decisions line `- 2026-11-18 — The memory graph is also proven on the live page with the cloned corpus (owner: "Fixture + live (Recommended)"); the page is read-only, nothing is written, and Playwright specs never run against :8000.`

- [ ] **Step 4: Check the look against the reference (the spec's riskiest assumption)**

1. Start Storybook as a tracked background task: `cd frontend && npx storybook dev -p 6006 --ci`; wait for its ready line.
2. With Playwright MCP at 1600x1000, open `Graph/Constellation/RealCorpus` → `Default1000` in the dark theme, wait 10 s for the core run, and screenshot to `.playwright-mcp/real-corpus-default1000-dark.png`. Read it beside `graph.jpg`.
3. It passes when it shows a multi-coloured core with a soft edge, separate small clumps around it, a sparse field of small halo points thinning outward, and no white saturation. Record the verdict in the ledger as `Task 7: Ruling: look check — <pass|fail> — <what differs>`. On fail, take it to the ruling seat before Task 8 (a fix there is an AMEND).
4. Kill the Storybook process tree.

- [ ] **Step 5: Verify**

Run: `cd frontend && npm run typecheck`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/graph/components/real-corpus-board.stories.tsx docs/dforge/ui-ux/profile.md
git commit -m "feat(graph): add real-corpus constellation boards"
```

### Task 8: Halo size and hub labels

**Files:**
- Create: `frontend/src/features/graph/lib/hubs.ts`
- Create: `frontend/src/features/graph/lib/__tests__/hubs.test.ts`
- Modify: `frontend/src/features/graph/lib/constellation-runner.ts` (halo size after classification), `frontend/src/features/graph/lib/constellation-layout.ts` (`HALO_SIZE`)
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx` (memory `size`, node reducer label rule)
- Test: `frontend/src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx` (the `memory 2D renderer` describe)

**Interfaces:**
- Consumes: C5, C6
- Produces: C7

**Items:** 2, 5

**UI/UX:** UI-3, UI-4, UI-5

**Implementer:** dforge:impl-opus-high
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

Create `hubs.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { topHubs } from "../hubs"
import { loadRealCorpus } from "../../fixtures/real-corpus"

describe("topHubs", () => {
  it("A10: takes the top 2% by degree then id, only at 5 or more edges, at least one when any qualifies", () => {
    const d = new Map(Array.from({ length: 500 }, (_, i) => [`m${String(i).padStart(3, "0")}`, i % 10] as const))
    const hubs = topHubs(d)
    expect(hubs.size).toBe(10)
    for (const id of hubs) expect(d.get(id)).toBe(9)
    expect([...hubs].sort()[0]).toBe("m009")
    expect(topHubs(new Map([["a", 5], ["b", 1]])).size).toBe(1)
    expect(topHubs(new Map([["a", 4], ["b", 1]])).size).toBe(0)
  })

  it("A10: the 1,000-memory fixture has at most 20 hubs", () => {
    const c = loadRealCorpus(1000)
    const deg = new Map(c.memories.map((m) => [m.id, 0]))
    for (const e of c.edges) {
      deg.set(e.source, deg.get(e.source)! + 1)
      deg.set(e.target, deg.get(e.target)! + 1)
    }
    const hubs = topHubs(deg)
    expect(hubs.size).toBeGreaterThan(0)
    expect(hubs.size).toBeLessThanOrEqual(20)
  })
})
```

In `constellation-graphs.acceptance.test.tsx`, give `Scene` an optional `sizeMode` prop (`sizeMode={(props.sizeMode ?? "connections") as RendererProps["sizeMode"]}`) and add inside `describe("memory 2D renderer", …)`:

```ts
  it("A9: halo nodes take one small size whatever their importance", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const loud = { ...memory("h0"), importance: 1 }
    const quiet = { ...memory("h1"), importance: 0 }
    const memories = [...ring, loud, quiet, ...ids("z", 10).map((id) => memory(id))]
    const edges = path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target))
    render(<Scene memories={memories} edges={edges} sizeMode={"importance" as RendererProps["sizeMode"]} />)
    advance(50)
    const g = lastSigma().graph
    const core = ids("c", 8).map((id) => g.getNodeAttribute(id, "size") as number).sort((a, b) => a - b)
    const median = (core[3]! + core[4]!) / 2
    expect(g.getNodeAttribute("h0", "size")).toBe(g.getNodeAttribute("h1", "size"))
    expect(g.getNodeAttribute("h0", "size") as number).toBeLessThanOrEqual(0.4 * median + 1e-9)
  })

  it("A10: at the fit view with nothing hovered or selected, no memory carries a label, hubs included", () => {
    const star = ["c0", ...ids("x", 9)].map((id) => memory(id))
    const edges = ids("x", 9).map((id) => edge("c0", id))
    render(<Scene memories={star} edges={edges} />)
    advance(50)
    const sigma = lastSigma()
    for (const id of sigma.graph.nodes()) {
      const out = sigma.settings.nodeReducer(id, sigma.graph.getNodeAttributes(id))
      expect(out.label ?? "").toBe("")
    }
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/hubs.test.ts src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx -t "topHubs|A9: halo|A10: at the fit view"`
Expected: FAIL — `hubs.ts` does not exist, halo sizes follow importance, and `c0` (degree 9) is labelled at rest.

- [ ] **Step 3: Implement**

1. `topHubs` per C7: keep ids with degree ≥ `minDegree`, sort by degree descending then id ascending, take `max(1, floor(share × degrees.size))` of them when any qualifies.
2. `HALO_SIZE = 1.5` in `constellation-layout.ts`; after classification the runner sets every halo node's `size` per C7, for both canvases. Nodes named in `roles.attachments` (entity diamonds) are excluded both from the resize and from the median core size.
3. Memory renderer: memory `size` is `computeSize(...) × MEMORY_SIZE_SCALE` (0.25) instead of `× 0.5`; compute `topHubs` over memory degrees per build; in the node reducer's rest tier, call `labelVisible` with `isHub: hubs.has(node) && zoomedIn` and `zoomedIn: false` so only zoomed-in hubs and hovered nodes are labelled; focus and adjacent tiers are untouched. `labelVisible` itself does not change.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/hubs.test.ts src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx src/features/graph/components/__tests__/graph-2d-renderer.test.tsx && npm run typecheck`
Expected: PASS; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/hubs.ts frontend/src/features/graph/lib/__tests__/hubs.test.ts frontend/src/features/graph/lib/constellation-runner.ts frontend/src/features/graph/lib/constellation-layout.ts frontend/src/features/graph/components/graph-2d-renderer.tsx frontend/src/features/graph/__tests__/constellation-graphs.acceptance.test.tsx
git commit -m "feat(graph): small halo points and hub-only labels"
```

### Task 9: Default of 1,000 memories

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-prefs.ts` (`NODE_LIMIT_DEFAULT`, persist options)
- Test: `frontend/src/features/graph/lib/__tests__/graph-prefs.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces: C8

**Items:** 6

**UI/UX:** UX-3

**Implementer:** dforge:impl-sonnet-medium
**Evaluation:** files 1 - spec 1 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing test**

Append inside `describe("graphPrefs", …)` in `graph-prefs.test.ts` (add `NODE_LIMIT_DEFAULT` to its import):

```ts
  it("A11: defaults to 1,000 memories", () => {
    expect(NODE_LIMIT_DEFAULT).toBe(1000)
  })

  it("A11: a stored 200 from before version 1 loads as 1,000, and any other stored value is kept", async () => {
    for (const [stored, expected] of [[200, 1000], [500, 500], [50000, 50000]] as const) {
      localStorage.setItem("darkmem-graph-prefs", JSON.stringify({ state: { nodeLimit: stored }, version: 0 }))
      await useGraphPrefs.persist.rehydrate()
      expect(useGraphPrefs.getState().nodeLimit).toBe(expected)
    }
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/graph-prefs.test.ts`
Expected: FAIL — the default is 200 and a stored 200 stays 200.

- [ ] **Step 3: Implement**

1. `NODE_LIMIT_DEFAULT = 1000`.
2. Persist options: `version: 1` and a `migrate(persisted, version)` that, for `version < 1`, replaces a `nodeLimit` of exactly 200 with 1000 and returns everything else as stored.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/graph/lib/__tests__/graph-prefs.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-prefs.ts frontend/src/features/graph/lib/__tests__/graph-prefs.test.ts
git commit -m "feat(graph): show 1,000 memories by default"
```
