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

  it("warns that delete cannot be undone", async () => {
    renderActions()
    await userEvent.click(screen.getByRole("button", { name: /delete/i }))
    const dialog = await screen.findByRole("alertdialog")
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

  it("offers Edit as a button, not a Read/Edit pair", async () => {
    // A two-state toggle spends a control on "read", which is where every
    // selection already lands, and offers a choice where there is one action.
    const onModeChange = vi.fn()
    renderActions({ onModeChange })
    expect(screen.queryByRole("radio", { name: /read/i })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: /^edit$/i }))
    expect(onModeChange).toHaveBeenCalledWith("edit")
  })

  it("is the way back out of edit mode too, and says which mode it is in", async () => {
    const onModeChange = vi.fn()
    renderActions({ mode: "edit", onModeChange })
    const back = screen.getByRole("button", { name: /^read$/i })
    expect(back).toHaveAttribute("aria-pressed", "true")
    await userEvent.click(back)
    expect(onModeChange).toHaveBeenCalledWith("read")
  })

  it("names every icon-only control, so none is an unlabelled glyph", () => {
    // The toolbar is icon-only: without an accessible name each control is a
    // guess to anyone who does not recognise the glyph, and nothing at all to
    // a screen reader.
    renderActions()
    for (const name of [/^edit$/i, /^summarize$/i, /^delete$/i]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument()
    }
  })

  it("summarizes on an explicit click, never on mount", async () => {
    // It spends an LLM call, so opening a document must not fire it.
    renderActions()
    expect(summarize).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: /summarize/i }))
    expect(summarize).toHaveBeenCalledTimes(1)
  })

  it.each([
    "superpowers/registers/2026-09-23-work-log-lane.md",
    "superpowers/plans/2026-10-13-board.md",
  ])("offers no edit mode on a mirror-owned document (%s)", (uri) => {
    renderActions({ document: { ...DOC, uri } })
    expect(screen.queryByRole("button", { name: /^edit$/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument()
  })
})
