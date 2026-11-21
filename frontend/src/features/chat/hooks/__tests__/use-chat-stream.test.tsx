import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useChatStream } from "../use-chat-stream"

interface OpenStream {
  signal: AbortSignal
  emit: (event: object) => Promise<void>
  finish: (event: object) => Promise<void>
}

/** Each fetch answers a stream the test drives, recorded under the
 *  conversation the request named. */
function streamsByConversation() {
  const open = new Map<string, OpenStream>()
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init: RequestInit) => {
      const name = JSON.parse(String(init.body)).conversation_id as string
      let controller!: ReadableStreamDefaultController<Uint8Array>
      const body = new ReadableStream<Uint8Array>({
        start(c) {
          controller = c
        },
      })
      const encode = (event: object) =>
        new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)
      open.set(name, {
        signal: init.signal!,
        emit: async (event) => {
          await act(async () => {
            controller.enqueue(encode(event))
            await new Promise((r) => setTimeout(r, 0))
          })
        },
        finish: async (event) => {
          await act(async () => {
            controller.enqueue(encode(event))
            controller.close()
            await new Promise((r) => setTimeout(r, 0))
          })
        },
      })
      return Promise.resolve({ ok: true, body })
    }),
  )
  return open
}

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(qc, "invalidateQueries")
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  const hook = renderHook(({ active }: { active: string }) => useChatStream(active), {
    wrapper,
    initialProps: { active: "A" },
  })
  return { hook, invalidate }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("useChatStream: one stream per conversation", () => {
  it("a send in a second conversation leaves the first stream running", async () => {
    const open = streamsByConversation()
    const { hook, invalidate } = setup()

    let sentA!: Promise<string | null | undefined>
    act(() => {
      sentA = hook.result.current.sendMessage("A", "question for A")
    })
    await open.get("A")!.emit({ type: "token", content: "A is " })

    hook.rerender({ active: "B" })
    act(() => {
      void hook.result.current.sendMessage("B", "question for B")
    })
    await open.get("B")!.emit({ type: "token", content: "B answer" })
    expect(open.get("A")!.signal.aborted).toBe(false)

    await open.get("A")!.emit({ type: "token", content: "answered" })
    await open.get("A")!.finish({ type: "done", conversation_id: "A" })
    await act(async () => {
      await sentA
    })

    hook.rerender({ active: "A" })
    expect(hook.result.current.error).toBeNull()
    expect(hook.result.current.isStreaming).toBe(false)
    expect(hook.result.current.streamingContent).toBe("A is answered")
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["conversation", "A"] })
  })

  it("each conversation has its own stream state", async () => {
    const open = streamsByConversation()
    const { hook } = setup()

    act(() => {
      void hook.result.current.sendMessage("A", "question for A")
    })
    await open.get("A")!.emit({ type: "token", content: "partial A" })
    hook.rerender({ active: "B" })
    act(() => {
      void hook.result.current.sendMessage("B", "question for B")
    })
    await open.get("B")!.emit({ type: "token", content: "partial B" })

    expect(hook.result.current.streamingContent).toBe("partial B")
    expect(hook.result.current.pendingUserMessage).toBe("question for B")
    hook.rerender({ active: "A" })
    expect(hook.result.current.streamingContent).toBe("partial A")
    expect(hook.result.current.isStreaming).toBe(true)

    hook.rerender({ active: "B" })
    act(() => hook.result.current.abort())
    expect(open.get("B")!.signal.aborted).toBe(true)
    expect(hook.result.current.isStreaming).toBe(false)

    hook.rerender({ active: "A" })
    expect(open.get("A")!.signal.aborted).toBe(false)
    expect(hook.result.current.isStreaming).toBe(true)
    expect(hook.result.current.streamingContent).toBe("partial A")
  })

  it("a draft's turn shows under the conversation the server names", async () => {
    const open = streamsByConversation()
    const { hook } = setup()
    hook.rerender({ active: "draft:1" })
    act(() => {
      void hook.result.current.sendMessage(null, "first turn", undefined, "draft:1")
    })
    const stream = open.get(null as unknown as string)!
    await stream.emit({ type: "sources", memories: [], entities: [], conversation_id: "created" })
    await stream.emit({ type: "token", content: "still streaming" })

    hook.rerender({ active: "created" })
    expect(hook.result.current.isStreaming).toBe(true)
    expect(hook.result.current.streamingContent).toBe("still streaming")
  })
})
