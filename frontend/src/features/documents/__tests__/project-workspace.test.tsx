import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
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
  }: {
    documentId: string
    focusBlockId?: string | null
  }) => <div>reader:{documentId}:focus={focusBlockId ?? "none"}</div>,
}))
vi.mock("@/features/activity/components/checkpoints-tab", () => ({
  CheckpointsTab: () => <div>checkpoints-tab</div>,
}))

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

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
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
    // through to the list payload, and a DocumentListItem has no
    // `shared_entities`, so the connections panel throws on render.
    if (path.endsWith("/connections")) {
      return Promise.resolve({ items: [], horizon: true })
    }
    if (path.endsWith("/summary")) {
      return Promise.resolve(null)
    }
    if (path.startsWith("/documents")) {
      return result === "fail"
        ? Promise.reject(new Error("boom"))
        : Promise.resolve(result)
    }
    return Promise.resolve({})
  })
}

function renderWorkspace(props: Partial<Parameters<typeof ProjectWorkspace>[0]> = {}) {
  return render(
    <ProjectWorkspace project="darkmem" tab="artifacts" onTabChange={vi.fn()} {...props} />,
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
        <ProjectWorkspace project={project} tab="artifacts" onTabChange={vi.fn()} />
      )}
    </>
  )
}

afterEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
})

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
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
    renderWorkspace()
    expect(await screen.findByText("notes")).toBeInTheDocument()
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("restores a deeper expansion from localStorage, not just the top level", async () => {
    // The default (no selection) opens top-level folders only, so
    // "docs/planning" stays collapsed and "progress.md" is hidden -- see the
    // test above. A stored value naming that deeper folder must override the
    // default, or this test is indistinguishable from that one passing twice.
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
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
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
    window.localStorage.setItem(expansionStorageKey("darkmem"), JSON.stringify({}))
    renderWorkspace()
    expect(await screen.findByText("notes")).toBeInTheDocument()
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("writes an expansion change to localStorage", async () => {
    // Drives a real branch toggle through the UI (as document-tree.test.tsx
    // does) rather than calling onExpandedChange directly, so this covers the
    // wiring between the tree and the persisted key, not just the handler.
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
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
      items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }, DOC_SRC],
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
    const revealed = await screen.findByRole("treeitem", { name: "progress.md" })
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
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
    window.localStorage.setItem(
      expansionStorageKey("project-a"),
      JSON.stringify(["docs", "docs/planning"]),
    )
    render(<ProjectSwitcher initial="project-a" next="project-b" />, { wrapper })

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
    mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
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
