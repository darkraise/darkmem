import type { VerificationStatus } from "@/components/darkmem"
import type {
  DemoArticle,
  DemoFact,
  FactSource,
  OriginKind,
} from "./types"

/** A candidate ranks below every verified rung, always; disputed sits
 *  between so contested claims stay visible above raw signal. */
export const RUNG_SORT: Record<VerificationStatus, number> = {
  confirmed: 0,
  corroborated: 1,
  disputed: 2,
  candidate: 3,
  superseded: 4,
}

export interface OriginGroup {
  origin_key: string
  kind: OriginKind
  rows: FactSource[]
}

/** Groups fact_sources by origin_key, preserving first-seen order. */
export function groupSourcesByOrigin(sources: FactSource[]): OriginGroup[] {
  const groups: OriginGroup[] = []
  const byKey = new Map<string, OriginGroup>()
  for (const source of sources) {
    const existing = byKey.get(source.origin_key)
    if (existing) {
      existing.rows.push(source)
    } else {
      const group: OriginGroup = {
        origin_key: source.origin_key,
        kind: source.kind,
        rows: [source],
      }
      byKey.set(source.origin_key, group)
      groups.push(group)
    }
  }
  return groups
}

/** The badge's K — COUNT(DISTINCT origin_key), never the raw row count. */
export function distinctOriginCount(sources: FactSource[]): number {
  return new Set(sources.map((s) => s.origin_key)).size
}

export interface FactFilter {
  subject: string
  relation: string
  status: string
  project: string
}

/** Filters then sorts confirmed → corroborated → disputed → candidate,
 *  newest as_of first within a rung, id tie-break for determinism. */
export function filterFacts(facts: DemoFact[], filter: FactFilter): DemoFact[] {
  const subject = filter.subject.trim().toLowerCase()
  const matched = facts.filter((f) => {
    if (filter.project !== "all" && f.project !== filter.project) return false
    if (filter.relation !== "any" && f.rel_type !== filter.relation) return false
    if (filter.status !== "any" && f.verification_status !== filter.status) {
      return false
    }
    if (
      subject &&
      !f.subject_name.toLowerCase().includes(subject) &&
      !f.object_name.toLowerCase().includes(subject)
    ) {
      return false
    }
    return true
  })
  return matched.sort(
    (a, b) =>
      RUNG_SORT[a.verification_status] - RUNG_SORT[b.verification_status] ||
      b.as_of.localeCompare(a.as_of) ||
      a.id.localeCompare(b.id),
  )
}

export function distinctFactRelations(facts: DemoFact[]): string[] {
  return [...new Set(facts.map((f) => f.rel_type))].sort()
}

export function distinctFactProjects(facts: DemoFact[]): string[] {
  return [...new Set(facts.map((f) => f.project))].sort()
}

/** Exactly one live article per (project, subject_key): superseded rows are
 *  reachable via lineage only, and review_state='open' rows are withheld
 *  from the corroborated view and routed to Review instead. */
export function liveArticles(
  articles: DemoArticle[],
  project: string,
): DemoArticle[] {
  return articles.filter(
    (a) =>
      (project === "all" || a.project === project) &&
      a.verification_status !== "superseded" &&
      a.review_state !== "open",
  )
}

export function withheldArticles(
  articles: DemoArticle[],
  project: string,
): DemoArticle[] {
  return articles.filter(
    (a) =>
      (project === "all" || a.project === project) &&
      a.verification_status !== "superseded" &&
      a.review_state === "open",
  )
}

/** Stale = fact_set_hash no longer matches the current verified set. The
 *  label is data from the store (the mock backend), never recomputed
 *  differently client-side. */
export function isArticleStale(article: DemoArticle): boolean {
  return article.stale != null
}
