import { useEffect } from "react"
import {
  useMutation,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { createMutationQueue } from "@/features/documents/lib/mutation-queue"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import {
  documentBlocksQuery,
  type DocumentBlocksResponse,
} from "./use-documents-api"

export interface BlockWriteResponse {
  document_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** One queue per document, held outside React and created at its first write.
 *
 *  The editor calls the update, insert and delete hooks separately, so a
 *  queue owned by a hook instance would give each verb its own chain and
 *  serialise nothing -- which is the case the queue exists for, since the
 *  commit and the insert that follow one keystroke are two different verbs.
 *  Keyed by document id so two open documents never wait on each other.
 *  Created lazily so its seed is the hash the blocks query holds at the moment
 *  of the first write, not the one it held when the editor mounted.
 */
const queues = new Map<string, ReturnType<typeof createMutationQueue>>()
const holders = new Map<string, number>()

function queueFor(documentId: string, qc: QueryClient) {
  const existing = queues.get(documentId)
  if (existing) return existing
  const seed =
    qc.getQueryData<DocumentBlocksResponse>(
      documentBlocksQuery(documentId).queryKey,
    )?.content_hash ?? null
  const queue = createMutationQueue(seed, async () => {
    // The demo runs against no API at all -- one unguarded request signs it
    // out -- and no hash means the write goes unpreconditioned, which is what
    // the demo's mocked writes already assume.
    if (DEMO) return ""
    // Read straight through the query function rather than through
    // `fetchQuery`: an invalidation fired by the write this re-read follows
    // cancels whatever occupies the cache's in-flight slot for the key
    // (`refetchQueries` defaults `cancelRefetch` on), and a cancelled re-read
    // would reject the mutation waiting on it -- a silently lost edit. This
    // call shares no slot with the cache, so nothing can cancel it, and the
    // invalidation keeps its own guarantee that the view refetches after the
    // write.
    const data = await documentBlocksQuery(documentId).queryFn()
    return data.content_hash ?? ""
  })
  queues.set(documentId, queue)
  return queue
}

/** Discards a document's queue once nothing is editing it, so the registry
 *  cannot grow for the length of a session and no hash survives into a visit
 *  that would have to discover by refusal that the document had moved.
 */
function useQueueLifetime(documentId: string) {
  useEffect(() => {
    holders.set(documentId, (holders.get(documentId) ?? 0) + 1)
    return () => {
      const left = (holders.get(documentId) ?? 1) - 1
      if (left > 0) {
        holders.set(documentId, left)
      } else {
        holders.delete(documentId)
        queues.delete(documentId)
      }
    }
  }, [documentId])
}

/** All four verbs invalidate the document's blocks and its outline.
 *
 *  Every mutation re-serialises the whole document, so every block's
 *  `char_span` and `order_index` moved -- a partial cache update would be a
 *  wrong cache, not a stale one. The document list goes too, because
 *  `block_count` changed on insert and delete.
 *
 *  Every verb runs through the document's queue, which hands it the hash its
 *  predecessor produced and takes back the hash it wrote. A verb that answers
 *  no hash -- delete, which is 204 with no body -- reports null, and the next
 *  verb re-reads before it runs.
 */
function useBlockMutation<V>(
  fn: (value: V, expectedHash: string) => Promise<BlockWriteResponse | void>,
  documentId: string,
) {
  const qc = useQueryClient()
  useQueueLifetime(documentId)
  return useMutation({
    mutationFn: (value: V) =>
      queueFor(documentId, qc).enqueue(async (hash) => {
        const result = await fn(value, hash)
        return { result, content_hash: result?.content_hash ?? null }
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["documentBlocks", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentOutline", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentsAll"] })
    },
  })
}

/** An empty hash means none is known -- a document stored from bytes holds no
 *  content to hash. Omitting the field keeps that document's edits on the
 *  last-writer-wins path the routes default to, rather than refusing them all.
 */
function precondition(hash: string) {
  return hash === "" ? undefined : hash
}

export function useBlockUpdate(documentId: string) {
  return useBlockMutation<{
    blockId: string
    text: string
    type?: string
    properties?: Record<string, unknown> | null
  }>(
    ({ blockId, text, type, properties }, expectedHash) =>
      apiFetch<BlockWriteResponse>(
        `/documents/${documentId}/blocks/${blockId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            text,
            type,
            properties,
            expected_hash: precondition(expectedHash),
          }),
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
    ({ type, text, parentId, afterBlockId, properties }, expectedHash) =>
      apiFetch<BlockWriteResponse>(`/documents/${documentId}/blocks`, {
        method: "POST",
        body: JSON.stringify({
          type,
          text,
          parent_id: parentId ?? null,
          after_block_id: afterBlockId ?? null,
          properties: properties ?? null,
          expected_hash: precondition(expectedHash),
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
    ({ blockId, newParentId, afterBlockId }, expectedHash) =>
      apiFetch<BlockWriteResponse>(
        `/documents/${documentId}/blocks/${blockId}/move`,
        {
          method: "POST",
          body: JSON.stringify({
            new_parent_id: newParentId ?? null,
            after_block_id: afterBlockId ?? null,
            expected_hash: precondition(expectedHash),
          }),
        },
      ),
    documentId,
  )
}

export function useBlockDelete(documentId: string) {
  return useBlockMutation<{ blockId: string }>(({ blockId }, expectedHash) => {
    // The hash rides the query string here: DELETE carries no body.
    const query = precondition(expectedHash)
      ? `?expected_hash=${encodeURIComponent(expectedHash)}`
      : ""
    return apiFetch<void>(
      `/documents/${documentId}/blocks/${blockId}${query}`,
      { method: "DELETE" },
    )
  }, documentId)
}
