import { DEMO } from "@/lib/demo-flag"
import { useDemoFacts, useDemoReviewItems } from "@/demo/hooks"
import type { DemoFact, DemoReviewItem } from "@/demo/types"
import type { VerificationStatus } from "@/components/darkmem"
import {
  useReviewQueueArticles,
  useReviewQueueFacts,
  type ReviewQueueArticleItem,
  type ReviewQueueFactItem,
  type SuspectedContradiction,
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
  /** The fact's own id: what the detail link and the live ratify/reject
   *  mutations address. */
  id: string
  /** The queue row's identity, for React keys and the demo store's review
   *  actions. Live, the queue item *is* the fact, so the two agree; the demo
   *  fixture's review rows carry their own id and point at the fact through
   *  `target_id`, and linking by the row id lands on "Fact not found". */
  queue_id: string
  project: string
  /** Null when the triple is unknown — under demo, when the review row's
   *  target fact is missing from the store. A renderer must treat null as
   *  "no triple to show", not as an empty string to paper over. */
  subject_name: string | null
  rel_type: string | null
  object_name: string | null
  fact_text: string
  verification_status: VerificationStatus
  /** The backend's own reason the row is queued — 'disputed' |
   *  'under-sourced' | 'contradiction-suspected' | 'unspecified' — carried
   *  verbatim, never re-derived or reworded here (doc 12 §4's discipline
   *  extended to this field). */
  reason: string
  under_sourced: boolean
  /** Why the served rung is not the stored one, or null when nothing was
   *  withheld. This is the screen whose whole purpose is judging support, so
   *  a suppressed label has to be visible here above anywhere else. */
  label_suppressed: string | null
  /** T2.112's other side: the counterpart the model scan flagged this fact
   *  against. Null when there is no flag — a reviewer cannot confirm what
   *  they cannot see, and the fact keeps its rung while flagged, so this is
   *  a prompt to look rather than a demotion. */
  suspected_contradiction: SuspectedContradiction | null
  evidence: VerifiedEvidence | null
  created_at: string
}

export interface ReviewArticleRowData {
  /** The article's own id (see `ReviewFactRowData.id`). */
  id: string
  /** The queue row's identity (see `ReviewFactRowData.queue_id`). */
  queue_id: string
  project: string
  subject_key: string
  title: string | null
  status: string
  reason: string
  /** The held-re-synthesis finding, when the row is queued for one (doc 09
   *  §4.4, amended 2026-08-12). Null on an ordinary open-review row, and null
   *  in demo mode, whose fixture predates the marker. */
  resynthesis_held_at: string | null
  resynthesis_held_coverage: number | null
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

function factFromApi(item: ReviewQueueFactItem): ReviewFactRowData {
  return {
    id: item.id,
    queue_id: item.id,
    project: item.project,
    subject_name: item.subject_name,
    rel_type: item.rel_type,
    object_name: item.object_name,
    fact_text: item.fact,
    verification_status: statusOf(item.verification_status),
    reason: item.reason,
    under_sourced: item.demotion_pending_since !== null,
    label_suppressed: item.label_suppressed,
    suspected_contradiction: item.suspected_contradiction,
    evidence: item.evidence,
    created_at: item.created_at,
  }
}

function articleFromApi(item: ReviewQueueArticleItem): ReviewArticleRowData {
  return {
    id: item.id,
    queue_id: item.id,
    project: item.project,
    subject_key: item.subject_key,
    title: item.title,
    status: item.status,
    reason: item.reason,
    resynthesis_held_at: item.resynthesis_held_at,
    resynthesis_held_coverage: item.resynthesis_held_coverage,
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

function factFromDemo(
  item: DemoReviewItem,
  target: DemoFact | undefined,
): ReviewFactRowData {
  // The triple and the readable sentence come from the target fact itself,
  // so a queue row reads like the Facts list row it triages (triple, then
  // sentence). A missing target keeps the fallback: no triple, and the
  // review row's own text.
  return {
    id: item.target_id,
    queue_id: item.id,
    project: DEMO_PROJECT,
    subject_name: target?.subject_name ?? null,
    rel_type: target?.rel_type ?? null,
    object_name: target?.object_name ?? null,
    fact_text: target?.fact_text ?? item.claim_line ?? item.title,
    verification_status: statusOf(item.badge ?? null),
    reason: reasonOfDemo(item),
    under_sourced: Boolean(item.under_sourced),
    // The demo fixture models neither: it has no gated rung to explain and
    // no scan behind it. Inventing either would put a claim on the screen
    // that no producer made, which is what the demo/live split exists to
    // prevent.
    label_suppressed: null,
    suspected_contradiction: null,
    evidence: null,
    created_at: item.decayed ? "2026-01-01T00:00:00Z" : "2026-08-01T00:00:00Z",
  }
}

function articleFromDemo(item: DemoReviewItem): ReviewArticleRowData {
  return {
    id: item.target_id,
    queue_id: item.id,
    project: DEMO_PROJECT,
    subject_key: item.title,
    title: item.title,
    // The demo fixture predates the held marker and mints none: showing a
    // fabricated held finding would assert a measurement nothing took.
    resynthesis_held_at: null,
    resynthesis_held_coverage: null,
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
  const demoFacts = useDemoFacts()
  const api = useReviewQueueFacts(
    { project: query.project, limit: query.limit, offset: query.offset },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const matched = demoItems
      .filter((i) => i.kind === "fact")
      .filter(() => !query.project || query.project === DEMO_PROJECT)
      .map((i) =>
        factFromDemo(
          i,
          demoFacts.find((f) => f.id === i.target_id),
        ),
      )
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
