import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
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
    vi.clearAllMocks()
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
  // --- file-scoped reindex completion (spec 3.1 / 6) ------------------------

  async function emitCompleted(data: Record<string, unknown>) {
    const { toast } = await import("darkraise-ui/components/sonner")
    const { unmount } = renderWithSpy()
    const socket = MockWebSocket.latest()
    socket.emitOpen()
    socket.emitMessage({
      event: "repo.indexing_completed",
      data: {
        repo_id: "r1",
        files_changed: 0,
        symbols_indexed: 0,
        index_debt_drained: 0,
        index_debt_queued: 0,
        ...data,
      },
    })
    return { toast, unmount }
  }

  it("reports an all-unchanged file-scoped run as informational, not a zero-count success", async () => {
    const { toast } = await emitCompleted({
      union_accepted: 0,
      union_skipped_unchanged: 3,
      union_skipped_missing: 0,
      union_skipped_unindexable: 0,
    })

    expect(toast.success).not.toHaveBeenCalled()
    expect(toast.warning).not.toHaveBeenCalled()
    expect(toast.info).toHaveBeenCalledWith("Nothing to index", {
      description: "3 already up to date",
    })
  })

  it("warns, rather than informs, when a named file was missing or unindexable", async () => {
    const { toast } = await emitCompleted({
      union_accepted: 0,
      union_skipped_unchanged: 1,
      union_skipped_missing: 2,
      union_skipped_unindexable: 1,
    })

    expect(toast.info).not.toHaveBeenCalled()
    expect(toast.warning).toHaveBeenCalledWith("Nothing to index", {
      description: "1 already up to date · 2 not found · 1 not indexable",
    })
  })

  it("keeps the success toast when a file-scoped run indexed something, and appends what it skipped", async () => {
    const { toast } = await emitCompleted({
      files_changed: 2,
      symbols_indexed: 9,
      union_accepted: 2,
      union_skipped_unchanged: 1,
      union_skipped_missing: 0,
      union_skipped_unindexable: 0,
    })

    expect(toast.info).not.toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith("Indexed 2 files, 9 symbols", {
      description: "1 already up to date",
    })
  })

  it("leaves an ordinary reindex's toast exactly as it was", async () => {
    // No union keys at all: the run named no files, so there is nothing to
    // describe and the payload must render the way it always has.
    const { toast } = await emitCompleted({ files_changed: 4, symbols_indexed: 12 })

    expect(toast.info).not.toHaveBeenCalled()
    expect(toast.warning).not.toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith(
      "Indexed 4 files, 12 symbols",
      undefined,
    )
  })

  it("does not mistake an ordinary run that changed nothing for a file-scoped one", async () => {
    const { toast } = await emitCompleted({ files_changed: 0, symbols_indexed: 0 })

    expect(toast.info).not.toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith(
      "Indexed 0 files, 0 symbols",
      undefined,
    )
  })
})
