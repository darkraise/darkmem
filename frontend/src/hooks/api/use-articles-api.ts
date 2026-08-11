import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

/** One claim's grounding — doc 09 §4.3's hard FK, on the wire (T3.06).
 *
 *  `claim_span` is the stored `int4range` as `[lo, hi)`, served rather than
 *  recomputed: a span the renderer derived from the prose could disagree with
 *  the row the FK protects, and the citation would then mark text it does not
 *  ground. `fact` rides along so a claim's support renders without a second
 *  fetch per citation — "reachable in one click" is a property of the payload
 *  before it is a property of the UI. */
export interface ArticleCitation {
  id: string
  fact_id: string
  claim_span: [number | null, number | null]
  fact: string
  subject_name: string
  rel_type: string
  object_name: string
  /** False when the cited fact's belief window has closed. The citation still
   *  renders, flagged — hiding it would leave an uncited claim on the page. */
  believed: boolean
}

/** A live article row.
 *
 *  `status` is the rung a reader may **see**, already through the backend's
 *  one label producer; `label_suppressed` names why it differs from the column
 *  when it does. Nothing here recomputes either — a surface that derived a
 *  badge from `coverage` would be asserting a claim no evidence backs.
 *
 *  `coverage` is the claim-support fraction and is on the *list* row on
 *  purpose: doc 13 §5.2 shows it in Simple as well as Advanced, and a surface
 *  can only show in Simple what the list already carries. */
export interface ArticleRow {
  id: string
  subject_key: string
  project: string
  title: string | null
  status: string | null
  label_suppressed: string | null
  unverified: boolean
  coverage: number | null
  review_state: string | null
  fact_set_hash: string | null
  stale: boolean
  /** A re-synthesis of this subject was attempted and held below the coverage
   *  bar (doc 09 §4.4, amended 2026-08-12). Attention, never suppression: the
   *  article keeps its status, its badge and its place in retrieval. */
  resynthesis_held_at: string | null
  resynthesis_held_coverage: number | null
  superseded_by: string | null
  applies_when: Record<string, unknown> | null
  learned_in: string[]
  synthesized_at: string | null
  created_at: string | null
  excerpt?: string | null
}

export interface ArticleDetail extends ArticleRow {
  content: string
  citations: ArticleCitation[]
  supersedes: string | null
}

export interface ArticleListResponse {
  items: ArticleRow[]
  total: number
  limit: number
  offset: number
}

export interface ArticleListParams {
  project?: string
  limit?: number
  offset?: number
}

function articlesQueryString(params: ArticleListParams): string {
  const qs = new URLSearchParams()
  if (params.project) qs.set("project", params.project)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  return qs.toString()
}

/** `GET /knowledge/articles` — a page of live articles, each badged and
 *  stale-flagged. Superseded articles are not on it; they are reachable
 *  through the lineage pointer on the one that replaced them. */
export function useArticles(
  params: ArticleListParams = {},
  options?: { enabled?: boolean },
) {
  const query = articlesQueryString(params)
  return useQuery<ArticleListResponse>({
    queryKey: ["articles", "list", query],
    queryFn: () =>
      apiFetch<ArticleListResponse>(`/knowledge/articles${query ? `?${query}` : ""}`),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

/** `GET /knowledge/articles/{id}` — one article with its citations and both
 *  directions of its lineage. Reads a superseded article too: a pointer that
 *  404s is not lineage. */
export function useArticle(articleId: string, options?: { enabled?: boolean }) {
  return useQuery<ArticleDetail>({
    queryKey: ["articles", "detail", articleId],
    queryFn: () => apiFetch<ArticleDetail>(`/knowledge/articles/${articleId}`),
    enabled: (options?.enabled ?? true) && Boolean(articleId),
  })
}
