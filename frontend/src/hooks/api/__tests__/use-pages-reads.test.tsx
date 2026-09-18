import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { pageQuery, usePage, usePages, usePagesTrash } from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PAGE_WIRE = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Notes",
  content_hash: "h1",
  properties: null,
  content: null,
  blocks: [
    {
      id: "b1",
      parent_id: null,
      order_index: 0,
      type: "heading",
      text: "Sub",
      properties: { level: 2 },
      char_start: 0,
      char_end: 6,
      source: "## Sub",
    },
    {
      id: "b2",
      parent_id: null,
      order_index: 1,
      type: "paragraph",
      text: null,
      properties: null,
      char_start: null,
      char_end: null,
      source: null,
    },
  ],
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("usePages", () => {
  it("reads the project's flat list and keys on the project", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    const { result } = renderHook(() => usePages("my project"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages?project=my%20project")
  })
})

describe("usePage", () => {
  it("normalises wire blocks into the editor's BlockRow shape", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PAGE_WIRE)
    const { result } = renderHook(() => usePage("p1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1")
    expect(result.current.data).toEqual({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: "Notes",
      content_hash: "h1",
      blocks: [
        {
          block_id: "b1",
          type: "heading",
          text: "Sub",
          order_index: 0,
          char_span: [0, 6],
          parent_id: null,
          properties: { level: 2 },
          source: "## Sub",
        },
        {
          block_id: "b2",
          type: "paragraph",
          text: "",
          order_index: 1,
          char_span: null,
          parent_id: null,
          properties: null,
          source: null,
        },
      ],
    })
  })

  it("is idle with no page selected", () => {
    const { result } = renderHook(() => usePage(null), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("shares pageQuery's key so a hash re-read hits the rendered entry", () => {
    expect(pageQuery("p1").queryKey).toEqual(["page", "p1"])
  })
})

describe("usePagesTrash", () => {
  it("does not read while the sheet is closed", () => {
    const { result } = renderHook(() => usePagesTrash("personal", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("reads the trash roots when the sheet opens", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    const { result } = renderHook(() => usePagesTrash("personal", true), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/trash?project=personal")
  })
})
