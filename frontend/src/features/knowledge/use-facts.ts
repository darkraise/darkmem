import { DEMO } from "@/lib/demo-flag"
import { useDemoFacts } from "@/demo/hooks"
import { distinctFactProjects, distinctFactRelations } from "@/demo/knowledge"
import type { AppliesWhen, DemoFact } from "@/demo/types"
import { useFacts as useFactsApi, type FactListItem } from "@/hooks/api"
import type { VerificationStatus } from "@/components/darkmem"

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
  /** The right-hand meta line. Derived from the badge's own parts, never a
   *  second claim sentence. */
  meta: string
  review_state: "open" | null
  as_of: string
  /** T2.46's `under-sourced` overlay. Served, never withheld: a corroborated
   *  fact with a pending demotion renders the caution and stays in the list. */
  under_sourced: boolean
  /** The belief axis, independent of the verification axis above. */
  window_closed: boolean
  expired: boolean
  disputed: boolean
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

function statusOf(value: string | null): VerificationStatus {
  // An unrecognised value is rendered as `candidate` — the weakest rung —
  // rather than passed through. Under-claiming is the epic's rule, and a
  // status the UI cannot name must not be shown as a stronger one.
  return (
    KNOWN_STATUSES.has(value ?? "") ? value : "candidate"
  ) as VerificationStatus
}

function fromDemo(fact: DemoFact): FactRowData {
  return {
    id: fact.id,
    project: fact.project,
    subject_name: fact.subject_name,
    rel_type: fact.rel_type,
    object_name: fact.object_name,
    fact_text: fact.fact_text,
    verification_status: fact.verification_status,
    claim: fact.claim,
    meta: fact.meta,
    review_state: fact.review_state,
    as_of: fact.as_of,
    under_sourced: Boolean(fact.under_sourced_note),
    window_closed: false,
    expired: false,
    disputed: fact.verification_status === "disputed",
    created_at: fact.as_of,
    applies_when: fact.applies_when,
  }
}

function fromApi(item: FactListItem): FactRowData {
  const badge = item.badge
  const kinds = badge?.origin_kinds.length
    ? ` of kinds [${badge.origin_kinds.join(", ")}]`
    : ""
  return {
    id: item.id,
    project: item.project,
    subject_name: item.subject_name,
    rel_type: item.rel_type,
    object_name: item.object_name,
    fact_text: item.fact,
    verification_status: statusOf(item.verification_status),
    claim: badge?.claim ?? "",
    meta: badge
      ? `asserted by ${badge.origin_count} distinct ${
          badge.origin_count === 1 ? "origin" : "origins"
        }${kinds}`
      : "",
    review_state: item.review_state === "open" ? "open" : null,
    as_of: badge?.as_of ?? item.created_at,
    under_sourced: item.demotion_pending_since !== null,
    window_closed: item.belief_window.invalid_at !== null,
    expired: item.belief_window.expired_at !== null,
    disputed: item.verification_status === "disputed",
    created_at: item.created_at,
    // The backend labels the axis and the value; it does not say who declared
    // it, so the tag is left empty rather than guessed. Claiming "human" for
    // an LLM-extracted restriction is the badge lying in the direction this
    // epic's under-claiming rule forbids.
    applies_when: item.applies_when_labels.map((label) => ({
      key: label.axis,
      value: label.value,
      tag: "",
    })),
  }
}

export interface FactsQuery {
  project?: string
  rel_type?: string
  verification_status?: string
  limit: number
  offset: number
}

export interface FactsResult {
  rows: FactRowData[]
  /** The count **behind the filter**, not the page length. A surface that
   *  reports `rows.length` as the total tells the user the page is the
   *  corpus. */
  total: number
  loading: boolean
  error: boolean
  /** Filter options. Server-side these come from the rows on the current
   *  page, so they widen as the user pages — stated because a select that
   *  silently lists only page-one's projects looks like the whole set. */
  projects: string[]
  relations: string[]
}

export function useFactRows(query: FactsQuery): FactsResult {
  const demoFacts = useDemoFacts()
  const api = useFactsApi(
    {
      project: query.project,
      rel_type: query.rel_type,
      verification_status: query.verification_status,
      limit: query.limit,
      offset: query.offset,
    },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const rows = demoFacts.map(fromDemo)
    return {
      rows,
      total: rows.length,
      loading: false,
      error: false,
      projects: distinctFactProjects(demoFacts),
      relations: distinctFactRelations(demoFacts),
    }
  }

  const items = api.data?.items ?? []
  const rows = items.map(fromApi)
  return {
    rows,
    total: api.data?.total ?? 0,
    loading: api.isLoading,
    error: api.isError,
    projects: [...new Set(items.map((i) => i.project))].sort(),
    relations: [...new Set(items.map((i) => i.rel_type))].sort(),
  }
}
