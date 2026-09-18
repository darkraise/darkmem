import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
  apiFetchWithHeaders: vi.fn(),
}))

import { apiFetch, apiFetchWithHeaders } from "@/lib/api"
import {
  usePageBlockDelete,
  usePageBlockInsert,
  usePageBlockUpdate,
  usePageBlocksInsertBatch,
  usePageCreate,
  usePageMove,
  usePageRename,
} from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function lastBody() {
  const calls = vi.mocked(apiFetch).mock.calls
  const init = calls[calls.length - 1]![1] as RequestInit
  return JSON.parse(String(init.body))
}

/** The queue's hash re-read goes through `pageQuery`, which normalises a WHOLE
 *  page -- `blocks` included. A stub answering a bare `{content_hash}` throws
 *  inside the normaliser and every write below rejects before it is sent. */
function pageWire(content_hash: string) {
  return {
    id: "p1",
    project: "personal",
    parent_id: null,
    order_index: 0,
    title: "Notes",
    content_hash,
    properties: null,
    content: null,
    blocks: [],
  }
}

/** Writes are the calls carrying a body; the GET arms are not. */
function writeBodies() {
  return vi
    .mocked(apiFetch)
    .mock.calls.filter((c) => (c[1] as RequestInit | undefined)?.body)
    .map((c) => JSON.parse(String((c[1] as RequestInit).body)))
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetchWithHeaders).mockReset()
})

describe("page mutations", () => {
  it("creates a page at the named parent", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p2" })
    const { result } = renderHook(() => usePageCreate(), { wrapper })
    result.current.mutate({ project: "personal", parentId: "p1", title: "Child" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages")
    expect(lastBody()).toEqual({
      project: "personal",
      title: "Child",
      parent_id: "p1",
      after_id: null,
      content: null,
    })
  })

  // The route dispatches on field PRESENCE, so a rename carrying parent_id
  // would move the page to the root and a move carrying title would rename it.
  it("renames without naming parent_id", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageRename(), { wrapper })
    result.current.mutate({ pageId: "p1", title: "New" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages/p1")
    expect(lastBody()).toEqual({ title: "New" })
  })

  it("moves without naming title", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageMove(), { wrapper })
    result.current.mutate({ pageId: "p1", parentId: null, afterId: "p3" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(lastBody()).toEqual({ parent_id: null, after_id: "p3" })
  })
})

describe("page block verbs", () => {
  it("chains the hash from one write into the next", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1")) // the queue's seed re-read
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h2" })
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h3" })
    const { result } = renderHook(() => usePageBlockUpdate("p1"), { wrapper })
    result.current.mutate({ blockId: "b1", text: "one" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    result.current.mutate({ blockId: "b1", text: "two" })
    await waitFor(() => expect(writeBodies()).toHaveLength(2))
    const bodies = writeBodies()
    expect(bodies[0]!.expected_hash).toBe("h1")
    // The second write carries the first write's answer, not a re-read: only
    // one GET happened.
    expect(bodies[1]!.expected_hash).toBe("h2")
  })

  it("sends a client-chosen block id on insert", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h2" })
    const { result } = renderHook(() => usePageBlockInsert("p1"), { wrapper })
    result.current.mutate({
      type: "paragraph",
      text: "",
      afterBlockId: "b1",
      blockId: "b9",
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(lastBody()).toMatchObject({
      type: "paragraph",
      text: "",
      after_block_id: "b1",
      block_id: "b9",
    })
  })

  it("takes the delete's new hash from X-Content-Hash, sparing a re-read", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h3" })
    vi.mocked(apiFetchWithHeaders).mockResolvedValue({
      data: undefined,
      headers: new Headers({ "X-Content-Hash": "h2" }),
    })

    const del = renderHook(() => usePageBlockDelete("p1"), { wrapper })
    del.result.current.mutate({ blockId: "b1" })
    await waitFor(() => expect(del.result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![0]).toBe(
      "/pages/p1/blocks/b1?expected_hash=h1",
    )

    const upd = renderHook(() => usePageBlockUpdate("p1"), { wrapper })
    upd.result.current.mutate({ blockId: "b2", text: "x" })
    await waitFor(() => expect(writeBodies()).toHaveLength(1))
    // Exactly one GET, the seed: the delete answered a hash in its header, so
    // the write after it did not have to re-read one. Without the header the
    // queue would null the hash and this would be two.
    expect(
      vi.mocked(apiFetch).mock.calls.filter((c) => !(c[1] as RequestInit | undefined)?.body),
    ).toHaveLength(1)
    expect(lastBody().expected_hash).toBe("h2")
  })

  it("posts a batch insert as one request", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", block_ids: ["b8", "b9"], content_hash: "h2" })
    const { result } = renderHook(() => usePageBlocksInsertBatch("p1"), { wrapper })
    result.current.mutate({
      blocks: [
        { block_id: "b8", type: "paragraph", text: "a" },
        { block_id: "b9", type: "paragraph", text: "b", after_block_id: "b8" },
      ],
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe("/pages/p1/blocks/batch")
    expect(lastBody().blocks).toHaveLength(2)
    expect(lastBody().expected_hash).toBe("h1")
  })
})
