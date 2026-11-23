import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock("@/features/auth", () => ({
  useAuthStore: { getState: () => ({ logout: vi.fn(), setAuthenticated: vi.fn() }) },
}))

const update = vi.fn()
const insert = vi.fn()
const remove = vi.fn()
const blocksState: { data: { blocks: unknown[] } } = { data: { blocks: [] } }
const asAsync =
  (fn: (value: unknown, options: { onSuccess: (v?: unknown) => void; onError: (e: unknown) => void }) => void) =>
  (value: unknown) =>
    new Promise((onSuccess, onError) => fn(value, { onSuccess, onError }))

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBlockUpdate: () => ({ mutate: update, mutateAsync: asAsync(update) }),
  useBlockInsert: () => ({ mutate: insert, mutateAsync: asAsync(insert) }),
  useBlockDelete: () => ({ mutate: remove, mutateAsync: asAsync(remove) }),
  useBlockWriteRecovery: () => ({ retry: vi.fn(), discard: vi.fn(), discardAll: vi.fn() }),
  useDocumentBlocks: () => ({ isLoading: false, isError: false, data: blocksState.data }),
}))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})

import { apiFetch, ApiError } from "@/lib/api"
import { ProvidersPanel } from "@/features/settings/components/providers-panel"
import { FailedCapturesSection } from "@/features/activity/components/failed-captures-section"
import { BlockEditor } from "@/features/documents/components/block-editor"
import { EditableDocument } from "@/features/documents/components/editable-document"
import type { BlockRow } from "@/hooks/api"

function block(over: Partial<BlockRow>): BlockRow {
  return {
    block_id: "b1",
    type: "paragraph",
    text: "body text here",
    order_index: 0,
    char_span: null,
    parent_id: null,
    properties: null,
    source: "body text here",
    ...over,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  blocksState.data = { blocks: [block({})] }
})
afterEach(() => vi.unstubAllGlobals())

// ---------------------------------------------------------------- A24

describe("A24: a keyed provider whose address changed", () => {
  const PROVIDERS = {
    providers: [
      {
        name: "main-llm",
        api_kind: "openai",
        base_url: "https://api.example.com/v1",
        api_key: "***",
        used_by: ["extraction"],
        serves_verification: false,
      },
    ],
  }

  it("A24: disables Save, shows the hint, sends no request; typing a key enables Save", async () => {
    vi.mocked(apiFetch).mockImplementation(async () => PROVIDERS as never)
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <ProvidersPanel />
      </QueryClientProvider>,
    )
    fireEvent.click(await screen.findByLabelText("Edit main-llm"))
    const url = await screen.findByLabelText("main-llm base_url")
    const save = screen.getByRole("button", { name: "Save" })
    expect(screen.queryByText("The address or API kind changed. Enter the API key again.")).toBeNull()

    fireEvent.change(url, { target: { value: "https://other.example.com/v1" } })

    expect(await screen.findByText("The address or API kind changed. Enter the API key again.")).toBeInTheDocument()
    expect(save).toBeDisabled()
    fireEvent.click(save)
    const writes = () =>
      vi.mocked(apiFetch).mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === "PUT")
    expect(writes()).toHaveLength(0)

    fireEvent.change(screen.getByLabelText("main-llm api_key"), { target: { value: "sk-new-key" } })
    await waitFor(() => expect(screen.getByRole("button", { name: "Save" })).toBeEnabled())
  })
})

// ---------------------------------------------------------------- A25

describe("A25: a pending requeue", () => {
  it("A25: disables that row's Discard and Requeue until it settles", async () => {
    let settle: (v?: unknown) => void = () => {}
    const onRequeue = vi.fn(() => new Promise((resolve) => (settle = resolve)))
    const row = {
      id: "buf-1",
      content_preview: "a failed capture",
      project: "alpha",
      attempts: 3,
      max_attempts: 3,
      last_error: "boom",
      memory_exists: false,
      memory_id: null,
    }
    const user = userEvent.setup()
    render(
      <FailedCapturesSection
        items={[row as never]}
        total={1}
        isLoading={false}
        isError={false}
        onRequeue={onRequeue}
        onDiscard={vi.fn(async () => {})}
      />,
    )
    const requeue = screen.getByRole("button", { name: /Requeue/ })
    const discard = screen.getAllByRole("button", { name: /^Discard/ })[0]
    expect(requeue).toBeEnabled()
    expect(discard).toBeEnabled()

    await user.click(requeue)

    expect(onRequeue).toHaveBeenCalledWith("buf-1")
    expect(screen.getByRole("button", { name: /Requeue/ })).toBeDisabled()
    expect(screen.getAllByRole("button", { name: /^Discard/ })[0]).toBeDisabled()
    await act(async () => settle())
    await waitFor(() => expect(screen.getByRole("button", { name: /Requeue/ })).toBeEnabled())
  })
})

// ---------------------------------------------------------------- A26

describe("A26: opening a block for edit", () => {
  it("A26: puts the selection at the end of its text", async () => {
    const user = userEvent.setup()
    render(<BlockEditor documentId="d1" blocks={[block({ text: "twelve chars", source: "twelve chars" })]} />)
    await user.click(screen.getByRole("button", { name: /twelve chars/ }))
    const box = screen.getByRole("textbox") as HTMLTextAreaElement
    await waitFor(() => expect(box).toHaveFocus())
    expect(box.value).toBe("twelve chars")
    expect(box.selectionStart).toBe(12)
    expect(box.selectionEnd).toBe(12)
  })
})

// ---------------------------------------------------------------- A27 / A28

type Held = "refused" | "saving" | "none"

async function typeIntoBlock(held: Held) {
  if (held === "refused") {
    update.mockImplementation((_v, options) => options.onError(new ApiError("block type not allowed here", 422)))
  } else if (held === "saving") {
    update.mockImplementation(() => {})
  }
  const user = userEvent.setup()
  await user.click(screen.getByRole("button", { name: /body text here/ }))
  if (held !== "none") {
    await user.type(screen.getByRole("textbox"), " typed")
    await user.tab()
  }
  if (held === "refused") await screen.findByRole("alert")
  return user
}

function renderRouted() {
  const root = createRootRoute({
    component: () => (
      <>
        <EditableDocument documentId="d1" />
        <Outlet />
      </>
    ),
  })
  const routeTree = root.addChildren([
    createRoute({ getParentRoute: () => root, path: "/", component: () => <p>document page</p> }),
    createRoute({ getParentRoute: () => root, path: "/other", component: () => <p>other page</p> }),
  ])
  const router = createRouter({ routeTree, history: createMemoryHistory({ initialEntries: ["/"] }) })
  render(<RouterProvider router={router} />)
  return router
}

describe("A27: leaving the document inside the app", () => {
  it("A27: a refused write opens the dialog; Stay keeps the edit box, Leave and discard navigates", async () => {
    const router = renderRouted()
    await screen.findByText("document page")
    await typeIntoBlock("refused")

    await act(async () => {
      void router.navigate({ to: "/other" } as never)
    })
    const dialog = await screen.findByRole("alertdialog")
    expect(within(dialog).getByText("Leave without saving?")).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole("button", { name: "Stay" }))
    await waitFor(() => expect(screen.getByRole("textbox")).toHaveFocus())
    expect(router.state.location.pathname).toBe("/")
    expect(screen.getByRole("textbox")).toHaveValue("body text here typed")

    await act(async () => {
      void router.navigate({ to: "/other" } as never)
    })
    await userEvent.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Leave and discard" }),
    )
    await waitFor(() => expect(router.state.location.pathname).toBe("/other"))
  })

  it.each(["saving", "none"] as const)("A27: with %s held the navigation is immediate", async (held) => {
    const router = renderRouted()
    await screen.findByText("document page")
    await typeIntoBlock(held)

    await act(async () => {
      await router.navigate({ to: "/other" } as never)
    })
    expect(screen.queryByRole("alertdialog")).toBeNull()
    await waitFor(() => expect(router.state.location.pathname).toBe("/other"))
  })
})

describe("A28: closing or reloading the tab", () => {
  it.each(["refused", "saving"] as const)("A28: with a %s write held beforeunload is cancelled", async (held) => {
    render(<BlockEditor documentId="d1" blocks={[block({})]} />)
    await typeIntoBlock(held)
    const event = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it("A28: with none held beforeunload is not cancelled", async () => {
    render(<BlockEditor documentId="d1" blocks={[block({})]} />)
    const event = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })
})

// ---------------------------------------------------------------- A32

describe("A32: a refusal body carrying error.message and no detail", () => {
  it("A32: shows that message, not 'API error: N'", async () => {
    const { apiFetch: realFetch } = await vi.importActual<typeof import("@/lib/api")>("@/lib/api")
    for (const status of [403, 409, 422, 500]) {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => ({
          ok: false,
          status,
          statusText: "x",
          headers: new Headers(),
          json: async () => ({ error: { code: "refused", message: `the server refused ${status}` } }),
        })),
      )
      await expect(realFetch("/anything")).rejects.toThrow(`the server refused ${status}`)
    }
  })

  it("A32: falls back to 'API error: N' when the body carries no message", async () => {
    const { apiFetch: realFetch } = await vi.importActual<typeof import("@/lib/api")>("@/lib/api")
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 418,
        statusText: "",
        headers: new Headers(),
        json: async () => ({}),
      })),
    )
    await expect(realFetch("/anything")).rejects.toThrow("API error: 418")
  })
})

export type _Unused = ReactNode
