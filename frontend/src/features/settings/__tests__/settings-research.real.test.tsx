import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ResearchTab } from "../components/research-tab"

/**
 * T3.28's config half.
 *
 * The surface's job is to make arming an explicit act and to show the
 * disarmed state as a *state* — a never-configured install refuses every run,
 * and that is the shipped default rather than a fault. A tab that rendered
 * "disarmed" as a warning would push an operator toward arming a loop they had
 * not decided to arm.
 *
 * The trigger half is a **re-derivation**, and these tests pin the distinction
 * that shape rests on: re-running must not gather, must not file, and must
 * refuse a run whose evidence is gone rather than render an empty success.
 */

const DISARMED = {
  enabled: false,
  max_findings_per_run: 20,
  max_content_chars: 8000,
  default_enabled: false,
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const RUNS = {
  items: [
    {
      event_id: 7,
      occurred_at: "2026-08-14T09:00:00Z",
      run_id: "r-1",
      subject: "pgvector HNSW",
      project: "default",
      filed: 7,
      live: 7,
    },
    {
      event_id: 4,
      occurred_at: "2026-08-12T09:00:00Z",
      run_id: "r-0",
      subject: "uv vs pip",
      project: "default",
      filed: 4,
      live: 0,
    },
  ],
  total: 2,
}

function mockApi(config: unknown = DISARMED, runs: unknown = RUNS) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/config/auto-research") return Promise.resolve(config)
    if (path === "/config/auto-research/runs") return Promise.resolve(runs)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

afterEach(() => vi.clearAllMocks())

describe("ResearchTab — the arm switch", () => {
  it("shows the disarmed default as a state, not an error", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })

    await waitFor(() => expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0))
    expect(screen.getByText(/refuses every run while disarmed/)).toBeInTheDocument()
    expect(screen.queryByText(/could not be read/)).not.toBeInTheDocument()
  })

  it("arming is an explicit act that sends a real boolean", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    // Wait for the *loaded* state, not just the button: the control is
    // deliberately disabled while the config is in flight, so clicking a
    // rendered-but-loading button silently does nothing.
    await waitFor(() => expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0))
    fireEvent.click(screen.getByRole("button", { name: /Arm the research loop/ }))

    await waitFor(() => {
      const put = vi.mocked(apiFetch).mock.calls.find(
        ([, options]) => (options as RequestInit | undefined)?.method === "PUT",
      )
      expect(put).toBeTruthy()
      expect(put?.[0]).toBe("/config/auto-research")
      // A real boolean, never a string: `bool("false")` is the coercion the
      // writer refuses, and the client must not be the one that introduces it.
      expect(JSON.parse((put?.[1] as RequestInit).body as string)).toEqual({
        enabled: true,
      })
    })
  })

  it("an armed loop offers disarming rather than a second arm control", async () => {
    mockApi({ ...DISARMED, enabled: true })
    render(<ResearchTab />, { wrapper })

    await waitFor(() => expect(screen.getAllByText("armed").length).toBeGreaterThan(0))
    expect(screen.getByRole("button", { name: /Disarm/ })).toBeInTheDocument()
  })

  it("a failed read says so rather than rendering as disarmed", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<ResearchTab />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText(/a failed read, not a disarmed loop/)).toBeInTheDocument(),
    )
    expect(screen.getByText("unreadable")).toBeInTheDocument()
  })
})

describe("ResearchTab — the budgets", () => {
  it("saves both budgets without touching the arm switch", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByLabelText("Max findings per run")).toHaveValue("20"),
    )

    fireEvent.change(screen.getByLabelText("Max findings per run"), {
      target: { value: "5" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Save budgets/ }))

    await waitFor(() => {
      const put = vi.mocked(apiFetch).mock.calls.find(
        ([, options]) => (options as RequestInit | undefined)?.method === "PUT",
      )
      expect(put).toBeTruthy()
      expect(JSON.parse((put?.[1] as RequestInit).body as string)).toEqual({
        max_findings_per_run: 5,
        max_content_chars: 8000,
      })
    })
  })

  it("a refused write says why and leaves the switch alone", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, options?: RequestInit) => {
      if (options?.method === "PUT") {
        return Promise.reject(new Error("auto_research.enabled must be a boolean"))
      }
      if (path === "/config/auto-research") return Promise.resolve(DISARMED)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0))
    fireEvent.click(screen.getByRole("button", { name: /Arm the research loop/ }))

    await waitFor(() =>
      expect(screen.getByText(/not saved/)).toBeInTheDocument(),
    )
    expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0)
  })
})

describe("ResearchTab — the trigger re-derives, it does not gather", () => {
  it("offers no control that would make the server gather", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0))

    for (const label of [/Run research/i, /Gather/i, /Search the web/i]) {
      expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument()
    }
  })

  it("says why the caller has to be the gatherer", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/evidence an MCP agent gathered/)).toBeInTheDocument(),
    )
  })

  it("re-derives a run against the timestamp the listing gave it", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("pgvector HNSW")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: "Re-derive" }))

    // The composite-key bound rides back verbatim: `events` is partitioned by
    // month, and a re-run that sent only the id would scan every child.
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/config/auto-research/runs/7/rerun", {
        method: "POST",
        body: JSON.stringify({ occurred_at: "2026-08-14T09:00:00Z" }),
      }),
    )
  })

  it("refuses a run whose evidence is gone instead of offering an empty re-run", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("uv vs pip")).toBeInTheDocument())

    const dead = screen.getByRole("button", { name: "Nothing to re-derive" })
    expect(dead).toBeDisabled()
  })

  it("reports what it could not reach beside what it did", async () => {
    mockApi()
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/config/auto-research") return Promise.resolve(DISARMED)
      if (path === "/config/auto-research/runs") return Promise.resolve(RUNS)
      if (path === "/config/auto-research/runs/7/rerun") {
        return Promise.resolve({
          event_id: 7, subject: "pgvector HNSW", project: "default",
          filed: 7, reprocessed: 5, missing: 2, pending: 0, errors: 0,
        })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("pgvector HNSW")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: "Re-derive" }))

    // A run that re-derived fewer rows than it filed must say so: silently
    // reporting 5 of 5 would describe a corpus that is not there.
    await waitFor(() =>
      expect(screen.getByText(/re-derived 5 of 7 filed/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/2 no longer exist/)).toBeInTheDocument()
  })

  it("distinguishes rows still in the capture buffer from rows that are gone", async () => {
    // "not yet materialised" and "deleted" are different facts, and only the
    // second is unrecoverable. A run whose captures are queued — or settled
    // into buffer error awaiting triage — must not be reported as lost.
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/config/auto-research") return Promise.resolve(DISARMED)
      if (path === "/config/auto-research/runs") return Promise.resolve(RUNS)
      if (path === "/config/auto-research/runs/7/rerun") {
        return Promise.resolve({
          event_id: 7, subject: "pgvector HNSW", project: "default",
          filed: 7, reprocessed: 4, missing: 3, pending: 2, errors: 0,
        })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("pgvector HNSW")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("button", { name: "Re-derive" }))

    await waitFor(() =>
      expect(screen.getByText(/1 no longer exist/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/2 still in the capture buffer/)).toBeInTheDocument()
  })

  it("an empty install says so rather than rendering an empty table", async () => {
    mockApi(DISARMED, { items: [], total: 0 })
    render(<ResearchTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/no research run has been filed/)).toBeInTheDocument(),
    )
  })
})
