import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { JobsListLayout } from "../components/jobs-list-layout"

// Frozen at DEMO: true — matches settings-tabs.test.tsx's rationale (pins
// the fixture-backed render rather than the real default, T1.58).
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  useDemoStore.getState().resetActivity()
})

describe("JobsListLayout (demo)", () => {
  it("renders every registered job with a trigger control", () => {
    render(<JobsListLayout />, { wrapper })
    const jobs = useDemoStore.getState().jobs
    expect(jobs.length).toBeGreaterThan(0)
    const idle = jobs.filter((j) => !j.running).length
    const running = jobs.filter((j) => j.running).length
    expect(
      screen.getAllByRole("button", { name: /Trigger now/ }).length,
    ).toBe(idle)
    expect(
      screen.getAllByRole("button", { name: /Running…/ }).length,
    ).toBe(running)
  })

  it("triggering an idle job marks it ok, never shows a busy banner", () => {
    render(<JobsListLayout />, { wrapper })
    const job = useDemoStore.getState().jobs.find((j) => !j.running)
    if (!job) throw new Error("expected at least one idle demo job")
    const card = screen.getByText(job.key).closest("div.rounded-lg") as HTMLElement
    fireEvent.click(within(card).getByRole("button", { name: /Trigger now/ }))
    expect(screen.queryByText(/is already running/)).not.toBeInTheDocument()
    expect(
      useDemoStore.getState().jobs.find((j) => j.key === job.key)?.last_status,
    ).toBe("ok")
  })

  it("saving the enabled switch writes through to the demo store", () => {
    render(<JobsListLayout />, { wrapper })
    const [job] = useDemoStore.getState().jobs
    if (!job) throw new Error("expected at least one demo job")
    const toggle = screen.getByLabelText(`${job.key} enabled`)
    fireEvent.click(toggle)
    expect(
      useDemoStore.getState().jobs.find((j) => j.key === job.key)?.enabled,
    ).toBe(!job.enabled)
  })
})
