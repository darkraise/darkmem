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
})
