import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }))
vi.mock("../page-block-editor", () => ({
  PageBlockEditor: ({
    pageId,
    onStatus,
  }: {
    pageId: string
    onStatus: (s: { kind: string; message?: string }) => void
  }) => (
    <div>
      editor:{pageId}
      <button type="button" onClick={() => onStatus({ kind: "saving" })}>
        report saving
      </button>
      <button
        type="button"
        onClick={() => onStatus({ kind: "blocked", message: "the page moved" })}
      >
        report blocked
      </button>
    </div>
  ),
}))

import { apiFetch } from "@/lib/api"
import type { PageView } from "@/hooks/api"
import { PagePane } from "../page-pane"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PAGE: PageView = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Notes",
  content_hash: "h1",
  blocks: [],
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
})

describe("PagePane", () => {
  it("renders the title in an editable field and the editor below it", () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveValue("Notes")
    expect(screen.getByText("editor:p1")).toBeInTheDocument()
  })

  it("shows the fallback for an untitled page without sending it as a title", () => {
    render(<PagePane page={{ ...PAGE, title: null }} autoFocusTitle={false} />, {
      wrapper,
    })
    const field = screen.getByLabelText("Page title")
    expect(field).toHaveValue("")
    expect(field).toHaveAttribute("placeholder", "Untitled")
  })

  it("renames on blur, and not when the title is unchanged", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    const field = screen.getByLabelText("Page title")
    fireEvent.blur(field)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    fireEvent.change(field, { target: { value: "Renamed" } })
    fireEvent.blur(field)
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1", {
        method: "PATCH",
        body: JSON.stringify({ title: "Renamed" }),
      }),
    )
  })

  it("focuses the title when asked", () => {
    render(<PagePane page={PAGE} autoFocusTitle />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveFocus()
  })

  it("shows the save state and the blocked banner the editor reports", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    fireEvent.click(screen.getByText("report saving"))
    expect(await screen.findByText("Saving…")).toBeInTheDocument()
    fireEvent.click(screen.getByText("report blocked"))
    expect(await screen.findByText(/the page moved/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reload page" })).toBeInTheDocument()
  })
})
