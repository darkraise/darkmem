import { useInfiniteQuery, useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface DocumentRevisionItem {
  id: string
  content_hash: string
  actor: string | null
  api_key_id: string | null
  created_at: string
}

export interface DocumentRevisionPage {
  document_id: string
  items: DocumentRevisionItem[]
  next_before: string | null
}

export interface DocumentRevision extends DocumentRevisionItem {
  document_id: string
  content: string
}

/** A document's revisions newest first, without content, paged back on the
 *  server's `before` cursor. `enabled` is the sheet's open state. */
export function useDocumentRevisions(documentId: string, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: ["documentRevisions", documentId],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams()
      if (pageParam) qs.set("before", pageParam)
      return apiFetch<DocumentRevisionPage>(`/documents/${documentId}/revisions?${qs}`)
    },
    getNextPageParam: (last: DocumentRevisionPage) => last.next_before,
    enabled: enabled && !DEMO,
  })
}

/** One revision with the content it filed. A revision never changes, so it is
 *  never refetched once read. */
export function useDocumentRevision(documentId: string, revisionId: string | null) {
  return useQuery<DocumentRevision>({
    queryKey: ["documentRevision", documentId, revisionId],
    queryFn: () => apiFetch<DocumentRevision>(`/documents/${documentId}/revisions/${revisionId}`),
    enabled: !DEMO && revisionId !== null,
    staleTime: Infinity,
  })
}
