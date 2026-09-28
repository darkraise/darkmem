import { describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { DEMO_WORKSTREAMS } from "@/demo/worklog"
import {
  useWorklogEntries,
  useWorklogResume,
  useWorklogSearch,
  useWorkstreamUpdate,
  useWorkstreams,
} from "../use-worklog-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("the work log in demo mode", () => {
  it("serves fixtures and makes no request", async () => {
    const open = renderHook(() => useWorkstreams("darkmem", "open"), { wrapper })
    const openItems = open.result.current.data?.pages[0]?.items ?? []
    expect(openItems.length).toBeGreaterThan(0)
    expect(openItems.every((w) => w.state === "open")).toBe(true)

    const id = openItems[0]!.id
    const entries = renderHook(() => useWorklogEntries(id, null, true), { wrapper })
    expect(entries.result.current.data?.pages[0]?.items.length).toBeGreaterThan(0)

    const resume = renderHook(() => useWorklogResume("darkmem", openItems[0]!.key), { wrapper })
    expect(resume.result.current.data?.checkpoint?.kind).toBe("checkpoint")

    const search = renderHook(() => useWorklogSearch(), { wrapper })
    const answer = await search.result.current.mutateAsync({ project: "darkmem", query: "retention" })
    expect(answer.semantic_ran).toBe(false)
    expect(answer.items.length).toBeGreaterThan(0)

    expect(open.result.current.fetchStatus).toBe("idle")
    expect(entries.result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("refuses a write without calling the API", async () => {
    const update = renderHook(() => useWorkstreamUpdate(), { wrapper })
    await expect(
      update.result.current.mutateAsync({ id: DEMO_WORKSTREAMS[0]!.id, state: "closed" }),
    ).rejects.toThrow(/read-only/)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})
