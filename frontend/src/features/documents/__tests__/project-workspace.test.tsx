import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState, type ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

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

// The reader is exercised by its own suite; here it stands in so the
// assertions are about what the workspace hands it, not about block rendering.
vi.mock("@/features/documents/components/document-reader", () => ({
  DocumentReader: ({
    documentId,
    focusBlockId,
    onActiveHeadingChange,
  }: {
    documentId: string
    focusBlockId?: string | null
    onActiveHeadingChange?: (blockId: string | null) => void
  }) => (
    <div>
      reader:{documentId}:focus={focusBlockId ?? "none"}
      {/* Stands in for the scrollspy. The real reader reports this from a
          scroll listener over its own body; jsdom performs no layout, so the
          only thing the workspace's own suite can assert is that whatever the
          reader reports is what the rail marks. */}
      <button type="button" onClick={() => onActiveHeadingChange?.("block-h2")}>
        report heading
      </button>
    </div>
  ),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
vi.mock("@/features/worklog/components/work-log-panel", () => ({
  WorkLogPanel: ({
    initialWorkstream,
    onOpenDocument,
  }: {
    initialWorkstream?: string
    onOpenDocument?: (uri: string) => void
  }) => (
    <div>
      work-log-panel:{initialWorkstream ?? "none"}
      <button type="button" onClick={() => onOpenDocument?.("notes/design.md")}>
        open design
      </button>
      <button
        type="button"
        onClick={() => onOpenDocument?.("notes/missing.md")}
      >
        open missing
      </button>
    </div>
  ),
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch } from "@/lib/api"
import { ProjectWorkspace } from "../components/project-workspace"
import { expansionStorageKey } from "../tree-expansion"

const DOC = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Design notes",
  uri: "notes/design.md",
  source_type: "note",
  project: "darkmem",
  block_count: 3,
}

// Stashed so a test can drive the cache directly (invalidate, force a
// refetch) the way a real mutation's `onSuccess` would, without remounting
// the tree. Held in `useState` so the same client survives every re-render
// of this wrapper -- a fresh one per render would carry no cached data.
let lastQueryClient: QueryClient | null = null

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    lastQueryClient = client
    return client
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

/** `useAllDocuments` pages until a short page; one full-shaped page ends it. */
function mockDocuments(result: unknown | "fail") {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/documents/search")) {
      return Promise.resolve({ items: [] })
    }
    // The reader pane's detail panels. Without their own arms these fall
    // through to the list payload, which carries no `embedded`, so the
    // connections panel would render "not comparable yet" for every
    // document and this file would be asserting against the wrong state.
    if (path.endsWith("/connections")) {
      return Promise.resolve({
        items: [],
        embedded: true,
        comparable_documents: 0,
      })
    }
    if (path.endsWith("/summary")) {
      return Promise.resolve(null)
    }
    if (path.endsWith("/outline")) {
      return Promise.resolve({
        document_id: DOC.id,
        items: [
          {
            block_id: "block-h1",
            level: 1,
            text: "Design notes",
            order_index: 0,
          },
          { block_id: "block-h2", level: 2, text: "Storage", order_index: 4 },
        ],
      })
    }
    if (path.startsWith("/documents")) {
      return result === "fail"
        ? Promise.reject(new Error("boom"))
        : Promise.resolve(result)
    }
    return Promise.resolve({})
  })
}

function renderWorkspace(
  props: Partial<Parameters<typeof ProjectWorkspace>[0]> = {},
) {
  return render(
    <ProjectWorkspace
      project="darkmem"
      tab="artifacts"
      onTabChange={vi.fn()}
      {...props}
    />,
    { wrapper },
  )
}

/** Mirrors the route's own render: `key={project}` forces React to discard
 *  the whole ProjectWorkspace instance on a project switch, rather than
 *  re-rendering the same one in place — see
 *  `src/routes/_authenticated/projects_.$project.tsx`. `withKey=false` lets
 *  the mutation run reproduce the pre-fix behaviour to prove this test can
 *  fail. */
function ProjectSwitcher({
  initial,
  next,
  withKey = true,
}: {
  initial: string
  next: string
  withKey?: boolean
}) {
  const [project, setProject] = useState(initial)
  return (
    <>
      <button type="button" onClick={() => setProject(next)}>
        switch project
      </button>
      {withKey ? (
        <ProjectWorkspace
          key={project}
          project={project}
          tab="artifacts"
          onTabChange={vi.fn()}
        />
      ) : (
        <ProjectWorkspace
          project={project}
          tab="artifacts"
          onTabChange={vi.fn()}
        />
      )}
    </>
  )
}

afterEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
})

/** Mirrors `ROW_H` in document-outline.tsx: one rail row, which is the
 *  label's `leading-5` line box plus its `py-0.5`. */
const ROW_H = "1.5rem"

describe("project workspace — the states a reader must be able to tell apart", () => {
  it("says so when a search matched nothing, instead of rendering nothing", async () => {
    // Rendering null for zero hits makes "searched, no matches" look exactly
    // like "never searched" — the user cannot tell the feature ran.
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    await screen.findByText("design.md")

    fireEvent.change(screen.getByLabelText("search documents"), {
      target: { value: "nothing matches this" },
    })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))

    expect(await screen.findByText(/no sections matched/i)).toBeInTheDocument()
  })

  it("reports a failed search rather than falling silent", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    await screen.findByText("design.md")

    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.startsWith("/documents/search")
        ? Promise.reject(new Error("boom"))
        : Promise.resolve({ items: [DOC] }),
    )
    fireEvent.change(screen.getByLabelText("search documents"), {
      target: { value: "anything" },
    })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))

    expect(await screen.findByText(/search failed/i)).toBeInTheDocument()
  })

  it("distinguishes a failed document list from an empty project", async () => {
    // An empty tree on a failed fetch reads as "this project holds nothing",
    // which is a different and much more alarming claim than "it did not load".
    mockDocuments("fail")
    renderWorkspace()

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
  })

  it("hands the reader the block a search hit named, not just its document", async () => {
    // Selecting the document alone drops the user at the top, losing the
    // section they matched — which is the whole value of section search.
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith("/documents/search")) {
        return Promise.resolve({
          items: [
            {
              block_id: "block-42",
              document_id: DOC.id,
              heading_path: ["Design", "Storage"],
              path_truncated: false,
              text: "the storage section",
            },
          ],
        })
      }
      return Promise.resolve({ items: [DOC] })
    })
    renderWorkspace()
    await screen.findByText("design.md")

    fireEvent.change(screen.getByLabelText("search documents"), {
      target: { value: "storage" },
    })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))

    fireEvent.click(await screen.findByText("the storage section"))
    await waitFor(() =>
      expect(
        screen.getByText(`reader:${DOC.id}:focus=block-42`),
      ).toBeInTheDocument(),
    )
  })
})

describe("project workspace — selection identity", () => {
  it("follows the selected document when its uri changes under it", async () => {
    // The selection used to be a snapshot object, so a move left the
    // breadcrumbs rendering the path the document no longer had.
    const first = { ...DOC, id: "d1", title: "A", uri: "old/a.md" }
    const moved = { ...DOC, id: "d1", title: "A", uri: "new/a.md" }

    mockDocuments({ items: [first] })
    renderWorkspace()

    await userEvent.click(await screen.findByText("a.md"))
    const crumbs = () => screen.getByLabelText("document path")
    expect(within(crumbs()).getByText(/old/)).toBeInTheDocument()

    // Simulates what a real rename/move mutation does on success: the same
    // ProjectWorkspace instance stays mounted and its document list
    // refetches under it, rather than the tree remounting.
    mockDocuments({ items: [moved] })
    await lastQueryClient?.invalidateQueries({
      queryKey: ["documentsAll", "darkmem"],
    })

    await waitFor(() =>
      expect(within(crumbs()).getByText(/new/)).toBeInTheDocument(),
    )
    expect(within(crumbs()).queryByText(/old/)).not.toBeInTheDocument()
  })
})

describe("project workspace — layout", () => {
  it("gives the tree and reader a draggable split", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    await screen.findByText("design.md")
    // The handle is the affordance; without it the panes are a fixed w-72 rail.
    // The library gives it role="separator" with aria-orientation (verified in
    // dist/chunk-ZU5NS2PO.js), so assert the accessible role, not a data
    // attribute that could change with a bundler bump.
    expect(await screen.findByRole("separator")).toBeInTheDocument()
  })

  it("names where the open document lives", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    // DOC.uri is "notes/design.md"; both segments must be readable.
    const crumbs = await screen.findByLabelText("document path")
    expect(crumbs).toHaveTextContent("notes")
    expect(crumbs).toHaveTextContent("design.md")
  })

  it("marks only the open document as the current page, with valid list nesting", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    const crumbs = await screen.findByLabelText("document path")
    const current = crumbs.querySelectorAll('[aria-current="page"]')
    expect(current).toHaveLength(1)
    expect(current[0]).toHaveTextContent("design.md")
    expect(crumbs.querySelectorAll("li li")).toHaveLength(0)
  })

  it("shows one empty state, not two panes, when nothing is filed", async () => {
    mockDocuments({ items: [] })
    renderWorkspace()
    expect(
      await screen.findByText(/No documents filed in this project/),
    ).toBeInTheDocument()
    expect(screen.queryByText("Nothing selected")).not.toBeInTheDocument()
    expect(screen.queryByRole("separator")).not.toBeInTheDocument()
  })

  it("does not render the breadcrumb when no document is selected", async () => {
    // The reader pane itself still renders an EmptyState in this case; this
    // test is only about the breadcrumb, which must stay absent until a
    // document is picked.
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    await screen.findByText("design.md")
    expect(screen.queryByLabelText("document path")).not.toBeInTheDocument()
  })

  it("carries a height chain down to the resizable group at lg", async () => {
    // jsdom performs no layout, so this cannot verify anything renders at a
    // real pixel height -- only that the class chain the layout depends on is
    // present. Visual confirmation needs the running app.
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    await screen.findByText("design.md")

    const tabs = container.querySelector(".dr-tabs")
    expect(tabs).toHaveClass("flex", "flex-col", "lg:min-h-0", "lg:flex-1")

    // Only the active tab's panel is mounted (the library unmounts the
    // inactive one), so there is exactly one `tabpanel`.
    const artifactsPanel = container.querySelector('[role="tabpanel"]')
    expect(artifactsPanel).toHaveClass("lg:min-h-0", "lg:flex-1")

    const panelGroup = container.querySelector(".dr-resizable-panel-group")
    expect(panelGroup).toHaveClass("min-h-[60vh]", "lg:min-h-0", "lg:flex-1")
  })
})

describe("project workspace — tree expansion", () => {
  it("opens only the top level, not every folder, on first load", async () => {
    // 475 documents all expanded is the reported "hard to navigate".
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    renderWorkspace()
    expect(await screen.findByText("notes")).toBeInTheDocument()
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("restores a deeper expansion from localStorage, not just the top level", async () => {
    // The default (no selection) opens top-level folders only, so
    // "docs/planning" stays collapsed and "progress.md" is hidden -- see the
    // test above. A stored value naming that deeper folder must override the
    // default, or this test is indistinguishable from that one passing twice.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    window.localStorage.setItem(
      expansionStorageKey("darkmem"),
      JSON.stringify(["docs", "docs/planning"]),
    )
    renderWorkspace()
    expect(await screen.findByText("progress.md")).toBeInTheDocument()
  })

  it("falls back to the default expansion when localStorage holds a non-array value", async () => {
    // A corrupted or hand-edited key (e.g. "{}") must not reach the tree
    // library as `expanded`, where `.includes(...)` throws and takes the
    // pane down -- it must fall back to the same top-level default an
    // absent key produces.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    window.localStorage.setItem(
      expansionStorageKey("darkmem"),
      JSON.stringify({}),
    )
    renderWorkspace()
    expect(await screen.findByText("notes")).toBeInTheDocument()
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("writes an expansion change to localStorage", async () => {
    // Drives a real branch toggle through the UI (as document-tree.test.tsx
    // does) rather than calling onExpandedChange directly, so this covers the
    // wiring between the tree and the persisted key, not just the handler.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    renderWorkspace()
    // "docs" is open by default (top level); its child "planning" is a
    // collapsed folder -- clicking it expands it.
    await screen.findByText("planning")
    await userEvent.click(screen.getByText("planning"))

    await waitFor(() => {
      const raw = window.localStorage.getItem(expansionStorageKey("darkmem"))
      expect(raw).not.toBeNull()
      expect(JSON.parse(raw as string)).toContain("docs/planning")
    })
  })

  it("does not collapse a sibling folder that was open when a document is selected", async () => {
    // Default expansion opens every top-level folder ("notes", "docs" and
    // "src" all have children). Selecting a document under "notes" must not
    // collapse "src" -- replacing the expanded set with only the selected
    // document's own ancestor path did exactly that.
    const DOC_SRC = { ...DOC, id: "doc-src", uri: "src/readme.md" }
    mockDocuments({
      items: [
        DOC,
        { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" },
        DOC_SRC,
      ],
    })
    renderWorkspace()
    await screen.findByText("design.md")
    // "src" is a top-level folder, open by default -- its direct child is
    // visible before any selection is made.
    expect(await screen.findByText("readme.md")).toBeInTheDocument()

    await userEvent.click(screen.getByText("design.md"))

    // Selecting a document inside the sibling "notes" folder must not
    // collapse "src".
    expect(screen.getByText("readme.md")).toBeInTheDocument()
  })

  it("reveals a document inside a collapsed folder when a search hit selects it", async () => {
    // A persisted expansion (only "notes" open) is what a returning user
    // sees -- and what the search-hit selection path used to leave
    // untouched once `expanded` was non-null, so a hit inside "docs/planning"
    // selected the document with no reveal at all.
    window.localStorage.setItem(
      expansionStorageKey("darkmem"),
      JSON.stringify(["notes"]),
    )
    const DOC_2 = { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith("/documents/search")) {
        return Promise.resolve({
          items: [
            {
              block_id: "block-77",
              document_id: DOC_2.id,
              heading_path: ["Progress"],
              path_truncated: false,
              text: "progress note",
            },
          ],
        })
      }
      if (path.startsWith("/documents")) {
        return Promise.resolve({ items: [DOC, DOC_2] })
      }
      return Promise.resolve({})
    })
    renderWorkspace()
    await screen.findByText("design.md")
    // "docs/planning" is collapsed by the persisted expansion -- only
    // "notes" is open, so "docs" itself is collapsed too.
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("search documents"), {
      target: { value: "progress" },
    })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    fireEvent.click(await screen.findByText("progress note"))

    // Selecting the hit also renders a breadcrumb naming the same segment,
    // so scope to the tree row rather than the plain text, which now
    // matches twice.
    const revealed = await screen.findByRole("treeitem", {
      name: "progress.md",
    })
    expect(revealed).toBeInTheDocument()
  })

  it("lets a folder on the open document's own path stay collapsed", async () => {
    // The reveal used to be re-derived on every render and unioned into the
    // rendered set, so collapsing a folder on the selected document's path
    // was undone on the very next render and the folder sprang back open.
    // A reveal belongs to a selection *change*, not to every frame.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    renderWorkspace()

    // "docs" is a top-level folder and open by default, so "planning" is
    // already visible; opening it exposes the document to select.
    await screen.findByText("design.md")
    await userEvent.click(await screen.findByText("planning"))
    await userEvent.click(await screen.findByText("progress.md"))
    expect(
      await screen.findByRole("treeitem", { name: "progress.md" }),
    ).toBeInTheDocument()

    // Now collapse "planning" while its own document is the open one. The
    // breadcrumb names the same segment, so scope to the tree row.
    await userEvent.click(screen.getByRole("treeitem", { name: /planning/ }))

    await waitFor(() => {
      expect(
        screen.queryByRole("treeitem", { name: "progress.md" }),
      ).not.toBeInTheDocument()
    })
  })

  it("does not leak one project's expansion into another on project switch", async () => {
    // project-a has a stored deep expansion; project-b has none. Switching
    // must not carry project-a's opened-ness into project-b's tree -- the
    // route remounts ProjectWorkspace per project (key={project}) for
    // exactly this reason.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    window.localStorage.setItem(
      expansionStorageKey("project-a"),
      JSON.stringify(["docs", "docs/planning"]),
    )
    render(<ProjectSwitcher initial="project-a" next="project-b" />, {
      wrapper,
    })

    // project-a's stored expansion opens the deep folder.
    expect(await screen.findByText("progress.md")).toBeInTheDocument()

    fireEvent.click(screen.getByText("switch project"))

    // project-b has no stored value, so it falls back to its own default
    // (top-level folders only) -- "docs/planning" stays collapsed and
    // project-a's expansion did not leak across the switch.
    await screen.findByText("notes")
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("leaks one project's expansion into another WITHOUT the remount key", async () => {
    // This is the regression the test above guards against, made real: the
    // route's `key={project}` is what discards ProjectWorkspace's own state
    // on a project switch. Without it, React reuses the same component
    // instance and project-a's `expanded` state rides straight into
    // project-b's tree.
    mockDocuments({
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }],
    })
    window.localStorage.setItem(
      expansionStorageKey("project-a"),
      JSON.stringify(["docs", "docs/planning"]),
    )
    render(
      <ProjectSwitcher initial="project-a" next="project-b" withKey={false} />,
      { wrapper },
    )

    expect(await screen.findByText("progress.md")).toBeInTheDocument()

    fireEvent.click(screen.getByText("switch project"))

    // project-b has no stored value of its own, but the un-keyed instance
    // never re-initialised its `expanded` state, so project-a's deep
    // expansion is still in effect.
    await screen.findByText("notes")
    expect(screen.getByText("progress.md")).toBeInTheDocument()
  })
})

describe("project workspace — the reader's own chrome", () => {
  it("keeps the path and the toolbar with the reader as it scrolls", async () => {
    // jsdom performs no layout, so this asserts the class chain the sticky
    // header depends on, not a rendered position. A long document otherwise
    // scrolls its own identity and every action off the top.
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))

    const crumbs = await screen.findByLabelText("document path")
    const bar = crumbs.closest("div.sticky")
    expect(bar).not.toBeNull()
    expect(bar).toHaveClass("sticky", "top-0")
    // The toolbar rides the same bar, not a separate row below it.
    expect(bar).toContainElement(
      screen.getByRole("button", { name: /^edit$/i }),
    )
  })

  it("parks the outline in a sticky rail and jumps the reader to a heading", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))

    const outline = await screen.findByLabelText("document outline")
    const rail = outline.closest("aside")
    expect(rail).toHaveClass("sticky", "self-start")

    // The jump is a callback carrying the block id, never an `#id` anchor:
    // two readers can be mounted and block ids are unique per document.
    fireEvent.click(screen.getByRole("button", { name: "Storage" }))
    await waitFor(() =>
      expect(
        screen.getByText(`reader:${DOC.id}:focus=block-h2`),
      ).toBeInTheDocument(),
    )
  })
})

describe("project workspace — the two scrollbars that used to overlap", () => {
  it("reserves the reader scrollbar's gutter so it does not paint over the outline", async () => {
    // The bar is `absolute right-0 w-2.5` on the ScrollArea ROOT while the
    // viewport is inset by the root's padding. With no right padding the bar
    // is drawn over whatever the scrolling content puts at that edge, which
    // is the outline rail.
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))

    const readerScroller = container.querySelector(
      '[data-panel-id="reader"] .dr-scroll-area',
    )
    expect(readerScroller).toHaveClass("pr-3")

    const treeScroller = container.querySelector(
      '[data-panel-id="tree"] .dr-scroll-area',
    )
    expect(treeScroller).toHaveClass("pr-3")
  })

  it("gives the outline no VISIBLE scroller of its own", async () => {
    // A capped, overflowing rail put a SECOND scrollbar a few pixels from the
    // reader's, each scrolling something different. The rail still scrolls --
    // it has to, to follow a long document -- but it drives itself, so its bar
    // is hidden rather than offered as a control nobody needs to touch.
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))

    const nav = await screen.findByLabelText("document outline")
    const aside = nav.closest("aside")
    // Bounded, or the rail has nothing to scroll within.
    expect(aside!.className).toMatch(/max-h-/)
    const scroller = nav.querySelector(".overflow-y-auto")
    expect(scroller).not.toBeNull()
    expect(scroller!.className).toMatch(/scrollbar-width:none/)
  })

  it("renders each heading as a timeline item", async () => {
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))

    await screen.findByLabelText("document outline")
    // Two headings are mocked for this document.
    expect(container.querySelectorAll(".dr-timeline-item")).toHaveLength(2)
    // The marker follows the READER's reported position, not the last click:
    // one is a standing position, the other a one-off jump.
    expect(
      container.querySelectorAll(
        '.dr-timeline-indicator[data-status="current"]',
      ),
    ).toHaveLength(0)
    fireEvent.click(screen.getByRole("button", { name: "report heading" }))
    await waitFor(() =>
      expect(
        container.querySelectorAll(
          '.dr-timeline-indicator[data-status="current"]',
        ),
      ).toHaveLength(1),
    )
    expect(
      container.querySelector('[data-outline-block="block-h2"]'),
    ).toHaveClass("text-primary-text")
  })

  it("marks nothing when the reader reports no heading", async () => {
    // A document with no headings has no current section. Leaving the last
    // one marked would point the rail at a section of the previous document.
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    await screen.findByLabelText("document outline")

    fireEvent.click(screen.getByRole("button", { name: "report heading" }))
    await waitFor(() =>
      expect(
        container.querySelectorAll(
          '.dr-timeline-indicator[data-status="current"]',
        ),
      ).toHaveLength(1),
    )
  })

  it("keeps the rail's own scroller invisible", async () => {
    // The rail is driven by the document's scroll and by clicks, so a bar
    // here would be a control that never needs using, sitting beside the
    // reader's bar that does.
    mockDocuments({ items: [DOC] })
    const outline = await (async () => {
      renderWorkspace()
      fireEvent.click(await screen.findByText("design.md"))
      return screen.findByLabelText("document outline")
    })()
    const scroller = outline.querySelector(".overflow-y-auto")
    expect(scroller).not.toBeNull()
    expect(scroller!.className).toMatch(/scrollbar-width:none/)
  })

  it("aligns every dot with its own label and with the other dots", async () => {
    // Two failures, one cause: each `TimelineItem` is its own grid whose rail
    // column is as wide as its own indicator, and the indicator's own box
    // height is what decides where the dot sits vertically. Sizing the
    // indicator per level therefore put the dots on four different x
    // positions AND parked each one against the top of its label. The dot is
    // an inner disc now: one fixed indicator box at every level, one row
    // height the label's line box is held to.
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    await screen.findByLabelText("document outline")

    const rail = container.querySelector(".dr-timeline") as HTMLElement
    expect(rail.style.getPropertyValue("--timeline-dot-size")).not.toBe("")

    for (const item of container.querySelectorAll(".dr-timeline-item")) {
      // No per-item rail width: that is what made the column ragged.
      expect(
        (item as HTMLElement).style.getPropertyValue("--timeline-dot-size"),
      ).toBe("")
      const indicator = item.querySelector(
        ".dr-timeline-indicator",
      ) as HTMLElement
      // One box height at every level, with the disc centred inside it.
      expect(indicator.style.height).toBe(ROW_H)
      expect(indicator.querySelector("span[aria-hidden]")).not.toBeNull()
      // The label's line box is pinned so a `text-xs` level cannot drift
      // against a dot centred for a `text-sm` one.
      expect(item.querySelector("button")!.className).toContain("leading-5")
    }
  })

  it("runs the connector from dot centre to dot centre", async () => {
    // The library's connector starts under the indicator, which is unbroken
    // only while the dot fills the whole row. With the dot centred beside its
    // label that leaves a gap above and below every marker, so the connector
    // spans both grid rows and hangs half a row below its own.
    mockDocuments({ items: [DOC] })
    const { container } = renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    await screen.findByLabelText("document outline")

    const connectors = container.querySelectorAll(".dr-timeline-connector")
    expect(connectors.length).toBeGreaterThan(0)
    for (const connector of connectors) {
      expect(connector.className).toContain("[grid-row:1_/_3]")
      // jsdom folds the `calc()` the component writes, so the assertion is on
      // the folded pair: down by half a row, back up by the same half.
      const style = (connector as HTMLElement).style
      const half = Number.parseFloat(ROW_H) / 2
      expect(style.marginTop).toContain(`${half}rem`)
      expect(style.marginBottom).toContain(`-${half}rem`)
    }
  })

  it("differentiates heading levels on more than indentation", async () => {
    // Indentation alone does not survive truncation: a long h3 and a long h1
    // both become an ellipsis at the same width.
    mockDocuments({ items: [DOC] })
    renderWorkspace()
    fireEvent.click(await screen.findByText("design.md"))
    await screen.findByLabelText("document outline")

    // The mocked outline is one level-1 and one level-2 heading.
    const h1 = screen.getByRole("button", { name: "Design notes" })
    const h2 = screen.getByRole("button", { name: "Storage" })
    expect(h1.className).not.toEqual(h2.className)
    expect(h1.style.paddingLeft).not.toEqual(h2.style.paddingLeft)
  })
})

/** The ledger the progress corpus looks for. Its presence is what makes the
 *  corpus fetch document contents at all, so it is what lets a test tell an
 *  inert scan from a skipped one. */
const LEDGER = {
  id: "22222222-2222-2222-2222-222222222222",
  title: "progress",
  uri: "docs/planning/progress.md",
  source_type: "note",
  project: "darkmem",
  block_count: 1,
}

function contentReads() {
  return vi
    .mocked(apiFetch)
    .mock.calls.filter(([path]) =>
      String(path).includes("include_content=true"),
    )
}

describe("project workspace — the corpus browser's own surface", () => {
  it("runs the progress corpus scan the Progress tab reads", async () => {
    mockDocuments({ items: [DOC, LEDGER] })
    renderWorkspace()
    await screen.findByText("design.md")

    expect(screen.getByRole("tab", { name: /progress/i })).toBeInTheDocument()
    // The corpus scan is the Progress tab's data layer.
    await waitFor(() => expect(contentReads().length).toBeGreaterThan(0))
  })

  // Rendered at `tab="progress"` on purpose: darkraise-ui's TabsContent wraps
  // its panel in `Presence` with `present: isSelected`, so an unselected panel
  // renders null on the first pass.
  it("renders the progress panel", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace({ tab: "progress", workstream: "plan-a" })

    expect(await screen.findByText("work-log-panel:plan-a")).toBeInTheDocument()
    // The ledger path convention no longer appears in the board's empty state.
    expect(screen.queryByText(/planning\/progress\.md/)).toBeNull()
  })

  it("opens a document a workstream links to in the Artifacts tab", async () => {
    mockDocuments({ items: [DOC] })
    const onTabChange = vi.fn()
    renderWorkspace({ tab: "progress", onTabChange })
    await screen.findByText("work-log-panel:none")

    // The document list loads asynchronously; a click before it lands is the
    // not-filed branch, so retry the click until the list is there.
    await waitFor(() => {
      fireEvent.click(screen.getByRole("button", { name: "open design" }))
      expect(onTabChange).toHaveBeenCalledWith("artifacts")
    })
  })

  it("says the document list is loading rather than calling a link unfiled", async () => {
    vi.mocked(apiFetch).mockImplementation(() => new Promise(() => {}))
    const onTabChange = vi.fn()
    vi.mocked(toast.error).mockClear()
    renderWorkspace({ tab: "progress", onTabChange })
    await screen.findByText("work-log-panel:none")

    fireEvent.click(screen.getByRole("button", { name: "open design" }))
    expect(onTabChange).not.toHaveBeenCalled()
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "The document list is still loading; try again in a moment",
    )
  })

  it("names a linked document that is not filed instead of switching tabs", async () => {
    mockDocuments({ items: [DOC] })
    const onTabChange = vi.fn()
    vi.mocked(toast.error).mockClear()
    renderWorkspace({ tab: "progress", onTabChange })
    await screen.findByText("work-log-panel:none")

    // Clicked until the list lands; before that the answer is "still loading".
    await waitFor(() => {
      fireEvent.click(screen.getByRole("button", { name: "open missing" }))
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "notes/missing.md is not filed in this project",
      )
    })
    expect(onTabChange).not.toHaveBeenCalled()
  })

  it("offers no create affordance in an empty tree", async () => {
    // The corpus browser has no create verb at all.
    mockDocuments({ items: [] })
    renderWorkspace()

    expect(await screen.findByText(/no documents filed/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /new note/i })).toBeNull()
  })
})

describe("project workspace — the reveal after a uri change", () => {
  afterEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it("reveals the new folder after a document's uri changes under it", async () => {
    // `revealedFor` used to be keyed on the id alone, which is a second
    // snapshot: after a move the effect returned early and the new folder
    // stayed collapsed.
    window.localStorage.setItem(
      expansionStorageKey("darkmem"),
      JSON.stringify(["notes"]),
    )
    const OTHER = { ...DOC, id: "d2", uri: "archive/keep.md" }
    mockDocuments({ items: [DOC, OTHER] })
    renderWorkspace()
    await userEvent.click(await screen.findByText("design.md"))

    mockDocuments({ items: [{ ...DOC, uri: "archive/design.md" }, OTHER] })
    await lastQueryClient?.invalidateQueries({ queryKey: ["documentsAll"] })
    await waitFor(() =>
      expect(screen.getByLabelText("document path")).toHaveTextContent(
        "archive",
      ),
    )

    expect(
      await screen.findByRole("treeitem", { name: "design.md" }),
    ).toBeInTheDocument()
  })
})

describe("the corpus browser carries no tree management", () => {
  // `Function.length` cannot see this: the prop is a default inside one
  // destructured parameter, so it is 1 either way. The source is the only
  // observable that distinguishes a removed prop from a defaulted one.
  it("names treeManagement nowhere in its body", () => {
    expect(ProjectWorkspace.toString()).not.toContain("treeManagement")
  })

  it("renders the tab strip and the documents label", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    renderWorkspace()
    expect(
      await screen.findByRole("tab", { name: /Artifacts/i }),
    ).toBeInTheDocument()
    expect(screen.getByText("documents")).toBeInTheDocument()
  })

  it("offers no per-row actions and no create buttons", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    renderWorkspace()
    await screen.findByRole("tab", { name: /Artifacts/i })
    expect(screen.queryByText("New note")).toBeNull()
    expect(screen.queryByText("New folder")).toBeNull()
    expect(screen.queryByRole("button", { name: /^Actions for/ })).toBeNull()
  })
})
