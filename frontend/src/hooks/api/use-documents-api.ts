import { useMutation, useQuery } from "@tanstack/react-query"

import { ApiError, apiFetch } from "@/lib/api"

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

export function useDocuments(project?: string) {
  const qs = project ? `?project=${encodeURIComponent(project)}` : ""
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", project ?? null],
    queryFn: () => apiFetch<DocumentListResponse>(`/documents${qs}`),
  })
}

/** `null` when no summary has been generated — the door answers 404 for that,
 *  and it is an ordinary state rather than a fault: generating one is an
 *  explicit act nobody has performed yet. Every other status still throws. */
export function useDocumentSummary(documentId: string | null) {
  return useQuery<DocumentSummary | null>({
    queryKey: ["documentSummary", documentId],
    enabled: Boolean(documentId),
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
    enabled: Boolean(documentId),
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
