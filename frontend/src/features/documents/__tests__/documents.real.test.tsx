import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
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
  DocumentReader: ({
    documentId,
    focusBlockId,
  }: {
    documentId: string
    focusBlockId?: string | null
  }) => (
    <div>
      reader:{documentId}:focus={focusBlockId ?? "none"}
    </div>
  ),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { apiFetch, ApiError } from "@/lib/api"
import { DocumentActions, DocumentDetail } from "../components/document-actions"
import { ProjectWorkspace } from "../components/project-workspace"

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
  uri: "notes/sky.md",
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
      return Promise.resolve(
        overrides.list ?? { items: [DOCUMENT], horizon: true },
      )
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
      return Promise.resolve(
        overrides.connections ?? {
          items: [],
          embedded: true,
          comparable_documents: 0,
        },
      )
    }
    if (path === "/documents/qa") {
      return Promise.resolve(overrides.qa ?? WITHHELD)
    }
    if (path.endsWith("/outline")) {
      return Promise.resolve({ document_id: DOCUMENT.id, items: [] })
    }
    if (path.endsWith("/related-memories")) {
      return Promise.resolve({
        items: [],
        embedded: true,
        comparable_memories: 0,
      })
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
  fireEvent.click(await screen.findByRole("radio", { name: "Ask" }))
  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "what colour is the sky" },
  })
  fireEvent.click(screen.getByRole("button", { name: /^ask$/i }))
}

function renderWorkspace() {
  render(<ProjectWorkspace project="default" />, { wrapper })
}

function qaBody() {
  const call = vi
    .mocked(apiFetch)
    .mock.calls.find(([path]) => path === "/documents/qa")
  return JSON.parse(String(call?.[1]?.body))
}

afterEach(() => vi.clearAllMocks())

describe("ProjectWorkspace — the horizon surface", () => {
  it("renders an empty corpus honestly rather than as a failure", async () => {
    mockApi({ list: { items: [], horizon: true } })
    renderWorkspace()
    await waitFor(() =>
      expect(screen.getByText(/No documents filed/)).toBeInTheDocument(),
    )
  })

  it("renders without the project tabs when none are asked for", async () => {
    mockApi()
    renderWorkspace()
    await screen.findByText("sky.md")
    expect(screen.queryByRole("tab", { name: "Progress" })).toBeNull()
  })
})

describe("ProjectWorkspace — grounded Q&A", () => {
  it("a withheld answer says so plainly and carries no prose", async () => {
    mockApi({ qa: WITHHELD })
    renderWorkspace()
    await ask()

    await waitFor(() =>
      expect(
        screen.getByText(/Answer withheld — not grounded/),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/grounding could not be checked/),
    ).toBeInTheDocument()
    // The point of the clause: nothing answer-shaped is on the page.
    expect(screen.queryByText(/The sky is blue\./)).not.toBeInTheDocument()
  })

  it("asks across the project when no document is open", async () => {
    mockApi()
    renderWorkspace()
    await screen.findByText("sky.md")
    await ask()

    await waitFor(() => expect(qaBody()).toBeDefined())
    expect(qaBody()).toEqual({
      question: "what colour is the sky",
      project: "default",
      document_id: null,
    })
    expect(screen.getByText(/every document in default/)).toBeInTheDocument()
  })

  it("scopes the question to the open document", async () => {
    mockApi()
    renderWorkspace()
    fireEvent.click(await screen.findByText("sky.md"))
    await ask()

    await waitFor(() => expect(qaBody().document_id).toBe(DOCUMENT.id))
    expect(
      screen.getByText(/Answering from notes\/sky\.md only/),
    ).toBeInTheDocument()
  })

  it("a served answer cites each sentence and a citation opens its passage", async () => {
    mockApi({ qa: SERVED })
    renderWorkspace()
    await screen.findByText("sky.md")
    await ask()

    await waitFor(() =>
      expect(screen.getByText("The sky is blue.")).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole("button", { name: /sky\.md · 4–19/ }))
    await waitFor(() =>
      expect(
        screen.getByText(
          `reader:${DOCUMENT.id}:focus=22222222-2222-2222-2222-222222222222`,
        ),
      ).toBeInTheDocument(),
    )
  })

  it("a citation outside the loaded list stays an inert raw block id", async () => {
    mockApi({
      qa: {
        ...SERVED,
        sentences: [
          {
            text: "The sky is blue.",
            citation: {
              ...SERVED.sentences[0]!.citation,
              document_id: "elsewhere",
            },
          },
        ],
      },
    })
    renderWorkspace()
    await screen.findByText("sky.md")
    await ask()

    expect(await screen.findByText(/block 22222222 · 4–19/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /4–19/ })).toBeNull()
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
    renderWorkspace()
    await ask()

    await waitFor(() =>
      expect(
        screen.getByText(/Could not fully ground this answer/),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/1 of 2 sentences are supported/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/no citation — this sentence is not grounded/),
    ).toBeInTheDocument()
  })
})

describe("DocumentDetail — summary and connections", () => {
  it("a summary renders visibly unbadged", async () => {
    mockApi()
    render(<DocumentDetail documentId={DOCUMENT.id} />, { wrapper })

    await waitFor(() =>
      expect(
        screen.getByText("A report over one document."),
      ).toBeInTheDocument(),
    )
    expect(
      screen.queryByText(/corroborated|confirmed|verified claim badge/),
    ).toBeNull()
  })

  it("a document with no summary says one has not been generated", async () => {
    mockApi({ summary: "missing" })
    render(<DocumentDetail documentId={DOCUMENT.id} />, { wrapper })

    await waitFor(() =>
      expect(
        screen.getByText(/no summary yet/),
      ).toBeInTheDocument(),
    )
  })

  it("never asks for a summary the list says does not exist", async () => {
    // The door answers 404 for "not generated yet", and the browser logs
    // every 404 as a failed request -- so asking unconditionally put an
    // error in the console for every unsummarised document opened.
    mockApi({ summary: "missing" })
    render(<DocumentDetail documentId={DOCUMENT.id} hasSummary={false} />, {
      wrapper,
    })

    expect(await screen.findByText(/no summary yet/)).toBeInTheDocument()
    await screen.findByText(/no other documents in this project/)
    const asked = vi
      .mocked(apiFetch)
      .mock.calls.some(([path]) => String(path).endsWith("/summary"))
    expect(asked).toBe(false)
  })

  it("shows a summary just generated even though the list said none", async () => {
    // The read stays disabled until the list catches up; the generated
    // summary is seeded into its cache, which a disabled query still serves.
    mockApi()
    const base = vi.mocked(apiFetch).getMockImplementation()!
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) =>
      init?.method === "POST" && path.endsWith("/summary")
        ? Promise.resolve({
            document_id: DOCUMENT.id,
            text: "Freshly generated.",
            generated_at: "2026-10-06T00:00:00Z",
            block_count: 3,
            badged: false,
          })
        : base(path, init),
    )
    render(
      <>
        <DocumentActions
          document={{ ...DOCUMENT, has_summary: false }}
          mode="read"
          onModeChange={vi.fn()}
          onDeleted={vi.fn()}
        />
        <DocumentDetail documentId={DOCUMENT.id} hasSummary={false} />
      </>,
      { wrapper },
    )
    expect(await screen.findByText(/no summary yet/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Summarize" }))

    expect(await screen.findByText("Freshly generated.")).toBeInTheDocument()
  })

  it("the workspace hands the reader the list's has_summary", async () => {
    mockApi({
      list: { items: [{ ...DOCUMENT, has_summary: false }], horizon: true },
      summary: "missing",
    })
    renderWorkspace()
    fireEvent.click(await screen.findByText("sky.md"))

    expect(await screen.findByText(/no summary yet/)).toBeInTheDocument()
    const asked = vi
      .mocked(apiFetch)
      .mock.calls.some(([path]) => String(path).endsWith("/summary"))
    expect(asked).toBe(false)
  })

  it("a single-document project says so rather than 'still being embedded'", async () => {
    // Both `embedded: false` and `comparable_documents: 0` hold here, and the
    // arm order is what decides which sentence the reader gets. Nothing will
    // ever embed a document this project does not have, so the pending copy
    // would be permanent and false.
    mockApi({
      connections: { items: [], embedded: false, comparable_documents: 0 },
    })
    render(<DocumentDetail documentId={DOCUMENT.id} />, { wrapper })

    await waitFor(() =>
      expect(
        screen.getByText(
          /no other documents in this project to compare against/,
        ),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByText(/still being indexed/)).not.toBeInTheDocument()
  })

  it("an unembedded sibling document renders the pending copy instead", async () => {
    mockApi({
      connections: { items: [], embedded: false, comparable_documents: 2 },
    })
    render(<DocumentDetail documentId={DOCUMENT.id} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText(/still being indexed/)).toBeInTheDocument(),
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
    render(<DocumentDetail documentId={DOCUMENT.id} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText("Other notes")).toBeInTheDocument(),
    )
    expect(screen.getByText("0.612")).toBeInTheDocument()
    expect(screen.getByText("postgres tuning notes")).toBeInTheDocument()
    expect(screen.getByText("linux kernel parameters")).toBeInTheDocument()
  })
})
