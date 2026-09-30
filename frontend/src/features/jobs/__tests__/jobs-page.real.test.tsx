import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), ApiError }
})

import { apiFetch, ApiError } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
import { JobsPage } from "../components/jobs-page"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const JOB = {
  key: "graph_orphan_cleanup",
  display_name: "Graph orphan cleanup",
  description: "sweeps orphaned entities",
  enabled: true,
  cron: "0 * * * *",
  min_interval_seconds: 60,
  default_cron: "0 * * * *",
  last_run_at: "2026-07-27T10:00:00Z",
  last_status: "ok" as const,
  last_error: null,
  running: false,
  config: {},
  config_schema: [],
}

const listOnly = () =>
  vi.mocked(apiFetch).mockImplementation((path: string) =>
    path === "/jobs"
      ? Promise.resolve({ jobs: [JOB] })
      : Promise.reject(new Error(`unexpected apiFetch(${path})`)),
  )

async function renderRows() {
  render(<JobsPage />, { wrapper })
  await waitFor(() => expect(screen.getByText(JOB.key)).toBeInTheDocument())
}

describe("JobsPage — ruling 1: a held lock reports as busy, never as queued", () => {
  afterEach(() => vi.clearAllMocks())

  it("never fabricates max_run_seconds, which JobItem does not carry", async () => {
    listOnly()
    await renderRows()
    expect(screen.queryByText(/max_run_seconds/)).not.toBeInTheDocument()
  })

  it("reports a 409 trigger as busy rather than as a failure", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}/trigger` && init?.method === "POST")
        return Promise.reject(new ApiError(`Job '${JOB.key}' is already running`, 409))
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    await renderRows()

    fireEvent.click(screen.getByRole("button", { name: "Trigger now" }))

    await waitFor(() =>
      expect(toast.warning).toHaveBeenCalledWith(
        `${JOB.display_name} — busy`,
        expect.objectContaining({
          description: expect.stringContaining("try again when it finishes"),
        }),
      ),
    )
    // The busy path must never read as a request failure.
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("mutation proof: a non-409 error is not swallowed as busy", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}/trigger` && init?.method === "POST")
        return Promise.reject(new ApiError("Unknown job", 404))
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    await renderRows()

    fireEvent.click(screen.getByRole("button", { name: "Trigger now" }))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    // A genuine failure rendering as busy is the "silently appears to queue"
    // outcome ruling 1 forbids.
    expect(toast.warning).not.toHaveBeenCalled()
  })

  it("saves cron through the configure dialog, PUT /jobs/{key}", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}` && init?.method === "PUT")
        return Promise.resolve({ ...JOB, cron: "*/10 * * * *" })
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    await renderRows()

    fireEvent.click(screen.getByRole("button", { name: "Configure" }))
    const cron = await screen.findByLabelText(`${JOB.key} cron`)
    fireEvent.change(cron, { target: { value: "*/10 * * * *" } })
    fireEvent.click(screen.getByRole("button", { name: "Save schedule" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        `/jobs/${JOB.key}`,
        expect.objectContaining({ method: "PUT" }),
      ),
    )
  })
})

describe("JobsPage layouts", () => {
  afterEach(() => vi.clearAllMocks())

  it("offers both layouts as icon-only segments and starts on grid", async () => {
    listOnly()
    await renderRows()
    expect(screen.getByRole("radio", { name: "Grid layout" })).toBeChecked()
    expect(screen.getByRole("radio", { name: "List layout" })).not.toBeChecked()
  })

  it("keeps the same verbs after switching layout", async () => {
    listOnly()
    await renderRows()
    fireEvent.click(screen.getByRole("radio", { name: "List layout" }))

    // Same three actions, because both layouts render one JobActions.
    for (const label of ["Trigger now", "Configure", "Run history"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument()
    }
  })

  it("disables Trigger while a run holds the lock", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path === "/jobs"
        ? Promise.resolve({ jobs: [{ ...JOB, running: true }] })
        : Promise.reject(new Error("unexpected")),
    )
    await renderRows()
    expect(
      screen.getByRole("button", { name: /Running — trigger unavailable/ }),
    ).toBeDisabled()
  })
})


describe("the running signal", () => {
  afterEach(() => vi.clearAllMocks())

  // `POST .../trigger` awaits the run, so the job is running for exactly as
  // long as the request is open. Waiting for the response to refetch showed
  // the state only after it was over, and the 5s poll misses a ~0.1s run
  // entirely — the row went idle to done with nothing between.
  it("marks the job running while the trigger request is in flight", async () => {
    let release: (v: unknown) => void = () => {}
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}/trigger` && init?.method === "POST")
        return new Promise((resolve) => { release = resolve })
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    await renderRows()

    fireEvent.click(screen.getByRole("button", { name: "Trigger now" }))

    // Mid-flight: the control states the lock is held rather than inviting a
    // second press that the backend would refuse with a 409.
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Running — trigger unavailable/ }),
      ).toBeDisabled(),
    )

    release({ key: JOB.key, last_status: "ok", last_error: null, last_run_at: null })
  })
})
