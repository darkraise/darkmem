import { useEffect } from "react"
import {
  useMutation,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { createMutationQueue } from "@/features/documents/lib/mutation-queue"
import { apiFetch } from "@/lib/api"
import { expectedHashParam } from "@/lib/hash-precondition"
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
    // `fetchQuery`. A cache read taken while a fetch is already running for
    // the key starts none of its own -- it is handed that fetch's retryer
    // promise, unwrapped. The fetch it lands on belongs to some EARLIER
    // write's invalidation, or to any other refetch of the key still in
    // flight; the write immediately before this re-read is the one that then
    // CANCELS it, its own invalidation arriving a few ticks after this call.
    // Two different writes, which is why the race needs three mutations. The
    // rejection surfaces here, in a mutation that has not been sent yet: a
    // lost edit rather than a stale view. A fetch this call starts itself has
    // no second owner to cancel it, and the invalidation keeps its own
    // guarantee that the view refetches after the write.
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
    // Settled, not succeeded: a refusal is exactly when the rendered tree is
    // known to be wrong, and the operator decides between retrying and
    // discarding against the refetched view. One handler rather than an
    // onError beside an onSuccess, so the two paths cannot come to invalidate
    // different keys.
    onSettled: () => invalidateDocument(qc, documentId),
  })
}

export interface BlockUpdateValue {
  blockId: string
  text: string
  type?: string
  properties?: Record<string, unknown> | null
}

/** Omitting the hash (the demo's re-read answers "") falls back to the
 *  last-writer-wins the routes default to. Every filed document has a
 *  `content_hash`, including one filed from bytes, so outside the demo this is
 *  a defence against a null the server does not send. */
function sendBlockUpdate(
  documentId: string,
  { blockId, text, type, properties }: BlockUpdateValue,
  expectedHash: string,
) {
  return apiFetch<BlockWriteResponse>(
    `/documents/${documentId}/blocks/${blockId}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        text,
        type,
        properties,
        expected_hash: expectedHashParam(expectedHash),
      }),
    },
  )
}

function invalidateDocument(qc: QueryClient, documentId: string) {
  void qc.invalidateQueries({ queryKey: ["documentBlocks", documentId] })
  void qc.invalidateQueries({ queryKey: ["documentOutline", documentId] })
  void qc.invalidateQueries({ queryKey: ["documentsAll"] })
}

/** The operator's way out of a paused queue: resend the failed write (an
 *  edited update in its place when given) or drop it. Either releases the
 *  writes queued behind it. */
export function useBlockWriteRecovery(documentId: string) {
  const qc = useQueryClient()
  return {
    retry: (update?: BlockUpdateValue) =>
      queueFor(documentId, qc)
        .retry(
          update
            ? async (hash) => {
                const result = await sendBlockUpdate(documentId, update, hash)
                return { result, content_hash: result.content_hash }
              }
            : undefined,
        )
        .finally(() => invalidateDocument(qc, documentId)),
    discard: () => {
      queueFor(documentId, qc).discard()
      invalidateDocument(qc, documentId)
    },
  }
}

export function useBlockUpdate(documentId: string) {
  return useBlockMutation<BlockUpdateValue>(
    (value, expectedHash) => sendBlockUpdate(documentId, value, expectedHash),
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
          expected_hash: expectedHashParam(expectedHash),
        }),
      }),
    documentId,
  )
}

export function useBlockDelete(documentId: string) {
  return useBlockMutation<{ blockId: string }>(({ blockId }, expectedHash) => {
    // The hash rides the query string here: DELETE carries no body.
    const query = expectedHashParam(expectedHash)
      ? `?expected_hash=${encodeURIComponent(expectedHash)}`
      : ""
    return apiFetch<void>(
      `/documents/${documentId}/blocks/${blockId}${query}`,
      { method: "DELETE" },
    )
  }, documentId)
}
