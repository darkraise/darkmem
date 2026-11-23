import { describe, it, expect, vi } from "vitest"
import { render, screen, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query"
import { createRef, type ReactNode } from "react"

import { BlockEditor, type BlockEditorControls } from "../components/block-editor"
import type { BlockRow } from "@/hooks/api"
import { ApiError } from "@/lib/api"

// Real useMutation observers, so per-call callback semantics are TanStack's.
const pending: Array<{ resolve: () => void; reject: (e: unknown) => void }> = []
const write = () =>
  new Promise<void>((resolve, reject) => pending.push({ resolve, reject }))

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBlockUpdate: () => useMutation({ mutationFn: write }),
  useBlockInsert: () => useMutation({ mutationFn: write }),
  useBlockDelete: () => useMutation({ mutationFn: write }),
  useBlockWriteRecovery: () => ({ retry: vi.fn(), discard: vi.fn(), discardAll: vi.fn() }),
}))

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

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe("BlockEditor writes to two blocks", () => {
  it("the first block's refusal still shows after a second block is committed", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({}), block({ block_id: "b2", text: "second", source: "second", order_index: 1 })]}
      />,
      { wrapper },
    )
    await userEvent.click(screen.getByRole("button", { name: /body/ }))
    await userEvent.keyboard(" typed")
    await userEvent.click(screen.getByRole("button", { name: /second/ }))
    await userEvent.keyboard(" more")
    await userEvent.tab()
    expect(pending).toHaveLength(2)

    await act(async () => {
      pending[0]!.reject(new ApiError("stale", 409, undefined, "hash_conflict"))
      pending[1]!.resolve()
    })
    expect(await screen.findByRole("alert")).toHaveTextContent("stale")
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument()
    expect(screen.getByRole("textbox")).toHaveValue("body typed")
  })
})

describe("held writes", () => {
  const unloadCancelled = () => {
    const event = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(event)
    return event.defaultPrevented
  }

  async function editAndCommit(text: string) {
    await userEvent.click(screen.getByRole("button", { name: new RegExp(text) }))
    await userEvent.keyboard(" typed")
    await userEvent.tab()
  }

  it("a held write cancels beforeunload", async () => {
    pending.length = 0
    const { unmount } = render(
      <BlockEditor
        documentId="d1"
        blocks={[block({}), block({ block_id: "b2", text: "second", source: "second", order_index: 1 })]}
      />,
      { wrapper },
    )
    expect(unloadCancelled()).toBe(false)

    await editAndCommit("body")
    expect(pending).toHaveLength(1)
    expect(unloadCancelled()).toBe(true)

    await act(async () => {
      pending[0]!.reject(new ApiError("stale", 409, undefined, "hash_conflict"))
    })
    await screen.findByRole("alert")
    expect(unloadCancelled()).toBe(true)

    await editAndCommit("second")
    expect(unloadCancelled()).toBe(true)

    unmount()
    expect(unloadCancelled()).toBe(false)
  })

  it("reports its held-write state", async () => {
    pending.length = 0
    const onHeldWritesChange = vi.fn()
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({}), block({ block_id: "b2", text: "second", source: "second", order_index: 1 })]}
        onHeldWritesChange={onHeldWritesChange}
      />,
      { wrapper },
    )
    const last = () => onHeldWritesChange.mock.calls[onHeldWritesChange.mock.calls.length - 1]?.[0]

    await editAndCommit("body")
    expect(last()).toBe("saving")

    await act(async () => {
      pending[0]!.reject(new ApiError("stale", 409, undefined, "hash_conflict"))
    })
    await screen.findByRole("alert")
    expect(last()).toBe("refused")

    await editAndCommit("second")
    expect(last()).toBe("refused")

    await userEvent.click(screen.getByRole("button", { name: "Discard" }))
    await act(async () => {
      pending[1]!.resolve()
    })
    expect(last()).toBe("none")
  })

  it("its controls refocus the refused edit and discard it", async () => {
    pending.length = 0
    const onHeldWritesChange = vi.fn()
    const controls = createRef<BlockEditorControls>()
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({})]}
        onHeldWritesChange={onHeldWritesChange}
        controls={controls}
      />,
      { wrapper },
    )
    await editAndCommit("body")
    await act(async () => {
      pending[0]!.reject(new ApiError("stale", 409, undefined, "hash_conflict"))
    })
    await screen.findByRole("alert")

    act(() => controls.current!.restoreFocus())
    expect(screen.getByRole("textbox")).toHaveFocus()
    expect(screen.getByRole("textbox")).toHaveValue("body typed")

    act(() => controls.current!.discardHeld())
    expect(onHeldWritesChange.mock.calls[onHeldWritesChange.mock.calls.length - 1]?.[0]).toBe("none")
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })
})
