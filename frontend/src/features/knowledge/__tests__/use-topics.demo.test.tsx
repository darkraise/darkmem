import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// The other producer. `use-topics.ts` exists so the demo fixture and the live
// doors feed one row shape and the surface has a single render path; a demo
// path that drifts is how a demo-only field becomes load-bearing.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useTopics } from "../use-topics"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useTopics (DEMO on — the fixture producer)", () => {
  it("serves the fixture without touching the network", () => {
    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })

    expect(apiFetch).not.toHaveBeenCalled()
    expect(result.current.topics.length).toBeGreaterThan(0)
    expect(result.current.loading).toBe(false)
  })

  it("produces the same row shape the live door produces", () => {
    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })

    for (const topic of result.current.topics) {
      expect(typeof topic.label).toBe("string")
      expect(typeof topic.memberCount).toBe("number")
      expect(Array.isArray(topic.dominantEntities)).toBe(true)
      expect(["ready", "pending"]).toContain(topic.reportStatus)
    }
    for (const suggestion of result.current.suggestions) {
      expect(typeof suggestion.subjectKey).toBe("string")
      expect(typeof suggestion.subject).toBe("string")
    }
  })

  it("has no cross-run diff, because the fixture is a single run", () => {
    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })

    // Stated rather than faked: the demo store holds one snapshot, so there
    // is no prior to diff against and the tab shows no status chips in demo
    // mode. Inventing them would make the fixture claim a history it has not
    // got — the failure the T2.39/T2.39a split existed to prevent.
    expect(result.current.diff).toEqual([])
  })
})
