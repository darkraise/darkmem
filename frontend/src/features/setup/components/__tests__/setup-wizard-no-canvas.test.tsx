import { render } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))
// SetupWizard calls useNavigate() at render; stub it so the test needs no
// RouterProvider (and no console warning).
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SetupWizard } from "../SetupWizard"

describe("SetupWizard", () => {
  it("does not render its own particle canvas (backdrop is the guest shell's)", () => {
    const qc = new QueryClient()
    const { container } = render(
      <QueryClientProvider client={qc}>
        <SetupWizard />
      </QueryClientProvider>,
    )
    expect(container.querySelectorAll("canvas")).toHaveLength(0)
  })
})
