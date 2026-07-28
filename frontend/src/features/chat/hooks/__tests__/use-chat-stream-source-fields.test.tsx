import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useChatStream } from "../use-chat-stream"

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
