import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

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
import { useJobBoard } from "../use-job-board"

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

describe("useJobBoard (DEMO off — real /jobs)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("lists the registered jobs without fabricating next_run_label or max_run_seconds", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ jobs: [JOB] })
    const { result } = renderHook(() => useJobBoard(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    const [job] = result.current.jobs
    expect(job!.key).toBe("graph_orphan_cleanup")
    expect(job!.max_run_seconds).toBeNull()
    expect(job!.next_run_label).toBeNull()
  })

  it("ruling 4: a 409 from the trigger endpoint resolves as busy, never throws to the caller", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return Promise.reject(new ApiError("Job is already running", 409))
      }
      return Promise.resolve({ jobs: [JOB] })
    })
    const { result } = renderHook(() => useJobBoard(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const outcome = await result.current.trigger(JOB.key)
    expect(outcome).toEqual({ ok: false, status: 409, lock_held_since: null })
  })

  it("a non-409 trigger failure still propagates — busy is not a catch-all", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return Promise.reject(new ApiError("boom", 500))
      }
      return Promise.resolve({ jobs: [JOB] })
    })
    const { result } = renderHook(() => useJobBoard(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await expect(result.current.trigger(JOB.key)).rejects.toThrow("boom")
  })

  it("a successful trigger resolves ok:true", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return Promise.resolve({ key: JOB.key, last_status: "ok", last_error: null, last_run_at: null })
      }
      return Promise.resolve({ jobs: [JOB] })
    })
    const { result } = renderHook(() => useJobBoard(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const outcome = await result.current.trigger(JOB.key)
    expect(outcome).toEqual({ ok: true })
  })
})
