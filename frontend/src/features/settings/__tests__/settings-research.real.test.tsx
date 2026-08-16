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
 * The trigger half is deliberately absent and its absence is asserted: a UI
 * button cannot gather evidence, and a button that made the server gather is
 * the shape doc 09 §6 refuses.
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

function mockApi(config: unknown = DISARMED) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/config/auto-research") return Promise.resolve(config)
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

describe("ResearchTab — the trigger half is absent on purpose", () => {
  it("offers no run control", async () => {
    mockApi()
    render(<ResearchTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("disarmed").length).toBeGreaterThan(0))

    for (const label of [/Run research/i, /Trigger/i, /Gather/i]) {
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
})
