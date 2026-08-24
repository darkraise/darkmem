import type {
  UnifiedMemory,
  GraphEntity,
  EntityRelation,
  SimilarityEdge,
} from "@/hooks/api"

export interface FacetRow {
  key: string
  label: string
  count: number
}

export interface ClusterRow {
  id: number
  count: number
}

export interface HubEntity {
  id: string
  name: string
  entityType: string
  /** Memories on screen that assert this entity — not `memory_ids.length`,
   *  which counts assertions filtered off the canvas. */
  count: number
}

export interface LifecycleRow {
  status: string
  count: number
}

export interface GraphSummaryStats {
  memoryCount: number
  edgeCount: number
  entityCount: number
  relationCount: number
  /** Mean edges per memory. Null on an empty graph rather than NaN. */
  averageDegree: number | null
  /** Null when no memory on screen carried a status: a bar of one "unknown"
   *  band reports nothing and implies the payload said something. */
  lifecycle: LifecycleRow[] | null
  largestCluster: { id: number; count: number; share: number } | null
  unclusteredCount: number
  /** Memories with no edge to another visible memory. */
  isolatedCount: number
  meanImportance: number | null
  /** Every list below is sorted and complete; the panel decides where to cut. */
  hubs: HubEntity[]
  relationTypes: FacetRow[]
  clusters: ClusterRow[]
  tagCategories: FacetRow[]
  types: FacetRow[]
  sources: FacetRow[]
  entityTypes: FacetRow[]
}

/** The rungs in lifecycle order, so the bar reads as the lifecycle it is and
 *  not as a ranking that reshuffles when one rung overtakes another. */
const STATUS_ORDER = ["active", "superseded", "deprecated"]
const UNKNOWN_STATUS = "unknown"

function byCountThenLabel(a: FacetRow, b: FacetRow): number {
  return b.count - a.count || a.label.localeCompare(b.label)
}

function toRows(counts: Map<string, number>): FacetRow[] {
  return [...counts.entries()]
    .map(([key, count]) => ({ key, label: key, count }))
    .sort(byCountThenLabel)
}

function increment(counts: Map<string, number>, key: string): void {
  counts.set(key, (counts.get(key) ?? 0) + 1)
}

/**
 * Every number the graph summary reports, derived in one pass and with no
 * React in scope so the measures can be asserted directly.
 *
 * All four inputs are the *visible* sets. Counting entities off `data.entities`
 * while relations came from the filtered set was the panel's own long-standing
 * inconsistency: with the entity layer off it reported hundreds of entities
 * beside zero relations, and neither was on the canvas.
 */
export function deriveGraphSummary(
  memories: UnifiedMemory[],
  edges: SimilarityEdge[],
  entities: GraphEntity[],
  relations: EntityRelation[],
): GraphSummaryStats {
  const memoryIds = new Set(memories.map((m) => m.id))

  const clusterCounts = new Map<number, number>()
  const typeCounts = new Map<string, number>()
  const sourceCounts = new Map<string, number>()
  const tagCategoryCounts = new Map<string, number>()
  const statusCounts = new Map<string, number>()
  let unclusteredCount = 0
  let importanceTotal = 0
  let sawStatus = false

  for (const m of memories) {
    if (m.cluster >= 0) {
      clusterCounts.set(m.cluster, (clusterCounts.get(m.cluster) ?? 0) + 1)
    } else {
      unclusteredCount++
    }
    increment(typeCounts, m.memory_type || "(none)")
    increment(sourceCounts, m.source)
    for (const tag of m.tags) {
      increment(tagCategoryCounts, tag.includes("/") ? tag.split("/")[0]! : tag)
    }
    const status = m.status?.trim()
    if (status) sawStatus = true
    increment(statusCounts, status || UNKNOWN_STATUS)
    importanceTotal += m.importance
  }

  const connected = new Set<string>()
  let edgeCount = 0
  for (const e of edges) {
    if (!memoryIds.has(e.source) || !memoryIds.has(e.target)) continue
    edgeCount++
    connected.add(e.source)
    connected.add(e.target)
  }

  const entityTypeCounts = new Map<string, number>()
  const hubs: HubEntity[] = []
  for (const e of entities) {
    increment(entityTypeCounts, e.entity_type)
    let visible = 0
    for (const mid of e.memory_ids) if (memoryIds.has(mid)) visible++
    if (visible > 0) {
      hubs.push({
        id: e.id,
        name: e.name,
        entityType: e.entity_type,
        count: visible,
      })
    }
  }
  hubs.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))

  const relationTypeCounts = new Map<string, number>()
  for (const r of relations) increment(relationTypeCounts, r.type)

  const clusters: ClusterRow[] = [...clusterCounts.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count || a.id - b.id)

  const lifecycle = sawStatus
    ? [...statusCounts.entries()]
        .map(([status, count]) => ({ status, count }))
        .sort((a, b) => {
          const ai = STATUS_ORDER.indexOf(a.status)
          const bi = STATUS_ORDER.indexOf(b.status)
          if (ai !== bi) return (ai < 0 ? STATUS_ORDER.length : ai) -
            (bi < 0 ? STATUS_ORDER.length : bi)
          return b.count - a.count || a.status.localeCompare(b.status)
        })
    : null

  const largest = clusters[0]
  return {
    memoryCount: memories.length,
    edgeCount,
    entityCount: entities.length,
    relationCount: relations.length,
    averageDegree: memories.length > 0 ? (2 * edgeCount) / memories.length : null,
    lifecycle,
    largestCluster: largest
      ? {
          id: largest.id,
          count: largest.count,
          share: largest.count / memories.length,
        }
      : null,
    unclusteredCount,
    isolatedCount: memories.length - connected.size,
    meanImportance:
      memories.length > 0 ? importanceTotal / memories.length : null,
    hubs,
    relationTypes: toRows(relationTypeCounts),
    clusters,
    tagCategories: toRows(tagCategoryCounts),
    types: toRows(typeCounts),
    sources: toRows(sourceCounts),
    entityTypes: toRows(entityTypeCounts),
  }
}
