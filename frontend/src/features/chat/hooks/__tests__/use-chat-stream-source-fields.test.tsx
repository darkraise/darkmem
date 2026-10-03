import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useChatStream } from "../use-chat-stream"
import { useAuthStore } from "@/features/auth"

function sseStreamFromEvents(events: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("")
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  vi.unstubAllGlobals()
})

// T1.60 Step 6: ChatSources.memories[] gained id/project/status (depends on
// Step 5's backend fix — the SSE wire didn't carry id before that). This is
// the "runtime-shape assertion" the plan calls for: a fixture SSE payload
// carrying all three parses into the typed ChatSources with no cast
// anywhere in this file.
describe("useChatStream: the sources event's id/project/status reach state.sources untouched", () => {
  it("uses shared session handling on unauthorized responses", async () => {
    const logout = vi.spyOn(useAuthStore.getState(), "logout")
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401, text: async () => "Unauthorized" }))
    const { result } = renderHook(() => useChatStream(), { wrapper })
    await act(async () => { await result.current.sendMessage(null, "draft") })
    expect(logout).toHaveBeenCalled()
    logout.mockRestore()
  })
  it("ignores a late response from an aborted older send", async () => {
    let resolveFirst!: (value: unknown) => void
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve }))
      .mockResolvedValueOnce({ ok: true, body: sseStreamFromEvents([
        { type: "token", content: "new answer" }, { type: "done", conversation_id: "second" },
      ]) }))
    const { result } = renderHook(() => useChatStream(), { wrapper })
    let first!: ReturnType<typeof result.current.sendMessage>
    act(() => { first = result.current.sendMessage("first", "old") })
    await act(async () => { await result.current.sendMessage("second", "new") })
    await act(async () => {
      resolveFirst({ ok: true, body: sseStreamFromEvents([{ type: "token", content: "old answer" }, { type: "done", conversation_id: "first" }]) })
      await first
    })
    expect(result.current.streamingContent).toBe("new answer")
    expect(result.current.conversationId).toBe("second")
  })

  it("refreshes an existing thread on SSE failure without making its stored user turn retryable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body: sseStreamFromEvents([{ type: "error", message: "provider failed" }]) }))
    const queryClient = new QueryClient()
    const invalidate = vi.spyOn(queryClient, "invalidateQueries")
    const { result } = renderHook(() => useChatStream("existing"), { wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider> })
    await act(async () => { await result.current.sendMessage("existing", "stored user turn") })
    expect(result.current.error).toContain("may already be saved")
    expect(result.current.retryDraft).toBeNull()
    expect(result.current.uncertainDraft).toBe("stored user turn")
    expect(result.current.pendingUserMessage).toBeNull()
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["conversation", "existing"] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["conversations"] })
  })

  it("reports EOF without done as an uncertain failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body: sseStreamFromEvents([{ type: "token", content: "partial" }]) }))
    const { result } = renderHook(() => useChatStream(), { wrapper })
    await act(async () => { await result.current.sendMessage(null, "draft") })
    expect(result.current.error).toContain("before completion")
    expect(result.current.uncertainDraft).toBe("draft")
  })

  it("aborts the request when the owner unmounts", async () => {
    const fetchMock = vi.fn().mockImplementation(() => new Promise(() => {}))
    vi.stubGlobal("fetch", fetchMock)
    const { result, unmount } = renderHook(() => useChatStream(), { wrapper })
    act(() => { void result.current.sendMessage(null, "draft") })
    const signal = fetchMock.mock.calls[0]![1].signal as AbortSignal
    unmount()
    expect(signal.aborted).toBe(true)
  })
  it("carries id, project, and status through from the SSE payload", async () => {
    const seededMemory = {
      index: 1,
      id: "11111111-1111-1111-1111-111111111111",
      content: "hello",
      source: "api",
      tags: [],
      score: 0.9,
      project: "default",
      status: "superseded" as const,
    }
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: sseStreamFromEvents([
          { type: "sources", memories: [seededMemory], entities: [] },
          { type: "done", message_id: "m1", conversation_id: "c1" },
        ]),
      }),
    )

    const { result } = renderHook(() => useChatStream(), { wrapper })

    await act(async () => {
      await result.current.sendMessage(null, "hi")
    })

    await waitFor(() => expect(result.current.sources).not.toBeNull())
    const mem = result.current.sources!.memories[0]!
    expect(mem.id).toBe(seededMemory.id)
    expect(mem.project).toBe("default")
    expect(mem.status).toBe("superseded")
  })
})
