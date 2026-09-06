import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { DocumentDetail } from "../components/document-actions"

// The dialog links on to the full memory page; the router is not the subject
// here, so the link stands in as a plain anchor.
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...rest }: { children: React.ReactNode }) => (
    <a {...rest}>{children}</a>
  ),
}))

const CONNECTION = {
  document_id: "doc-2",
  title: "Storage design",
  score: 0.812,
  block_id: "block-here",
  block_text: "this document's passage",
  other_block_id: "block-there",
  other_block_text: "the other document's passage",
}

const RELATED = {
  memory_id: "mem-1",
  content: "the buffer flush claims rows FOR UPDATE SKIP LOCKED",
  memory_type: "insight",
  status: "active",
  source: "mcp",
  project: "darkmem",
  score: 0.744,
  block_id: "block-here",
  block_text: "the passage it sits near",
  span_start: null,
  span_end: null,
}

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useDocumentSummary: () => ({ isLoading: false, data: null }),
  useDocumentConnections: () => ({
    isLoading: false,
    isError: false,
    data: { items: [CONNECTION], embedded: true, comparable_documents: 4 },
  }),
  useRelatedMemories: () => ({
    isLoading: false,
    isError: false,
    data: { items: [RELATED], embedded: true, comparable_memories: 9 },
  }),
  useMemory: () => ({
    isLoading: false,
    isError: false,
    data: {
      id: "mem-1",
      content: RELATED.content,
      source: "mcp",
      source_agent: null,
      memory_type: "insight",
      importance: 0.5,
      metadata: {},
      tags: ["project/darkmem"],
      created_at: "2026-09-01T10:00:00Z",
      updated_at: "2026-09-01T10:00:00Z",
      expires_at: null,
      is_archived: false,
      status: "active",
    },
  }),
}))

function renderDetail(onOpenDocument?: (id: string, blockId: string) => void) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <DocumentDetail documentId="doc-1" onOpenDocument={onOpenDocument} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.clearAllMocks())

describe("DocumentDetail — the two panels that name another object", () => {
  it("opens a connected document at the passage that made it a connection", async () => {
    // `other_block_id` is the passage in the OTHER document. Landing on
    // `block_id` would scroll the document the reader is already on.
    const onOpenDocument = vi.fn()
    renderDetail(onOpenDocument)
    await userEvent.click(screen.getByText("Storage design"))
    expect(onOpenDocument).toHaveBeenCalledWith("doc-2", "block-there")
  })

  it("leaves the connection inert where the surface has no reader to steer", async () => {
    // The legacy documents page mounts this panel with no navigation
    // callback; offering a click that goes nowhere is worse than no click.
    renderDetail()
    expect(
      screen.queryByRole("button", { name: /Storage design/ }),
    ).not.toBeInTheDocument()
  })

  it("reads a related memory in a dialog rather than routing away", async () => {
    // The memory is evidence for the document that is open; leaving the page
    // to read it throws away the context that made it interesting.
    renderDetail()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    await userEvent.click(screen.getByText(RELATED.content))
    const dialog = await screen.findByRole("dialog")
    expect(dialog).toHaveTextContent(RELATED.content)
    // The full page is still one click on, never replaced by the dialog.
    expect(dialog).toHaveTextContent(/open the full memory/i)
  })
})
