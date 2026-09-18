import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Profiler, useState, type ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), ApiError: class extends Error {} }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
vi.mock("@/features/activity/components/checkpoints-tab", () => ({
  CheckpointsTab: () => null,
}))
// The scrollspy the real reader drives from a scroll listener. Each click is
// one heading crossing, which is the frame budget under test: the workspace
// holds `activeHeadingId`, so every crossing re-renders it.
vi.mock("@/features/documents/components/document-reader", () => ({
  DocumentReader: ({
    onActiveHeadingChange,
  }: {
    onActiveHeadingChange?: (blockId: string | null) => void
  }) => (
    <button
      type="button"
      onClick={() => onActiveHeadingChange?.(`h-${Math.random()}`)}
    >
      report heading
    </button>
  ),
}))

/** The instrument. `fileIcon` is called once per leaf INSIDE `DocumentTree`'s
 *  own render body, so its call count is that component's render count times
 *  the row count -- and it goes to zero for a crossing the `memo` skipped.
 *  A Profiler around the workspace cannot see this: it commits whenever the
 *  workspace does, whether or not the memoised child bailed out. */
const rowRenders = vi.fn()
vi.mock("@/features/documents/file-icons", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../file-icons")>()
  return {
    ...actual,
    fileIcon: (name: string) => {
      rowRenders(name)
      return actual.fileIcon(name)
    },
  }
})

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

/** Renders the REAL `DocumentTree` and counts its commits.
 *
 * The stub-based sibling suite proves one prop's reference is stable, which
 * is necessary and not sufficient: `memo` compares EVERY prop shallowly, so a
 * single fresh object anywhere in the list defeats it and a stub can never
 * see that. This asks the question the comments actually claim an answer to
 * -- was the render skipped -- and it is the only test that can fail when a
 * new inline prop is added to the call site.
 */
async function countTreeRenders() {
  let renders = 0
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (String(path).startsWith("/documents?")) {
      return Promise.resolve({ items: [DOC] })
    }
    return Promise.resolve({})
  })
  render(
    <Profiler id="workspace" onRender={() => (renders += 1)}>
      <ProjectWorkspace
        project="darkmem"
        tab="artifacts"
        onTabChange={vi.fn()}
      />
    </Profiler>,
    { wrapper },
  )
  await userEvent.click(await screen.findByText("design.md"))
  await screen.findByText("report heading")

  // Proves the spy is bound to the module `document-tree.tsx` actually
  // imports, and that a leaf really rendered. Without it a zero count is
  // ambiguous: memo bailed (what is under test), the mock never intercepted,
  // or the tree drew no rows at all.
  expect(rowRenders).toHaveBeenCalledWith("design.md")

  // Baseline taken after the selection has settled; the deltas are what the
  // crossings cost.
  rowRenders.mockClear()
  const rendersBefore = renders
  await userEvent.click(screen.getByText("report heading"))
  const afterOne = rowRenders.mock.calls.length
  await userEvent.click(screen.getByText("report heading"))
  return {
    perCrossing: afterOne,
    second: rowRenders.mock.calls.length - afterOne,
    // The DELTA, not the total: counting from mount is satisfied by the mount
    // itself, so it would prove nothing about the two clicks. If the reader
    // stub's `onActiveHeadingChange` ever stopped reaching
    // `setActiveHeadingId` -- a prop rename does it -- the row count would
    // read zero and this test would go green having measured nothing.
    workspaceRenders: renders - rendersBefore,
  }
}

describe("project workspace — the memoised tree is really skipped", () => {
  beforeEach(() => {
    rowRenders.mockClear()
  })

  it("does not re-render the tree on a heading crossing on the corpus browser", async () => {
    // `onExpandedChange` was a plain declaration, so this surface -- which
    // predates every note action -- was paying the same cost.
    //
    // The workspace itself DOES re-render on each of the two crossings -- it
    // holds `activeHeadingId` -- which is what makes a zero row count mean
    // "the memo skipped it" rather than "nothing happened".
    const { perCrossing, second, workspaceRenders } = await countTreeRenders()
    expect(workspaceRenders).toBeGreaterThanOrEqual(2)
    expect(perCrossing).toBe(0)
    expect(second).toBe(0)
  })
})
