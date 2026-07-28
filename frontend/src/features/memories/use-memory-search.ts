import { useMemo } from "react"
import type { ExclusionItem, TraceChannel } from "@/components/darkmem"
import {
  usePaginatedSearch,
  type Memory,
  type MemoryResultTrace,
  type MemoryStatus,
} from "@/hooks/api"

export interface MemoryTraceView {
  channels: TraceChannel[]
  rrfScore: number
  summary: string
}

// Human copy for the schema-v2 exclusion reasons `_schema_v2_exclusion_reasons`
// actually emits (T1.33 amendment log) — deliberately not doc 07 §8's
// forward-looking {by_project, by_status, by_context_conflict}, which SQL
// pushdown (T1.29 series) closed before this code path can see, let alone
// count, the rows they would have named.
const EXCLUSION_COPY: Record<string, string> = {
  memory_type: "did not match the requested memory type",
  source: "did not match the requested source",
  technologies: "did not overlap the requested technologies",
  tags: "did not carry any of the requested tags",
  not_found: "ranked, then vanished before it could be re-fetched",
}

function exclusionLabel(reason: string): string {
  return EXCLUSION_COPY[reason] ?? `excluded — ${reason}`
}

// Ruling 1: an empty (or partial) exclusion strip is never proof that
// project or status scoping removed nothing. Those two run in SQL before
// this envelope can see the rows they drop, so their count would read
// "zero forever" — worse than honest silence, because zero reads as an
// affirmative "nothing was removed." This caveat renders unconditionally
// alongside the strip, including when there is nothing else to show.
export const EXCLUSION_CAVEAT =
  "These are only the reasons this request can count. Project and status scoping run in the database before counting — an absent reason here never means nothing was filtered by it."

export function traceToView(trace: MemoryResultTrace): MemoryTraceView {
  const { scores, rank_fusion_factor } = trace
  const semantic = scores.semantic ?? null
  const keyword = scores.keyword ?? null
  const rerank = scores.rerank_score ?? null
  const rrfScore = scores.rrf_score ?? 0

  const channels: TraceChannel[] = [
    { name: "semantic", fraction: semantic },
    { name: "keyword", fraction: keyword },
  ]
  if (rerank != null) {
    channels.push({
      name: "rerank",
      fraction: rerank / 10,
      display: `${rerank.toFixed(1)} / 10`,
    })
  }

  const parts = [
    `semantic ${semantic != null ? semantic.toFixed(2) : "off"}`,
    `keyword ${keyword != null ? keyword.toFixed(2) : "off"}`,
  ]
  if (rerank != null) parts.push(`reranked ${rerank.toFixed(1)}/10`)
  if (Math.abs(rank_fusion_factor - 1) > 0.001) {
    parts.push(`rank-fusion factor ${rank_fusion_factor.toFixed(3)}x`)
  }

  return {
    channels,
    rrfScore,
    summary: `${parts.join(", ")} — fused into rrf_score ${rrfScore.toFixed(4)}, the signal that ranked this row.`,
  }
}

export interface MemorySearchPageParams {
  query: string
  /** "all" or a project name — omitted from the request when "all". */
  project: string
  status: MemoryStatus[]
  limit: number
}

export interface MemorySearchRow {
  memory: Memory
  trace?: MemoryTraceView
}

export interface MemorySearchPageResult {
  rows: MemorySearchRow[]
  total: number
  exclusions: ExclusionItem[]
  isLoading: boolean
  isError: boolean
  /** A page-size bump is in flight — distinct from `isLoading` (the very
   *  first fetch), so the "loading more" footer only shows on a real
   *  paginating refetch, never a fake client-side timer. */
  isFetching: boolean
}

/**
 * The real (non-demo) counterpart of `searchDemoMemories` — always calls
 * `/search/paginated` with `with_trace: true` (Ruling 2: the bare
 * `/search` route carries no trace, and this surface needs the paginated
 * route for virtualization and paging regardless). An empty query still
 * pages the full corpus; the envelope simply reports both channels as
 * not-ran (`channels.semantic.ran === false`).
 */
export function useMemorySearchPage({
  query,
  project,
  status,
  limit,
}: MemorySearchPageParams): MemorySearchPageResult {
  const result = usePaginatedSearch({
    query: query.trim() || undefined,
    project: project === "all" ? undefined : project,
    status,
    limit,
    offset: 0,
    with_trace: true,
  })

  const rows: MemorySearchRow[] = useMemo(
    () =>
      (result.data?.items ?? []).map((memory) => ({
        memory,
        trace: memory.trace ? traceToView(memory.trace) : undefined,
      })),
    [result.data],
  )

  const exclusions: ExclusionItem[] = useMemo(() => {
    const excluded = result.data?.envelope?.excluded ?? {}
    return Object.entries(excluded)
      .filter(([, count]) => count > 0)
      .map(([reason, count]) => ({
        count,
        unit: count === 1 ? "memory" : "memories",
        reason: exclusionLabel(reason),
        tag: reason,
      }))
  }, [result.data])

  return {
    rows,
    total: result.data?.total ?? 0,
    exclusions,
    isLoading: result.isLoading,
    isError: result.isError,
    isFetching: result.isFetching,
  }
}

/** Adapts the demo store's own trace shape (`rrf_score`, doc-typed) to the
 *  same view `traceToView` produces for the real backend, so `MemoryRow`
 *  renders both sources through one prop shape. */
export function demoTraceToView(trace: {
  channels: TraceChannel[]
  rrf_score: number
  summary: string
}): MemoryTraceView {
  return { channels: trace.channels, rrfScore: trace.rrf_score, summary: trace.summary }
}
