import { beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { toast } from "darkraise-ui/components/sonner"
import type { BufferRow } from "@/hooks/api/use-memory-buffer-api"
import { shortId } from "@/lib/short-id"
import { FailedCapturesSection } from "../components/failed-captures-section"

function row(overrides: Partial<BufferRow> = {}): BufferRow {
  return {
    id: "0190f000-0000-7000-8000-00000000b001",
    memory_id: "0190f000-0000-7000-8000-0000abcd1234",
    memory_exists: true,
    project: "darkmem",
    source: "api",
    status: "error",
    is_stale: false,
    attempts: 5,
    max_attempts: 5,
    last_error: "value too long for type character varying(64)",
    created_at: "2026-11-20T10:00:00Z",
    claimed_at: null,
    claimed_by: null,
    token_size: null,
    content_preview: "the payments worker kept restarting",
    content_length: 35,
    ...overrides,
  }
}

const SECOND = row({
  id: "0190f000-0000-7000-8000-00000000b002",
  memory_id: "0190f000-0000-7000-8000-00000000ffff",
  memory_exists: false,
  project: "notes",
  attempts: 3,
  last_error: "embedder unreachable",
  content_preview: "we chose redis for the cache",
})

function renderSection(
  props: Partial<Parameters<typeof FailedCapturesSection>[0]> = {},
) {
  const onRequeue = vi.fn().mockResolvedValue(undefined)
  const onDiscard = vi.fn().mockResolvedValue(undefined)
  render(
    <FailedCapturesSection
      items={[row(), SECOND]}
      total={2}
      isLoading={false}
      isError={false}
      onRequeue={onRequeue}
      onDiscard={onDiscard}
      {...props}
    />,
  )
  return { onRequeue, onDiscard }
}

// The dialog keeps its node with data-state="closed" until its exit
// animation ends, which happy-dom never fires.
function dialogState(): string {
  return screen.queryByRole("alertdialog")?.getAttribute("data-state") ?? "closed"
}

function rowOf(text: string): HTMLElement {
  return screen.getByText(text).closest("[data-buffer-row]") as HTMLElement
}

beforeEach(() => {
  vi.mocked(toast.error).mockReset()
  vi.mocked(toast.success).mockReset()
})

describe("FailedCapturesSection", () => {
  it("a requeue in flight cannot be sent twice", async () => {
    let finish: () => void = () => {}
    const onRequeue = vi.fn(() => new Promise<void>((resolve) => { finish = resolve }))
    renderSection({ onRequeue })
    const first = rowOf("the payments worker kept restarting")
    const requeue = within(first).getByRole("button", { name: "Requeue" })

    await userEvent.click(requeue)
    expect(requeue).toBeDisabled()
    await userEvent.click(requeue)
    expect(onRequeue).toHaveBeenCalledTimes(1)

    finish()
    await waitFor(() => expect(requeue).toBeEnabled())
  })

  it("lists failed captures with their error", () => {
    renderSection()
    expect(screen.getByText("Failed captures")).toBeInTheDocument()
    const first = rowOf("the payments worker kept restarting")
    expect(within(first).getByText("darkmem")).toBeInTheDocument()
    expect(within(first).getByText("5 of 5 attempts")).toBeInTheDocument()
    expect(
      within(first).getByText("value too long for type character varying(64)"),
    ).toBeInTheDocument()
    const second = rowOf("we chose redis for the cache")
    expect(within(second).getByText("notes")).toBeInTheDocument()
    expect(within(second).getByText("3 of 5 attempts")).toBeInTheDocument()
    expect(within(second).getByText("embedder unreachable")).toBeInTheDocument()
    cleanup()

    const items = Array.from({ length: 200 }, (_, i) =>
      row({ id: `row-${i}`, content_preview: `capture ${i}` }),
    )
    renderSection({ items, total: 230 })
    expect(
      screen.getByText("Showing the newest 200 of 230"),
    ).toBeInTheDocument()
    cleanup()

    const { unmount } = render(
      <FailedCapturesSection
        items={[]}
        total={0}
        isLoading={false}
        isError={false}
        onRequeue={vi.fn()}
        onDiscard={vi.fn()}
      />,
    )
    expect(screen.getByText("No failed captures")).toBeInTheDocument()
    unmount()
    render(
      <FailedCapturesSection
        items={[]}
        total={0}
        isLoading={false}
        isError
        onRequeue={vi.fn()}
        onDiscard={vi.fn()}
      />,
    )
    expect(
      screen.getByText("Couldn't load failed captures"),
    ).toBeInTheDocument()
    expect(screen.queryByText("No failed captures")).not.toBeInTheDocument()
  })

  it("names the memory and deletes only on confirm", async () => {
    const user = userEvent.setup()
    const { onDiscard } = renderSection()
    const first = rowOf("the payments worker kept restarting")
    const discardButton = within(first).getByRole("button", { name: "Discard" })

    await user.click(discardButton)
    let dialog = await screen.findByRole("alertdialog")
    expect(
      within(dialog).getByText("Discard this capture?"),
    ).toBeInTheDocument()
    const description = within(dialog).getByText(/This also deletes the memory\./)
    expect(description.textContent).toContain(
      shortId("0190f000-0000-7000-8000-0000abcd1234"),
    )
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }))
    await waitFor(() => expect(dialogState()).toBe("closed"))
    expect(onDiscard).not.toHaveBeenCalled()

    await user.click(discardButton)
    dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Discard" }))
    expect(onDiscard).toHaveBeenCalledTimes(1)
    expect(onDiscard).toHaveBeenCalledWith(
      "0190f000-0000-7000-8000-00000000b001",
    )
    await waitFor(() => expect(dialogState()).toBe("closed"))
    await waitFor(() => expect(discardButton).toHaveFocus())
  })

  it("a row without a memory does not mention one", async () => {
    const user = userEvent.setup()
    renderSection()
    const second = rowOf("we chose redis for the cache")
    await user.click(within(second).getByRole("button", { name: "Discard" }))
    const dialog = await screen.findByRole("alertdialog")
    const description = within(dialog).getByText(
      "The capture is removed from the queue.",
    )
    expect(description.textContent).not.toMatch(/memory/i)
  })

  it("requeue runs at once and reports a refusal", async () => {
    const user = userEvent.setup()
    const onRequeue = vi.fn().mockRejectedValue(new Error("only a poison row"))
    renderSection({ onRequeue })
    const first = rowOf("the payments worker kept restarting")
    await user.click(within(first).getByRole("button", { name: "Requeue" }))
    expect(onRequeue).toHaveBeenCalledTimes(1)
    expect(onRequeue).toHaveBeenCalledWith(
      "0190f000-0000-7000-8000-00000000b001",
    )
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1))
    expect(
      screen.getByText("the payments worker kept restarting"),
    ).toBeInTheDocument()
  })

  it("reports a failed discard", async () => {
    const user = userEvent.setup()
    const onDiscard = vi.fn().mockRejectedValue(new Error("boom"))
    renderSection({ onDiscard })
    const first = rowOf("the payments worker kept restarting")
    await user.click(within(first).getByRole("button", { name: "Discard" }))
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Discard" }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1))
    expect(
      screen.getByText("the payments worker kept restarting"),
    ).toBeInTheDocument()
  })
})
