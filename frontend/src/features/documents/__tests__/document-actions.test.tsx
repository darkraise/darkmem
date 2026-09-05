import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { DocumentActions } from "../components/document-actions"
import type { DocumentListItem } from "@/hooks/api"

const summarize = vi.fn()
const remove = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useDocumentSummarize: () => ({ mutate: summarize, isPending: false }),
  useDocumentDelete: () => ({ mutate: remove, isPending: false }),
}))

const DOC: DocumentListItem = {
  id: "doc-1", title: "Design", uri: "docs/design.md",
  source_type: "markdown", project: "darkmem", block_count: 4,
}

function renderActions(over: Partial<Parameters<typeof DocumentActions>[0]> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <DocumentActions
        document={DOC}
        mode="read"
        onModeChange={vi.fn()}
        onDeleted={vi.fn()}
        {...over}
      />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.clearAllMocks())

describe("DocumentActions", () => {
  it("never deletes from a bare button — the confirm dialog gates it", async () => {
    renderActions()
    await userEvent.click(screen.getByRole("button", { name: /delete/i }))
    expect(remove).not.toHaveBeenCalled()
  })

  it("states what delete does beyond removing the row", async () => {
    // Deleting a document cascades its blocks and their embeddings. It
    // withdraws no provenance and expires no fact — nothing mints a fact
    // from a block, so there is none to withdraw.
    renderActions()
    await userEvent.click(screen.getByRole("button", { name: /delete/i }))
    const dialog = await screen.findByRole("alertdialog")
    expect(dialog.textContent).toMatch(/blocks/i)
    expect(dialog.textContent).toMatch(/embeddings/i)
    expect(dialog.textContent).toMatch(/cannot be undone/i)
  })

  it("deletes only after the confirm action, then tells the parent", async () => {
    const onDeleted = vi.fn()
    remove.mockImplementation((_id: string, opts: { onSuccess?: () => void }) =>
      opts.onSuccess?.(),
    )
    renderActions({ onDeleted })
    await userEvent.click(screen.getByRole("button", { name: /delete/i }))
    const dialog = await screen.findByRole("alertdialog")
    const confirm = within(dialog).getByRole("button", { name: /^delete$/i })
    await userEvent.click(confirm)

    await waitFor(() => expect(remove).toHaveBeenCalledWith("doc-1", expect.anything()))
    expect(onDeleted).toHaveBeenCalled()
  })

  it("summarizes on an explicit click, never on mount", async () => {
    // It spends an LLM call, so opening a document must not fire it.
    renderActions()
    expect(summarize).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: /summarize/i }))
    expect(summarize).toHaveBeenCalledTimes(1)
  })
})
