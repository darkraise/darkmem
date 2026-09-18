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

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import { PageTrashSheet } from "../page-trash-sheet"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const TRASH = [
  {
    id: "p1",
    title: "Gone",
    parent_id: null,
    deleted_at: new Date(Date.now() - 3600_000).toISOString(),
  },
  { id: "p2", title: null, parent_id: null, deleted_at: new Date().toISOString() },
]

function open(props: Partial<Parameters<typeof PageTrashSheet>[0]> = {}) {
  const onRestored = vi.fn()
  render(
    <PageTrashSheet
      project="personal"
      open
      onOpenChange={vi.fn()}
      onRestored={onRestored}
      {...props}
    />,
    { wrapper },
  )
  return { onRestored }
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("PageTrashSheet", () => {
  it("lists the trashed roots with a relative deletion time", async () => {
    vi.mocked(apiFetch).mockResolvedValue(TRASH)
    open()
    expect(await screen.findByText("Gone")).toBeInTheDocument()
    expect(screen.getByText("Untitled")).toBeInTheDocument()
    expect(screen.getByText(/ago/)).toBeInTheDocument()
  })

  it("restores a row and tells the workspace", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.endsWith("/restore")
        ? Promise.resolve({ restored: 1 })
        : Promise.resolve(TRASH),
    )
    const { onRestored } = open()
    fireEvent.click(await screen.findByRole("button", { name: "Restore Gone" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1/restore", {
        method: "POST",
      }),
    )
    await waitFor(() => expect(onRestored).toHaveBeenCalled())
  })

  it("shows the server's own message when a restore is refused", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.endsWith("/restore")
        ? Promise.reject(new ApiError("the parent page is still trashed", 409))
        : Promise.resolve(TRASH),
    )
    open()
    fireEvent.click(await screen.findByRole("button", { name: "Restore Gone" }))
    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "the parent page is still trashed",
      ),
    )
  })

  it("empties the trash only behind the confirmation", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.includes("/trash/empty")
        ? Promise.resolve({ purged: 2 })
        : Promise.resolve(TRASH),
    )
    open()
    await screen.findByText("Gone")
    fireEvent.click(await screen.findByRole("button", { name: "Empty trash" }))
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalledWith(
      expect.stringContaining("/trash/empty"),
      expect.anything(),
    )
    fireEvent.click(await screen.findByRole("button", { name: "Delete permanently" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
        "/pages/trash/empty?project=personal",
        { method: "POST" },
      ),
    )
  })

  it("says the trash is empty rather than showing nothing", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    open()
    expect(await screen.findByText(/Trash is empty/)).toBeInTheDocument()
  })
})
