import { DEMO } from "@/lib/demo-flag"
import { useDemoHygiene } from "@/demo/hooks"
import type { HygieneLineageChain, HygieneRow } from "@/demo/types"
import {
  useHygieneCounts,
  useHygieneDuplicates,
  useHygieneExpiringSoon,
  useHygieneLowConfidence,
  useHygieneSuperseded,
  type HygieneCountsResponse,
  type HygieneDuplicateItem,
  type HygieneMemoryItem,
} from "@/hooks/api"

/** The Hygiene queue's four row shapes — demo and live are two producers of
 *  each, mirroring `use-review-queue.ts`. Duplicates keep their own shape
 *  (an edge between two memories, no content) rather than merging into the
 *  memory-row shape the other three arms share, because
 *  `HygieneDuplicateItem` genuinely carries different fields (two ids and a
 *  score, not one memory's content/status). */

export interface HygieneDuplicateRowData {
  id: string
  source_memory_id: string
  target_memory_id: string
  rel_type: string
  project: string
  score: number | null
  verdict: string | null
  hygiene_state: string | null
  detected_at: string | null
  created_at: string
}

export interface HygieneMemoryRowData {
  id: string
  project: string
  content_preview: string
  confidence: number | null
  expires_at: string | null
  status: string
  superseded_by: string | null
  reason: string
  created_at: string
}

export interface HygienePageQuery {
  project?: string
  limit: number
  offset: number
}

export interface HygieneListResult<T> {
  rows: T[]
  total: number
  loading: boolean
  error: boolean
}

export interface HygieneCountsResult {
  duplicates: number
  low_confidence: number
  expiring_soon: number
  superseded: number
  loading: boolean
  error: boolean
}

const DEMO_PROJECT = "darkmem"

function duplicateFromApi(item: HygieneDuplicateItem): HygieneDuplicateRowData {
  return {
    id: item.id,
    source_memory_id: item.source_memory_id,
    target_memory_id: item.target_memory_id,
    rel_type: item.rel_type,
    project: item.project,
    score: item.score,
    verdict: item.verdict,
    hygiene_state: item.hygiene_state,
    detected_at: item.detected_at,
    created_at: item.created_at,
  }
}

function memoryFromApi(item: HygieneMemoryItem): HygieneMemoryRowData {
  return {
    id: item.id,
    project: item.project,
    content_preview: item.content_preview,
    confidence: item.confidence,
    expires_at: item.expires_at,
    status: item.status,
    superseded_by: item.superseded_by,
    reason: item.reason,
    created_at: item.created_at,
  }
}

function duplicateFromDemo(
  pair: { id: string; connector: string; rows: [HygieneRow, HygieneRow] },
): HygieneDuplicateRowData {
  return {
    id: pair.id,
    source_memory_id: pair.rows[0].id,
    target_memory_id: pair.rows[1].id,
    rel_type: "near_duplicate",
    project: DEMO_PROJECT,
    score: null,
    verdict: pair.connector,
    hygiene_state: "open",
    detected_at: null,
    created_at: "2026-08-01T00:00:00Z",
  }
}

function memoryFromDemoRow(row: HygieneRow, reason: string): HygieneMemoryRowData {
  return {
    id: row.id,
    project: DEMO_PROJECT,
    content_preview: row.text,
    confidence: null,
    expires_at: null,
    status: "active",
    superseded_by: null,
    reason,
    created_at: "2026-08-01T00:00:00Z",
  }
}

/** The backend's `superseded` arm lists individually-superseded memory rows,
 *  never a multi-hop chain — flattening the demo's richer chain fixture into
 *  that shape drops the chain grouping, which is the honest translation:
 *  live has no chain grouping to preserve either. Only links the demo itself
 *  marks `superseded` survive, matching the backend's own
 *  `status = 'superseded'` predicate. */
function supersededRowsFromDemo(chains: HygieneLineageChain[]): HygieneMemoryRowData[] {
  const rows: HygieneMemoryRowData[] = []
  for (const chain of chains) {
    chain.links.forEach((link, i) => {
      if (link.status !== "superseded") return
      const successor = chain.links[i + 1]
      rows.push({
        id: `${chain.id}-${i}`,
        project: DEMO_PROJECT,
        content_preview: link.text,
        confidence: null,
        expires_at: null,
        status: "superseded",
        superseded_by: successor ? `${chain.id}-${i + 1}` : null,
        reason: "superseded_lineage",
        created_at: "2026-08-01T00:00:00Z",
      })
    })
  }
  return rows
}

function demoPage<T>(
  rows: T[],
  query: { limit: number; offset: number },
): { rows: T[]; total: number } {
  return { rows: rows.slice(query.offset, query.offset + query.limit), total: rows.length }
}

function projectMatches(project: string | undefined): boolean {
  return !project || project === DEMO_PROJECT
}

export function useHygieneDuplicateRows(
  query: HygienePageQuery,
): HygieneListResult<HygieneDuplicateRowData> {
  const demo = useDemoHygiene()
  const api = useHygieneDuplicates(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = projectMatches(query.project)
      ? demo.duplicates.map(duplicateFromDemo)
      : []
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(duplicateFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

export function useHygieneLowConfidenceRows(
  query: HygienePageQuery,
): HygieneListResult<HygieneMemoryRowData> {
  const demo = useDemoHygiene()
  const api = useHygieneLowConfidence(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = projectMatches(query.project)
      ? demo.lowConfidence.map((r) => memoryFromDemoRow(r, "low_confidence"))
      : []
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(memoryFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

export function useHygieneExpiringRows(
  query: HygienePageQuery,
): HygieneListResult<HygieneMemoryRowData> {
  const demo = useDemoHygiene()
  const api = useHygieneExpiringSoon(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = projectMatches(query.project)
      ? demo.expiring.map((r) => memoryFromDemoRow(r, "expiring_soon"))
      : []
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(memoryFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

export function useHygieneSupersededRows(
  query: HygienePageQuery,
): HygieneListResult<HygieneMemoryRowData> {
  const demo = useDemoHygiene()
  const api = useHygieneSuperseded(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = projectMatches(query.project)
      ? supersededRowsFromDemo(demo.lineage)
      : []
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(memoryFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

function demoCounts(
  demo: ReturnType<typeof useDemoHygiene>,
  project: string | undefined,
): HygieneCountsResponse {
  if (!projectMatches(project)) {
    return { duplicates: 0, low_confidence: 0, expiring_soon: 0, superseded: 0 }
  }
  return {
    duplicates: demo.duplicates.length,
    low_confidence: demo.lowConfidence.length,
    expiring_soon: demo.expiring.length,
    superseded: supersededRowsFromDemo(demo.lineage).length,
  }
}

export function useHygieneCountsRows(query: { project?: string }): HygieneCountsResult {
  const demo = useDemoHygiene()
  const api = useHygieneCounts({ project: query.project }, { enabled: !DEMO })

  if (DEMO) {
    const counts = demoCounts(demo, query.project)
    return { ...counts, loading: false, error: false }
  }

  return {
    duplicates: api.data?.duplicates ?? 0,
    low_confidence: api.data?.low_confidence ?? 0,
    expiring_soon: api.data?.expiring_soon ?? 0,
    superseded: api.data?.superseded ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}
