import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import type { WorklogEntry, Workstream } from "@/hooks/api"
import { WorkLogPanel } from "../components/work-log-panel"
import { WorklogSearch } from "../components/worklog-search"

const OPEN: Workstream = {
  id: "w-open",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: null,
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}
const OTHER: Workstream = { ...OPEN, id: "w-other", key: "plan-b", title: "Plan B" }
const FAR: Workstream = { ...OPEN, id: "w-far", key: "plan-z", title: "Far plan" }
const HIT: WorklogEntry = {
  id: "e9",
  workstream_id: "w-other",
  seq: 9,
  run_key: "claude-code:r2",
  kind: "note",
  body: "Retention runs at 05:15 UTC",
  properties: {},
  created_at: "2026-09-28T09:30:00Z",
}

const FAR_HIT: WorklogEntry = {
  ...HIT,
  id: "e20",
  workstream_id: "w-far",
  seq: 20,
  body: "Retention on the far plan",
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/worklog/search") {
      return Promise.resolve({
        items: [
          { entry: HIT, workstream: "plan-b", rrf_score: 0.02, arms: ["keyword"] },
          { entry: FAR_HIT, workstream: "plan-z", rrf_score: 0.01, arms: ["keyword"] },
        ],
        semantic_ran: false,
      })
    }
    if (path === "/worklog/resume?project=darkmem&workstream=plan-z") {
      return Promise.resolve({ workstream: FAR, checkpoint: null, notes: [], notes_truncated: false, ledger: [] })
    }
    if (path.startsWith("/worklog/workstreams/w-far/entries")) {
      return Promise.resolve({ items: [FAR_HIT], next_after: null })
    }
    if (path.startsWith("/worklog/workstreams?")) {
      const open = path.includes("state=open")
      return Promise.resolve({ items: open ? [OPEN, OTHER] : [], next_before: null })
    }
    if (path.startsWith("/worklog/workstreams/w-other/entries")) {
      return Promise.resolve({ items: [HIT], next_after: null })
    }
    if (path.includes("/entries")) return Promise.resolve({ items: [], next_after: null })
    return Promise.reject(new Error(`unrouted ${path}`))
  })
})

describe("WorklogSearch", () => {
  it("searches the project and says when only the keyword arm ran", async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<WorklogSearch project="darkmem" onOpen={onOpen} />, { wrapper })

    await user.type(screen.getByRole("searchbox", { name: "Search the work log" }), "retention{Enter}")
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/worklog/search", {
      method: "POST",
      body: JSON.stringify({ project: "darkmem", query: "retention" }),
    })
    expect(await screen.findByText(/keyword matches only/i)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Retention runs at 05:15 UTC/ }))
    expect(onOpen).toHaveBeenCalledWith("plan-b", "e9")
  })

  it("opens a hit's workstream and entry in the panel", async () => {
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await user.type(
      await screen.findByRole("searchbox", { name: "Search the work log" }),
      "retention{Enter}",
    )
    await user.click(await screen.findByRole("button", { name: /Retention runs at 05:15 UTC/ }))
    expect(await screen.findByRole("region", { name: "workstream plan-b" })).toBeInTheDocument()
    const detail = await screen.findByRole("article", { name: "entry" })
    expect(within(detail).getByText("Retention runs at 05:15 UTC")).toBeInTheDocument()
  })

  it("opens a hit whose workstream is not in the loaded list", async () => {
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await user.type(
      await screen.findByRole("searchbox", { name: "Search the work log" }),
      "retention{Enter}",
    )
    await user.click(await screen.findByRole("button", { name: /Retention on the far plan/ }))
    expect(await screen.findByRole("region", { name: "workstream plan-z" })).toBeInTheDocument()
    const detail = await screen.findByRole("article", { name: "entry" })
    expect(within(detail).getByText("Retention on the far plan")).toBeInTheDocument()
  })

  it("pages forward to a hit past the first page of entries", async () => {
    const base = vi.mocked(apiFetch).getMockImplementation()!
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith("/worklog/workstreams/w-other/entries")) {
        return path.includes("after=")
          ? Promise.resolve({ items: [HIT], next_after: null })
          : Promise.resolve({ items: [{ ...HIT, id: "e1", seq: 1, body: "Older" }], next_after: 1 })
      }
      return base(path)
    })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await user.type(
      await screen.findByRole("searchbox", { name: "Search the work log" }),
      "retention{Enter}",
    )
    await user.click(await screen.findByRole("button", { name: /Retention runs at 05:15 UTC/ }))
    const detail = await screen.findByRole("article", { name: "entry" })
    expect(within(detail).getByText("Retention runs at 05:15 UTC")).toBeInTheDocument()
  })
})
