import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
// The pane is exercised by its own suite; here it stands in so the assertions
// are about what the workspace hands it.
vi.mock("../page-pane", () => ({
  PagePane: ({ page }: { page: { id: string } }) => <div>pane:{page.id}</div>,
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import { NotesWorkspace } from "../notes-workspace"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const LIST = [
  {
    id: "p1",
    project: "personal",
    parent_id: null,
    order_index: 0,
    title: "Alpha",
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  },
]
const PAGE = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Alpha",
  content_hash: "h",
  properties: null,
  content: null,
  blocks: [],
}

function route(path: string) {
  if (path.startsWith("/pages/trash")) return Promise.resolve([])
  if (path.startsWith("/pages?")) return Promise.resolve(LIST)
  if (path === "/pages/p1") return Promise.resolve(PAGE)
  return Promise.resolve({})
}

function renderWorkspace(props: Partial<Parameters<typeof NotesWorkspace>[0]> = {}) {
  const onSelect = vi.fn()
  render(
    <NotesWorkspace
      project="personal"
      selectedId={null}
      onSelect={onSelect}
      {...props}
    />,
    { wrapper },
  )
  return { onSelect }
}

beforeEach(() => {
  window.localStorage.clear()
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(route as never)
  vi.mocked(toast.error).mockReset()
  vi.mocked(toast.success).mockReset()
})

describe("NotesWorkspace", () => {
  it("renders the tree and the empty pane with nothing selected", async () => {
    renderWorkspace()
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
    expect(screen.getByText(/Pick a page/)).toBeInTheDocument()
  })

  it("renders the pane for the selected page", async () => {
    renderWorkspace({ selectedId: "p1" })
    expect(await screen.findByText("pane:p1")).toBeInTheDocument()
  })

  // A 404 means the selection no longer exists -- a state, not a fault. It
  // used to clear the selection, so a dashboard link to a purged page landed
  // on "Nothing selected" with no word that the page was gone.
  it("says a purged page no longer exists, keeping the selection", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string) =>
      path === "/pages/gone"
        ? Promise.reject(new ApiError("no page gone", 404))
        : route(path)) as never)
    const { onSelect } = renderWorkspace({ selectedId: "gone" })

    expect(
      await screen.findByText("This page no longer exists"),
    ).toBeInTheDocument()
    expect(screen.queryByText("Nothing selected")).toBeNull()
    expect(onSelect).not.toHaveBeenCalled()
    // The trash is where a page trashed with its parent can still be found.
    fireEvent.click(screen.getByRole("button", { name: "Open trash" }))
    expect(await screen.findByText("Trash is empty.")).toBeInTheDocument()
  })

  it("says a trashed page is in the trash and restores it in place", async () => {
    let restored = false
    vi.mocked(apiFetch).mockImplementation(((
      path: string,
      init?: RequestInit,
    ) => {
      if (path === "/pages/p1") {
        return restored
          ? Promise.resolve(PAGE)
          : Promise.reject(new ApiError("no live page with id p1", 404))
      }
      if (path.startsWith("/pages/trash")) {
        return Promise.resolve(
          restored
            ? []
            : [
                {
                  id: "p1",
                  title: "Alpha",
                  parent_id: null,
                  deleted_at: new Date().toISOString(),
                },
              ],
        )
      }
      if (path === "/pages/p1/restore" && init?.method === "POST") {
        restored = true
        return Promise.resolve({ restored: 1 })
      }
      return route(path)
    }) as never)
    renderWorkspace({ selectedId: "p1" })

    expect(
      await screen.findByText("This page is in the trash"),
    ).toBeInTheDocument()
    expect(screen.getByText(/Alpha was moved to the trash/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Restore" }))
    expect(await screen.findByText("pane:p1")).toBeInTheDocument()
  })

  it("shows an error, never the empty pane, when the page read fails otherwise", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string) =>
      path === "/pages/p1"
        ? Promise.reject(new ApiError("boom", 500))
        : route(path)) as never)
    const { onSelect } = renderWorkspace({ selectedId: "p1" })
    expect(await screen.findByText(/could not be loaded/)).toBeInTheDocument()
    expect(screen.queryByText(/Pick a page/)).toBeNull()
    expect(onSelect).not.toHaveBeenCalled()
  })

  it("creates a root page and selects it", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) =>
      path === "/pages" && init?.method === "POST"
        ? Promise.resolve({ id: "p9" })
        : route(path)) as never)
    const { onSelect } = renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "New page" }))
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith("p9"))
  })

  it("trashes a page and offers an undo that restores it", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p1" && init?.method === "DELETE") return Promise.resolve()
      if (path === "/pages/p1/restore") return Promise.resolve({ restored: 1 })
      return route(path)
    }) as never)
    renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Alpha" }))
    fireEvent.click(screen.getByText("Delete"))
    await waitFor(() => expect(vi.mocked(toast.success)).toHaveBeenCalled())
    const [, options] = vi.mocked(toast.success).mock.calls[0]!
    options!.action!.onClick()
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1/restore", {
        method: "POST",
      }),
    )
  })

  it("opens the trash sheet from the sidebar foot", async () => {
    renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "Trash" }))
    expect(await screen.findByText(/Trash is empty/)).toBeInTheDocument()
  })
})
