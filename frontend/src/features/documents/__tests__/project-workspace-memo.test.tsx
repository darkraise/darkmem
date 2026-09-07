import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), ApiError: class extends Error {} }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
vi.mock("@/features/activity/components/checkpoints-tab", () => ({
  CheckpointsTab: () => null,
}))
vi.mock("@/features/documents/components/document-reader", () => ({
  DocumentReader: ({
    onActiveHeadingChange,
  }: {
    onActiveHeadingChange?: (blockId: string | null) => void
  }) => (
    <button type="button" onClick={() => onActiveHeadingChange?.(`h-${Math.random()}`)}>
      report heading
    </button>
  ),
}))

/** Records the `nodeActions` reference the workspace hands down on each
 *  render. Stubbing the tree is the only way to observe that identity: the
 *  real component is `memo`'d precisely so it does NOT re-render, which is
 *  what makes the defect invisible from the outside. */
const seen: Array<unknown> = []
vi.mock("@/features/documents/components/document-tree", () => ({
  DocumentTree: ({
    nodeActions,
    items,
    onSelect,
  }: {
    nodeActions?: unknown
    items: Array<{ id: string }>
    onSelect: (doc: unknown) => void
  }) => {
    seen.push(nodeActions)
    return (
      <button type="button" onClick={() => onSelect(items[0])}>
        tree-stub
      </button>
    )
  },
}))

import { apiFetch } from "@/lib/api"
import { ProjectWorkspace } from "../components/project-workspace"

const DOC = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Design notes",
  uri: "notes/design.md",
  source_type: "note",
  project: "darkmem",
  block_count: 3,
}

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("project workspace — the memoised tree", () => {
  it("hands the tree a stable nodeActions across a heading crossing", async () => {
    // `useMutation` returns a NEW result object every render and only
    // `.mutate` is stable, so depending on the mutation objects made
    // `nodeActions` change identity on every frame -- re-rendering the whole
    // tree once per heading the reader scrolls past, which is exactly what
    // `handleSelectDocument`'s own stability exists to prevent.
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (String(path).startsWith("/documents?")) {
        return Promise.resolve({ items: [DOC] })
      }
      return Promise.resolve({})
    })
    render(
      <ProjectWorkspace
        project="darkmem"
        tab="artifacts"
        onTabChange={vi.fn()}
        treeManagement
      />,
      { wrapper },
    )
    await userEvent.click(await screen.findByText("tree-stub"))
    await screen.findByText("report heading")
    seen.length = 0

    await userEvent.click(await screen.findByText("report heading"))
    await userEvent.click(screen.getByText("report heading"))

    expect(seen.length).toBeGreaterThan(0)
    expect(new Set(seen).size).toBe(1)
  })
})
