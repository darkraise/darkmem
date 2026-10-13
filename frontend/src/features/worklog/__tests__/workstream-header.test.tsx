import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { apiFetch } from "@/lib/api"
import type { Workstream } from "@/hooks/api"
import { WorkstreamHeader } from "../components/workstream-header"

const WORKSTREAM: Workstream = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-forge",
  state: "open",
  closed_at: null,
  retain: false,
  properties: {
    plan_uri: "superpowers/plans/plan-a.md",
    spec_uri: "superpowers/specs/spec-a.md",
  },
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockResolvedValue({})
})

describe("WorkstreamHeader", () => {
  it("links the documents the workstream names, and only those", async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<WorkstreamHeader workstream={WORKSTREAM} onOpenDocument={onOpen} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Plan" }))
    expect(onOpen).toHaveBeenCalledWith("superpowers/plans/plan-a.md")
    expect(screen.getByRole("button", { name: "Spec" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Handoff" })).toBeNull()
  })

  it("closes an open workstream and reopens a closed one", async () => {
    const user = userEvent.setup()
    const { rerender } = render(<WorkstreamHeader workstream={WORKSTREAM} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Close" }))
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "closed" }),
    })

    rerender(
      <WorkstreamHeader
        workstream={{ ...WORKSTREAM, state: "closed", closed_at: "2026-09-28T11:00:00Z" }}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Reopen" }))
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "open" }),
    })
  })

  it("purges only after the confirmation", async () => {
    const user = userEvent.setup()
    render(<WorkstreamHeader workstream={WORKSTREAM} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Purge workstream" }))
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    await user.click(await screen.findByRole("button", { name: "Purge" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/worklog/workstreams/w1", {
        method: "DELETE",
      }),
    )
  })
})
