import { useMutation, useQuery } from "@tanstack/react-query"

import { ApiError, apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** Every documents payload carries `horizon`. The label rides the data, not
 *  only the page chrome: a client rendering this anywhere else must still be
 *  able to say what it is looking at. */
export interface DocumentListItem {
  id: string
  title: string | null
  uri: string | null
  source_type: string | null
  project: string
  block_count: number
}

export interface DocumentListResponse {
  items: DocumentListItem[]
  horizon: boolean
}

export interface DocumentSummary {
  document_id: string
  text: string
  generated_at: string
  block_count: number
  /** Always false. A summary is a report over one document, never a verified
   *  claim — the wire says so rather than leaving a renderer to infer it. */
  badged: boolean
}

export interface DocumentConnection {
  document_id: string
  title: string | null
  shared_entities: string[]
}

export interface QaCitation {
  block_id: string
  document_id: string
  span_start: number
  span_end: number
}

export interface QaSentence {
  text: string
  citation: QaCitation | null
}

export interface QaResponse {
  question: string
  outcome: "served" | "labelled" | "withheld"
  grounded: boolean
  label: string | null
  entailed: number
  total: number
  judged: boolean
  reason: string | null
  sentences: QaSentence[]
  horizon: boolean
}

/** Demo mode carries no document fixtures and no backend, so this read 401s
 *  there — and `handleUnauthorized` answers a 401 with a hard navigation to
 *  /login, which takes the page down rather than leaving the list empty. The
 *  guard is the same one `useProjects` and the usage reads carry, and
 *  `tests/demo-makes-no-api-calls.spec.ts` is what keeps the next hook from
 *  shipping without it. */
export function useDocuments(project?: string) {
  const qs = project ? `?project=${encodeURIComponent(project)}` : ""
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", project ?? null],
    queryFn: () => apiFetch<DocumentListResponse>(`/documents${qs}`),
    enabled: !DEMO,
  })
}

/** `null` when no summary has been generated — the door answers 404 for that,
 *  and it is an ordinary state rather than a fault: generating one is an
 *  explicit act nobody has performed yet. Every other status still throws. */
export function useDocumentSummary(documentId: string | null) {
  return useQuery<DocumentSummary | null>({
    queryKey: ["documentSummary", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: async () => {
      try {
        return await apiFetch<DocumentSummary>(`/documents/${documentId}/summary`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })
}

export function useDocumentConnections(documentId: string | null) {
  return useQuery<{ items: DocumentConnection[]; horizon: boolean }>({
    queryKey: ["documentConnections", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () =>
      apiFetch<{ items: DocumentConnection[]; horizon: boolean }>(
        `/documents/${documentId}/connections`,
      ),
  })
}

export interface QaParams {
  question: string
  project: string
  document_id?: string | null
}

export function useGroundedQa() {
  return useMutation<QaResponse, Error, QaParams>({
    mutationFn: (params) =>
      apiFetch<QaResponse>("/documents/qa", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

// ── The workspace's reads (2026-08-31 spec §2, §3) ───────────────────

/** The list route clamps `limit` to 200 (`backend/app/api/routes/documents.py`)
 *  and carries no `total`, so one page cannot hold a ~465-file corpus and
 *  cannot even say it was cut (review finding m1). Stitch pages until a short
 *  one; dedupe by id, because the order is `created_at DESC` and a filing that
 *  lands mid-pagination shifts every later offset. */
const PAGE_LIMIT = 200
const MAX_PAGES = 25 // 5,000 documents; a guard, not a target

export interface AllDocumentsResult {
  items: DocumentListItem[]
  /** True only when MAX_PAGES was exhausted while pages were still full.
   *  Render it as a visible banner, never drop it (invariant 14). */
  truncated: boolean
}

export function useAllDocuments(project: string) {
  return useQuery<AllDocumentsResult>({
    queryKey: ["documentsAll", project],
    enabled: !DEMO,
    queryFn: async () => {
      const byId = new Map<string, DocumentListItem>()
      let truncated = false
      for (let page = 0; ; page++) {
        if (page >= MAX_PAGES) {
          truncated = true
          break
        }
        const res = await apiFetch<DocumentListResponse>(
          `/documents?project=${encodeURIComponent(project)}` +
            `&limit=${PAGE_LIMIT}&offset=${page * PAGE_LIMIT}`,
        )
        for (const item of res.items) byId.set(item.id, item)
        if (res.items.length < PAGE_LIMIT) break
      }
      return { items: [...byId.values()], truncated }
    },
  })
}

export interface OutlineNode {
  block_id: string
  level: number
  text: string
  order_index: number | null
}

export interface BlockRow {
  block_id: string
  type: string | null
  text: string
  order_index: number | null
  char_span: [number, number] | null
}

export function useDocumentOutline(documentId: string | null) {
  return useQuery<{ document_id: string; items: OutlineNode[] }>({
    queryKey: ["documentOutline", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () => apiFetch(`/documents/${documentId}/outline`),
  })
}

export function useDocumentBlocks(documentId: string | null) {
  return useQuery<{ document_id: string; blocks: BlockRow[] }>({
    queryKey: ["documentBlocks", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () => apiFetch(`/documents/${documentId}`),
  })
}

export interface SectionHit {
  block_id: string
  document_id: string
  uri: string | null
  title: string | null
  heading_path: string[]
  path_truncated: boolean
  text: string
  score: number
}

export function useDocumentSearch() {
  return useMutation<
    { items: SectionHit[] },
    Error,
    { query: string; project: string; limit?: number }
  >({
    mutationFn: (params) =>
      apiFetch(`/documents/search`, {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}
