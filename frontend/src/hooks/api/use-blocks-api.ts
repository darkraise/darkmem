import { useMutation, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

export interface BlockWriteResponse {
  document_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** All four verbs invalidate the document's blocks and its outline.
 *
 *  Every mutation re-serialises the whole document, so every block's
 *  `char_span` and `order_index` moved -- a partial cache update would be a
 *  wrong cache, not a stale one. The document list goes too, because
 *  `block_count` changed on insert and delete.
 */
function useBlockMutation<V>(
  fn: (value: V) => Promise<BlockWriteResponse | void>,
  documentId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["documentBlocks", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentOutline", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentsAll"] })
    },
  })
}

export function useBlockUpdate(documentId: string) {
  return useBlockMutation<{
    blockId: string
    text: string
    type?: string
    properties?: Record<string, unknown> | null
  }>(
    ({ blockId, text, type, properties }) =>
      apiFetch<BlockWriteResponse>(
        `/documents/${documentId}/blocks/${blockId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ text, type, properties }),
        },
      ),
    documentId,
  )
}

export function useBlockInsert(documentId: string) {
  return useBlockMutation<{
    type: string
    text: string
    parentId?: string | null
    afterBlockId?: string | null
    properties?: Record<string, unknown> | null
  }>(
    ({ type, text, parentId, afterBlockId, properties }) =>
      apiFetch<BlockWriteResponse>(`/documents/${documentId}/blocks`, {
        method: "POST",
        body: JSON.stringify({
          type,
          text,
          parent_id: parentId ?? null,
          after_block_id: afterBlockId ?? null,
          properties: properties ?? null,
        }),
      }),
    documentId,
  )
}

export function useBlockMove(documentId: string) {
  return useBlockMutation<{
    blockId: string
    newParentId?: string | null
    afterBlockId?: string | null
  }>(
    ({ blockId, newParentId, afterBlockId }) =>
      apiFetch<BlockWriteResponse>(
        `/documents/${documentId}/blocks/${blockId}/move`,
        {
          method: "POST",
          body: JSON.stringify({
            new_parent_id: newParentId ?? null,
            after_block_id: afterBlockId ?? null,
          }),
        },
      ),
    documentId,
  )
}

export function useBlockDelete(documentId: string) {
  return useBlockMutation<{ blockId: string }>(
    ({ blockId }) =>
      apiFetch<void>(`/documents/${documentId}/blocks/${blockId}`, {
        method: "DELETE",
      }),
    documentId,
  )
}
