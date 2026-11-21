import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("darkraise-ui/components/sonner", () => ({ toast: { error: vi.fn() } }))

// The spread keeps the module's other exports real. `isAttachmentUrl` lives
// here too and `inline-markdown` imports it, so a factory that returned only
// these three would make every standalone-link fixture in this file throw.
vi.mock("../lib/attachments", async (importOriginal) => {
  let inFlight = 0
  const listeners = new Set<() => void>()
  return {
    ...(await importOriginal<typeof import("../lib/attachments")>()),
    uploadsInFlight: () => inFlight,
    subscribeUploads: (listener: () => void) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    __setUploads: (n: number) => {
      inFlight = n
      for (const listener of listeners) listener()
    },
  }
})

vi.mock("../lib/block-mapping", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/block-mapping")>()
  return { ...actual, toSyncTree: vi.fn(actual.toSyncTree) }
})

import { toast } from "darkraise-ui/components/sonner"
import * as mapping from "../lib/block-mapping"
import * as attachments from "../lib/attachments"
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

const setUploads = (n: number) =>
  (attachments as unknown as { __setUploads: (n: number) => void }).__setUploads(n)

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
  it.each([409, 422])("retains a stopped %s draft across navigation until explicit discard", async (status) => {
    const { t, sent } = transport(status)
    const first = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => first.result.current.onDocumentChange([para("a", "retained draft")]))
    await act(async () => first.result.current.flushNow())
    expect(first.result.current.status.kind).toBe("stopped")
    first.unmount()
    await act(async () => vi.runAllTimersAsync())
    const leaving = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(leaving)
    expect(leaving.defaultPrevented).toBe(true)
    const reopened = renderHook(({ generation }) => usePageSync(PAGE, generation, () => t), {
      wrapper, initialProps: { generation: 0 },
    })
    expect(reopened.result.current.initialBlocks[0]!.content).toEqual([
      { type: "text", text: "retained draft", styles: {} },
    ])
    expect(reopened.result.current.status.kind).toBe("stopped")
    expect(sent).toHaveLength(1)
    act(() => reopened.result.current.discard())
    reopened.rerender({ generation: 1 })
    expect(reopened.result.current.initialBlocks[0]!.content).toEqual([
      { type: "text", text: "a", styles: {} },
    ])
    const discarded = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(discarded)
    expect(discarded.defaultPrevented).toBe(false)
  })

  it("protects an in-flight save after the notes route unmounts, until it settles", async () => {
    const { t } = transport(undefined, 50)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => view.result.current.onDocumentChange([para("a", "draft")]))
    view.unmount()
    const leaving = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(leaving)
    expect(leaving.defaultPrevented).toBe(true)
    await act(async () => vi.advanceTimersByTimeAsync(50))
    const saved = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(saved)
    expect(saved.defaultPrevented).toBe(false)
  })

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

  it("the editor document is converted once per change batch", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    vi.mocked(mapping.toSyncTree).mockClear()
    let text = "a"
    for (let i = 0; i < 10; i++) {
      text += "b"
      act(() => result.current.onDocumentChange([para("a", text)]))
    }
    await act(async () => vi.advanceTimersByTimeAsync(TEXT_IDLE_MS))
    expect(vi.mocked(mapping.toSyncTree)).toHaveBeenCalledTimes(1)
    expect(sent).toEqual([{ kind: "update", id: "a", type: "paragraph", text, properties: null }])
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
    const { t, sent } = transport()
    const view = renderHook(({ gen }) => usePageSync(PAGE, gen, () => t), { wrapper, initialProps: { gen: 0 } })
    act(() => view.result.current.onDocumentChange([para("a", "local")]))
    act(() => view.result.current.discard())
    view.rerender({ gen: 1 })
    expect(view.result.current.initialBlocks[0]!.content).toEqual([{ type: "text", text: "a", styles: {} }])
    expect(sent).toEqual([])
  })
})

describe("an upload in flight", () => {
  afterEach(() => setUploads(0))

  it("keeps unload protection after the last editor unmounts until the upload settles", async () => {
    const view = renderHook(() => usePageSync(PAGE, 0, () => transport().t), { wrapper })
    await act(async () => setUploads(1))
    view.unmount()
    const leaving = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(leaving)
    expect(leaving.defaultPrevented).toBe(true)
    await act(async () => setUploads(0))
    const settled = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(settled)
    expect(settled.defaultPrevented).toBe(false)
  })

  it("warns on unload even when the tree is settled", () => {
    renderHook(() => usePageSync(PAGE, 0, () => transport().t), { wrapper })

    const settled = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(settled)
    expect(settled.defaultPrevented).toBe(false)

    setUploads(1)
    const pending = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(pending)
    expect(pending.defaultPrevented).toBe(true)
  })

  it("shows the saving state while a file is going up", async () => {
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => transport().t), { wrapper })
    expect(result.current.status.kind).not.toBe("saving")
    await act(async () => setUploads(1))
    expect(result.current.status.kind).toBe("saving")
    await act(async () => setUploads(0))
    expect(result.current.status.kind).not.toBe("saving")
  })
})
