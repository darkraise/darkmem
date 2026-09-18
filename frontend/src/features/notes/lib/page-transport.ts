import { ApiError, apiFetchWithHeaders } from "@/lib/api"
import { pageQuery } from "@/hooks/api"
import { canonicalTree, fromPageBlocks } from "./block-mapping"
import { SyncTransportError, type PageTransport } from "./page-sync"
import type { SyncOp } from "./sync-tree"

/** Browsers cap the bodies of all in-flight keepalive requests together at
 *  64 KiB; one write stays under it with room for the headers. */
export const KEEPALIVE_MAX_BODY = 60_000

function toTransportError(error: unknown): SyncTransportError {
  if (error instanceof ApiError) return new SyncTransportError(error.message, error.status)
  return new SyncTransportError(error instanceof Error ? error.message : String(error))
}

/** The page block verbs as the sync engine's transport. Every write is sent
 *  with `keepalive` when it fits, so the one in flight when the tab closes
 *  still lands. */
export function createPageTransport(pageId: string): PageTransport {
  const send = async (path: string, method: string, body?: object) => {
    const json = body === undefined ? undefined : JSON.stringify(body)
    // The keepalive cap is bytes; `json.length` counts UTF-16 code units,
    // which undercounts anything outside the Basic Latin range.
    const keepalive = json === undefined || new Blob([json]).size <= KEEPALIVE_MAX_BODY
    return apiFetchWithHeaders<{ content_hash?: string } | undefined>(path, { method, body: json, keepalive })
  }
  return {
    async read() {
      try {
        const page = await pageQuery(pageId).queryFn()
        return { tree: canonicalTree(fromPageBlocks(page.blocks)).tree, hash: page.content_hash ?? "" }
      } catch (error) {
        throw toTransportError(error)
      }
    },
    async send(op: SyncOp, expectedHash: string) {
      const expected_hash = expectedHash === "" ? undefined : expectedHash
      try {
        switch (op.kind) {
          case "insert": {
            const { data } = await send(`/pages/${pageId}/blocks/batch`, "POST", { blocks: op.blocks, expected_hash })
            return data?.content_hash ?? ""
          }
          case "move": {
            const { data } = await send(`/pages/${pageId}/blocks/${op.id}/move`, "POST", {
              new_parent_id: op.parentId,
              after_block_id: op.afterId,
              expected_hash,
            })
            return data?.content_hash ?? ""
          }
          case "update": {
            const { data } = await send(`/pages/${pageId}/blocks/${op.id}`, "PATCH", {
              text: op.text,
              type: op.type,
              properties: op.properties,
              expected_hash,
            })
            return data?.content_hash ?? ""
          }
          case "delete": {
            // DELETE carries no body, so the precondition rides the query and
            // the new hash comes back in a header.
            const query = expected_hash ? `?expected_hash=${encodeURIComponent(expected_hash)}` : ""
            const { headers } = await send(`/pages/${pageId}/blocks/${op.id}${query}`, "DELETE")
            const hash = headers.get("X-Content-Hash")
            if (hash === null) throw new SyncTransportError("the delete answered no content hash")
            return hash
          }
        }
      } catch (error) {
        throw error instanceof SyncTransportError ? error : toTransportError(error)
      }
    },
  }
}
