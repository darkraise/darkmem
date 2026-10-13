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
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { DEMO_BOARD_VIEWS } from "@/demo/board"
import type { BoardView } from "@/hooks/api"
import { BoardPanel, sourceNotes } from "../components/board-panel"
import { RECORDS } from "./fixtures"

const SAVED: BoardView = {
  ...DEMO_BOARD_VIEWS[0]!,
  id: "11111111-1111-4111-8111-111111111111",
  name: "Mine",
  builtin: false,
  position: 0,
}

function routeApi(views: BoardView[] = DEMO_BOARD_VIEWS, records = RECORDS) {
  vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
    if (path.startsWith("/board/records?")) return Promise.resolve(records)
    if (path.startsWith("/board/views?")) return Promise.resolve(views)
    if (path === "/board/views" && init?.method === "POST") {
      return Promise.resolve({
        ...SAVED,
        id: "22222222-2222-4222-8222-222222222222",
      })
    }
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function renderPanel(props: Partial<Parameters<typeof BoardPanel>[0]> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onViewChange = vi.fn()
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  render(
    <BoardPanel
      project="darkmem"
      viewId={undefined}
      onViewChange={onViewChange}
      onOpenDocument={vi.fn()}
      onShowInWorkLog={vi.fn()}
      {...props}
    />,
    { wrapper },
  )
  return { onViewChange }
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("BoardPanel", () => {
  it("opens on the open-register-items built-in: register rows by state, done hidden", async () => {
    routeApi()
    renderPanel()
    const lane = await screen.findByRole("region", { name: "Register rows" })
    expect(within(lane).getByText("Alpha")).toBeInTheDocument()
    expect(within(lane).getByText("Beta")).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Plan tasks" })).toBeNull()
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull()
  })

  it("reports a view change through the tabs", async () => {
    routeApi()
    const user = userEvent.setup()
    const { onViewChange } = renderPanel()
    await user.click(
      await screen.findByRole("tab", { name: "Plans in flight" }),
    )
    expect(onViewChange).toHaveBeenCalledWith("builtin:plans-in-flight")
  })

  it("groups the plans-in-flight view by plan and hides untracked tasks", async () => {
    routeApi()
    renderPanel({ viewId: "builtin:plans-in-flight" })
    expect(
      await screen.findByRole("heading", { name: /^p\s*2$/ }),
    ).toBeInTheDocument()
    expect(screen.queryByText("Loose")).toBeNull()
  })

  it("duplicates a built-in by saving it as a new view", async () => {
    routeApi()
    const user = userEvent.setup()
    const { onViewChange } = renderPanel()
    await user.click(
      await screen.findByRole("button", { name: "Save as view" }),
    )
    const name = screen.getByLabelText("Name")
    expect(name).toHaveValue("Open register items copy")
    await user.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() =>
      expect(onViewChange).toHaveBeenCalledWith(
        "22222222-2222-4222-8222-222222222222",
      ),
    )
    const post = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/board/views")!
    expect(JSON.parse(String(post[1]!.body))).toEqual({
      project: "darkmem",
      name: "Open register items copy",
      definition: DEMO_BOARD_VIEWS[0]!.definition,
    })
  })

  it("switches to the table layout", async () => {
    routeApi()
    const user = userEvent.setup()
    renderPanel()
    await user.click(await screen.findByRole("radio", { name: "Table" }))
    expect(screen.getByRole("table")).toBeInTheDocument()
  })

  it("offers rename, delete and update only on a saved view", async () => {
    routeApi([...DEMO_BOARD_VIEWS, SAVED])
    const user = userEvent.setup()
    renderPanel({ viewId: SAVED.id })
    expect(
      await screen.findByRole("button", { name: "Rename" }),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Update view" })).toBeNull()
    await user.click(screen.getByRole("radio", { name: "Table" }))
    expect(
      screen.getByRole("button", { name: "Update view" }),
    ).toBeInTheDocument()
  })

  it("says so when the project has no registers or plans", async () => {
    routeApi(DEMO_BOARD_VIEWS, { project: "darkmem", registers: [], plans: [] })
    renderPanel()
    expect(await screen.findByText("No registers or plans")).toBeInTheDocument()
  })

  it("lists what each source says about itself", async () => {
    const plan = {
      ...RECORDS.plans[0]!,
      other_workstreams: 2,
      orphans: [9, 12],
    }
    const records = { ...RECORDS, plans: [plan, ...RECORDS.plans.slice(1)] }
    expect(sourceNotes(records)).toEqual([
      "superpowers/plans/p.md: 2 other workstreams name this plan",
      "superpowers/plans/p.md: the ledger names task 9, 12 with no heading in the plan",
    ])
    routeApi(DEMO_BOARD_VIEWS, records)
    renderPanel()
    const notes = await screen.findByRole("list", { name: "source notes" })
    expect(within(notes).getAllByRole("listitem")).toHaveLength(2)
  })
})
