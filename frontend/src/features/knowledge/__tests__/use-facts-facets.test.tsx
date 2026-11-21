import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ALL_PROJECTS, ANY, useFactRows } from "../use-facts"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const row = {
  id: "f1",
  id_kind: "fact",
  subject_name: "darkmem",
  object_name: "postgres",
  rel_type: "USES",
  fact: "darkmem uses postgres",
  project: "darkmem",
  verification_status: "candidate",
  lifecycle: null,
  badge: null,
  confidence: 0.8,
  review_state: null,
  demotion_pending_since: null,
  belief_window: { valid_at: null, invalid_at: null, expired_at: null },
  applies_when: null,
  applies_when_labels: [],
  created_at: "2026-07-01T00:00:00Z",
}

describe("useFactRows filter options", () => {
  it("filter options come from the server facets", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [row],
      total: 60,
      limit: 50,
      offset: 0,
      facets: {
        project: ["darkmem", "other"],
        rel_type: ["DEPENDS_ON", "USES"],
        verification_status: ["candidate", "disputed"],
      },
    })
    const { result } = renderHook(
      () =>
        useFactRows({ project: ALL_PROJECTS, relation: ANY, status: ANY, subject: "" }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.loaded).toBe(1))
    expect(result.current.hasMore).toBe(true)
    expect(result.current.statuses).toEqual(["candidate", "disputed"])
    expect(result.current.relations).toEqual(["DEPENDS_ON", "USES"])
    expect(result.current.projects).toEqual(["darkmem", "other"])
    expect(result.current.optionsComplete).toBe(true)
  })
})
