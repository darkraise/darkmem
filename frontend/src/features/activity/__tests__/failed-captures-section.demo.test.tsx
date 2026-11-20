import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { TriageTab } from "../components/triage-tab"

describe("failed captures in demo mode", () => {
  it("the triage tab shows no failed captures in demo mode", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TriageTab />
      </QueryClientProvider>,
    )
    expect(screen.getByText("Failure triage")).toBeInTheDocument()
    expect(screen.queryByText("Failed captures")).not.toBeInTheDocument()
    const requested = [
      ...vi.mocked(apiFetch).mock.calls.map((c) => String(c[0])),
      ...fetchSpy.mock.calls.map((c) => String(c[0])),
    ]
    expect(requested.some((path) => path.includes("memory-buffer"))).toBe(false)
    fetchSpy.mockRestore()
  })
})
