import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useApiKeys,
  useAutoResearch,
  useClassificationAreas,
  useJobs,
  useResearchRuns,
} from "@/hooks/api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => vi.clearAllMocks())

// A demo read that reaches apiFetch 401s, and the 401 handler navigates the
// whole demo to /login — so "no request" is the only acceptable outcome.
describe("demo mode issues none of the Settings reads", () => {
  const hooks: Array<[string, () => unknown]> = [
    ["useClassificationAreas", () => useClassificationAreas()],
    ["useApiKeys", () => useApiKeys()],
    ["useJobs", () => useJobs()],
    ["useAutoResearch", () => useAutoResearch()],
    ["useResearchRuns", () => useResearchRuns()],
  ]

  for (const [name, hook] of hooks) {
    it(`${name} stays idle`, async () => {
      renderHook(hook, { wrapper })
      await act(async () => {})
      expect(apiFetch).not.toHaveBeenCalled()
    })
  }
})
