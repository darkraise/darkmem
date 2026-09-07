import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import {
  QueryClient,
  QueryClientProvider,
  QueryObserver,
} from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useBlockDelete,
  useBlockInsert,
  useBlockUpdate,
} from "../use-blocks-api"
import { useDocumentBlocks } from "../use-documents-api"

const DOC = "doc-1"

interface Seen {
  path: string
  method: string
  body: Record<string, unknown> | null
}

let seen: Seen[]
/** What a read answers, and what a write answers, kept apart on purpose: a
 *  hash carried forward from a write and a hash that came from a re-read must
 *  be distinguishable in the assertions. */
let readHash: string
let writeCount: number

function serve(path: string, init?: RequestInit) {
  const method = init?.method ?? "GET"
  seen.push({
    path,
    method,
    body: init?.body ? JSON.parse(String(init.body)) : null,
  })
  if (method === "GET") {
    return Promise.resolve({
      document_id: DOC,
      blocks: [],
      content_hash: readHash,
    })
  }
  // Delete is 204 with no body, and it moved the document -- so a read after
  // one answers a hash no write handed back.
  if (method === "DELETE") {
    readHash = "h-after-delete"
    return Promise.resolve(undefined)
  }
  writeCount += 1
  readHash = `w${writeCount}`
  return Promise.resolve({
    document_id: DOC,
    block_id: "b1",
    outcome: "written",
    content_hash: `w${writeCount}`,
    blocks_total: 1,
    blocks_embedded: 1,
  })
}

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function wrapperFor(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

/** The editor's own shape: the blocks query is mounted beside the verbs, so
 *  the invalidation each write fires has a live observer to refetch. */
function useEditorHooks(documentId: string) {
  return {
    blocks: useDocumentBlocks(documentId),
    update: useBlockUpdate(documentId),
    insert: useBlockInsert(documentId),
    remove: useBlockDelete(documentId),
  }
}

const writes = () => seen.filter((c) => c.method !== "GET")

describe("the block hooks share one chain per document", () => {
  beforeEach(() => {
    seen = []
    readHash = "h0"
    writeCount = 0
    vi.mocked(apiFetch).mockImplementation(serve as never)
  })

  it("feeds the insert the hash the update returned, with no read between", async () => {
    const qc = makeClient()
    const { result } = renderHook(() => useEditorHooks(DOC), {
      wrapper: wrapperFor(qc),
    })
    await waitFor(() => expect(result.current.blocks.isSuccess).toBe(true))
    seen = []

    // Fired synchronously, exactly as the editor fires a commit and an insert.
    act(() => {
      result.current.update.mutate({ blockId: "b1", text: "one" })
      result.current.insert.mutate({ type: "paragraph", text: "" })
    })
    await waitFor(() => {
      expect(result.current.update.isSuccess).toBe(true)
      expect(result.current.insert.isSuccess).toBe(true)
    })

    const [patch, post] = writes()
    expect(patch!.method).toBe("PATCH")
    expect(post!.method).toBe("POST")
    // The seed comes from the blocks query's cached hash, so the first write
    // costs no read of its own.
    expect(seen[0]!.method).toBe("PATCH")
    expect(patch!.body!.expected_hash).toBe("h0")
    expect(post!.body!.expected_hash).toBe("w1")
  })

  it("survives a delete's own invalidation and still sends the next write", async () => {
    const qc = makeClient()
    const { result } = renderHook(() => useEditorHooks(DOC), {
      wrapper: wrapperFor(qc),
    })
    await waitFor(() => expect(result.current.blocks.isSuccess).toBe(true))
    seen = []

    act(() => {
      result.current.remove.mutate({ blockId: "b1" })
      result.current.update.mutate({ blockId: "b2", text: "two" })
    })
    await waitFor(() => {
      expect(result.current.remove.isSuccess).toBe(true)
      expect(result.current.update.isPending).toBe(false)
      expect(result.current.update.isIdle).toBe(false)
    })

    expect(result.current.update.error).toBeNull()
    const [del, patch] = writes()
    expect(del!.method).toBe("DELETE")
    expect(del!.path).toContain("expected_hash=h0")
    expect(patch!.method).toBe("PATCH")
    // Delete answers 204 with no body, so the hash for the next write can only
    // come from a re-read.
    expect(patch!.body!.expected_hash).toBe("h-after-delete")
  })

  it("discards the queue once nothing is editing the document", async () => {
    const qc = makeClient()
    const wrapper = wrapperFor(qc)
    qc.setQueryData(["documentBlocks", DOC], {
      document_id: DOC,
      blocks: [],
      content_hash: "h0",
    })

    const first = renderHook(() => useBlockUpdate(DOC), { wrapper })
    act(() => {
      first.result.current.mutate({ blockId: "b1", text: "one" })
    })
    await waitFor(() => expect(first.result.current.isSuccess).toBe(true))
    first.unmount()

    const second = renderHook(() => useBlockUpdate(DOC), { wrapper })
    act(() => {
      second.result.current.mutate({ blockId: "b1", text: "two" })
    })
    await waitFor(() => expect(second.result.current.isSuccess).toBe(true))
    second.unmount()

    // A retained queue would still be holding the first write's answer.
    expect(writes()[1]!.body!.expected_hash).toBe("h0")
  })
})

/** Why the re-read calls the query function directly instead of going through
 *  `fetchQuery`. An invalidation cancels whatever occupies the cache's
 *  in-flight slot for a key, and the queue's re-read is awaited by a mutation
 *  that has not been sent yet -- so a cancelled re-read is a lost edit, not a
 *  stale view. The ordering that produces it is not ours to control: a
 *  reconnect refetch, a second observer mounting or any later invalidation of
 *  this key all fire on their own schedule.
 */
describe("the cache's in-flight slot", () => {
  it("cancels a fetchQuery an invalidation lands on", async () => {
    const qc = makeClient()
    const options = {
      queryKey: ["documentBlocks", "probe"],
      queryFn: () =>
        new Promise((resolve) => setTimeout(() => resolve("read"), 20)),
    }
    const unsubscribe = new QueryObserver(qc, options as never).subscribe(
      () => {},
    )
    await qc.fetchQuery(options as never)

    // A write's invalidation puts a refetch in the slot; the re-read that
    // follows it dedupes onto that refetch rather than starting its own, and
    // the next invalidation cancels the one retryer they now share.
    void qc.invalidateQueries({ queryKey: options.queryKey })
    const cacheRead = qc.fetchQuery({ ...options, staleTime: 0 } as never)
    void qc.invalidateQueries({ queryKey: options.queryKey })
    await expect(cacheRead).rejects.toThrow("CancelledError")

    // The same read taken outside the cache is untouched by the same event.
    const directRead = options.queryFn()
    void qc.invalidateQueries({ queryKey: options.queryKey })
    await expect(directRead).resolves.toBe("read")
    unsubscribe()
  })
})
