import { MEMORY_TYPES } from "@/lib/taxonomy"
import type { SimilarityEdge, UnifiedMemory } from "@/hooks/api"

export interface SyntheticGraph {
  memories: UnifiedMemory[]
  edges: SimilarityEdge[]
  clusterNames: Record<string, string>
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * A deterministic memory graph for measuring the renderers at scale. About
 * 5% of nodes are unclustered; every other node draws its edges from members
 * of its own cluster.
 */
export function syntheticMemoryGraph(
  nodeCount: number,
  clusterCount: number,
  edgesPerNode: number,
  seed = 1,
): SyntheticGraph {
  const rand = mulberry32(seed)
  const members = new Map<number, string[]>()
  const memories: UnifiedMemory[] = []
  for (let i = 0; i < nodeCount; i++) {
    const id = `m${i}`
    const cluster = rand() < 0.05 ? -1 : i % clusterCount
    memories.push({
      id,
      content: `Synthetic memory ${i} about topic ${cluster}`,
      source: "synthetic",
      tags: [`topic-${cluster}`],
      memory_type: MEMORY_TYPES[i % MEMORY_TYPES.length]!,
      importance: rand(),
      cluster,
      status: "active",
    })
    if (cluster >= 0) {
      const list = members.get(cluster) ?? []
      list.push(id)
      members.set(cluster, list)
    }
  }

  const seen = new Set<string>()
  const edges: SimilarityEdge[] = []
  for (const m of memories) {
    const pool = members.get(m.cluster)
    if (!pool || pool.length < 2) continue
    for (let e = 0; e < edgesPerNode; e++) {
      const target = pool[Math.floor(rand() * pool.length)]!
      if (target === m.id) continue
      const key = m.id < target ? `${m.id}|${target}` : `${target}|${m.id}`
      if (seen.has(key)) continue
      seen.add(key)
      edges.push({ source: m.id, target, score: 0.5 + rand() * 0.5 })
    }
  }

  const clusterNames: Record<string, string> = {}
  for (const cluster of members.keys()) clusterNames[String(cluster)] = `Topic ${cluster}`
  return { memories, edges, clusterNames }
}

export type SyntheticShape =
  | "one-component"
  | "all-orphans"
  | "no-orphans"
  | "many-satellites"
  | "mixed"

/**
 * A deterministic memory graph with a chosen component distribution, for the
 * constellation boards. Each component is a chain (so it stays connected)
 * with a few extra chords; satellites have 2-7 members, below CORE_MIN.
 */
export function syntheticShape(shape: SyntheticShape, n: number, seed = 1): SyntheticGraph {
  const rand = mulberry32(seed)
  const memories: UnifiedMemory[] = []
  const edges: SimilarityEdge[] = []
  const seen = new Set<string>()
  const clusterNames: Record<string, string> = {}
  let next = 0
  let cluster = 0

  const link = (a: string, b: string) => {
    const key = a < b ? `${a}|${b}` : `${b}|${a}`
    if (a === b || seen.has(key)) return
    seen.add(key)
    edges.push({ source: a, target: b, score: 0.5 + rand() * 0.5 })
  }
  const add = (c: number) => {
    const i = next++
    memories.push({
      id: `m${i}`,
      content: `Synthetic memory ${i} about topic ${c}`,
      source: "synthetic",
      tags: [`topic-${c}`],
      memory_type: MEMORY_TYPES[i % MEMORY_TYPES.length]!,
      importance: rand(),
      cluster: c,
      status: "active",
    })
    return `m${i}`
  }
  const component = (size: number) => {
    const c = cluster++
    clusterNames[String(c)] = `Topic ${c}`
    const ids = Array.from({ length: size }, () => add(c))
    for (let i = 1; i < ids.length; i++) link(ids[i - 1]!, ids[i]!)
    for (let k = 0; k < Math.floor(size / 2); k++) {
      link(ids[Math.floor(rand() * size)]!, ids[Math.floor(rand() * size)]!)
    }
  }
  // Never leaves a remainder of one, which would be a lone halo node.
  const satellites = (count: number) => {
    let remaining = count
    while (remaining > 0) {
      let size = 2 + Math.floor(rand() * 6)
      if (remaining - size === 1) size = size < 7 ? size + 1 : size - 1
      if (size > remaining) size = remaining
      component(size)
      remaining -= size
    }
  }
  const orphans = (count: number) => {
    for (let i = 0; i < count; i++) add(-1)
  }

  if (shape === "one-component") {
    component(n)
  } else if (shape === "all-orphans") {
    orphans(n)
  } else if (shape === "no-orphans") {
    const core = Math.floor(n / 4)
    for (let i = 0; i < 3; i++) component(core)
    satellites(n - 3 * core)
  } else if (shape === "many-satellites") {
    const core = Math.floor(n * 0.4)
    component(core)
    satellites(n - core)
  } else {
    const core = Math.floor(n * 0.5)
    const sats = Math.floor(n * 0.2)
    component(core)
    satellites(sats)
    orphans(n - core - sats)
  }
  return { memories, edges, clusterNames }
}
