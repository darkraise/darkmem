import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
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
  vi.mocked(apiFetch).mockImplementation((() => Promise.resolve({})) as never)
})

describe("the page tree header menu under DEMO", () => {
  it("offers no import under DEMO", () => {
    renderWorkspace()
    expect(
      screen.queryByRole("button", { name: /page tree actions/i }),
    ).not.toBeInTheDocument()
  })
})
