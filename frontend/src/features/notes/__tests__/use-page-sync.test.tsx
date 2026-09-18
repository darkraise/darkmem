import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("darkraise-ui/components/sonner", () => ({ toast: { error: vi.fn() } }))

import { toast } from "darkraise-ui/components/sonner"
import type { PageView } from "@/hooks/api"
import type { EditorBlockLike } from "../lib/block-mapping"
import { SyncTransportError, type PageTransport } from "../lib/page-sync"
import type { SyncOp } from "../lib/sync-tree"
import { resetPageSyncEngines, TEXT_IDLE_MS, usePageSync } from "../use-page-sync"

const PAGE: PageView = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Plans",
  content_hash: "h0",
  blocks: [
    { block_id: "a", type: "paragraph", text: "a", order_index: 0, char_span: null, parent_id: null, properties: null, source: "a" },
  ],
}

const para = (id: string, text: string): EditorBlockLike => ({
  id,
  type: "paragraph",
  props: {},
  content: [{ type: "text", text, styles: {} }],
  children: [],
})

function transport(fail?: number, latencyMs = 0) {
  const sent: SyncOp[] = []
  let n = 0
  const t: PageTransport = {
    read: async () => ({ tree: [], hash: "x" }),
    send: async (op) => {
      sent.push(op)
      if (latencyMs > 0) await new Promise((resolve) => setTimeout(resolve, latencyMs))
      if (fail !== undefined) throw new SyncTransportError(`status ${fail}`, fail)
      return `h${++n}`
    },
  }
  return { t, sent }
}

let qc: QueryClient
function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.useFakeTimers()
  qc = new QueryClient()
  vi.mocked(toast.error).mockReset()
})

afterEach(() => {
  resetPageSyncEngines()
  vi.useRealTimers()
})

describe("usePageSync", () => {
  it("mounts the page's blocks and sends typing after the idle pause", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(result.current.initialBlocks.map((b) => b.id)).toEqual(["a"])
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    await act(async () => vi.advanceTimersByTimeAsync(TEXT_IDLE_MS - 1))
    expect(sent).toEqual([])
    await act(async () => vi.advanceTimersByTimeAsync(1))
    expect(sent).toEqual([{ kind: "update", id: "a", type: "paragraph", text: "ab", properties: null }])
    expect(result.current.status).toEqual({ kind: "saved" })
  })

  it("sends a structural change at once", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    await act(async () => result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    expect(sent.map((op) => op.kind)).toEqual(["insert"])
  })

  it("flushes pending typing when the tab is hidden", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden")
    await act(async () => document.dispatchEvent(new Event("visibilitychange")))
    expect(sent).toHaveLength(1)
  })

  it("asks before leaving while work is unsent", () => {
    const { t } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    const quiet = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(quiet)
    expect(quiet.defaultPrevented).toBe(false)
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    const leaving = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(leaving)
    expect(leaving.defaultPrevented).toBe(true)
  })

  it("keeps draining after unmount and hands a remount the unsent work", async () => {
    const { t, sent } = transport()
    const first = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => first.result.current.onDocumentChange([para("a", "draft")]))
    first.unmount()
    const again = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(again.result.current.initialBlocks[0]!.content).toEqual([{ type: "text", text: "draft", styles: {} }])
    await act(async () => vi.runAllTimersAsync())
    expect(sent).toHaveLength(1)
  })

  it("forgets the page's cached read once its engine is released", async () => {
    const { t } = transport()
    // Never collected on its own, so only the release can remove it.
    qc = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } })
    qc.setQueryData(["page", "p1"], PAGE)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    await act(async () => view.result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    view.unmount()
    await act(async () => vi.runAllTimersAsync())
    expect(qc.getQueryData(["page", "p1"])).toBeUndefined()
  })

  it("releases an engine whose write was still in flight when its pane unmounted", async () => {
    const { t } = transport(undefined, 50)
    qc = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } })
    qc.setQueryData(["page", "p1"], PAGE)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => view.result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    view.unmount()
    expect(qc.getQueryData(["page", "p1"])).toBeDefined()
    await act(async () => vi.advanceTimersByTimeAsync(50))
    expect(qc.getQueryData(["page", "p1"])).toBeUndefined()
    const reopened = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(reopened.result.current.initialBlocks.map((b) => b.id)).toEqual(["a"])
  })

  it("sends pending typing at once when the editor loses focus", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    await act(async () => result.current.flushNow())
    expect(sent).toHaveLength(1)
  })

  it("raises a toast when a page nobody is looking at fails to save", async () => {
    const { t } = transport(422)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => view.result.current.onDocumentChange([para("a", "ab")]))
    view.unmount()
    await act(async () => vi.runAllTimersAsync())
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("“Plans” was not saved — status 422")
  })

  it("builds a fresh engine for a new generation after a discard", () => {
    const { t } = transport()
    const view = renderHook(({ gen }) => usePageSync(PAGE, gen, () => t), { wrapper, initialProps: { gen: 0 } })
    act(() => view.result.current.onDocumentChange([para("a", "local")]))
    act(() => view.result.current.discard())
    view.rerender({ gen: 1 })
    expect(view.result.current.initialBlocks[0]!.content).toEqual([{ type: "text", text: "a", styles: {} }])
  })
})
