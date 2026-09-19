import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T3.21 — the Session-checkpoints surface, against the real doors.
//
// The four done-whens, and the shape each assertion takes:
//   1. the latest checkpoint per run is one click away — a run card selects,
//      and the digest that arrives is that run's, fetched under its own key;
//   2. copy-resume yields the exact injected text — the clipboard receives
//      the server's `resume_line` byte for byte, never a re-rendering;
//   3. `checkpoint_saved` / `resumed` are both visible in the run's history;
//   4. Simple/Advanced is honoured — `simple` collapses technical detail and
//      never hides an honesty signal (invariant 14).

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch, ApiError } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { CheckpointsTab } from "../components/checkpoints-tab"
import { LIVE_POLL_MS } from "../use-checkpoint-runs"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const SUMMARY = "Rewired the checkpoints tab onto the real doors."
const RESUME_LINE =
  "- (resume) Rewired the checkpoints tab onto the real doors. Next: run the gate; update progress.md"

function journalEvent(over: Record<string, unknown>) {
  return {
    id: 1,
    created_at: "2026-08-11T09:41:00Z",
    event_type: "checkpoint_saved",
    object_type: "checkpoint",
    object_id: "11111111-1111-1111-1111-111111111111",
    project: "darkmem",
    actor: null,
    api_key_id: null,
    source: null,
    payload: { origin_key: "cc-run-8f3a2c", next_steps: 2 },
    ...over,
  }
}

const JOURNAL = {
  items: [
    journalEvent({ id: 3, event_type: "resumed", payload: { origin_key: "cc-run-8f3a2c", tokens_used: 1850 } }),
    journalEvent({ id: 2 }),
    journalEvent({
      id: 1,
      project: "other-proj",
      payload: { origin_key: "cc-run-other", next_steps: 1 },
      created_at: "2026-08-10T22:00:00Z",
    }),
  ],
  total: 3,
}

const CHECKPOINT = {
  id: "22222222-2222-2222-2222-222222222222",
  origin_key: "cc-run-8f3a2c",
  project: "darkmem",
  summary: SUMMARY,
  next_steps: ["run the gate", "update progress.md"],
  created_at: "2026-08-11T09:41:00Z",
  resume_line: RESUME_LINE,
  token_estimate: 42,
}

/** Routes each call by path, so a test never depends on call order. */
function route(handlers: Record<string, unknown>, missing: string[] = []) {
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    for (const key of missing) {
      if (path.includes(key)) throw new ApiError("not found", 404)
    }
    for (const [fragment, value] of Object.entries(handlers)) {
      if (path.includes(fragment)) return value as never
    }
    throw new Error(`unrouted call: ${path}`)
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  useDetailLevel.setState({ level: "advanced" })
  useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
})

describe("CheckpointsTab — runs come from the journal", () => {
  it("groups runs by origin_key and asks the door for the selected one", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    await screen.findByText("cc-run-8f3a2c")
    expect(screen.getByText("cc-run-other")).toBeInTheDocument()

    // The journal is read with the object type pushed down, not filtered here.
    const eventsCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => (path as string).includes("/events"))!
    expect(eventsCall[0]).toContain("object_type=checkpoint")

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            (path as string).includes("origin_key=cc-run-8f3a2c"),
          ),
      ).toBe(true),
    )
  })

  it("selecting a run fetches that run's own latest checkpoint", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    await userEvent.click(await screen.findByText("cc-run-other"))

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            (path as string).includes("origin_key=cc-run-other"),
          ),
      ).toBe(true),
    )
  })

  it("shows both journalled event kinds for the selected run", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    await screen.findByText("checkpoint_saved")
    expect(screen.getByText("resumed")).toBeInTheDocument()
  })

  it("an event whose payload names no run is dropped, never bucketed", async () => {
    // The door refuses an undeclared origin at write time precisely so two
    // runs cannot share one key. Bucketing them here would reintroduce that
    // merge as a display artefact.
    route({
      "/events": {
        items: [journalEvent({ id: 9, payload: {} })],
        total: 1,
      },
      "/checkpoints/latest": CHECKPOINT,
    })
    render(<CheckpointsTab />, { wrapper })

    expect(await screen.findByText("No runs have checkpointed yet")).toBeInTheDocument()
  })

  it("a run with no checkpoint reads as empty, not as an error", async () => {
    route({ "/events": JOURNAL }, ["/checkpoints/latest"])
    render(<CheckpointsTab />, { wrapper })

    expect(
      await screen.findByText("No checkpoints for this run yet"),
    ).toBeInTheDocument()
    expect(
      screen.queryByText("The checkpoint journal could not be read."),
    ).not.toBeInTheDocument()
  })
})

describe("CheckpointsTab — copy-resume yields the injected text", () => {
  it("copies the server's resume_line byte for byte", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    await userEvent.click(await screen.findByRole("button", { name: /copy resume block/i }))

    expect(writeText).toHaveBeenCalledWith(RESUME_LINE)
  })

  it("copies what the door served, not a re-rendering of summary and steps", async () => {
    // The guard that matters: a surface that assembled the line itself would
    // still produce plausible prose here, so the assertion is that the copied
    // bytes track the *wire* field when it diverges from what any local
    // rendering would produce.
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    const divergent = { ...CHECKPOINT, resume_line: "- (resume) SERVER TEXT ONLY" }
    route({ "/events": JOURNAL, "/checkpoints/latest": divergent })
    render(<CheckpointsTab />, { wrapper })

    await userEvent.click(await screen.findByRole("button", { name: /copy resume block/i }))

    expect(writeText).toHaveBeenCalledWith("- (resume) SERVER TEXT ONLY")
    expect(writeText).not.toHaveBeenCalledWith(
      expect.stringContaining("Rewired the checkpoints tab"),
    )
  })
})

describe("CheckpointsTab — detail level (invariant 14)", () => {
  it("advanced shows the origin key, the token estimate and the raw block", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    expect(
      await screen.findByText(/~42 tokens of the inject budget/),
    ).toBeInTheDocument()
    expect(screen.getByText(/origin_key: cc-run-8f3a2c/)).toBeInTheDocument()
    expect(screen.getByText(RESUME_LINE)).toBeInTheDocument()
  })

  it("simple collapses those and keeps the copy affordance", async () => {
    useDetailLevel.setState({ level: "simple" })
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    // Wait for the digest itself, or every negative below would pass while
    // the surface was still a spinner.
    await screen.findByText(SUMMARY)
    expect(screen.queryByText(/origin_key:/)).not.toBeInTheDocument()
    expect(screen.queryByText(/tokens of the inject budget/)).not.toBeInTheDocument()
    expect(screen.queryByText(RESUME_LINE)).not.toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /copy resume block/i }),
    ).toBeInTheDocument()
  })

  it("never hides the honesty label, at either level", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    const { unmount } = render(<CheckpointsTab />, { wrapper })
    expect(
      (await screen.findAllByText(/not verified knowledge/)).length,
    ).toBeGreaterThan(0)
    unmount()

    useDetailLevel.setState({ level: "simple" })
    render(<CheckpointsTab />, { wrapper })
    expect(
      (await screen.findAllByText(/not verified knowledge/)).length,
    ).toBeGreaterThan(0)
  })

  it("renders no verification badge vocabulary at either level", async () => {
    // T3.18's pixel-level half: the wire cannot carry a rung, and this is the
    // surface that would have rendered one if it could.
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    const { container, unmount } = render(<CheckpointsTab />, { wrapper })
    await screen.findByText(SUMMARY)
    for (const rung of ["corroborated", "confirmed", "disputed", "candidate"]) {
      expect(container.textContent).not.toContain(rung)
    }
    unmount()

    useDetailLevel.setState({ level: "simple" })
    const simple = render(<CheckpointsTab />, { wrapper })
    await screen.findByText(SUMMARY)
    for (const rung of ["corroborated", "confirmed", "disputed", "candidate"]) {
      expect(simple.container.textContent).not.toContain(rung)
    }
  })
})

describe("CheckpointsTab — the live watch surface (increment 1)", () => {
  it("follows the header scope through the server-side project predicate, not client slicing", async () => {
    // The distinction matters: a client-side filter would still show every
    // run the unfiltered page happened to carry, and would silently disagree
    // with `total`. The assertion is that the *request* narrowed.
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.includes("/events")) {
        return (
          path.includes("project=other-proj")
            ? { items: JOURNAL.items.filter((e) => e.project === "other-proj"), total: 1 }
            : JOURNAL
        ) as never
      }
      return CHECKPOINT as never
    })
    render(<CheckpointsTab />, { wrapper })

    await screen.findByText("cc-run-8f3a2c")
    expect(screen.getByText("cc-run-other")).toBeInTheDocument()
    expect(
      screen.queryByRole("combobox", { name: /project/i }),
    ).not.toBeInTheDocument()

    act(() => useProjectStore.getState().setProject("other-proj"))

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            (path as string).includes("project=other-proj"),
          ),
      ).toBe(true),
    )
    await waitFor(() =>
      expect(screen.queryByText("cc-run-8f3a2c")).not.toBeInTheDocument(),
    )
  })

  it("polls the journal on the live interval", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      render(<CheckpointsTab />, { wrapper })
      await screen.findByText("cc-run-8f3a2c")

      const eventsCalls = () =>
        vi
          .mocked(apiFetch)
          .mock.calls.filter(([path]) => (path as string).includes("/events"))
          .length
      const before = eventsCalls()

      await vi.advanceTimersByTimeAsync(LIVE_POLL_MS + 500)

      expect(eventsCalls()).toBeGreaterThan(before)
    } finally {
      vi.useRealTimers()
    }
  })

  it("states that the history carries no step content (review m2)", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab />, { wrapper })

    expect(
      await screen.findByText(/only the latest note's text is readable/i),
    ).toBeInTheDocument()
  })
})


describe("CheckpointsTab — pinned to one project (increment 4)", () => {
  it("reads that project's journal and offers no filter to escape it", async () => {
    route({ "/events": JOURNAL, "/checkpoints/latest": CHECKPOINT })
    render(<CheckpointsTab project="darkmem" />, { wrapper })

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            (path as string).includes("project=darkmem"),
          ),
      ).toBe(true),
    )
    // The workspace's scope is its route param; a filter here would let the
    // reader navigate out of the page they are on.
    expect(
      screen.queryByRole("combobox", { name: /project/i }),
    ).not.toBeInTheDocument()
  })
})
