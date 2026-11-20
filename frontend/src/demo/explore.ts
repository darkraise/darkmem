import type { DemoCodeGraph, DemoCodeProcess } from "@/features/code/types"
import type { DemoIndexPhase, DemoMemoryGraph, ReindexOptions } from "./types"
import { INDEX_PHASE_LABELS } from "./data/code-curated"

// ---------------------------------------------------------------------------
// Reindex phases
// ---------------------------------------------------------------------------

/** Phases 1–12 always run; 13–14 are the opt-in LLM phases — they render as
 *  "skipped — opt-in" rather than silently missing when left off. */
export function buildReindexPhases(opts: ReindexOptions): DemoIndexPhase[] {
  return INDEX_PHASE_LABELS.map((label, i) => {
    const n = i + 1
    if (n === 13 && !opts.enrich_symbols)
      return { n, label, state: "skipped" as const }
    if (n === 14 && !opts.generate_wiki)
      return { n, label, state: "skipped" as const }
    return { n, label, state: n === 1 ? ("current" as const) : ("pending" as const) }
  })
}

// ---------------------------------------------------------------------------
// Deterministic demo layouts — a representative sketch, not a physics engine.
// ---------------------------------------------------------------------------

export type GraphLayoutMode = "force" | "tree" | "circles"

export interface LayoutItem {
  id: string
  /** Cluster key — community id (code) or topic id (memory graph). */
  group: string
}

export interface LayoutEdge {
  source: string
  target: string
}

export interface Point {
  x: number
  y: number
}

const GOLDEN_ANGLE = 2.399963229728653
const PAD = 34

const clamp = (v: number, lo: number, hi: number) =>
  Math.min(Math.max(v, lo), hi)

function distinctGroups(items: LayoutItem[]): string[] {
  const groups: string[] = []
  for (const item of items) {
    if (!groups.includes(item.group)) groups.push(item.group)
  }
  return groups
}

function forceLayout(
  items: LayoutItem[],
  width: number,
  height: number,
): Record<string, Point> {
  const groups = distinctGroups(items)
  const cx = width / 2
  const cy = height / 2
  const centers = new Map<string, Point>()
  groups.forEach((g, gi) => {
    if (groups.length === 1) {
      centers.set(g, { x: cx, y: cy })
      return
    }
    const angle = (2 * Math.PI * gi) / groups.length - Math.PI / 2
    centers.set(g, {
      x: cx + Math.cos(angle) * width * 0.28,
      y: cy + Math.sin(angle) * height * 0.26,
    })
  })
  const counters = new Map<string, number>()
  const out: Record<string, Point> = {}
  for (const item of items) {
    const center = centers.get(item.group) ?? { x: cx, y: cy }
    const i = counters.get(item.group) ?? 0
    counters.set(item.group, i + 1)
    const r = i === 0 ? 0 : 16 + 15 * Math.sqrt(i)
    const angle = i * GOLDEN_ANGLE
    out[item.id] = {
      x: clamp(center.x + Math.cos(angle) * r, PAD, width - PAD),
      y: clamp(center.y + Math.sin(angle) * r, PAD, height - PAD),
    }
  }
  return out
}

function treeLayout(
  items: LayoutItem[],
  edges: LayoutEdge[],
  width: number,
  height: number,
): Record<string, Point> {
  const adjacency = new Map<string, string[]>()
  const addAdj = (a: string, b: string) => {
    const list = adjacency.get(a)
    if (list) list.push(b)
    else adjacency.set(a, [b])
  }
  for (const e of edges) {
    addAdj(e.source, e.target)
    addAdj(e.target, e.source)
  }
  const outDegree = new Map<string, number>()
  for (const e of edges) {
    outDegree.set(e.source, (outDegree.get(e.source) ?? 0) + 1)
  }
  const depth = new Map<string, number>()
  const queue: string[] = []
  const seed = (id: string) => {
    depth.set(id, 0)
    queue.push(id)
  }
  const bestRoot = [...items]
    .sort((a, b) => (outDegree.get(b.id) ?? 0) - (outDegree.get(a.id) ?? 0))
    .find(() => true)
  if (bestRoot) seed(bestRoot.id)
  let head = 0
  while (head < queue.length) {
    const id = queue[head]
    head += 1
    if (id === undefined) break
    const d = depth.get(id) ?? 0
    for (const next of adjacency.get(id) ?? []) {
      if (!depth.has(next)) {
        depth.set(next, d + 1)
        queue.push(next)
      }
    }
    // seed the next unvisited component once this one drains
    if (head === queue.length) {
      const orphan = items.find((it) => !depth.has(it.id))
      if (orphan) seed(orphan.id)
    }
  }
  const maxDepth = Math.max(0, ...[...depth.values()])
  const columns = new Map<number, string[]>()
  for (const item of items) {
    const d = depth.get(item.id) ?? maxDepth
    const col = columns.get(d)
    if (col) col.push(item.id)
    else columns.set(d, [item.id])
  }
  const out: Record<string, Point> = {}
  const usableW = width - 2 * PAD
  const usableH = height - 2 * PAD
  for (const [d, ids] of columns) {
    const x = maxDepth === 0 ? width / 2 : PAD + (usableW * d) / maxDepth
    ids.forEach((id, i) => {
      const y = PAD + (usableH * (i + 1)) / (ids.length + 1)
      out[id] = { x, y }
    })
  }
  return out
}

function circlesLayout(
  items: LayoutItem[],
  width: number,
  height: number,
): Record<string, Point> {
  const groups = distinctGroups(items)
  const cx = width / 2
  const cy = height / 2
  const maxR = Math.min(width, height) / 2 - PAD
  const out: Record<string, Point> = {}
  const counters = new Map<string, number>()
  const sizes = new Map<string, number>()
  for (const item of items) {
    sizes.set(item.group, (sizes.get(item.group) ?? 0) + 1)
  }
  for (const item of items) {
    const gi = groups.indexOf(item.group)
    const ringR = (maxR * (gi + 1)) / groups.length
    const size = sizes.get(item.group) ?? 1
    const i = counters.get(item.group) ?? 0
    counters.set(item.group, i + 1)
    const angle = (2 * Math.PI * i) / size + gi * 0.6
    out[item.id] = {
      x: cx + Math.cos(angle) * ringR,
      y: cy + Math.sin(angle) * ringR,
    }
  }
  return out
}

export function layoutGraph(
  items: LayoutItem[],
  edges: LayoutEdge[],
  mode: GraphLayoutMode,
  width: number,
  height: number,
): Record<string, Point> {
  if (mode === "tree") return treeLayout(items, edges, width, height)
  if (mode === "circles") return circlesLayout(items, width, height)
  return forceLayout(items, width, height)
}

// ---------------------------------------------------------------------------
// Graph queries
// ---------------------------------------------------------------------------

/** Undirected BFS — the ids within `depth` hops of `start`, start included. */
export function neighborhoodWithin(
  edges: LayoutEdge[],
  start: string,
  depth: number,
): Set<string> {
  const adjacency = new Map<string, string[]>()
  const addAdj = (a: string, b: string) => {
    const list = adjacency.get(a)
    if (list) list.push(b)
    else adjacency.set(a, [b])
  }
  for (const e of edges) {
    addAdj(e.source, e.target)
    addAdj(e.target, e.source)
  }
  const dist = new Map<string, number>([[start, 0]])
  const queue = [start]
  let head = 0
  while (head < queue.length) {
    const id = queue[head]
    head += 1
    if (id === undefined) break
    const d = dist.get(id) ?? 0
    if (d >= depth) continue
    for (const next of adjacency.get(id) ?? []) {
      if (!dist.has(next)) {
        dist.set(next, d + 1)
        queue.push(next)
      }
    }
  }
  return new Set(dist.keys())
}

export type BlastRisk = "low" | "medium" | "high" | "critical"

export interface BlastRadius {
  total: number
  risk: BlastRisk
  /** d1 / d2 / d3+ buckets. */
  depths: { label: string; count: number }[]
  affected: { id: string; name: string; file: string; depth: number }[]
}

/** Transitive dependents of a symbol — BFS over reversed edges (callers,
 *  containers, importers), never the symbol's own callees. */
export function computeBlastRadius(
  graph: DemoCodeGraph,
  nodeId: string,
): BlastRadius {
  const reverse = new Map<string, string[]>()
  for (const e of graph.edges) {
    const list = reverse.get(e.target)
    if (list) list.push(e.source)
    else reverse.set(e.target, [e.source])
  }
  const dist = new Map<string, number>([[nodeId, 0]])
  const queue = [nodeId]
  let head = 0
  while (head < queue.length) {
    const id = queue[head]
    head += 1
    if (id === undefined) break
    const d = dist.get(id) ?? 0
    for (const prev of reverse.get(id) ?? []) {
      if (!dist.has(prev)) {
        dist.set(prev, d + 1)
        queue.push(prev)
      }
    }
  }
  const affected = graph.nodes
    .filter((n) => n.id !== nodeId && dist.has(n.id))
    .map((n) => ({
      id: n.id,
      name: n.name,
      file: n.file,
      depth: dist.get(n.id) ?? 0,
    }))
    .sort((a, b) => a.depth - b.depth || a.name.localeCompare(b.name))
  const bucket = (predicate: (d: number) => boolean) =>
    affected.filter((a) => predicate(a.depth)).length
  const total = affected.length
  const risk: BlastRisk =
    total <= 2 ? "low" : total <= 5 ? "medium" : total <= 9 ? "high" : "critical"
  return {
    total,
    risk,
    depths: [
      { label: "d1", count: bucket((d) => d === 1) },
      { label: "d2", count: bucket((d) => d === 2) },
      { label: "d3+", count: bucket((d) => d >= 3) },
    ],
    affected,
  }
}

// Mermaid reads node text as HTML entities; quotes and brackets would
// otherwise end the `["..."]` node syntax early.
function escapeMermaid(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\[/g, "#91;")
    .replace(/\]/g, "#93;")
    .replace(/\{/g, "#123;")
    .replace(/\}/g, "#125;")
    .replace(/[\r\n]+/g, " ")
}

export function mermaidForProcess(
  process: DemoCodeProcess,
  graph: DemoCodeGraph,
): string {
  // A step the graph does not draw (a symbol step on a file-level graph)
  // still names its symbol, never its whole `name::file` key.
  const name = (id: string) =>
    graph.nodes.find((n) => n.id === id)?.name ?? (id.split("::")[0] || id)
  const lines = ["flowchart TD"]
  process.steps.forEach((step, i) => {
    lines.push(`  n${i}["${escapeMermaid(name(step))}"]`)
  })
  for (let i = 0; i + 1 < process.steps.length; i++) {
    lines.push(`  n${i} --> n${i + 1}`)
  }
  return lines.join("\n")
}

// ---------------------------------------------------------------------------
// Memory-graph scoping
// ---------------------------------------------------------------------------

export function scopeMemoryGraph(
  graph: DemoMemoryGraph,
  project: string,
): DemoMemoryGraph {
  const entities = graph.entities.filter((e) => e.project === project)
  const ids = new Set(entities.map((e) => e.id))
  return {
    entities,
    relations: graph.relations.filter(
      (r) => ids.has(r.source) && ids.has(r.target),
    ),
    topics: graph.topics.filter((t) => t.project === project),
  }
}

export function distinctGraphProjects(graph: DemoMemoryGraph): string[] {
  const projects: string[] = []
  for (const e of graph.entities) {
    if (!projects.includes(e.project)) projects.push(e.project)
  }
  return projects
}

/** Entity ids whose name matches the query (case-insensitive substring). */
export function matchEntities(
  graph: DemoMemoryGraph,
  query: string,
): Set<string> {
  const q = query.trim().toLowerCase()
  if (q === "") return new Set()
  return new Set(
    graph.entities
      .filter((e) => e.name.toLowerCase().includes(q))
      .map((e) => e.id),
  )
}
