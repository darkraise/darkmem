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
import {
  usePageCreate,
  usePageMove,
  usePageRename,
} from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function lastBody() {
  const calls = vi.mocked(apiFetch).mock.calls
  const init = calls[calls.length - 1]![1] as RequestInit
  return JSON.parse(String(init.body))
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("page mutations", () => {
  it("creates a page at the named parent", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p2" })
    const { result } = renderHook(() => usePageCreate(), { wrapper })
    result.current.mutate({ project: "personal", parentId: "p1", title: "Child" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages")
    expect(lastBody()).toEqual({
      project: "personal",
      title: "Child",
      parent_id: "p1",
      after_id: null,
      content: null,
    })
  })

  // The route dispatches on field PRESENCE, so a rename carrying parent_id
  // would move the page to the root and a move carrying title would rename it.
  it("renames without naming parent_id", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageRename(), { wrapper })
    result.current.mutate({ pageId: "p1", title: "New" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages/p1")
    expect(lastBody()).toEqual({ title: "New" })
  })

  it("moves without naming title", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageMove(), { wrapper })
    result.current.mutate({ pageId: "p1", parentId: null, afterId: "p3" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(lastBody()).toEqual({ parent_id: null, after_id: "p3" })
  })
})
