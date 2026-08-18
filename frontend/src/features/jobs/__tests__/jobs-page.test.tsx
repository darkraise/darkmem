import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { JobsPage } from "../components/jobs-page"

// Frozen at DEMO: true — matches settings-tabs.test.tsx's rationale (pins
// the fixture-backed render rather than the real default, T1.58).
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  useDemoStore.getState().resetActivity()
  vi.clearAllMocks()
})

describe("JobsPage (demo)", () => {
  it("gives every registered job a trigger control", () => {
    render(<JobsPage />, { wrapper })
    const jobs = useDemoStore.getState().jobs
    expect(jobs.length).toBeGreaterThan(0)

    const idle = jobs.filter((j) => !j.running).length
    const running = jobs.filter((j) => j.running).length
    expect(screen.getAllByRole("button", { name: "Trigger now" })).toHaveLength(idle)
    // A held lock is stated on the control itself rather than after the click.
    expect(
      screen.getAllByRole("button", { name: /Running — trigger unavailable/ }),
    ).toHaveLength(running)
  })

  it("triggering an idle job marks it ok and reports no busy lock", () => {
    render(<JobsPage />, { wrapper })
    const job = useDemoStore.getState().jobs.find((j) => !j.running)
    if (!job) throw new Error("expected at least one idle demo job")

    const row = screen.getByText(job.key).closest("div.rounded-md") as HTMLElement
    fireEvent.click(within(row).getByRole("button", { name: "Trigger now" }))

    expect(screen.queryByText(/is already running/)).not.toBeInTheDocument()
    expect(
      useDemoStore.getState().jobs.find((j) => j.key === job.key)?.last_status,
    ).toBe("ok")
  })

  it("writes the enabled switch through to the store", () => {
    render(<JobsPage />, { wrapper })
    const [job] = useDemoStore.getState().jobs
    if (!job) throw new Error("expected at least one demo job")

    fireEvent.click(screen.getByLabelText(`${job.key} enabled`))
    expect(
      useDemoStore.getState().jobs.find((j) => j.key === job.key)?.enabled,
    ).toBe(!job.enabled)
  })

  it("renders one row per job in list and one card per job in grid", () => {
    render(<JobsPage />, { wrapper })
    const count = useDemoStore.getState().jobs.length

    expect(screen.getAllByRole("button", { name: "Configure" })).toHaveLength(count)
    fireEvent.click(screen.getByRole("radio", { name: "Grid layout" }))
    expect(screen.getAllByRole("button", { name: "Configure" })).toHaveLength(count)
  })

  it("opens run history for one job from its own row", () => {
    render(<JobsPage />, { wrapper })
    const job = useDemoStore.getState().jobs[0]!
    const row = screen.getByText(job.key).closest("div.rounded-md") as HTMLElement

    fireEvent.click(within(row).getByRole("button", { name: "Run history" }))
    expect(screen.getByRole("dialog")).toHaveTextContent("run history")
  })
})
