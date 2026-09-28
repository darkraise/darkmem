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

const TYPES = ["fact", "decision", "preference", "problem", "reference"]

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
      memory_type: TYPES[i % TYPES.length]!,
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
