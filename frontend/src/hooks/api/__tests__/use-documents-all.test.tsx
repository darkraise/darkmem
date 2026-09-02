import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// Review m1: the list route clamps at 200 and carries no total, so a single
// page silently drops over half a ~465-file corpus. These tests pin the two
// halves of the fix -- that the hook stitches, and that it says so when it
// gives up rather than returning a quietly short list.

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { useAllDocuments } from "../use-documents-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function page(n: number, offset: number) {
  return {
    items: Array.from({ length: n }, (_, i) => ({
      id: `doc-${offset + i}`,
      title: null,
      uri: `docs/f${offset + i}.md`,
      source_type: "md",
      project: "p",
      block_count: 1,
    })),
    horizon: true,
  }
}

beforeEach(() => vi.clearAllMocks())

describe("useAllDocuments", () => {
  it("stitches pages until a short one and reports no truncation", async () => {
    const pages = [page(200, 0), page(200, 200), page(37, 400)]
    let call = 0
    vi.mocked(apiFetch).mockImplementation(async () => pages[call++] as never)

    const { result } = renderHook(() => useAllDocuments("p"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data!.items).toHaveLength(437)
    expect(result.current.data!.truncated).toBe(false)
    expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(3)
  })

  it("dedupes by id, because a concurrent filing shifts later offsets", async () => {
    // Page 2 repeats one row page 1 already carried -- what a created_at DESC
    // insert between the two requests actually produces.
    const first = page(200, 0)
    const second = page(200, 199)
    let call = 0
    vi.mocked(apiFetch).mockImplementation(async () =>
      (call++ === 0 ? first : { ...second, items: second.items.slice(0, 50) }) as never,
    )

    const { result } = renderHook(() => useAllDocuments("p"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    const ids = result.current.data!.items.map((d) => d.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toHaveLength(249)
  })

  it("reports truncated when the page guard is exhausted", async () => {
    vi.mocked(apiFetch).mockImplementation(async () => page(200, 0) as never)

    const { result } = renderHook(() => useAllDocuments("p"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data!.truncated).toBe(true)
    expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(25)
  })
})
