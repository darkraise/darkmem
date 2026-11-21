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

/** Sizing by weight rather than by degree: degree is already drawn, as the
 *  spokes leaving the node, so spending radius on it says one thing twice. */
export const DEFAULT_SIZE_MODE: SizeMode = "importance"

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
  /** Where the cluster force pulls this node; set for clustered memories. */
  anchor?: { x: number; y: number; z: number }
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

/** The node carries only a preview of its content, so the text filter reads
 *  the preview and the tags. */
export function matchesSearchText(
  memory: Pick<UnifiedMemory, "content" | "tags">,
  searchText: string,
): boolean {
  const term = searchText.trim().toLowerCase()
  if (!term) return true
  return (
    memory.content.toLowerCase().includes(term) ||
    memory.tags.some((t) => t.toLowerCase().includes(term))
  )
}

function matchesFilter(memory: UnifiedMemory, filters: FilterState): boolean {
  if (filters.searchText) {
    if (!matchesSearchText(memory, filters.searchText)) return false
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

  // Clusters hold together through one anchor each (the renderer's cluster
  // force), not hidden links: a link per member pair is quadratic in the
  // cluster's size.
  const nodeById = new Map(nodes.map((n) => [n.id, n]))
  const clusterIds = [...clusterMembers.keys()]
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
      const node = nodeById.get(id)
      if (node) {
        node.anchor = { x: cx, y: cy, z: cz }
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
 * The node set actually being drawn. Adding or
 * dropping the entity overlay genuinely changes the graph, so it belongs here
 * and the simulation should re-settle around it.
 *
 * What it must NOT change on is a fetch in flight. Toggling the layer starts a
 * request, and the render that happens in between draws the same nodes as
 * before -- same signature, no re-run, nothing moves. The signature moves when
 * the data lands, which is when there is something new to arrange.
 */
export function layoutSignature(
  memoryIds: string[],
  entityIds: string[] = [],
): string {
  // Sorted, because the server may return the same set in a different order
  // and that is not a reason to re-simulate.
  return [
    ...[...memoryIds].sort(),
    "|entities|",
    ...[...entityIds].sort(),
  ].join("|")
}


/**
 * What the entity overlay would draw, as a string.
 *
 * The renderer keys its rebuild on this rather than on the toggle, because the
 * two are not the same thing. Flipping the switch on starts a fetch, and until
 * it lands there are no entities in hand -- the overlay would draw exactly what
 * it drew before. Rebuilding for that tears down and recreates sigma's WebGL
 * canvases to produce an identical picture.
 *
 * Empty means "nothing to overlay", whether the layer is off or its data has
 * not arrived. Those two states look the same, so they key the same.
 */
export function entityRenderKey(
  enabled: boolean,
  entities: { id: string; entity_type: string }[],
): string {
  if (!enabled) return ""
  // Type is in the key because it picks the node's colour: an entity whose
  // type changed is a different picture even at the same id.
  return entities.map((e) => `${e.id}:${e.entity_type}`).join("|")
}

/** The same, for the relations drawn between those entities. */
export function relationRenderKey(
  enabled: boolean,
  relations: { source: string; target: string; type: string }[],
): string {
  if (!enabled) return ""
  return relations.map((r) => `${r.source}>${r.target}:${r.type}`).join("|")
}
