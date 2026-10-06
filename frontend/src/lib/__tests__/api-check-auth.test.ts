import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth", () => ({
  useAuthStore: { getState: () => ({ logout: vi.fn(), setAuthenticated: vi.fn() }) },
}))

import { checkAuth } from "../api"

function answer(status: number) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status } as Response),
  )
}

describe("checkAuth", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("is true for a live session and false only when the server refuses it", async () => {
    answer(200)
    expect(await checkAuth()).toBe(true)
    answer(401)
    expect(await checkAuth()).toBe(false)
    answer(403)
    expect(await checkAuth()).toBe(false)
  })

  it("cannot tell when the probe fails, so it does not report a sign-out", async () => {
    // A navigation that aborts the probe used to log a valid session out.
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")))
    expect(await checkAuth()).toBeNull()
    answer(502)
    expect(await checkAuth()).toBeNull()
  })
})
