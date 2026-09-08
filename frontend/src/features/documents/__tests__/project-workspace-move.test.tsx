import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState, type ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

import type { MoveTarget } from "../move-target"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), ApiError }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

/** The tree stands in so a drop can be delivered at all: a real pointer drag
 *  needs layout, which jsdom does not do, and the drag pipeline that turns a
 *  release into a `MoveTarget` is covered by `document-tree-drag.test.tsx`.
 *  What is under test here is what the workspace does with the target --
 *  observed on `apiFetch` and the toast, never on a callback wired for the
 *  test. */
let lastOnMove: ((target: MoveTarget) => void) | undefined
let onMoveIdentities: Array<((target: MoveTarget) => void) | undefined> = []
vi.mock("@/features/documents/components/document-tree", () => ({
  DocumentTree: ({ onMove }: { onMove?: (target: MoveTarget) => void }) => {
    lastOnMove = onMove
    onMoveIdentities.push(onMove)
    return <div>tree</div>
  },
}))
vi.mock("@/features/documents/components/document-reader", () => ({
  DocumentReader: () => <div>reader</div>,
}))
vi.mock("@/features/activity/components/checkpoints-tab", () => ({
  CheckpointsTab: () => <div>checkpoints-tab</div>,
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import { ProjectWorkspace } from "../components/project-workspace"

const ONE = {
  id: "11111111-1111-1111-1111-111111111111",
  title: null,
  uri: "a/one.md",
  source_type: "note",
  project: "darkmem",
  block_count: 1,
}
const TWO = { ...ONE, id: "22222222-2222-2222-2222-222222222222", uri: "b/two.md" }

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function mockList() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/documents/search")) return Promise.resolve({ items: [] })
    if (path.startsWith("/documents")) return Promise.resolve({ items: [ONE, TWO] })
    return Promise.resolve({})
  })
}

async function renderWorkspace(treeManagement = true) {
  render(
    <ProjectWorkspace
      project="darkmem"
      tab="artifacts"
      onTabChange={vi.fn()}
      treeManagement={treeManagement}
    />,
    { wrapper },
  )
  await screen.findByText("tree")
}

/** What `apiFetch` was actually called with, method and parsed body. */
function calls() {
  return vi.mocked(apiFetch).mock.calls.map(([path, options]) => ({
    path,
    method: (options as RequestInit | undefined)?.method,
    body: (options as RequestInit | undefined)?.body
      ? JSON.parse(String((options as RequestInit).body))
      : undefined,
  }))
}

afterEach(() => {
  vi.clearAllMocks()
  lastOnMove = undefined
  onMoveIdentities = []
  window.localStorage.clear()
})

describe("project workspace — a drop is a real uri rewrite", () => {
  it("moves a dropped document with a uri PATCH", async () => {
    mockList()
    await renderWorkspace()
    lastOnMove!({ kind: "document", documentId: ONE.id, uri: "b/one.md" })
    await waitFor(() =>
      expect(calls()).toContainEqual({
        path: `/documents/${ONE.id}`,
        method: "PATCH",
        body: { uri: "b/one.md" },
      }),
    )
  })

  it("moves a dropped folder with the subtree rename", async () => {
    mockList()
    await renderWorkspace()
    lastOnMove!({ kind: "subtree", uriPrefix: "a", newUriPrefix: "b/a" })
    await waitFor(() =>
      expect(calls()).toContainEqual({
        path: "/documents/rename",
        method: "POST",
        body: { project: "darkmem", uri_prefix: "a", new_uri_prefix: "b/a" },
      }),
    )
  })

  it("surfaces a 409 in the server's own words, naming the colliding uri", async () => {
    // A move onto an occupied path is a real refusal, not a bug: the target
    // uri is another document's identity. The message is the server's --
    // `DocumentUriConflict` names the ONE document that collides, which on a
    // subtree move is not the prefix the reader dropped.
    mockList()
    await renderWorkspace()
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(
        "another document in this project already holds the uri 'b/two.md'",
        409,
      ),
    )
    lastOnMove!({ kind: "subtree", uriPrefix: "a", newUriPrefix: "b" })
    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "another document in this project already holds the uri 'b/two.md'",
      ),
    )
  })

  it("reports a non-409 failure in the server's own words too", async () => {
    mockList()
    await renderWorkspace()
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError("Storage is full", 500))
    lastOnMove!({ kind: "subtree", uriPrefix: "a", newUriPrefix: "b/a" })
    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith("Storage is full"),
    )
  })

  it("reports a folder move that matched no row instead of falling silent", async () => {
    // The tree drops empty uri segments when it builds a folder path, and
    // the door's prefix predicate does not normalise at all -- so a folder
    // holding only `/notes/a.md` renders as `notes` and matches none of its
    // own rows. The 200 that comes back is indistinguishable from a move.
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/documents/rename") return Promise.resolve({ renamed: 0 })
      if (path.startsWith("/documents/search")) return Promise.resolve({ items: [] })
      if (path.startsWith("/documents")) return Promise.resolve({ items: [ONE, TWO] })
      return Promise.resolve({})
    })
    await renderWorkspace()
    lastOnMove!({ kind: "subtree", uriPrefix: "notes", newUriPrefix: "b/notes" })
    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        expect.stringMatching(/nothing was moved/i),
      ),
    )
  })

  it("reports no refusal when the move did rewrite rows", async () => {
    // The other half of the pair: a handler that toasted unconditionally
    // would satisfy the test above and be wrong on every real move.
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/documents/rename") return Promise.resolve({ renamed: 2 })
      if (path.startsWith("/documents/search")) return Promise.resolve({ items: [] })
      if (path.startsWith("/documents")) return Promise.resolve({ items: [ONE, TWO] })
      return Promise.resolve({})
    })
    await renderWorkspace()
    lastOnMove!({ kind: "subtree", uriPrefix: "a", newUriPrefix: "b/a" })
    await waitFor(() =>
      expect(calls().some((c) => c.path === "/documents/rename")).toBe(true),
    )
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled()
  })

  it("mounts no drag layer where tree management is off", async () => {
    mockList()
    await renderWorkspace(false)
    expect(lastOnMove).toBeUndefined()
  })

  it("hands the tree one stable onMove across re-renders", async () => {
    // `DocumentTree` is memo'd with a shallow compare, so a fresh handler per
    // render re-renders the whole pane on every keystroke.
    mockList()
    await renderWorkspace()
    await userEvent.type(screen.getByLabelText("search documents"), "abc")
    const seen = new Set(onMoveIdentities)
    expect(onMoveIdentities.length).toBeGreaterThan(1)
    expect(seen.size).toBe(1)
  })
})
