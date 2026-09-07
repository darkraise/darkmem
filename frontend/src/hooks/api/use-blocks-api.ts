import { useEffect } from "react"
import {
  useMutation,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { createMutationQueue } from "@/features/documents/lib/mutation-queue"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { documentBlocksQuery } from "./use-documents-api"

export interface BlockWriteResponse {
  document_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** One queue per document, held outside React.
 *
 *  The editor calls the update, insert and delete hooks separately, so a
 *  queue owned by a hook instance would give each verb its own chain and
 *  serialise nothing -- which is the case the queue exists for, since the
 *  commit and the insert that follow one keystroke are two different verbs.
 *  Keyed by document id so two open documents never wait on each other.
 */
const queues = new Map<
  string,
  { queue: ReturnType<typeof createMutationQueue>; holders: number }
>()

function queueFor(documentId: string, qc: QueryClient) {
  const existing = queues.get(documentId)
  if (existing) return existing.queue
  // Seeded null so the first mutation reads the hash it is about to use,
  // rather than one captured before the editor rendered.
  const queue = createMutationQueue(null, async () => {
    // The re-read is the only fetch the queue makes, and the demo runs
    // against no API at all -- one unguarded request signs the demo out.
    if (DEMO) return ""
    const data = await qc.fetchQuery({
      ...documentBlocksQuery(documentId),
      staleTime: 0,
    })
    return data.content_hash ?? ""
  })
  queues.set(documentId, { queue, holders: 0 })
  return queue
}

/** Discards a document's queue once nothing is editing it, so the registry
 *  cannot grow for the length of a session and no hash survives into a visit
 *  that would have to discover by refusal that the document had moved.
 */
function useQueueLifetime(documentId: string, qc: QueryClient) {
  useEffect(() => {
    queueFor(documentId, qc)
    const entry = queues.get(documentId)!
    entry.holders += 1
    return () => {
      entry.holders -= 1
      if (entry.holders <= 0 && queues.get(documentId) === entry) {
        queues.delete(documentId)
      }
    }
  }, [documentId, qc])
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
  useQueueLifetime(documentId, qc)
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
