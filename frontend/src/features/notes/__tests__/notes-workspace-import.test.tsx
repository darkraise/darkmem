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
vi.mock("../page-pane", () => ({
  PagePane: ({ page }: { page: { id: string } }) => <div>pane:{page.id}</div>,
}))
vi.mock("../notion-import-dialog", () => ({
  NotionImportDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="import-dialog" /> : null,
}))

import { apiFetch } from "@/lib/api"
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

function route(path: string) {
  if (path.startsWith("/pages/trash")) return Promise.resolve([])
  if (path.startsWith("/pages?")) return Promise.resolve(LIST)
  return Promise.resolve({})
}

function renderWorkspace() {
  const onSelect = vi.fn()
  render(
    <NotesWorkspace project="personal" selectedId={null} onSelect={onSelect} />,
    { wrapper },
  )
  return { onSelect }
}

beforeEach(() => {
  window.localStorage.clear()
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(route as never)
})

describe("the page tree header menu", () => {
  it("offers Import from Notion", async () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole("button", { name: /page tree actions/i }))
    expect(
      await screen.findByRole("menuitem", { name: /import from notion/i }),
    ).toBeInTheDocument()
  })

  it("opens the dialog when chosen", async () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole("button", { name: /page tree actions/i }))
    fireEvent.click(
      await screen.findByRole("menuitem", { name: /import from notion/i }),
    )
    await waitFor(() =>
      expect(screen.getByTestId("import-dialog")).toBeInTheDocument(),
    )
  })

  it("keeps the New page button beside it", () => {
    renderWorkspace()
    expect(screen.getByRole("button", { name: /new page/i })).toBeInTheDocument()
  })
})
