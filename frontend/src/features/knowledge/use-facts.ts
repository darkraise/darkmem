import { useCallback, useMemo } from "react"

import { ApiError } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { useDemoFacts } from "@/demo/hooks"
import {
  distinctFactProjects,
  distinctFactRelations,
  distinctOriginCount,
  filterFacts,
} from "@/demo/knowledge"
import type { AppliesWhen, DemoFact } from "@/demo/types"
import {
  useFactDetailQuery,
  useFactPages,
  type AppliesWhenLabel,
  type FactDetailItem,
  type FactListItem,
} from "@/hooks/api"
import type { VerificationStatus } from "@/components/darkmem"

/** The one sentinel pair the filters use, defined once and read by both the
 *  select options and the adapter. Two hand-written mappings on the same
 *  control is how "All projects" once travelled to the server as a project
 *  literally named `all` and came back empty. */
export const ALL_PROJECTS = "all"
export const ANY = "any"

/** The one row shape the Facts tab renders, whichever source fed it.
 *
 *  Mirrors `features/activity/use-feed.ts`: the demo fixture and the live API
 *  are two producers of one shape, so the surface has a single render path and
 *  a demo-only field cannot quietly become load-bearing.
 *
 *  **`claim` is carried, never composed.** Doc 12 §4 makes the badge string
 *  the contract — a consumer shows it verbatim or not at all — so this adapter
 *  moves it and never builds one. When the backend has no badge to give (a row
 *  predating the badge writer), `claim` is empty and the row renders without
 *  one rather than with a sentence this file invented. */
export interface FactRowData {
  id: string
  project: string
  subject_name: string
  rel_type: string
  object_name: string
  fact_text: string
  verification_status: VerificationStatus
  /** Verbatim from the backend's badge. Empty when there is none. */
  claim: string
  /** The badge's parts, for a surface to lay out — never to re-word. A
   *  count and a kind list are values; the sentence built from them is the
   *  claim above, and it has exactly one producer. */
  origin_count: number | null
  origin_kinds: string[]
  review_state: "open" | null
  as_of: string
  /** T2.46's `under-sourced` overlay. Served, never withheld: a corroborated
   *  fact with a pending demotion renders the caution and stays in the list. */
  under_sourced: boolean
  /** T2.95: the reason a promoted rung was withheld, null when nothing was.
   *  Carried so a suppressed row and a genuine `candidate` are distinguishable
   *  on screen, which is the whole point of the backend emitting it. */
  label_suppressed: string | null
  /** The belief axis, independent of the verification axis above. */
  window_closed: boolean
  invalid_at: string | null
  expired: boolean
  created_at: string
  /** The context restriction, as the backend labelled it. An empty array is
   *  an explicit "no restriction", which `AppliesWhenChips` renders as such —
   *  it is not the same as unknown, and must not be collapsed into one. */
  applies_when: AppliesWhen[]
}

const KNOWN_STATUSES = new Set([
  "candidate",
  "corroborated",
  "confirmed",
  "disputed",
])

export function statusOf(value: string | null): VerificationStatus {
  // An unrecognised value is rendered as `candidate` — the weakest rung —
  // rather than passed through. Under-claiming is the epic's rule, and a
  // status the UI cannot name must not be shown as a stronger one.
  return (
    KNOWN_STATUSES.has(value ?? "") ? value : "candidate"
  ) as VerificationStatus
}

/** The backend labels the axis and the value; it does not say who declared
 *  it, so the tag is left empty rather than guessed. Claiming "human" for
 *  an LLM-extracted restriction is the badge lying in the direction this
 *  epic's under-claiming rule forbids. One producer, so the list row and the
 *  detail page cannot drift into two different tag conventions. */
export function appliesWhenFromLabels(labels: AppliesWhenLabel[]): AppliesWhen[] {
  return labels.map((label) => ({ key: label.axis, value: label.value, tag: "" }))
}

function fromDemo(fact: DemoFact): FactRowData {
  // Demo windows are newest-first, so the head is the fact's current belief.
  const current = fact.windows[0]
  return {
    id: fact.id,
    project: fact.project,
    subject_name: fact.subject_name,
    rel_type: fact.rel_type,
    object_name: fact.object_name,
    fact_text: fact.fact_text,
    verification_status: fact.verification_status,
    claim: fact.claim,
    origin_count: fact.sources.length ? distinctOriginCount(fact.sources) : null,
    origin_kinds: [...new Set(fact.sources.map((s) => s.kind))],
    review_state: fact.review_state,
    as_of: fact.as_of,
    under_sourced: Boolean(fact.under_sourced_note),
    // The fixture has no suppression: the demo store is not behind a claim
    // gate, so it has no withheld rung to explain. Null is the honest value,
    // not a placeholder.
    label_suppressed: null,
    window_closed: current?.invalid_at != null,
    invalid_at: current?.invalid_at ?? null,
    expired: current?.expired_at != null,
    created_at: fact.as_of,
    applies_when: fact.applies_when,
  }
}

function fromApi(item: FactListItem): FactRowData {
  const badge = item.badge
  return {
    id: item.id,
    project: item.project,
    subject_name: item.subject_name,
    rel_type: item.rel_type,
    object_name: item.object_name,
    fact_text: item.fact,
    verification_status: statusOf(item.verification_status),
    claim: badge?.claim ?? "",
    origin_count: badge?.origin_count ?? null,
    origin_kinds: badge?.origin_kinds ?? [],
    review_state: item.review_state === "open" ? "open" : null,
    as_of: badge?.as_of ?? item.created_at,
    under_sourced: item.demotion_pending_since !== null,
    label_suppressed: item.label_suppressed,
    window_closed: item.belief_window.invalid_at !== null,
    invalid_at: item.belief_window.invalid_at,
    expired: item.belief_window.expired_at !== null,
    created_at: item.created_at,
    applies_when: appliesWhenFromLabels(item.applies_when_labels),
  }
}

/** The free-text needle matches subject **or** object, on both producers.
 *  One matcher, so a filter cannot mean one thing with the fixture and
 *  another against the vault. */
function matchesSubject(row: FactRowData, needle: string): boolean {
  if (!needle) return true
  return (
    row.subject_name.toLowerCase().includes(needle) ||
    row.object_name.toLowerCase().includes(needle)
  )
}

export interface FactsQuery {
  /** `ALL_PROJECTS` means every project — the route's own `project: None`. */
  project: string
  relation: string
  status: string
  /** Free text, matched over the loaded rows only. The route matches
   *  `subject_name` exactly, so a substring sent as a server predicate would
   *  return nothing for every partial word typed. */
  subject: string
}

export interface FactsResult {
  /** The loaded rows the free-text needle matched. */
  rows: FactRowData[]
  /** How many rows have actually been fetched, before the needle. The
   *  denominator any sentence about the free-text filter must use — it is
   *  the only corpus that filter has seen. */
  loaded: number
  /** The count **behind the server-side filters**, not the page length. A
   *  surface that reports `rows.length` as the total tells the user the page
   *  is the corpus. */
  total: number
  loading: boolean
  error: boolean
  hasMore: boolean
  fetchingMore: boolean
  fetchMore: () => void
  projects: string[]
  relations: string[]
  /** False when the option lists were derived from loaded rows with more
   *  still unfetched — the select is then a sample, and saying so is the
   *  difference between a filter and a claim about the vault. */
  optionsComplete: boolean
}

export function useFactRows(query: FactsQuery): FactsResult {
  const demoFacts = useDemoFacts()
  const api = useFactPages(
    {
      project: query.project === ALL_PROJECTS ? undefined : query.project,
      rel_type: query.relation === ANY ? undefined : query.relation,
      verification_status: query.status === ANY ? undefined : query.status,
    },
    { enabled: !DEMO },
  )

  const demoScoped = useMemo(
    () =>
      DEMO
        ? filterFacts(demoFacts, {
            subject: "",
            relation: query.relation,
            status: query.status,
            project: query.project,
          }).map(fromDemo)
        : [],
    [demoFacts, query.relation, query.status, query.project],
  )

  const apiScoped = useMemo(
    () => (api.data?.pages ?? []).flatMap((page) => page.items).map(fromApi),
    [api.data],
  )

  const scoped = DEMO ? demoScoped : apiScoped
  const needle = query.subject.trim().toLowerCase()
  const rows = useMemo(
    () => scoped.filter((row) => matchesSubject(row, needle)),
    [scoped, needle],
  )

  const pages = api.data?.pages ?? []
  const total = DEMO ? scoped.length : (pages[pages.length - 1]?.total ?? 0)
  const hasMore = DEMO ? false : (api.hasNextPage ?? false)

  const fetchNextPage = api.fetchNextPage
  const fetchMore = useCallback(() => {
    if (DEMO || !api.hasNextPage || api.isFetchingNextPage) return
    void fetchNextPage()
  }, [fetchNextPage, api.hasNextPage, api.isFetchingNextPage])

  const projects = useMemo(() => {
    if (DEMO) return distinctFactProjects(demoFacts)
    const seen = new Set(scoped.map((row) => row.project))
    // The active scope is always offered, even when this page holds no row
    // from it: a select that drops its own current value cannot be widened
    // back out of the scope it is stuck in.
    if (query.project !== ALL_PROJECTS) seen.add(query.project)
    return [...seen].sort()
  }, [demoFacts, scoped, query.project])

  const relations = useMemo(() => {
    if (DEMO) return distinctFactRelations(demoFacts)
    const seen = new Set(scoped.map((row) => row.rel_type))
    if (query.relation !== ANY) seen.add(query.relation)
    return [...seen].sort()
  }, [demoFacts, scoped, query.relation])

  return {
    rows,
    loaded: scoped.length,
    total,
    loading: DEMO ? false : api.isLoading,
    error: DEMO ? false : api.isError,
    hasMore,
    fetchingMore: DEMO ? false : api.isFetchingNextPage,
    fetchMore,
    projects,
    relations,
    optionsComplete: !hasMore,
  }
}

// ───────────────────────── the fact detail page (T2.86) ─────────────────────────

/** The live door's shape, adapted only enough to give the route stable field
 *  names — unlike `FactRowData` this is **not** shared with the demo store.
 *  The demo fixture renders a richer surface (per-side dispute provenance,
 *  a belief-window history, a ratifier's name) than `FactDetailResponse`
 *  serves; forcing one shape over both would mean either inventing fields
 *  the door does not have or stripping the demo page down to match, and
 *  T2.86 is scoped to the live path only. So the live page reads this shape
 *  and the demo page keeps reading `DemoFact` — two producers of two
 *  honestly different shapes, not one shape quietly narrowed. */
export interface LiveFactDetailData {
  id: string
  project: string
  subject_name: string
  rel_type: string
  object_name: string
  fact_text: string
  verification_status: VerificationStatus
  claim: string
  origin_count: number | null
  origin_kinds: string[]
  review_state: "open" | null
  as_of: string
  under_sourced: boolean
  label_suppressed: string | null
  demotion_pending_since: string | null
  belief_window: { valid_at: string | null; invalid_at: string | null; expired_at: string | null }
  applies_when: AppliesWhen[]
  created_at: string
  sources: FactDetailItem["sources"]
  triple_key: string
  learned_in: string[] | null
  source_file: string | null
  reference_time: string | null
  ladder: FactDetailItem["ladder"]
  ladder_total: number
  dispute: FactDetailItem["dispute"]
}

function fromApiDetail(item: FactDetailItem): LiveFactDetailData {
  const badge = item.badge
  return {
    id: item.id,
    project: item.project,
    subject_name: item.subject_name,
    rel_type: item.rel_type,
    object_name: item.object_name,
    fact_text: item.fact,
    verification_status: statusOf(item.verification_status),
    claim: badge?.claim ?? "",
    origin_count: badge?.origin_count ?? null,
    origin_kinds: badge?.origin_kinds ?? [],
    review_state: item.review_state === "open" ? "open" : null,
    as_of: badge?.as_of ?? item.created_at,
    under_sourced: item.demotion_pending_since !== null,
    label_suppressed: item.label_suppressed,
    demotion_pending_since: item.demotion_pending_since,
    belief_window: item.belief_window,
    applies_when: appliesWhenFromLabels(item.applies_when_labels),
    created_at: item.created_at,
    sources: item.sources,
    triple_key: item.triple_key,
    learned_in: item.learned_in,
    source_file: item.source_file,
    reference_time: item.reference_time,
    ladder: item.ladder,
    ladder_total: item.ladder_total,
    dispute: item.dispute,
  }
}

/** Invariant 14, applied to a single-item read: a failed fetch, a genuine
 *  404, a malformed id, and "still loading" are four states, not two, and a
 *  caller must be able to render each one differently. `not_found` requires
 *  an `ApiError` with `status === 404` specifically; `invalid` requires
 *  `status === 422` — the path param fails FastAPI's `UUID` coercion before
 *  any lookup runs, so no retry could ever succeed and none is offered. Any
 *  other thrown shape (a network error, a 500, a thrown `Error` from a test
 *  double) is `failed`, never quietly folded into either. */
export type FactDetailState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "invalid" }
  | { status: "failed"; retry: () => void }
  | { status: "ready"; fact: LiveFactDetailData }

export function useFactDetail(factId: string): FactDetailState {
  const query = useFactDetailQuery(factId, { enabled: !DEMO })

  if (DEMO) return { status: "loading" }
  if (query.isLoading) return { status: "loading" }
  if (query.isError) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return { status: "not_found" }
    }
    if (query.error instanceof ApiError && query.error.status === 422) {
      return { status: "invalid" }
    }
    return { status: "failed", retry: () => void query.refetch() }
  }
  if (!query.data) return { status: "loading" }
  return { status: "ready", fact: fromApiDetail(query.data) }
}
