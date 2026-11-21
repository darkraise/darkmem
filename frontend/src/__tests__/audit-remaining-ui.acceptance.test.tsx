import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, to: _to, params: _params, ...rest }: { children?: ReactNode; [key: string]: unknown }) => (
    <a {...rest}>{children}</a>
  ),
}))

const prune = vi.fn()
const update = vi.fn()
const insert = vi.fn()
const remove = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBulkPrune: () => ({ mutate: prune }),
  useBulkSupersede: () => ({ mutate: vi.fn() }),
  useBulkConfirmDedup: () => ({ mutate: vi.fn() }),
  useUndoDreamCycle: () => ({ mutate: vi.fn() }),
  useBlockUpdate: () => ({ mutate: update }),
  useBlockInsert: () => ({ mutate: insert }),
  useBlockDelete: () => ({ mutate: remove }),
  useBlockWriteRecovery: () => ({ retry: vi.fn(), discard: vi.fn() }),
}))

const empty = { rows: [], total: 0, loading: false, error: false }
vi.mock("@/features/knowledge/use-hygiene-queue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/knowledge/use-hygiene-queue")>()),
  useHygieneLowConfidenceRows: (q: { project?: string }) => ({
    rows: [0, 1, 2].map((i) => ({
      id: `row-${i}`,
      project: q.project ?? "all",
      content_preview: `memory ${q.project ?? "all"} number ${i}`,
      confidence: 0.2,
      expires_at: null,
      status: "active",
      superseded_by: null,
      reason: "low confidence",
      created_at: "2026-07-01T00:00:00Z",
    })),
    total: 3,
    loading: false,
    error: false,
  }),
  useHygieneDuplicateRows: () => empty,
  useHygieneExpiringRows: () => empty,
  useHygieneSupersededRows: () => empty,
}))

import { HygieneQueue } from "@/features/knowledge/components/hygiene-queue"
import { BlockEditor } from "@/features/documents/components/block-editor"
import { createMutationQueue } from "@/features/documents/lib/mutation-queue"
import { ApiError } from "@/lib/api"
import type { BlockRow } from "@/hooks/api"

beforeEach(() => vi.clearAllMocks())

describe("A40: hygiene bulk actions after a project change", () => {
  it("A40: a bulk prune touches no row selected before the project change", async () => {
    const user = userEvent.setup()
    const { rerender } = render(<HygieneQueue project="alpha" />)
    await user.click(screen.getByRole("checkbox", { name: /Select memory alpha number 0/ }))
    await user.click(screen.getByRole("checkbox", { name: /Select memory alpha number 1/ }))
    rerender(<HygieneQueue project="beta" />)

    for (const box of screen.getAllByRole("checkbox")) {
      expect(box).not.toBeChecked()
    }
    const pruneButtons = screen.queryAllByRole("button", { name: /^Prune/ })
    for (const button of pruneButtons) {
      if (!(button as HTMLButtonElement).disabled) await user.click(button)
    }
    const dialog = screen.queryByRole("alertdialog")
    if (dialog) {
      const confirm = within(dialog).queryAllByRole("button").find((b) => /prune/i.test(b.textContent ?? ""))
      if (confirm) await user.click(confirm)
    }
    for (const call of prune.mock.calls) {
      const ids = JSON.stringify(call[0])
      expect(ids).not.toContain("row-0")
      expect(ids).not.toContain("row-1")
    }
  })
})

function block(over: Partial<BlockRow>): BlockRow {
  return {
    block_id: "b1",
    type: "paragraph",
    text: "body",
    order_index: 0,
    char_span: null,
    parent_id: null,
    properties: null,
    source: "body",
    ...over,
  }
}

describe("A39: a refused block write", () => {
  it("A39: keeps the typed text in the edit box and sends no queued write after it", async () => {
    update.mockImplementationOnce((_v, options) =>
      options.onError(new ApiError("block type not allowed here", 422)),
    )
    update.mockImplementation(() => {})
    const user = userEvent.setup()
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({}), block({ block_id: "b2", text: "second", order_index: 1, source: "second" })]}
      />,
    )
    await user.click(screen.getByRole("button", { name: /body/ }))
    await user.type(screen.getByRole("textbox"), " typed")
    await user.tab()
    expect(screen.getByRole("textbox")).toHaveValue("body typed")
    expect(screen.getByRole("alert")).toHaveTextContent("block type not allowed here")
    expect(update).toHaveBeenCalledTimes(1)
  })

  it("A39: the mutation queue sends nothing queued behind a refused write until the operator acts", async () => {
    const queue = createMutationQueue("h0", async () => "h1")
    const second = vi.fn(async () => ({ result: "ok", content_hash: "h3" }))
    const first = queue.enqueue(async () => {
      throw new ApiError("refused", 422)
    })
    await expect(first).rejects.toThrow("refused")
    void queue.enqueue(second)
    await new Promise((r) => setTimeout(r, 50))
    expect(second).not.toHaveBeenCalled()
  })
})
