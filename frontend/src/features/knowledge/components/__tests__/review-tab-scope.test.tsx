import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children }: { children?: ReactNode }) => <a>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { useProjectStore } from "@/stores/project-store"
import { ReviewTab } from "../review-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("ReviewTab scope", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch).mockRejectedValue(new Error("offline"))
  })

  it("sends the header switcher's project and offers no project field", async () => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
    render(<ReviewTab />, { wrapper })
    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some((call) =>
          String(call[0]).includes("project=darkmem"),
        ),
      ).toBe(true),
    )
    expect(screen.queryByRole("textbox", { name: "Project filter" })).toBeNull()
  })
})
