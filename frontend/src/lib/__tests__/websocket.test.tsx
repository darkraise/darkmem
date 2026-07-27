import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

import { useWebSocket } from "../websocket"

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  closed = false

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emitOpen() {
    this.onopen?.()
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }

  emitClose() {
    this.onclose?.()
  }

  static latest(): MockWebSocket {
    const socket = MockWebSocket.instances[MockWebSocket.instances.length - 1]
    if (!socket) throw new Error("no MockWebSocket instance was created")
    return socket
  }

  static at(index: number): MockWebSocket {
    const socket = MockWebSocket.instances[index]
    if (!socket) throw new Error(`no MockWebSocket instance at index ${index}`)
    return socket
  }
}

const PIPELINE_STATUS = {
  memory_id: "11111111-1111-1111-1111-111111111111",
  embed: "ok",
  extract: "ok",
  vector: "ok",
  graph: "ok",
  entities_count: 2,
  relations_count: 1,
  error: null,
}

const CORE_PIPELINE_KEYS = [
  "memories",
  "memory",
  "memoriesPaginated",
  "stats",
  "overview",
  "tags",
  "pipelineLogs",
]

describe("useWebSocket", () => {
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    originalWebSocket = window.WebSocket
    // @ts-expect-error -- test double stands in for the real constructor
    window.WebSocket = MockWebSocket
  })

  afterEach(() => {
    window.WebSocket = originalWebSocket
    vi.useRealTimers()
  })

  function renderWithSpy() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries")
    function localWrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    }
    const view = renderHook(() => useWebSocket(), { wrapper: localWrapper })
    return { ...view, invalidateSpy, qc }
  }

  function invalidatedKeys(spy: ReturnType<typeof vi.fn>): string[] {
    return spy.mock.calls
      .map((call) => (call[0] as { queryKey?: unknown[] })?.queryKey?.[0])
      .filter((k): k is string => typeof k === "string")
  }

  it("invalidates the same core key set for completed, partial, and failed — partial is not folded into failure", () => {
    for (const outcome of ["pipeline.completed", "pipeline.partial", "pipeline.failed"]) {
      const { invalidateSpy, unmount } = renderWithSpy()
      const socket = MockWebSocket.latest()
      socket.emitOpen()
      invalidateSpy.mockClear()

      socket.emitMessage({ event: outcome, data: PIPELINE_STATUS })

      const keys = invalidatedKeys(invalidateSpy)
      for (const expected of CORE_PIPELINE_KEYS) {
        expect(keys, `${outcome} must invalidate ${expected}`).toContain(expected)
      }
      unmount()
    }
  })

  it("gives partial its own toast branch distinct from completed/failed (Ruling 4)", async () => {
    const { toast } = await import("darkraise-ui/components/sonner")
    renderWithSpy()
    const socket = MockWebSocket.latest()
    socket.emitOpen()

    socket.emitMessage({ event: "pipeline.partial", data: PIPELINE_STATUS })

    expect(toast.warning).toHaveBeenCalled()
    expect(toast.success).not.toHaveBeenCalled()
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("does not reconcile on the first connection", () => {
    const { invalidateSpy } = renderWithSpy()
    const socket = MockWebSocket.latest()
    invalidateSpy.mockClear()

    socket.emitOpen()

    expect(invalidateSpy).not.toHaveBeenCalled()
  })

  it("reconciles every live query key after a dropped socket reconnects (Ruling 5)", () => {
    const { invalidateSpy } = renderWithSpy()
    const firstSocket = MockWebSocket.at(0)
    firstSocket.emitOpen()

    // The socket drops. onclose schedules a reconnect via the exponential
    // backoff timer rather than reconnecting immediately.
    firstSocket.emitClose()
    invalidateSpy.mockClear()

    vi.runOnlyPendingTimers()

    expect(MockWebSocket.instances.length).toBe(2)
    const secondSocket = MockWebSocket.at(1)
    secondSocket.emitOpen()

    const keys = invalidatedKeys(invalidateSpy)
    for (const expected of [
      "memories",
      "memory",
      "memoriesPaginated",
      "stats",
      "overview",
      "tags",
      "pipelineLogs",
      "pipelineFailures",
      "pipelineFailureCounts",
      "repos",
      "repoTasks",
      "repoStats",
    ]) {
      expect(keys, `reconnect must reconcile ${expected}`).toContain(expected)
    }
  })

  it("closes the socket and cancels the reconnect timer on unmount (no leaked reconnect)", () => {
    const { unmount } = renderWithSpy()
    const socket = MockWebSocket.at(0)
    socket.emitOpen()

    unmount()
    socket.emitClose()
    vi.runOnlyPendingTimers()

    // Only the original socket exists — the unmount-triggered close is
    // recognised as caller-initiated and must not schedule a reconnect.
    expect(MockWebSocket.instances.length).toBe(1)
  })
})
