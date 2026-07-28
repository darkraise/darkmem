import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
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
import { JobsSettingsTab } from "../components/jobs-settings-tab"

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

function mockJobsList() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

describe("JobsSettingsTab (real) — ruling 1: a held lock renders as busy, never queued", () => {
  afterEach(() => vi.clearAllMocks())

  it("renders max_run_seconds as skipped, not fabricated (JobItem carries no such field)", async () => {
    mockJobsList()
    render(<JobsSettingsTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(JOB.key)).toBeInTheDocument(),
    )
    expect(
      screen.queryByText("max_run_seconds (ceiling)"),
    ).not.toBeInTheDocument()
  })

  it("a 409 trigger response renders the busy banner, not a silent queue", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}/trigger` && init?.method === "POST") {
        return Promise.reject(new ApiError(`Job '${JOB.key}' is already running`, 409))
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<JobsSettingsTab />, { wrapper })
    await waitFor(() => expect(screen.getByText(JOB.key)).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: /Trigger now/ }))

    await waitFor(() =>
      expect(
        screen.getByText(`busy — ${JOB.key} is already running`),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText(/HTTP 409/)).toBeInTheDocument()
    // The busy path must never read as a request failure or a silent queue.
    expect(screen.queryByText(/Trigger failed/)).not.toBeInTheDocument()
  })

  it("mutation proof: a non-409 error is not swallowed as busy", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}/trigger` && init?.method === "POST") {
        return Promise.reject(new ApiError("Unknown job", 404))
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<JobsSettingsTab />, { wrapper })
    await waitFor(() => expect(screen.getByText(JOB.key)).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: /Trigger now/ }))

    // A genuine failure must never render as the busy banner — that would
    // be the "silently appears to queue" failure ruling 1 forbids.
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(
      `/jobs/${JOB.key}/trigger`,
      expect.objectContaining({ method: "POST" }),
    ))
    expect(
      screen.queryByText(`busy — ${JOB.key} is already running`),
    ).not.toBeInTheDocument()
  })

  it("saving cron PUTs /jobs/{key}", async () => {
    mockJobsList()
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/jobs") return Promise.resolve({ jobs: [JOB] })
      if (path === `/jobs/${JOB.key}` && init?.method === "PUT") {
        return Promise.resolve({ ...JOB, cron: "*/10 * * * *" })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<JobsSettingsTab />, { wrapper })
    await waitFor(() => expect(screen.getByText(JOB.key)).toBeInTheDocument())

    const cronInput = screen.getByLabelText(`${JOB.key} cron`)
    fireEvent.change(cronInput, { target: { value: "*/10 * * * *" } })
    fireEvent.click(screen.getByRole("button", { name: "Save schedule" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        `/jobs/${JOB.key}`,
        expect.objectContaining({ method: "PUT" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(
        ([path, init]) =>
          path === `/jobs/${JOB.key}` &&
          (init as RequestInit | undefined)?.method === "PUT",
      )
    expect(JSON.parse((call![1] as RequestInit).body as string)).toEqual({
      cron: "*/10 * * * *",
    })
  })
})
