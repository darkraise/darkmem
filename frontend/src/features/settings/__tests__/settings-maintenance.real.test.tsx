import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
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
import { MaintenanceTab } from "../components/maintenance-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const OBSOLETE_COUNTS = {
  memories: 12,
  entities: 3,
  code_chunks: 40,
  current_fingerprint: "qwen3-embedding:0.6b|1024",
}
const FAILURE_COUNTS = { memory_ingest: 2, code_index: 1 }

function mockHappy() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/reembed/obsolete-counts") return Promise.resolve(OBSOLETE_COUNTS)
    if (path === "/pipeline-failures/counts") return Promise.resolve(FAILURE_COUNTS)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

describe("MaintenanceTab (real)", () => {
  afterEach(() => vi.clearAllMocks())

  it("renders the reembed counts and fingerprint from GET /reembed/obsolete-counts", async () => {
    mockHappy()
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(`fp: ${OBSOLETE_COUNTS.current_fingerprint}`)).toBeInTheDocument(),
    )
    expect(screen.getByText("12 missing a vector")).toBeInTheDocument()
    expect(screen.getByText("3 missing")).toBeInTheDocument()
  })

  it("code_chunks re-embed stays disabled in real mode — ReembedService.reembed_code_chunks is a stub that never embeds anything", async () => {
    mockHappy()
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("40 missing")).toBeInTheDocument())
    expect(
      screen.getByRole("button", { name: "Re-embed code chunks" }),
    ).toBeDisabled()
    expect(screen.getByText("use Repositories → Reindex")).toBeInTheDocument()
  })

  it("triggering re-embed memories POSTs /reembed/memories after confirm", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/reembed/obsolete-counts") return Promise.resolve(OBSOLETE_COUNTS)
      if (path === "/pipeline-failures/counts") return Promise.resolve(FAILURE_COUNTS)
      if (path === "/reembed/memories" && init?.method === "POST") {
        return Promise.resolve({ accepted: true })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("12 missing a vector")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: /Re-embed memories/ }))
    fireEvent.click(screen.getByRole("button", { name: "Confirm — start re-embed" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/reembed/memories",
        expect.objectContaining({ method: "POST" }),
      ),
    )
    await waitFor(() =>
      expect(screen.getByText(/re-embed memories started/)).toBeInTheDocument(),
    )
  })

  it("expired_memory_cleanup has no live count — renders the honest gap, never a fabricated N, and stays enabled", async () => {
    mockHappy()
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("count not exposed via the API")).toBeInTheDocument())
    expect(
      screen.getByRole("button", { name: /Run sweep now/ }),
    ).not.toBeDisabled()
  })

  it("triggering expired_memory_cleanup reuses POST /jobs/{key}/trigger, the same mechanism Jobs uses", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/reembed/obsolete-counts") return Promise.resolve(OBSOLETE_COUNTS)
      if (path === "/pipeline-failures/counts") return Promise.resolve(FAILURE_COUNTS)
      if (path === "/jobs/expired_memory_cleanup/trigger" && init?.method === "POST") {
        return Promise.resolve({ key: "expired_memory_cleanup", last_status: "ok", last_error: null, last_run_at: null })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("count not exposed via the API")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: /Run sweep now/ }))
    fireEvent.click(screen.getByRole("button", { name: "Confirm — delete now" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/jobs/expired_memory_cleanup/trigger",
        expect.objectContaining({ method: "POST" }),
      ),
    )
  })

  it("mutation proof: a 409 on a cleanup trigger renders busy, not a fabricated success", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/reembed/obsolete-counts") return Promise.resolve(OBSOLETE_COUNTS)
      if (path === "/pipeline-failures/counts") return Promise.resolve(FAILURE_COUNTS)
      if (path === "/jobs/graph_orphan_cleanup/trigger" && init?.method === "POST") {
        return Promise.reject(new ApiError("Job 'graph_orphan_cleanup' is already running", 409))
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getAllByText("on schedule").length).toBeGreaterThan(0),
    )

    const [firstRunButton] = screen.getAllByRole("button", { name: "Run now" })
    if (!firstRunButton) throw new Error("expected at least one Run now button")
    fireEvent.click(firstRunButton)
    fireEvent.click(screen.getByRole("button", { name: "Confirm — run now" }))

    await waitFor(() =>
      expect(screen.getByText(/is already running — this trigger was not queued/)).toBeInTheDocument(),
    )
  })

  it("ruling 2: every trigger now journals to events, so the honest gap banner is gone", async () => {
    mockHappy()
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("count not exposed via the API")).toBeInTheDocument())
    expect(
      screen.queryByText(/None of these triggers are journaled to the events timeline today/),
    ).not.toBeInTheDocument()
  })

  it("failure counts come from GET /pipeline-failures/counts, keyed memory_ingest/code_index", async () => {
    mockHappy()
    render(<MaintenanceTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText("2 memory_ingest · 1 code_repo")).toBeInTheDocument(),
    )
  })
})
