import { DEMO } from "@/lib/demo-flag"
import { useDemoReviewItems } from "@/demo/hooks"
import type { DemoReviewItem } from "@/demo/types"
import type { VerificationStatus } from "@/components/darkmem"
import {
  useReviewQueueArticles,
  useReviewQueueCounts,
  useReviewQueueFacts,
  type ConsequenceExplanation,
  type ReviewQueueArticleItem,
  type ReviewQueueFactItem,
  type VerifiedEvidence,
} from "@/hooks/api"

/** The row shapes the Review queue renders, whichever source fed them.
 *  Mirrors `features/knowledge/use-facts.ts`: demo and live are two
 *  producers of one shape each, so the queue keeps one render path per arm
 *  and a demo-only field cannot quietly become load-bearing.
 *
 *  Facts and articles stay **two** row types rather than one merged
 *  "review item" — their backend schemas (`ReviewQueueFactItem` /
 *  `ReviewQueueArticleItem`) share almost no fields (no subject/rel/object
 *  triple on an article, no synthesized_at/title on a fact), so forcing one
 *  shape would mean every renderer branching on which half of the union is
 *  actually populated. */

const KNOWN_STATUSES = new Set([
  "candidate",
  "corroborated",
  "confirmed",
  "disputed",
])

function statusOf(value: string | null | undefined): VerificationStatus {
  return (
    KNOWN_STATUSES.has(value ?? "") ? value : "candidate"
  ) as VerificationStatus
}

export interface ReviewFactRowData {
  id: string
  project: string
  /** Null under demo — the fixture has no subject/rel/object split, and
   *  faking one would be inventing data the demo never had. A renderer must
   *  treat null as "no triple to show", not as an empty string to paper
   *  over. */
  subject_name: string | null
  rel_type: string | null
  object_name: string | null
  fact_text: string
  verification_status: VerificationStatus
  /** The backend's own reason the row is queued — 'disputed' |
   *  'under-sourced' | 'unspecified' — carried verbatim, never re-derived
   *  or reworded here (doc 12 §4's discipline extended to this field). */
  reason: string
  under_sourced: boolean
  /** One-line ranking readout, always present — composed from
   *  `consequence`'s numeric fields (there is no competing backend prose
   *  string for ranking rationale to duplicate, unlike a verification
   *  claim). Demo carries its own hand-authored equivalent. */
  rank_note: string
  /** The full per-arm breakdown backing `rank_note`. Null under demo and
   *  whenever the backend computed no ranking for the row. */
  consequence: ConsequenceExplanation | null
  evidence: VerifiedEvidence | null
  created_at: string
}

export interface ReviewArticleRowData {
  id: string
  project: string
  subject_key: string
  title: string | null
  status: string
  reason: string
  content_preview: string | null
  synthesized_at: string | null
  created_at: string
}

export interface ReviewPageQuery {
  project?: string
  limit: number
  offset: number
}

export interface ReviewFactsResult {
  rows: ReviewFactRowData[]
  total: number
  loading: boolean
  error: boolean
}

export interface ReviewArticlesResult {
  rows: ReviewArticleRowData[]
  total: number
  loading: boolean
  error: boolean
}

export interface ReviewCountsResult {
  facts: number
  articles: number
  loading: boolean
  error: boolean
  /** True whenever a project filter is active — `GET /review-queue/counts`
   *  carries no `project` parameter at all, so this total is never scoped to
   *  it. A consumer with a project filter on must say the count is
   *  unscoped, not silently present it as agreeing with the filtered list. */
  unscoped: boolean
}

function rankNoteOf(c: ConsequenceExplanation): string {
  const parts = [
    `score ${c.score.toFixed(2)}`,
    `tier ${c.tier}`,
    `frequency ${c.retrieval_frequency.component.toFixed(2)}`,
    `salience ${c.subject_salience.component.toFixed(2)}`,
  ]
  // Matches `ConsequenceBreakdown` in review-queue.tsx, which renders the
  // same boolean as "stale" — one frontend word for one backend field,
  // never two (F8). The backend's own `label` still rides verbatim either
  // way.
  if (c.staleness.stale) parts.push(`stale (${c.staleness.label})`)
  return parts.join(" · ")
}

function factFromApi(item: ReviewQueueFactItem): ReviewFactRowData {
  return {
    id: item.id,
    project: item.project,
    subject_name: item.subject_name,
    rel_type: item.rel_type,
    object_name: item.object_name,
    fact_text: item.fact,
    verification_status: statusOf(item.verification_status),
    reason: item.reason,
    under_sourced: item.demotion_pending_since !== null,
    rank_note: item.consequence
      ? rankNoteOf(item.consequence)
      : "arrival order — no consequence signal computed for this row",
    consequence: item.consequence,
    evidence: item.evidence,
    created_at: item.created_at,
  }
}

function articleFromApi(item: ReviewQueueArticleItem): ReviewArticleRowData {
  return {
    id: item.id,
    project: item.project,
    subject_key: item.subject_key,
    title: item.title,
    status: item.status,
    reason: item.reason,
    content_preview: item.content_preview,
    synthesized_at: item.synthesized_at,
    created_at: item.created_at,
  }
}

const DEMO_PROJECT = "darkmem"

function reasonOfDemo(item: DemoReviewItem): string {
  if (item.badge === "disputed") return "disputed"
  if (item.under_sourced) return "under-sourced"
  return "unspecified"
}

function factFromDemo(item: DemoReviewItem): ReviewFactRowData {
  return {
    id: item.id,
    project: DEMO_PROJECT,
    subject_name: null,
    rel_type: null,
    object_name: null,
    fact_text: item.claim_line ?? item.title,
    verification_status: statusOf(item.badge ?? null),
    reason: reasonOfDemo(item),
    under_sourced: Boolean(item.under_sourced),
    rank_note: item.rank_note,
    consequence: null,
    evidence: null,
    created_at: item.decayed ? "2026-01-01T00:00:00Z" : "2026-08-01T00:00:00Z",
  }
}

function articleFromDemo(item: DemoReviewItem): ReviewArticleRowData {
  return {
    id: item.id,
    project: DEMO_PROJECT,
    subject_key: item.title,
    title: item.title,
    status: item.badge ?? "candidate",
    reason: item.badge === "disputed" ? "disputed" : "unspecified",
    content_preview: item.note ?? item.claim_line ?? null,
    synthesized_at: null,
    created_at: item.decayed ? "2026-01-01T00:00:00Z" : "2026-08-01T00:00:00Z",
  }
}

/** Applies the same predicates the live query would send — a project filter
 *  and offset/limit paging — to the demo fixture, so a demo session's filter
 *  controls are not silently inert (a live-only guarantee is not what "the
 *  demo path must honour the query too" means). */
function demoPage<T>(
  rows: T[],
  query: { limit: number; offset: number },
): { rows: T[]; total: number } {
  return { rows: rows.slice(query.offset, query.offset + query.limit), total: rows.length }
}

export function useReviewFactRows(query: ReviewPageQuery): ReviewFactsResult {
  const demoItems = useDemoReviewItems()
  const api = useReviewQueueFacts(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = demoItems
      .filter((i) => i.kind === "fact")
      .filter(() => !query.project || query.project === DEMO_PROJECT)
      .map(factFromDemo)
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(factFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

export function useReviewArticleRows(query: ReviewPageQuery): ReviewArticlesResult {
  const demoItems = useDemoReviewItems()
  const api = useReviewQueueArticles(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = demoItems
      .filter((i) => i.kind === "article")
      .filter(() => !query.project || query.project === DEMO_PROJECT)
      .map(articleFromDemo)
    const { rows, total } = demoPage(matched, query)
    return { rows, total, loading: false, error: false }
  }

  const items = api.data?.items ?? []
  return {
    rows: items.map(articleFromApi),
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
  }
}

export function useReviewCounts(query: { project?: string }): ReviewCountsResult {
  const demoItems = useDemoReviewItems()
  const api = useReviewQueueCounts({ enabled: !DEMO })

  if (DEMO) {
    return {
      facts: demoItems.filter((i) => i.kind === "fact").length,
      articles: demoItems.filter((i) => i.kind === "article").length,
      loading: false,
      error: false,
      unscoped: Boolean(query.project),
    }
  }

  return {
    facts: api.data?.facts ?? 0,
    articles: api.data?.articles ?? 0,
    loading: api.isLoading,
    error: api.isError,
    unscoped: Boolean(query.project),
  }
}
