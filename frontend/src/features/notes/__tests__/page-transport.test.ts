import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }
})

import { ApiError, apiFetch, apiFetchWithHeaders } from "@/lib/api"
import { createPageTransport, KEEPALIVE_MAX_BODY } from "../lib/page-transport"
import { SyncTransportError } from "../lib/page-sync"

const answer = (data: unknown, headers: Record<string, string> = {}) => ({ data, headers: new Headers(headers) })

beforeEach(() => {
  vi.mocked(apiFetchWithHeaders).mockReset()
  vi.mocked(apiFetch).mockReset()
})

describe("page transport", () => {
  it("sends inserts as one batch with the precondition and keepalive", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const blocks = [{ block_id: "n", type: "paragraph", text: "x", properties: null, parent_id: null, after_block_id: null }]
    await expect(createPageTransport("p1").send({ kind: "insert", blocks }, "h1")).resolves.toBe("h2")
    const [path, init] = vi.mocked(apiFetchWithHeaders).mock.calls[0]!
    expect(path).toBe("/pages/p1/blocks/batch")
    expect(init).toMatchObject({ method: "POST", keepalive: true })
    expect(JSON.parse(String(init!.body))).toEqual({ blocks, expected_hash: "h1" })
  })

  it("maps move and update to their routes", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const t = createPageTransport("p1")
    await t.send({ kind: "move", id: "b", parentId: "l", afterId: null }, "h1")
    await t.send({ kind: "update", id: "b", type: "todo", text: "t", properties: { checked: true } }, "h2")
    const calls = vi.mocked(apiFetchWithHeaders).mock.calls
    expect(calls[0]![0]).toBe("/pages/p1/blocks/b/move")
    expect(JSON.parse(String(calls[0]![1]!.body))).toEqual({ new_parent_id: "l", after_block_id: null, expected_hash: "h1" })
    expect(calls[1]![0]).toBe("/pages/p1/blocks/b")
    expect(calls[1]![1]).toMatchObject({ method: "PATCH" })
    expect(JSON.parse(String(calls[1]![1]!.body))).toEqual({ text: "t", type: "todo", properties: { checked: true }, expected_hash: "h2" })
  })

  it("takes a delete's new hash from X-Content-Hash", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer(undefined, { "X-Content-Hash": "h9" }) as never)
    await expect(createPageTransport("p1").send({ kind: "delete", id: "b" }, "h1")).resolves.toBe("h9")
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![0]).toBe("/pages/p1/blocks/b?expected_hash=h1")
  })

  it("drops keepalive for a body over the browser's budget", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const big = "x".repeat(KEEPALIVE_MAX_BODY)
    await createPageTransport("p1").send({ kind: "update", id: "b", type: "paragraph", text: big, properties: null }, "h1")
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![1]).toMatchObject({ keepalive: false })
  })

  it("carries the HTTP status of a refusal, and none for a network failure", async () => {
    vi.mocked(apiFetchWithHeaders).mockRejectedValueOnce(new ApiError("stale", 409))
    const refused = await createPageTransport("p1")
      .send({ kind: "delete", id: "b" }, "h1")
      .catch((e: unknown) => e)
    expect(refused).toBeInstanceOf(SyncTransportError)
    expect((refused as SyncTransportError).status).toBe(409)

    vi.mocked(apiFetchWithHeaders).mockRejectedValueOnce(new TypeError("Failed to fetch"))
    const offline = await createPageTransport("p1")
      .send({ kind: "delete", id: "b" }, "h1")
      .catch((e: unknown) => e)
    expect((offline as SyncTransportError).status).toBeUndefined()
  })

  it("reads the page back canonicalised", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: null,
      content_hash: "h5",
      properties: null,
      content: null,
      blocks: [
        { id: "b", parent_id: null, order_index: 1, type: "paragraph", text: "__x__", properties: null, char_start: 0, char_end: 5, source: "__x__" },
        { id: "a", parent_id: null, order_index: 0, type: "list", text: "a", properties: { ordered: false, marker: "*", number: 1 }, char_start: 0, char_end: 3, source: "* a" },
      ],
    })
    await expect(createPageTransport("p1").read()).resolves.toEqual({
      hash: "h5",
      tree: [
        { id: "a", parentId: null, type: "list", text: "a", properties: { ordered: false, marker: "*" } },
        { id: "b", parentId: null, type: "paragraph", text: "**x**", properties: null },
      ],
    })
  })
})
