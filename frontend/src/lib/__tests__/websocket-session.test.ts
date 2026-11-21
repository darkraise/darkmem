import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import { createElement, type ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { toast } from "darkraise-ui/components/sonner"
import { RENEWED_AT_KEY, recordRenewal, resetSessionRenewal, startSessionRenewal } from "../session-renewal"
import { useWebSocket } from "../websocket"
import { FakeSocket, json, minutesAhead, routeFetch } from "./session-test-kit"

const signIn = vi.fn()
const EXPIRED = "Session expired or revoked"

function wrapper({ children }: { children: ReactNode }) {
  return createElement(QueryClientProvider, { client: new QueryClient() }, children)
}

const tick = (ms = 0) => act(async () => {
  await vi.advanceTimersByTimeAsync(ms)
})

async function connected() {
  const hook = renderHook(() => useWebSocket(), { wrapper })
  await tick()
  const socket = FakeSocket.latest()
  act(() => socket.open())
  return { hook, socket }
}

beforeEach(async () => {
  vi.useFakeTimers()
  localStorage.clear()
  resetSessionRenewal()
  FakeSocket.instances = []
  vi.stubGlobal("WebSocket", FakeSocket)
  routeFetch({ "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(24 * 60) })] })
  startSessionRenewal(signIn)
  await tick()
})

afterEach(() => {
  resetSessionRenewal()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe("the socket and the session", () => {
  it("reconnects after 4001 only once the renewal is recorded", async () => {
    const { hook, socket } = await connected()
    act(() => socket.serverClose(4001, "Session renewed"))
    await tick(5_000)
    expect(FakeSocket.instances).toHaveLength(1)

    act(() => recordRenewal())
    await tick()
    expect(FakeSocket.instances).toHaveLength(2)
    expect(signIn).not.toHaveBeenCalled()
    hook.unmount()
  })

  it("reconnects after 4001 when another tab records the renewal", async () => {
    const { hook, socket } = await connected()
    act(() => socket.serverClose(4001, "Session renewed"))
    await tick(2_000)
    expect(FakeSocket.instances).toHaveLength(1)
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: RENEWED_AT_KEY, newValue: String(Date.now()) }))
    })
    await tick()
    expect(FakeSocket.instances).toHaveLength(2)
    hook.unmount()
  })

  it("goes to sign-in when no renewal follows a 4001 within ten seconds", async () => {
    const { hook, socket } = await connected()
    act(() => socket.serverClose(4001, "Session renewed"))
    await tick(10_500)
    expect(signIn).toHaveBeenCalledTimes(1)
    await tick(60_000)
    expect(FakeSocket.instances).toHaveLength(1)
    hook.unmount()
  })

  it("an expired close with no recent renewal ends the session with no retry", async () => {
    const { hook, socket } = await connected()
    act(() => socket.serverClose(1008, EXPIRED))
    await tick(120_000)
    expect(signIn).toHaveBeenCalledTimes(1)
    expect(FakeSocket.instances).toHaveLength(1)
    hook.unmount()
  })

  it("an expired close three seconds after a renewal reconnects once", async () => {
    const { hook, socket } = await connected()
    act(() => recordRenewal())
    await tick(3_000)
    act(() => socket.serverClose(1008, EXPIRED))
    await tick()
    expect(FakeSocket.instances).toHaveLength(2)
    act(() => FakeSocket.latest().serverClose(1008, EXPIRED))
    await tick(60_000)
    expect(FakeSocket.instances).toHaveLength(2)
    expect(signIn).toHaveBeenCalledTimes(1)
    hook.unmount()
  })

  it("a refused handshake after a renewal is retried once", async () => {
    const hook = renderHook(() => useWebSocket(), { wrapper })
    await tick()
    act(() => recordRenewal())
    act(() => FakeSocket.latest().serverClose(1008, "Unauthorized"))
    await tick()
    expect(FakeSocket.instances).toHaveLength(2)
    act(() => FakeSocket.latest().serverClose(1008, "Unauthorized"))
    await tick(60_000)
    expect(FakeSocket.instances).toHaveLength(2)
    expect(signIn).toHaveBeenCalledTimes(1)
    hook.unmount()
  })

  it("StrictMode leaves one socket", async () => {
    const hook = renderHook(() => useWebSocket(), { wrapper, reactStrictMode: true })
    await tick(5_000)
    expect(FakeSocket.live()).toHaveLength(1)

    const live = FakeSocket.live()[0]!
    act(() => live.open())
    act(() =>
      live.message({
        event: "pipeline.completed",
        data: {
          memory_id: "11111111-1111-1111-1111-111111111111",
          embed: "ok", extract: "ok", vector: "ok", graph: "ok",
          entities_count: 1, relations_count: 0, error: null,
        },
      }),
    )
    expect(toast.success).toHaveBeenCalledTimes(1)
    hook.unmount()
  })
})
