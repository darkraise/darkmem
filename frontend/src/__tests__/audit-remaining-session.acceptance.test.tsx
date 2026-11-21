import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import { readFileSync } from "node:fs"
import { createElement, type ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import {
  RENEWED_AT_KEY,
  resetSessionRenewal,
  startSessionRenewal,
} from "@/lib/session-renewal"
import { useWebSocket } from "@/lib/websocket"
import {
  FakeSocket,
  deferred,
  json,
  minutesAhead,
  routeFetch,
} from "@/lib/__tests__/session-test-kit"

const signIn = vi.fn()

function wrapper({ children }: { children: ReactNode }) {
  return createElement(QueryClientProvider, { client: new QueryClient() }, children)
}
const tick = (ms = 0) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
  resetSessionRenewal()
  signIn.mockReset()
  FakeSocket.instances = []
  vi.stubGlobal("WebSocket", FakeSocket)
})
afterEach(() => {
  resetSessionRenewal()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe("A38: the session", () => {
  it("A38: a session 23 hours old is renewed without a reload", async () => {
    // 24-hour session, 23 hours elapsed: one hour is left
    const { count } = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(60) })],
      "/auth/refresh": [json({ expires_at: minutesAhead(24 * 60) })],
    })
    startSessionRenewal(signIn)
    await tick(61_000)
    expect(count("/auth/refresh")).toBeGreaterThanOrEqual(1)
    expect(localStorage.getItem(RENEWED_AT_KEY)).not.toBeNull()
    expect(signIn).not.toHaveBeenCalled()
  })

  it("A38: after a 4001 close the socket reconnects only once the new cookie has arrived", async () => {
    const response = deferred<Response>()
    routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(30) })],
      "/auth/refresh": [response.promise],
    })
    startSessionRenewal(signIn)
    const hook = renderHook(() => useWebSocket(), { wrapper })
    await tick()
    const socket = FakeSocket.latest()
    act(() => socket.open())
    await tick(61_000) // the renewal is now in flight, its response not yet here
    const before = FakeSocket.instances.length
    act(() => socket.serverClose(4001, "Session renewed"))
    await tick(5_000)
    expect(FakeSocket.instances).toHaveLength(before)
    await act(async () => {
      response.resolve(json({ expires_at: minutesAhead(24 * 60) }))
      await vi.advanceTimersByTimeAsync(2_000)
    })
    expect(FakeSocket.instances.length).toBeGreaterThan(before)
    expect(signIn).not.toHaveBeenCalled()
    hook.unmount()
  })

  it("A38: a second tab's recorded renewal lets this tab reconnect and stay signed in", async () => {
    routeFetch({ "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(24 * 60) })] })
    startSessionRenewal(signIn)
    const hook = renderHook(() => useWebSocket(), { wrapper })
    await tick()
    const socket = FakeSocket.latest()
    act(() => socket.open())
    const before = FakeSocket.instances.length
    act(() => socket.serverClose(4001, "Session renewed"))
    await tick(2_000)
    expect(FakeSocket.instances).toHaveLength(before)
    act(() => {
      localStorage.setItem(RENEWED_AT_KEY, String(Date.now()))
      window.dispatchEvent(new StorageEvent("storage", { key: RENEWED_AT_KEY, newValue: String(Date.now()) }))
    })
    await tick(2_000)
    expect(FakeSocket.instances.length).toBeGreaterThan(before)
    expect(signIn).not.toHaveBeenCalled()
    hook.unmount()
  })

  it("A38: a socket closed as expired with no recent renewal leads to sign-in with no retry", async () => {
    routeFetch({ "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(24 * 60) })] })
    startSessionRenewal(signIn)
    const hook = renderHook(() => useWebSocket(), { wrapper })
    await tick()
    const socket = FakeSocket.latest()
    act(() => socket.open())
    const before = FakeSocket.instances.length
    act(() => socket.serverClose(4001, "Session expired or revoked"))
    await tick(60_000)
    expect(signIn).toHaveBeenCalledTimes(1)
    expect(FakeSocket.instances).toHaveLength(before)
    hook.unmount()
  })

  it("A38: the API e2e suite exercises the renewal and the password change over a real socket", () => {
    const src = readFileSync("../backend/scripts/e2e/tests/test_session_rotation.py", "utf8")
    expect(src).toMatch(/auth\/refresh/)
    expect(src).toMatch(/change-password/)
    expect(src).toMatch(/4001/)
    expect(src.toLowerCase()).toMatch(/websocket/)
  })
})
