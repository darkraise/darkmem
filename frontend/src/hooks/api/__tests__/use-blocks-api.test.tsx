import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
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
/** Reads are held open on demand. A read that answers instantly can never be
 *  in flight when the next thing happens, which is the whole subject of the
 *  in-flight-slot test below. */
let deferReads: boolean
let pendingReads: Array<() => void>

function serve(path: string, init?: RequestInit) {
  const method = init?.method ?? "GET"
  seen.push({
    path,
    method,
    body: init?.body ? JSON.parse(String(init.body)) : null,
  })
  if (method === "GET") {
    const answer = () => ({
      document_id: DOC,
      blocks: [],
      content_hash: readHash,
    })
    if (!deferReads) return Promise.resolve(answer())
    return new Promise((resolve) => {
      pendingReads.push(() => resolve(answer()))
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
    deferReads = false
    pendingReads = []
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
    // Both writes go out before the first one's invalidation refetch, which is
    // what says the insert took the update's answer rather than re-reading:
    // a re-read would be a GET sitting between them.
    expect(seen.slice(0, 2).map((c) => c.method)).toEqual(["PATCH", "POST"])
    expect(patch!.method).toBe("PATCH")
    expect(post!.method).toBe("POST")
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
 *  `fetchQuery`.
 *
 *  A re-read taken through the cache does not get a fetch of its own when one
 *  is already in flight for the key: `Query.fetch` hands back the running
 *  retryer's promise unwrapped. The write that preceded the re-read has just
 *  put such a fetch there -- its own `onSuccess` invalidation -- so the
 *  re-read lands on it. The next invalidation then cancels that retryer, and
 *  the rejection arrives at the mutation still waiting to be sent. The cost is
 *  a lost edit, not a stale view, which is why the re-read stays out of the
 *  cache entirely. A fetch the re-read started itself has no such second
 *  owner.
 */
describe("a write behind a delete, with a read still in flight", () => {
  beforeEach(() => {
    seen = []
    readHash = "h0"
    writeCount = 0
    deferReads = false
    pendingReads = []
    vi.mocked(apiFetch).mockImplementation(serve as never)
  })

  async function settle() {
    for (let i = 0; i < 10; i += 1) {
      const batch = pendingReads
      pendingReads = []
      batch.forEach((resolve) => resolve())
      await act(async () => {
        await Promise.resolve()
      })
    }
  }

  it("is still sent after the delete's invalidation lands", async () => {
    const qc = makeClient()
    qc.setQueryData(["documentBlocks", DOC], {
      document_id: DOC,
      blocks: [],
      content_hash: "h0",
    })
    // Every read from here is held open, so the invalidation each write fires
    // is still fetching when the next one runs.
    deferReads = true
    const { result } = renderHook(
      () => ({ ...useEditorHooks(DOC), second: useBlockUpdate(DOC) }),
      { wrapper: wrapperFor(qc) },
    )

    act(() => {
      result.current.update.mutate({ blockId: "b1", text: "one" })
    })
    await waitFor(() => expect(result.current.update.isSuccess).toBe(true))
    // The first write's invalidation is now fetching and will not finish.

    act(() => {
      result.current.remove.mutate({ blockId: "b2" })
      result.current.second.mutate({ blockId: "b3", text: "three" })
    })
    await waitFor(() => expect(result.current.remove.isSuccess).toBe(true))
    await settle()

    await waitFor(() => expect(result.current.second.isSuccess).toBe(true))
    expect(result.current.second.error).toBeNull()
    expect(writes().map((c) => c.method)).toEqual(["PATCH", "DELETE", "PATCH"])
    expect(writes()[2]!.body!.expected_hash).toBe("h-after-delete")
  })
})
