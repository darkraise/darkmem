import type {
  UnifiedMemory,
  UnifiedGraphData,
  GraphEntity,
  EntityRelation,
} from "@/hooks/api"
import {
  resolveNodeColor,
  entityTypeColor,
  type ColorMode,
  type MemoryPalette,
} from "./graph-colors"
import { seededUnit } from "./code-graph-theme"
export type { ColorMode }

export type SizeMode = "connections" | "importance" | "uniform"

export interface Node3D {
  id: string
  nodeKind: "memory" | "entity"
  content: string
  source: string
  tags: string[]
  memoryType: string | null
  importance: number
  cluster: number
  clusterName: string
  color: string
  val: number
  entityName?: string
  entityType?: string
  entityMemoryIds?: string[]
  x?: number
  y?: number
  z?: number
  fx?: number
  fy?: number
  fz?: number
}

export interface Link3D {
  source: string
  target: string
  score: number
  hidden?: boolean
  linkKind?: "similarity" | "relation" | "membership"
  relationType?: string
}

export interface GraphData3D {
  nodes: Node3D[]
  links: Link3D[]
}

export interface FilterState {
  searchText: string
  selectedTags: Set<string>
  selectedTypes: Set<string>
  selectedSources: Set<string>
  selectedClusters: Set<number>
  selectedEntityTypes?: Set<string>
}

export function computeNodeVal(
  mode: SizeMode,
  connectionCount: number,
  importance: number,
): number {
  if (mode === "uniform") return 2
  if (mode === "importance") return 1 + importance * 5
  return 1 + Math.min(5, Math.log1p(connectionCount) * 1.5)
}

export function computeSize(
  mode: SizeMode,
  connections: number,
  importance: number,
): number {
  if (mode === "uniform") return 18
  if (mode === "importance") return 12 + importance * 28
  return 12 + Math.min(28, Math.log1p(connections) * 8)
}

function matchesFilter(memory: UnifiedMemory, filters: FilterState): boolean {
  if (filters.searchText) {
    const term = filters.searchText.toLowerCase()
    if (!memory.content.toLowerCase().includes(term)) return false
  }
  if (filters.selectedTags.size > 0) {
    if (!memory.tags.some((t) => filters.selectedTags.has(t))) return false
  }
  if (filters.selectedTypes.size > 0) {
    if (!memory.memory_type || !filters.selectedTypes.has(memory.memory_type))
      return false
  }
  if (filters.selectedSources.size > 0) {
    if (!filters.selectedSources.has(memory.source)) return false
  }
  if (filters.selectedClusters.size > 0) {
    if (!filters.selectedClusters.has(memory.cluster)) return false
  }
  return true
}

export function transformToGraphData(
  data: UnifiedGraphData,
  sizeMode: SizeMode,
  filters: FilterState,
  colorMode: ColorMode = "type",
  entityLayerEnabled = false,
  entities: GraphEntity[] = [],
  entityRelations: EntityRelation[] = [],
  palette: MemoryPalette,
): GraphData3D {
  const edgeCountMap = new Map<string, number>()
  for (const edge of data.similarity_edges) {
    edgeCountMap.set(edge.source, (edgeCountMap.get(edge.source) ?? 0) + 1)
    edgeCountMap.set(edge.target, (edgeCountMap.get(edge.target) ?? 0) + 1)
  }

  const filteredMemories = data.memories.filter((m) =>
    matchesFilter(m, filters),
  )
  const filteredIds = new Set(filteredMemories.map((m) => m.id))

  const nodes: Node3D[] = filteredMemories.map((m) => ({
    id: m.id,
    nodeKind: "memory" as const,
    content: m.content,
    source: m.source,
    tags: m.tags,
    memoryType: m.memory_type,
    importance: m.importance,
    cluster: m.cluster,
    clusterName: data.cluster_names[String(m.cluster)] ?? "",
    color: resolveNodeColor(m, colorMode, palette),
    val: computeNodeVal(sizeMode, edgeCountMap.get(m.id) ?? 0, m.importance),
  }))

  const links: Link3D[] = data.similarity_edges
    .filter((e) => filteredIds.has(e.source) && filteredIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target, score: e.score }))

  const clusterMembers = new Map<number, string[]>()
  for (const node of nodes) {
    if (node.cluster >= 0) {
      const members = clusterMembers.get(node.cluster) ?? []
      members.push(node.id)
      clusterMembers.set(node.cluster, members)
    }
  }

  const existingEdges = new Set(links.map((l) => `${l.source}-${l.target}`))
  for (const [, members] of clusterMembers) {
    for (let i = 0; i < members.length; i++) {
      for (let j = i + 1; j < members.length; j++) {
        // loop bounds guarantee both indices are within range
        const a = members[i]!
        const b = members[j]!
        const key1 = `${a}-${b}`
        const key2 = `${b}-${a}`
        if (!existingEdges.has(key1) && !existingEdges.has(key2)) {
          links.push({
            source: a,
            target: b,
            score: 0,
            hidden: true,
          })
        }
      }
    }
  }

  const clusterIdList = [...clusterMembers.keys()]
  for (let i = 0; i < clusterIdList.length; i++) {
    for (let j = i + 1; j < clusterIdList.length; j++) {
      // indices come from the key list; loop bounds keep them in range
      const rep1 = clusterMembers.get(clusterIdList[i]!)?.[0]
      const rep2 = clusterMembers.get(clusterIdList[j]!)?.[0]
      if (rep1 === undefined || rep2 === undefined) continue
      const key1 = `${rep1}-${rep2}`
      const key2 = `${rep2}-${rep1}`
      if (!existingEdges.has(key1) && !existingEdges.has(key2)) {
        links.push({ source: rep1, target: rep2, score: 0, hidden: true })
      }
    }
  }

  const clusterIds = clusterIdList
  const nClusters = clusterIds.length
  const clusterRadius = 60 + nClusters * 12
  for (let ci = 0; ci < clusterIds.length; ci++) {
    // ci is bounded by clusterIds.length, so the id and its members exist
    const clusterId = clusterIds[ci]!
    const theta = (2 * Math.PI * ci) / nClusters
    // Seed jitter deterministically (by cluster/node id) so the layout is stable
    // across rebuilds instead of reshuffling on every render.
    const phi = Math.PI / 2 + (seededUnit(String(clusterId)) - 0.5) * 0.5
    const cx = Math.sin(phi) * Math.cos(theta) * clusterRadius
    const cy = Math.sin(phi) * Math.sin(theta) * clusterRadius
    const cz = Math.cos(phi) * clusterRadius * 0.3
    const spread = 30 + Math.sqrt(nodes.length) * 3
    const members = clusterMembers.get(clusterId) ?? []
    for (const id of members) {
      const node = nodes.find((n) => n.id === id)
      if (node) {
        node.x = cx + (seededUnit(id, 1) - 0.5) * spread
        node.y = cy + (seededUnit(id, 2) - 0.5) * spread
        node.z = cz + (seededUnit(id, 3) - 0.5) * spread
      }
    }
  }

  if (entityLayerEnabled && entities.length > 0) {
    const entityTypeFilter = filters.selectedEntityTypes
    const visibleEntities = entities.filter((e) => {
      if (
        entityTypeFilter &&
        entityTypeFilter.size > 0 &&
        !entityTypeFilter.has(e.entity_type)
      )
        return false
      return e.memory_ids.some((mid) => filteredIds.has(mid))
    })

    const entityIdSet = new Set(visibleEntities.map((e) => e.id))

    for (const e of visibleEntities) {
      nodes.push({
        id: `entity:${e.id}`,
        nodeKind: "entity",
        content: e.name,
        source: "",
        tags: [],
        memoryType: null,
        importance: 0,
        cluster: -1,
        clusterName: "",
        color: entityTypeColor(e.entity_type, palette),
        val: 1,
        entityName: e.name,
        entityType: e.entity_type,
        entityMemoryIds: e.memory_ids,
      })
    }

    for (const r of entityRelations) {
      if (entityIdSet.has(r.source) && entityIdSet.has(r.target)) {
        links.push({
          source: `entity:${r.source}`,
          target: `entity:${r.target}`,
          score: r.weight ?? 0,
          linkKind: "relation",
          relationType: r.type,
        })
      }
    }

    for (const e of visibleEntities) {
      for (const mid of e.memory_ids) {
        if (filteredIds.has(mid)) {
          links.push({
            source: `entity:${e.id}`,
            target: mid,
            score: 0,
            hidden: true,
            linkKind: "membership",
          })
        }
      }
    }
  }

  return { nodes, links }
}


/**
 * What a ForceAtlas2 run is computed for.
 *
 * The simulation is a function of the memory set and the two force sliders and
 * of nothing else. Deliberately absent: the entity overlay. Entities hang off
 * memories that are already placed, so toggling the layer does not invalidate
 * a layout -- and re-running one because of it threw every node across the
 * canvas twice per toggle, once on the switch and again when the data landed.
 *
 * Adding anything here means "changing this re-scatters the graph". Weigh that
 * before extending it.
 */
export function layoutSignature(
  spacing: number,
  clusterTightness: number,
  memoryIds: string[],
): string {
  // Sorted, because the server may return the same set in a different order
  // and that is not a reason to re-simulate.
  return [spacing, clusterTightness, ...[...memoryIds].sort()].join("|")
}
