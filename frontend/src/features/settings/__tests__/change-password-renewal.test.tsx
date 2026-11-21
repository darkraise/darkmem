import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { RENEWED_AT_KEY, resetSessionRenewal, startSessionRenewal } from "@/lib/session-renewal"
import { useWebSocket } from "@/lib/websocket"
import { useChangePassword } from "../use-change-password"
import { FakeSocket, deferred, json, minutesAhead, routeFetch } from "@/lib/__tests__/session-test-kit"

const signIn = vi.fn()

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
}

const tick = (ms = 0) => act(async () => {
  await vi.advanceTimersByTimeAsync(ms)
})

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
  resetSessionRenewal()
  FakeSocket.instances = []
  vi.stubGlobal("WebSocket", FakeSocket)
})

afterEach(() => {
  resetSessionRenewal()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe("a password change", () => {
  it.each(["before", "after"] as const)(
    "a password change keeps its own tab signed in and connected (4001 %s the response)",
    async (closeArrives) => {
      const changed = deferred<Response>()
      const renewed = minutesAhead(24 * 60)
      const net = routeFetch({
        "/auth/me": [
          json({ authenticated: true, expires_at: minutesAhead(20 * 60) }),
          json({ authenticated: true, expires_at: renewed }),
        ],
        "/auth/change-password": [changed.promise],
      })
      startSessionRenewal(signIn)
      const hook = renderHook(() => ({ password: useChangePassword(), socket: useWebSocket() }), { wrapper })
      await tick()
      const socket = FakeSocket.latest()
      act(() => socket.open())

      act(() => hook.result.current.password.change({ currentPassword: "old-pass-1", newPassword: "new-pass-12" }))
      await tick()
      if (closeArrives === "before") {
        act(() => socket.serverClose(4001, "Session renewed"))
        await tick(2_000)
        expect(FakeSocket.instances).toHaveLength(1)
      }
      expect(localStorage.getItem(RENEWED_AT_KEY)).toBeNull()

      changed.resolve(json({ ok: true }))
      await tick()
      expect(localStorage.getItem(RENEWED_AT_KEY)).not.toBeNull()
      expect(net.count("/auth/me")).toBe(2)

      if (closeArrives === "after") {
        act(() => socket.serverClose(4001, "Session renewed"))
        await tick()
      }
      await tick(30_000)
      expect(FakeSocket.instances).toHaveLength(2)
      expect(signIn).not.toHaveBeenCalled()
      hook.unmount()
    },
  )
})
