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

import { ApiError, apiFetch } from "@/lib/api"
import type { WorklogEntry, Workstream } from "@/hooks/api"
import { WorkLogPanel } from "../components/work-log-panel"

const OPEN: Workstream = {
  id: "w-open",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-superpowers",
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}
const CLOSED: Workstream = {
  ...OPEN,
  id: "w-closed",
  key: "plan-old",
  title: "Old plan",
  state: "closed",
  closed_at: "2026-09-01T00:00:00Z",
}
const FAR: Workstream = { ...OPEN, id: "w-far", key: "plan-z", title: "Far plan" }
const ENTRIES: WorklogEntry[] = [
  {
    id: "e1",
    workstream_id: "w-open",
    seq: 1,
    run_key: "claude-code:r1",
    kind: "ledger",
    body: "Task 1: done\n",
    properties: {},
    created_at: "2026-09-28T09:00:00Z",
  },
  {
    id: "e2",
    workstream_id: "w-open",
    seq: 2,
    run_key: "claude-code:r1",
    kind: "checkpoint",
    body: "## Where it stands\n\nHalfway there",
    properties: {},
    created_at: "2026-09-28T10:00:00Z",
  },
]

function routeApi(workstreams: { open: Workstream[]; closed: Workstream[] }) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/worklog/workstreams?")) {
      const qs = new URLSearchParams(path.split("?")[1])
      const items = qs.get("state") === "open" ? workstreams.open : workstreams.closed
      // One workstream per page, so paging is observable with two of them.
      const at = qs.get("before") ? 1 : 0
      return Promise.resolve({
        items: items.slice(at, at + 1),
        next_before: items.length > at + 1 ? "cursor" : null,
      })
    }
    if (path.startsWith("/worklog/resume?")) {
      const key = new URLSearchParams(path.split("?")[1]).get("workstream")
      return key === FAR.key
        ? Promise.resolve({ workstream: FAR, checkpoint: null, notes: [], notes_truncated: false, ledger: [] })
        : Promise.reject(new ApiError("No workstream", 404))
    }
    const entries = path.match(/^\/worklog\/workstreams\/([^/]+)\/entries\?(.*)$/)
    if (entries) {
      const kind = new URLSearchParams(entries[2]).get("kind")
      const items = entries[1] === "w-open" ? ENTRIES : []
      return Promise.resolve({
        items: kind ? items.filter((e) => e.kind === kind) : items,
        next_after: null,
      })
    }
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("WorkLogPanel", () => {
  it("opens on the first open workstream and reads an entry in full", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    expect(await screen.findByText("Task 1: done")).toBeInTheDocument()
    await user.click(screen.getByText("Where it stands"))
    const detail = screen.getByRole("article", { name: "entry" })
    expect(within(detail).getByText("Halfway there")).toBeInTheDocument()
  })

  it("keeps closed workstreams collapsed until asked", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByRole("button", { name: /Plan A/ })
    expect(screen.queryByText("Old plan")).toBeNull()
    await user.click(screen.getByRole("button", { name: "Closed (1)" }))
    await user.click(screen.getByText("Old plan"))
    expect(await screen.findByText("No entries yet")).toBeInTheDocument()
  })

  it("filters entries by kind on the server", async () => {
    routeApi({ open: [OPEN], closed: [] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByText("Where it stands")
    await user.click(screen.getByRole("radio", { name: "Ledger" }))
    await waitFor(() => expect(screen.queryByText("Where it stands")).toBeNull())
    expect(screen.getByText("Task 1: done")).toBeInTheDocument()
    expect(
      vi.mocked(apiFetch).mock.calls.some(([path]) => String(path).includes("kind=ledger")),
    ).toBe(true)
  })

  it("selects the workstream it is handed, even a closed one", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    render(<WorkLogPanel project="darkmem" initialWorkstream="plan-old" />, { wrapper })

    expect(await screen.findByRole("region", { name: "workstream plan-old" })).toBeInTheDocument()
    expect(screen.getByText("Old plan", { selector: "h3" })).toBeInTheDocument()
  })

  it("pages through a project's workstreams", async () => {
    routeApi({ open: [OPEN, { ...OPEN, id: "w-two", key: "plan-b", title: "Plan B" }], closed: [] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByRole("button", { name: /Plan A/ })
    expect(screen.queryByText("Plan B")).toBeNull()
    await user.click(screen.getByRole("button", { name: "More open workstreams" }))
    expect(await screen.findByText("Plan B")).toBeInTheDocument()
  })

  it("looks up a workstream past the loaded pages instead of replacing it", async () => {
    routeApi({ open: [OPEN], closed: [] })
    render(<WorkLogPanel project="darkmem" initialWorkstream="plan-z" />, { wrapper })

    expect(await screen.findByRole("region", { name: "workstream plan-z" })).toBeInTheDocument()
    expect(screen.getByText("Far plan", { selector: "h3" })).toBeInTheDocument()
  })

  it("says so when the project has no work log", async () => {
    routeApi({ open: [], closed: [] })
    render(<WorkLogPanel project="darkmem" />, { wrapper })
    expect(await screen.findByText("No work log yet")).toBeInTheDocument()
  })

  it("reports a failed read as a failure, not as an empty log", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<WorkLogPanel project="darkmem" />, { wrapper })
    expect(await screen.findByText("Could not read the work log")).toBeInTheDocument()
  })
})
