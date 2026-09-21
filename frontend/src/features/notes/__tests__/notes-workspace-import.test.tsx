import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

const dialogProps = vi.hoisted(() => vi.fn())

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
  NotionImportDialog: (props: {
    project: string
    open: boolean
    onOpenChange: (open: boolean) => void
    onImported: (rootPageId: string) => void
  }) => {
    dialogProps(props)
    return props.open ? (
      <div data-testid="import-dialog">
        <button type="button" onClick={() => props.onImported("root-1")}>
          fire imported
        </button>
        <button type="button" onClick={() => props.onOpenChange(false)}>
          fire close
        </button>
      </div>
    ) : null
  },
}))

import { apiFetch } from "@/lib/api"
import { NotesWorkspace } from "../notes-workspace"

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
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const invalidate = vi.spyOn(qc, "invalidateQueries")
  render(
    <QueryClientProvider client={qc}>
      <NotesWorkspace project="personal" selectedId={null} onSelect={onSelect} />
    </QueryClientProvider>,
  )
  return { onSelect, qc, invalidate }
}

async function openImportDialog() {
  fireEvent.click(screen.getByRole("button", { name: /page tree actions/i }))
  fireEvent.click(
    await screen.findByRole("menuitem", { name: /import from notion/i }),
  )
  await waitFor(() =>
    expect(screen.getByTestId("import-dialog")).toBeInTheDocument(),
  )
}

beforeEach(() => {
  window.localStorage.clear()
  dialogProps.mockClear()
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

  it("hands the dialog the workspace's project", async () => {
    renderWorkspace()
    await openImportDialog()
    const calls = dialogProps.mock.calls
    const last = calls[calls.length - 1] as [{ project: string }]
    expect(last[0]).toMatchObject({ project: "personal" })
  })

  it("refreshes and selects on a confirmed import", async () => {
    const { onSelect, invalidate } = renderWorkspace()
    await openImportDialog()
    invalidate.mockClear()
    fireEvent.click(screen.getByRole("button", { name: /fire imported/i }))
    await waitFor(() =>
      expect(screen.queryByTestId("import-dialog")).not.toBeInTheDocument(),
    )
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["pages"] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["pagesTrash"] })
    expect(onSelect).toHaveBeenCalledWith("root-1")
  })

  it("refreshes on a dismissed import without selecting", async () => {
    const { onSelect, invalidate } = renderWorkspace()
    await openImportDialog()
    invalidate.mockClear()
    onSelect.mockClear()
    fireEvent.click(screen.getByRole("button", { name: /fire close/i }))
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ["pages"] }),
    )
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["pagesTrash"] })
    expect(onSelect).not.toHaveBeenCalled()
  })
})
