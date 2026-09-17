import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ComponentType, ReactNode } from "react"
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

import { apiFetch, ApiError } from "@/lib/api"
import type { ProjectSummary } from "@/hooks/api"
import { DocumentsView } from "../components/documents-view"
import { Route as DocumentsRoute } from "../../../routes/_authenticated/documents"

/**
 * TH1.16's four done-when clauses, each tested for the reason it exists.
 *
 * The withheld case is the one that matters: a client that rendered the answer
 * and appended a caveat would satisfy "shows the outcome" while serving
 * ungrounded prose. So the assertion is that the prose is *absent*, not that a
 * label is present alongside it.
 */

const DOCUMENT = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Design notes",
  uri: "file:///notes.md",
  source_type: "note",
  project: "default",
  block_count: 3,
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function mockApi(overrides: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/documents?") || path === "/documents") {
      return Promise.resolve(overrides.list ?? { items: [DOCUMENT], horizon: true })
    }
    if (path.endsWith("/summary")) {
      if (overrides.summary === "missing") {
        return Promise.reject(new ApiError("not found", 404))
      }
      return Promise.resolve(
        overrides.summary ?? {
          document_id: DOCUMENT.id,
          text: "A report over one document.",
          generated_at: "2026-08-16T00:00:00Z",
          block_count: 3,
          badged: false,
        },
      )
    }
    if (path.endsWith("/connections")) {
      return Promise.resolve(overrides.connections ?? {
        items: [],
        embedded: true,
        comparable_documents: 0,
      })
    }
    if (path === "/documents/qa") {
      return Promise.resolve(overrides.qa ?? WITHHELD)
    }
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

const WITHHELD = {
  question: "q",
  outcome: "withheld",
  grounded: false,
  label: "answer withheld: not grounded",
  entailed: 0,
  total: 1,
  judged: false,
  reason: "no faithfulness record on this branch",
  sentences: [],
  horizon: true,
}

const SERVED = {
  question: "q",
  outcome: "served",
  grounded: true,
  label: null,
  entailed: 1,
  total: 1,
  judged: true,
  reason: null,
  sentences: [
    {
      text: "The sky is blue.",
      citation: {
        block_id: "22222222-2222-2222-2222-222222222222",
        document_id: DOCUMENT.id,
        span_start: 4,
        span_end: 19,
      },
    },
  ],
  horizon: true,
}

async function ask() {
  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "what colour is the sky" },
  })
  fireEvent.click(screen.getByRole("button", { name: /Ask/ }))
}

function renderRoute(_path: string) {
  const Component = DocumentsRoute.options.component as ComponentType
  render(<Component />, { wrapper })
}

function mockProjects(
  rows: Array<
    Pick<ProjectSummary, "name" | "kind" | "document_count">
  >,
) {
  const full: ProjectSummary[] = rows.map((row) => ({
    memory_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: null,
    ...row,
  }))
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/projects") return Promise.resolve(full)
    if (path.startsWith("/documents")) {
      return Promise.resolve({ items: [], horizon: true })
    }
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

afterEach(() => vi.clearAllMocks())

// The list became a uri-segment tree (increment 4): leaves render the path's
// last segment, so a document titled "Design notes" filed at
// file:///notes.md is selected by "notes.md". The title still renders in the
// detail panel below -- the tree is a path view, deliberately.

describe("DocumentsView — the horizon surface", () => {
  it("labels itself horizon in the IA", async () => {
    mockApi()
    render(<DocumentsView />, { wrapper })
    expect(screen.getByText("horizon")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText("notes.md")).toBeInTheDocument())
  })

  it("renders an empty corpus honestly rather than as a failure", async () => {
    mockApi({ list: { items: [], horizon: true } })
    render(<DocumentsView />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/No documents filed/)).toBeInTheDocument(),
    )
  })
})

describe("DocumentsView — grounded Q&A", () => {
  it("a withheld answer says so plainly and carries no prose", async () => {
    mockApi({ qa: WITHHELD })
    render(<DocumentsView />, { wrapper })
    await ask()

    await waitFor(() =>
      expect(screen.getByText(/Answer withheld — not grounded/)).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/faithfulness judge is not qualified/),
    ).toBeInTheDocument()
    // The point of the clause: nothing answer-shaped is on the page.
    expect(screen.queryByText(/The sky is blue\./)).not.toBeInTheDocument()
  })

  it("a served answer shows every sentence with its block span", async () => {
    mockApi({ qa: SERVED })
    render(<DocumentsView />, { wrapper })
    await ask()

    await waitFor(() =>
      expect(screen.getByText("The sky is blue.")).toBeInTheDocument(),
    )
    expect(screen.getByText(/block 22222222 · 4–19/)).toBeInTheDocument()
  })

  it("a labelled answer names how far short it fell and marks the uncited sentence", async () => {
    mockApi({
      qa: {
        ...SERVED,
        outcome: "labelled",
        grounded: false,
        label: "could not fully ground this answer",
        entailed: 1,
        total: 2,
        sentences: [
          ...SERVED.sentences,
          { text: "Unsupported claim.", citation: null },
        ],
      },
    })
    render(<DocumentsView />, { wrapper })
    await ask()

    await waitFor(() =>
      expect(
        screen.getByText(/Could not fully ground this answer/),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText(/1 of 2 sentences are supported/)).toBeInTheDocument()
    expect(
      screen.getByText(/no citation — this sentence is not grounded/),
    ).toBeInTheDocument()
  })
})

describe("DocumentsView — summary and connections", () => {
  it("a summary renders visibly unbadged", async () => {
    mockApi()
    render(<DocumentsView />, { wrapper })
    fireEvent.click(await screen.findByText("notes.md"))

    await waitFor(() =>
      expect(screen.getByText("A report over one document.")).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/not a verified claim, and never/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/corroborated|confirmed|verified claim badge/)).toBeNull()
  })

  it("a document with no summary says one has not been generated", async () => {
    mockApi({ summary: "missing" })
    render(<DocumentsView />, { wrapper })
    fireEvent.click(await screen.findByText("notes.md"))

    await waitFor(() =>
      expect(
        screen.getByText(/no summary has been generated/),
      ).toBeInTheDocument(),
    )
  })

  it("a single-document project says so rather than 'still being embedded'", async () => {
    // Both `embedded: false` and `comparable_documents: 0` hold here, and the
    // arm order is what decides which sentence the reader gets. Nothing will
    // ever embed a document this project does not have, so the pending copy
    // would be permanent and false.
    mockApi({
      connections: { items: [], embedded: false, comparable_documents: 0 },
    })
    render(<DocumentsView />, { wrapper })
    fireEvent.click(await screen.findByText("notes.md"))

    await waitFor(() =>
      expect(
        screen.getByText(/no other documents in this project to compare against/),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByText(/still being embedded/)).not.toBeInTheDocument()
  })

  it("an unembedded sibling document renders the pending copy instead", async () => {
    mockApi({
      connections: { items: [], embedded: false, comparable_documents: 2 },
    })
    render(<DocumentsView />, { wrapper })
    fireEvent.click(await screen.findByText("notes.md"))

    await waitFor(() =>
      expect(screen.getByText(/still being embedded/)).toBeInTheDocument(),
    )
  })

  it("connections render the matching passages and a raw score", async () => {
    mockApi({
      connections: {
        items: [
          {
            document_id: "33333333-3333-3333-3333-333333333333",
            title: "Other notes",
            score: 0.6123,
            block_id: "44444444-4444-4444-4444-444444444444",
            block_text: "postgres tuning notes",
            other_block_id: "55555555-5555-5555-5555-555555555555",
            other_block_text: "linux kernel parameters",
          },
        ],
        embedded: true,
        comparable_documents: 4,
      },
    })
    render(<DocumentsView />, { wrapper })
    fireEvent.click(await screen.findByText("notes.md"))

    await waitFor(() => expect(screen.getByText("Other notes")).toBeInTheDocument())
    expect(screen.getByText("0.612")).toBeInTheDocument()
    expect(screen.getByText("postgres tuning notes")).toBeInTheDocument()
    expect(screen.getByText("linux kernel parameters")).toBeInTheDocument()
  })
})

describe("/documents route — project picker", () => {
  it("defaults to a project that actually holds documents", async () => {
    mockProjects([
      { name: "empty", kind: "project", document_count: 0 },
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute("/documents")
    // `useProjects` orders busiest-first by a different measure, so the
    // default needs its own document_count filter.
    expect(await screen.findByRole("combobox")).toHaveTextContent("darkmem")
  })

  it("keeps the personal space out of the picker", async () => {
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute("/documents")
    await userEvent.click(await screen.findByRole("combobox"))
    // A positive assertion too: the dropdown genuinely opened and listed the
    // eligible project, rather than this test passing because it never did.
    expect(await screen.findByRole("option", { name: "darkmem" })).toBeInTheDocument()
    expect(screen.queryByText("notes")).toBeNull()
  })

  it("reports a failed project read instead of an empty corpus", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute("/documents")
    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()
  })

  it("says so when the corpus holds no non-personal project", async () => {
    mockProjects([{ name: "notes", kind: "personal", document_count: 3 }])
    renderRoute("/documents")
    expect(await screen.findByText(/no project holds/i)).toBeInTheDocument()
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()
  })
})
