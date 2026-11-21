import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth", () => ({
  useAuthStore: { getState: () => ({ logout: vi.fn(), setAuthenticated: vi.fn() }) },
}))

import { ApiError, apiFetch, apiFetchWithHeaders } from "../api"

function respond(init: {
  status: number
  body?: unknown
  headers?: Record<string, string>
}) {
  return {
    ok: init.status >= 200 && init.status < 300,
    status: init.status,
    statusText: "",
    headers: new Headers(init.headers ?? {}),
    json: async () => init.body,
  } as unknown as Response
}

describe("apiFetchWithHeaders", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("returns the parsed body beside the response headers", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 200, body: { id: "p1" }, headers: { "X-Content-Hash": "h9" } }),
    )
    const { data, headers } = await apiFetchWithHeaders<{ id: string }>("/pages/p1")
    expect(data).toEqual({ id: "p1" })
    expect(headers.get("X-Content-Hash")).toBe("h9")
    expect(vi.mocked(fetch).mock.calls[0]![0]).toBe("/api/v1/pages/p1")
  })

  it("serves headers on a 204, where the body is undefined", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 204, headers: { "X-Content-Hash": "h10" } }),
    )
    const { data, headers } = await apiFetchWithHeaders<void>("/pages/p1/blocks/b1", {
      method: "DELETE",
    })
    expect(data).toBeUndefined()
    expect(headers.get("X-Content-Hash")).toBe("h10")
  })

  it("throws the same ApiError apiFetch does, carrying the server's detail", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 409, body: { detail: "expected_hash a does not match b" } }),
    )
    await expect(apiFetchWithHeaders("/pages/p1/blocks/b1")).rejects.toBeInstanceOf(
      ApiError,
    )
    await expect(apiFetchWithHeaders("/pages/p1/blocks/b1")).rejects.toMatchObject({
      status: 409,
      message: "expected_hash a does not match b",
    })
  })

  it("apiFetch still answers the bare body", async () => {
    vi.mocked(fetch).mockResolvedValue(respond({ status: 200, body: { ok: true } }))
    await expect(apiFetch<{ ok: boolean }>("/pages")).resolves.toEqual({ ok: true })
  })
})

describe("ApiError from an error envelope", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("carries the envelope's code and details beside the message", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({
        status: 409,
        body: {
          detail: "this register changed since it was loaded",
          error: {
            code: "hash_conflict",
            message: "this register changed since it was loaded",
            details: [{ current_hash: "h2" }],
          },
        },
      }),
    )
    await expect(apiFetch("/board/registers/d/rows/1")).rejects.toMatchObject({
      status: 409,
      code: "hash_conflict",
      details: [{ current_hash: "h2" }],
      message: "this register changed since it was loaded",
    })
  })

  it("carries a 409's symbol candidates", async () => {
    const candidates = [{ id: "u1", key: "run::a.py::Worker" }]
    vi.mocked(fetch).mockResolvedValue(
      respond({
        status: 409,
        body: {
          detail: "run matches 2 symbols",
          error: { code: "symbol_ambiguous", message: "run matches 2 symbols", candidates },
        },
      }),
    )
    await expect(apiFetch("/code/blast-radius")).rejects.toMatchObject({
      status: 409,
      code: "symbol_ambiguous",
      candidates,
    })
  })

  it("leaves the code undefined when the body is not an envelope", async () => {
    vi.mocked(fetch).mockResolvedValue(respond({ status: 500, body: { detail: "boom" } }))
    await expect(apiFetch("/x")).rejects.toMatchObject({ status: 500, code: undefined })
  })
})
