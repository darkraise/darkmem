import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react"
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
vi.mock("@/features/documents/components/document-reader", () => ({
  DocumentReader: ({ documentId }: { documentId: string }) => (
    <div>reader:{documentId}</div>
  ),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import type { DocumentListItem } from "@/hooks/api"
import { ProjectWorkspace } from "../components/project-workspace"

const PINNED: DocumentListItem = {
  id: "d1",
  title: "Design notes",
  uri: "notes/design.md",
  source_type: "md",
  project: "darkmem",
  block_count: 3,
  pinned_at: "2026-10-01T00:00:00Z",
  tags: ["arch", "draft"],
  has_summary: false,
}
const PLAIN: DocumentListItem = {
  id: "d2",
  title: "Runbook",
  uri: "notes/runbook.md",
  source_type: "md",
  project: "darkmem",
  block_count: 2,
  pinned_at: null,
  tags: [],
  has_summary: false,
}

interface Call {
  path: string
  method: string
  body: unknown
}

let calls: Call[] = []

/** Records every call; `answer` overrides the default reply per call. */
function mockApi(
  answer: (path: string, method: string, body: unknown) => unknown = () =>
    undefined,
  items: DocumentListItem[] = [PINNED, PLAIN],
) {
  calls = []
  vi.mocked(apiFetch).mockImplementation(((
    path: string,
    init?: RequestInit,
  ) => {
    const method = init?.method ?? "GET"
    const body = init?.body ? JSON.parse(String(init.body)) : null
    calls.push({ path, method, body })
    const own = answer(path, method, body)
    if (own !== undefined) {
      return own instanceof Error ? Promise.reject(own) : Promise.resolve(own)
    }
    if (path.startsWith("/documents?")) return Promise.resolve({ items })
    if (path.startsWith("/documents/manifest")) {
      return Promise.resolve({ items: [], next_after: null })
    }
    if (path.endsWith("/connections")) {
      return Promise.resolve({
        items: [],
        embedded: true,
        comparable_documents: 0,
      })
    }
    if (path.endsWith("/related-memories")) {
      return Promise.resolve({
        items: [],
        embedded: true,
        comparable_memories: 0,
      })
    }
    if (path.endsWith("/outline")) {
      return Promise.resolve({ document_id: "d1", items: [] })
    }
    if (path === "/documents/d1") {
      return Promise.resolve({
        document_id: "d1",
        blocks: [],
        content_hash: "h1",
      })
    }
    return Promise.resolve({})
  }) as never)
}

const writes = () => calls.filter((c) => c.method !== "GET")

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function renderWorkspace() {
  render(<ProjectWorkspace project="darkmem" />, { wrapper })
}

afterEach(() => vi.clearAllMocks())

describe("document metadata is visible", () => {
  it("marks a pinned document in the tree and shows pin and tags by the path", async () => {
    mockApi()
    renderWorkspace()
    const row = await screen.findByRole("treeitem", { name: /design\.md/ })
    expect(within(row).getByText("(pinned)")).toBeInTheDocument()
    expect(
      within(screen.getByRole("treeitem", { name: "runbook.md" })).queryByText(
        "(pinned)",
      ),
    ).toBeNull()

    fireEvent.click(row)
    expect(await screen.findByText("Pinned")).toBeInTheDocument()
    expect(screen.getByText("arch")).toBeInTheDocument()
    expect(screen.getByText("draft")).toBeInTheDocument()
  })
})

describe("the Details dialog", () => {
  async function openDetails() {
    renderWorkspace()
    fireEvent.click(await screen.findByRole("treeitem", { name: /design\.md/ }))
    fireEvent.click(await screen.findByRole("button", { name: "Details" }))
    return screen.findByRole("dialog")
  }

  it("sends only the fields that changed", async () => {
    mockApi((_path, method) =>
      method === "PATCH" ? { document_id: "d1" } : undefined,
    )
    const dialog = await openDetails()
    fireEvent.change(within(dialog).getByLabelText("Title"), {
      target: { value: "Design" },
    })
    fireEvent.click(within(dialog).getByRole("switch"))
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))

    await waitFor(() => expect(writes()).toHaveLength(1))
    expect(writes()[0]).toEqual({
      path: "/documents/d1",
      method: "PATCH",
      body: { title: "Design", pinned: false },
    })
  })

  it("moves under the read hash and says plainly when the path is taken", async () => {
    mockApi((_path, method) =>
      method === "PATCH"
        ? new ApiError(
            "another document in this project already holds the uri 'notes/runbook.md'",
            409,
          )
        : undefined,
    )
    const dialog = await openDetails()
    // The blocks read the reader makes is what the hash comes from.
    await waitFor(() =>
      expect(calls.some((c) => c.path === "/documents/d1")).toBe(true),
    )
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "notes/runbook.md" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))

    expect(
      await within(dialog).findByText(
        "Another document in this project is already filed at notes/runbook.md.",
      ),
    ).toBeInTheDocument()
    expect(writes()[0]!.body).toEqual({
      uri: "notes/runbook.md",
      expected_hash: "h1",
    })
  })

  it("explains a stale hash rather than echoing the server", async () => {
    mockApi((_path, method) =>
      method === "PATCH"
        ? new ApiError(
            "expected_hash h1 does not match the document's current content_hash h2",
            409,
          )
        : undefined,
    )
    const dialog = await openDetails()
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "archive/design.md" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))
    expect(
      await within(dialog).findByText(/changed since you opened it/),
    ).toBeInTheDocument()
  })

  it("refuses a path the folder actions could not address", async () => {
    mockApi()
    const dialog = await openDetails()
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "/notes/design.md" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))
    expect(
      await within(dialog).findByText("A path cannot start with a slash."),
    ).toBeInTheDocument()
    expect(writes()).toHaveLength(0)
  })
})

describe("New document", () => {
  async function openCreate() {
    fireEvent.click(await screen.findByRole("button", { name: "New document" }))
    return screen.findByRole("dialog")
  }

  it("refuses a path the tree already shows, without posting", async () => {
    mockApi()
    renderWorkspace()
    await screen.findByRole("treeitem", { name: /design\.md/ })
    const dialog = await openCreate()
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "notes/runbook.md" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Create" }))
    expect(
      await within(dialog).findByText(/already filed at notes\/runbook\.md/),
    ).toBeInTheDocument()
    expect(writes()).toHaveLength(0)
  })

  it("refuses a path the server holds though the list does not", async () => {
    // POST /documents is an upsert: aimed at a taken path it would replace
    // that document's content.
    mockApi((path) =>
      path.startsWith("/documents/manifest")
        ? { items: [{ uri: "notes/late.md" }], next_after: null }
        : undefined,
    )
    renderWorkspace()
    await screen.findByRole("treeitem", { name: /design\.md/ })
    const dialog = await openCreate()
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "notes/late.md" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Create" }))
    expect(
      await within(dialog).findByText(/already filed at notes\/late\.md/),
    ).toBeInTheDocument()
    expect(writes()).toHaveLength(0)
  })

  it("files the markdown it was given and opens it", async () => {
    mockApi((path, method) =>
      path === "/documents" && method === "POST"
        ? { document_id: "d9", outcome: "created" }
        : undefined,
    )
    renderWorkspace()
    await screen.findByRole("treeitem", { name: /design\.md/ })
    const dialog = await openCreate()
    fireEvent.change(within(dialog).getByLabelText("Path"), {
      target: { value: "notes/new.md" },
    })
    fireEvent.change(within(dialog).getByLabelText("Title"), {
      target: { value: "New one" },
    })
    fireEvent.change(within(dialog).getByLabelText("Content"), {
      target: { value: "# New one\n\nBody." },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Create" }))

    await waitFor(() => expect(writes()).toHaveLength(1))
    expect(writes()[0]).toEqual({
      path: "/documents",
      method: "POST",
      body: {
        project: "darkmem",
        uri: "notes/new.md",
        title: "New one",
        content: "# New one\n\nBody.",
      },
    })
    expect(toast.success).toHaveBeenCalledWith("Filed notes/new.md")
  })

  it("is offered in an empty project", async () => {
    mockApi(undefined, [])
    renderWorkspace()
    expect(
      await screen.findByRole("button", { name: "New document" }),
    ).toBeInTheDocument()
  })
})

describe("folder actions", () => {
  async function folderMenu(item: string) {
    renderWorkspace()
    fireEvent.click(
      await screen.findByRole("button", { name: "Actions for notes" }),
    )
    fireEvent.click(within(screen.getByRole("menu")).getByText(item))
  }

  it("renames a folder through the subtree rename and reports the count", async () => {
    mockApi((path) =>
      path === "/documents/rename" ? { renamed: 2 } : undefined,
    )
    await folderMenu("Rename folder")
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText(/\(2\)/)).toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText("New folder path"), {
      target: { value: "archive" },
    })
    fireEvent.click(within(dialog).getByRole("button", { name: "Rename" }))

    await waitFor(() => expect(writes()).toHaveLength(1))
    expect(writes()[0]).toEqual({
      path: "/documents/rename",
      method: "POST",
      body: {
        project: "darkmem",
        uri_prefix: "notes",
        new_uri_prefix: "archive",
      },
    })
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Moved 2 documents to archive",
      ),
    )
  })

  it("confirms a folder delete with the count it will remove", async () => {
    mockApi((path) =>
      path === "/documents/delete" ? { deleted: 2 } : undefined,
    )
    await folderMenu("Delete folder")
    const confirm = await screen.findByRole("alertdialog")
    expect(
      within(confirm).getByText(/deletes 2 documents under notes/),
    ).toBeInTheDocument()
    fireEvent.click(
      within(confirm).getByRole("button", { name: "Delete 2 documents" }),
    )

    await waitFor(() => expect(writes()).toHaveLength(1))
    expect(writes()[0]).toEqual({
      path: "/documents/delete",
      method: "POST",
      body: { project: "darkmem", uri_prefix: "notes" },
    })
  })

  it("refuses a folder whose documents the prefix cannot all reach", async () => {
    // `/notes/odd.md` sits in the tree's `notes` folder, but the server's
    // prefix predicate never matches a leading-slash uri.
    mockApi(undefined, [PINNED, { ...PLAIN, id: "d3", uri: "/notes/odd.md" }])
    await folderMenu("Delete folder")
    const confirm = await screen.findByRole("alertdialog")
    expect(within(confirm).getByText(/irregular paths/)).toBeInTheDocument()
    expect(
      within(confirm).queryByRole("button", { name: /^Delete \d/ }),
    ).toBeNull()
  })
})

describe("drag-to-move", () => {
  it("mounts the tree's drag layer", async () => {
    // The layer only mounts with an `onMove`; the workspace passed none.
    mockApi()
    renderWorkspace()
    await screen.findByRole("treeitem", { name: /design\.md/ })
    expect(document.querySelector("[data-drop-root]")).not.toBeNull()
  })
})
