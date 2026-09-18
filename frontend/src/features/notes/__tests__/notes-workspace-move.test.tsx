import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
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
vi.mock("../page-pane", () => ({ PagePane: () => <div>pane</div> }))
// The tree's own suites cover its rows and its drag layer; here it is the one
// thing that must not be real, so the move handler can be driven directly.
vi.mock("../page-tree", () => ({
  notesExpansionStorageKey: (project: string) => `k:${project}`,
  PageTree: ({
    onMove,
  }: {
    onMove: (
      id: string,
      placement: { parentId: string | null; afterId: string | null },
    ) => void
  }) => (
    <button
      type="button"
      onClick={() => onMove("p2", { parentId: "p1", afterId: null })}
    >
      drop
    </button>
  ),
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import type { PageListItem } from "@/hooks/api"
import { NotesWorkspace } from "../notes-workspace"

function row(id: string, order_index: number): PageListItem {
  return {
    id,
    project: "personal",
    parent_id: null,
    order_index,
    title: id,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}
const LIST = [row("p1", 0), row("p2", 1)]

function parentOf(qc: QueryClient, id: string) {
  return qc
    .getQueryData<PageListItem[]>(["pages", "personal"])!
    .find((r) => r.id === id)!.parent_id
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("NotesWorkspace move", () => {
  it("shows the move before the server answers, then rolls it back on refusal", async () => {
    // The list read fails after its first success, so the hook's own
    // invalidation cannot refetch the server's copy over the rollback and
    // pass this test for the wrong reason.
    let listCalls = 0
    let refuse: (reason: unknown) => void = () => {}
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p2" && init?.method === "PATCH") {
        return new Promise((_resolve, reject) => {
          refuse = reject
        })
      }
      if (path.startsWith("/pages?")) {
        listCalls += 1
        return listCalls === 1
          ? Promise.resolve(LIST)
          : Promise.reject(new ApiError("unavailable", 503))
      }
      if (path.startsWith("/pages/trash")) return Promise.resolve([])
      return Promise.resolve({})
    }) as never)

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <NotesWorkspace project="personal" selectedId={null} onSelect={vi.fn()} />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())

    fireEvent.click(screen.getByText("drop"))
    await waitFor(() => expect(parentOf(qc, "p2")).toBe("p1"))

    refuse(new ApiError("a page cannot be its own ancestor", 422))
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "a page cannot be its own ancestor",
    )
  })

  it("keeps the optimistic move when the server accepts it", async () => {
    let listCalls = 0
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p2" && init?.method === "PATCH") {
        return Promise.resolve({ id: "p2" })
      }
      if (path.startsWith("/pages?")) {
        listCalls += 1
        return listCalls === 1
          ? Promise.resolve(LIST)
          : Promise.reject(new ApiError("unavailable", 503))
      }
      if (path.startsWith("/pages/trash")) return Promise.resolve([])
      return Promise.resolve({})
    }) as never)

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <NotesWorkspace project="personal" selectedId={null} onSelect={vi.fn()} />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())
    fireEvent.click(screen.getByText("drop"))
    await waitFor(() => expect(parentOf(qc, "p2")).toBe("p1"))
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled()
  })
})
