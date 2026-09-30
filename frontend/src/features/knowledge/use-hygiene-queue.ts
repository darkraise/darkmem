import { DEMO } from "@/lib/demo-flag"
import { useDemoHygiene } from "@/demo/hooks"
import type { HygieneLineageChain, HygieneRow } from "@/demo/types"
import {
  useHygieneDuplicates,
  useHygieneExpiringSoon,
  useHygieneLowConfidence,
  useHygieneSuperseded,
  type HygieneDuplicateItem,
  type HygieneMemoryItem,
} from "@/hooks/api"

/** The Hygiene queue's four row shapes — demo and live are two producers of
 *  each, mirroring `use-review-queue.ts`. Duplicates keep their own shape
 *  (an edge between two memories) rather than merging into the memory-row
 *  shape the other three arms share, because `HygieneDuplicateItem`
 *  genuinely carries different fields (two ids, a score, and — since T2.87 —
 *  each endpoint's own preview and created_at, not one memory's
 *  content/status). */

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
  source_content_preview: string
  source_created_at: string
  target_content_preview: string
  target_created_at: string
}

export interface DuplicateDirection {
  olderId: string
  olderPreview: string
  olderCreatedAt: string
  newerId: string
  newerPreview: string
  newerCreatedAt: string
}

/** ISO instants compare correctly as plain strings only when every field is
 *  fixed-width. Pydantic drops the fractional-seconds field entirely when
 *  microseconds are exactly zero (`"...12:00:00Z"`) but emits a fixed
 *  6-digit fraction otherwise (`"...12:00:00.000001Z"`), and `'Z'` (0x5A)
 *  sorts after `'.'` (0x2E) — so the zero-fraction instant string-compares
 *  as *later* than one a microsecond after it, even though it is earlier.
 *  Padding the missing fraction before comparing restores fixed-width,
 *  order-faithful comparison without losing the microsecond precision a
 *  `Date.parse`-based comparison would (JS `Date` only resolves to the
 *  millisecond) (fix round 1, F1). */
function toComparableInstant(iso: string): string {
  return /\.\d+/.test(iso) ? iso : iso.replace(/(Z|[+-]\d{2}:\d{2})$/, ".000000$1")
}

/** Which endpoint of a duplicate pair is older — the direction a "Supersede
 *  instead" action needs to show before it applies (T2.87). This is a
 *  **display and default-payload** heuristic, not the final word:
 *  `supersede()` is the actual arbiter and refuses `successor_not_newer` if
 *  the guess is wrong. It approximates the server's own `(created_at, id)`
 *  tie-break (`successor_is_newer` in `app/services/supersede.py`):
 *  the id half of that tie-break is safe as a plain string comparison —
 *  canonical lowercase UUID text order matches Postgres's UUID byte order,
 *  the same bytes the server's own tie-break compares (verified over 200k
 *  pairs) — but the timestamp half is not safe as a raw string comparison;
 *  see `toComparableInstant` above for why, and normalize through it before
 *  comparing. */
export function duplicateDirection(row: HygieneDuplicateRowData): DuplicateDirection {
  const sourceInstant = toComparableInstant(row.source_created_at)
  const targetInstant = toComparableInstant(row.target_created_at)
  const sourceIsOlder =
    sourceInstant < targetInstant ||
    (sourceInstant === targetInstant && row.source_memory_id < row.target_memory_id)
  return sourceIsOlder
    ? {
        olderId: row.source_memory_id,
        olderPreview: row.source_content_preview,
        olderCreatedAt: row.source_created_at,
        newerId: row.target_memory_id,
        newerPreview: row.target_content_preview,
        newerCreatedAt: row.target_created_at,
      }
    : {
        olderId: row.target_memory_id,
        olderPreview: row.target_content_preview,
        olderCreatedAt: row.target_created_at,
        newerId: row.source_memory_id,
        newerPreview: row.source_content_preview,
        newerCreatedAt: row.source_created_at,
      }
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
    source_content_preview: item.source_content_preview,
    source_created_at: item.source_created_at,
    target_content_preview: item.target_content_preview,
    target_created_at: item.target_created_at,
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
    // The demo fixture carries no per-row timestamp, so the two synthetic
    // ones below are the only thing that can order this pair — rows[0]
    // always reads as the older side in demo mode.
    source_content_preview: pair.rows[0].text,
    source_created_at: "2026-08-01T00:00:00Z",
    target_content_preview: pair.rows[1].text,
    target_created_at: "2026-08-01T00:01:00Z",
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
