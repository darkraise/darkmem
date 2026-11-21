import { describe, it, expect, vi } from "vitest"
import { render, screen, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query"
import type { ReactNode } from "react"

import { BlockEditor } from "../components/block-editor"
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
  useBlockWriteRecovery: () => ({ retry: vi.fn(), discard: vi.fn() }),
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
