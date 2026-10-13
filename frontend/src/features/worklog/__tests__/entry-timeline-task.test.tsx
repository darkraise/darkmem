import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { WORKLOG_LIVE_MS, type WorklogEntry, type Workstream } from "@/hooks/api"
import { EntryTimeline } from "../components/entry-timeline"

const WORKSTREAM: Workstream = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-forge",
  state: "closed",
  closed_at: "2026-10-13T00:00:00Z",
  retain: false,
  properties: {},
  last_entry_at: "2026-10-13T00:00:00Z",
  created_at: "2026-10-12T00:00:00Z",
  updated_at: "2026-10-13T00:00:00Z",
}

function ledger(
  seq: number,
  body: string,
  properties: Record<string, unknown>,
): WorklogEntry {
  return {
    id: `e${seq}`,
    workstream_id: "w1",
    seq,
    run_key: "claude-code:r1",
    kind: "ledger",
    body,
    properties,
    created_at: "2026-10-13T09:00:00Z",
  }
}

const FIRST_PAGE = [
  ledger(1, "Task 1: implementer (assigned)\n", { task: 1, state: "wip" }),
  ledger(2, "Task 2: implementer (assigned)\n", { task: 2, state: "wip" }),
]
const SECOND_PAGE = [
  ledger(501, "Task 2: complete (commits a..9abc1234def)\n", {
    task: 2,
    state: "done",
    commit: "9abc1234def",
  }),
  ledger(502, "Task 2.5: odd\n", { task: 2.5 }),
]

function routeApi() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    const qs = new URLSearchParams(path.split("?")[1])
    if (qs.get("limit") === "500") {
      return Promise.resolve(
        qs.get("after") === "500"
          ? { items: SECOND_PAGE, next_after: null }
          : { items: FIRST_PAGE, next_after: 500 },
      )
    }
    return Promise.resolve({ items: FIRST_PAGE, next_after: 500 })
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("EntryTimeline's task filter", () => {
  it("holds the kind control on Ledger while a task is set, since only the ledger carries tasks", async () => {
    routeApi()
    const user = userEvent.setup()
    render(<EntryTimeline workstream={WORKSTREAM} />, { wrapper })
    await screen.findByText("Task 1: implementer (assigned)")
    const kinds = screen.getByRole("radiogroup", { name: "entry kind" })
    await user.click(within(kinds).getByRole("radio", { name: "Notes" }))
    await user.type(screen.getByLabelText("task"), "2")
    expect(within(kinds).getByRole("radio", { name: "Ledger" })).toBeChecked()
    expect(within(kinds).getByRole("radio", { name: "All" })).toBeDisabled()
    await user.clear(screen.getByLabelText("task"))
    expect(within(kinds).getByRole("radio", { name: "Notes" })).toBeChecked()
  })

  it("re-reads the whole ledger while an open workstream is filtered to a task", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      routeApi()
      render(
        <EntryTimeline
          workstream={{ ...WORKSTREAM, state: "open", closed_at: null }}
          initialTask={2}
        />,
        { wrapper },
      )
      await screen.findByText("Task 2: complete (commits a..9abc1234def)")
      const ledgerReads = () =>
        vi
          .mocked(apiFetch)
          .mock.calls.filter(([path]) => String(path).includes("limit=500"))
          .length
      const before = ledgerReads()
      await vi.advanceTimersByTimeAsync(WORKLOG_LIVE_MS + 100)
      await waitFor(() => expect(ledgerReads()).toBeGreaterThan(before))
    } finally {
      vi.useRealTimers()
    }
  })

  it("shows an entry's task, state and commit as badges", async () => {
    routeApi()
    render(<EntryTimeline workstream={WORKSTREAM} />, { wrapper })
    expect(
      await screen.findByText("Task 1: implementer (assigned)"),
    ).toBeInTheDocument()
    expect(screen.getAllByText("task 1").length).toBeGreaterThan(0)
    expect(screen.getAllByText("wip").length).toBeGreaterThan(0)
  })

  it("pages the whole ledger before filtering to the initial task", async () => {
    routeApi()
    render(<EntryTimeline workstream={WORKSTREAM} initialTask={2} />, {
      wrapper,
    })
    expect(
      await screen.findByText("Task 2: complete (commits a..9abc1234def)"),
    ).toBeInTheDocument()
    expect(
      screen.getByText("Task 2: implementer (assigned)"),
    ).toBeInTheDocument()
    expect(screen.queryByText("Task 1: implementer (assigned)")).toBeNull()
    expect(screen.queryByText("Task 2.5: odd")).toBeNull()
    expect(screen.getByText("9abc123")).toBeInTheDocument()
    const ledgerReads = vi
      .mocked(apiFetch)
      .mock.calls.map(([path]) => String(path))
      .filter((path) => path.includes("limit=500"))
    expect(ledgerReads).toEqual([
      "/worklog/workstreams/w1/entries?kind=ledger&limit=500",
      "/worklog/workstreams/w1/entries?kind=ledger&limit=500&after=500",
    ])
  })

  it("filters as the task box is typed and clears back to the paged timeline", async () => {
    routeApi()
    const user = userEvent.setup()
    render(<EntryTimeline workstream={WORKSTREAM} />, { wrapper })
    await screen.findByText("Task 1: implementer (assigned)")
    await user.type(screen.getByRole("textbox", { name: "task" }), "1")
    await waitFor(() =>
      expect(screen.queryByText("Task 2: implementer (assigned)")).toBeNull(),
    )
    expect(
      screen.getByText("Task 1: implementer (assigned)"),
    ).toBeInTheDocument()
    await user.clear(screen.getByRole("textbox", { name: "task" }))
    expect(
      await screen.findByText("Task 2: implementer (assigned)"),
    ).toBeInTheDocument()
  })
})
