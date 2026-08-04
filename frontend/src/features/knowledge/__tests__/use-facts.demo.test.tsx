import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// Two producers, one row shape — and one filter behaviour. A demo branch
// that ignores the query splits what a control means across modes: picking
// `status: disputed` with the fixture would silently do nothing while the
// same control is a server predicate on live data.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ALL_PROJECTS, ANY, useFactRows } from "../use-facts"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const QUERY = {
  project: ALL_PROJECTS,
  relation: ANY,
  status: ANY,
  subject: "",
}

function rowsFor(query: Partial<typeof QUERY>) {
  const { result } = renderHook(
    () => useFactRows({ ...QUERY, ...query }),
    { wrapper },
  )
  return result.current
}

describe("useFactRows (DEMO on — the curated fixture)", () => {
  it("never reaches the network", () => {
    rowsFor({})
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("honours the status filter", () => {
    const all = rowsFor({})
    const disputed = rowsFor({ status: "disputed" })
    expect(disputed.rows.length).toBeGreaterThan(0)
    expect(disputed.rows.length).toBeLessThan(all.rows.length)
    for (const row of disputed.rows) {
      expect(row.verification_status).toBe("disputed")
    }
  })

  it("honours the relation filter", () => {
    const all = rowsFor({})
    const rel = all.rows[0]!.rel_type
    const filtered = rowsFor({ relation: rel })
    expect(filtered.rows.length).toBeGreaterThan(0)
    for (const row of filtered.rows) expect(row.rel_type).toBe(rel)
  })

  it("honours the project scope, and the all-projects scope withholds nothing", () => {
    const all = rowsFor({})
    const project = all.rows[0]!.project
    const scoped = rowsFor({ project })
    for (const row of scoped.rows) expect(row.project).toBe(project)
    expect(rowsFor({ project: "no-such-project" }).rows).toHaveLength(0)
    expect(all.rows.length).toBeGreaterThanOrEqual(scoped.rows.length)
  })

  it("matches the free-text needle against subject and object alike", () => {
    const all = rowsFor({})
    const target = all.rows.find((r) => r.object_name.length > 4)!
    const needle = target.object_name.slice(0, 5)
    const matched = rowsFor({ subject: needle })
    expect(matched.rows.map((r) => r.id)).toContain(target.id)
  })

  it("carries the fixture's claim verbatim and its origin parts as values", () => {
    const row = rowsFor({}).rows.find((r) => r.origin_count !== null)!
    expect(row.claim.length).toBeGreaterThan(0)
    expect(row.origin_count).toBeGreaterThan(0)
    expect(row.origin_kinds.length).toBeGreaterThan(0)
  })

  it("reports the fixture as complete — nothing is paged and nothing is pending", () => {
    const result = rowsFor({})
    expect(result.loaded).toBe(result.total)
    expect(result.hasMore).toBe(false)
    expect(result.optionsComplete).toBe(true)
    expect(result.loading).toBe(false)
    expect(result.error).toBe(false)
  })
})
