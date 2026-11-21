import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  within,
} from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@/features/chat/components/chat-overlay", () => ({
  ChatOverlay: () => null,
}))
vi.mock("@/features/graph/components/graph-2d-renderer", () => ({
  Graph2DRenderer: () => null,
}))
const graph3dProps = vi.fn()
vi.mock("@/features/graph/components/graph-3d-renderer", () => ({
  Graph3DRenderer: (props: unknown) => {
    graph3dProps(props)
    return null
  },
}))
vi.mock("@/features/graph/components/mini-graph", () => ({
  MiniGraph: () => null,
}))
const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: (...args: unknown[]) => mockUseUnifiedGraph(...args),
}))
vi.mock("@/features/graph/lib/graph-utils", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/features/graph/lib/graph-utils")>()
  return { ...actual, transformToGraphData: vi.fn(actual.transformToGraphData) }
})

import { apiFetch } from "@/lib/api"
import { useChatStream } from "@/features/chat/hooks/use-chat-stream"
import { RealRepositoriesView } from "@/features/code/components/real-repositories-view"
import { RealMemoryGraphPage } from "@/features/memory-graph/components/real-memory-graph-page"
import { transformToGraphData } from "@/features/graph/lib/graph-utils"

function qcWrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("A2: chat streams are per conversation", () => {
  it("A2: a send in a second conversation does not abort the first, and the first answer is kept", async () => {
    const signals = new Map<string, AbortSignal>()
    const controllers = new Map<
      string,
      ReadableStreamDefaultController<Uint8Array>
    >()
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        const conv = JSON.parse(String(init.body)).conversation_id as string
        signals.set(conv, init.signal as AbortSignal)
        const body = new ReadableStream<Uint8Array>({
          start(c) {
            controllers.set(conv, c)
          },
        })
        return Promise.resolve({ ok: true, body })
      }),
    )
    const enc = (e: object) =>
      new TextEncoder().encode(`data: ${JSON.stringify(e)}\n\n`)
    const push = async (conv: string, e: object, close = false) => {
      await act(async () => {
        controllers.get(conv)!.enqueue(enc(e))
        if (close) controllers.get(conv)!.close()
        await new Promise((r) => setTimeout(r, 0))
      })
    }

    const qc = new QueryClient()
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )
    const hook = renderHook(
      ({ active }: { active: string }) => useChatStream(active),
      { wrapper, initialProps: { active: "conv-1" } },
    )

    let first!: Promise<unknown>
    act(() => {
      first = hook.result.current.sendMessage("conv-1", "first question")
    })
    await push("conv-1", { type: "token", content: "The first " })

    hook.rerender({ active: "conv-2" })
    act(() => {
      void hook.result.current.sendMessage("conv-2", "second question")
    })
    await push("conv-2", { type: "token", content: "second answer" })

    expect(signals.get("conv-1")!.aborted).toBe(false)

    await push("conv-1", { type: "token", content: "answer" })
    await push("conv-1", { type: "done", conversation_id: "conv-1" }, true)
    await act(async () => {
      await first
    })

    hook.rerender({ active: "conv-1" })
    expect(hook.result.current.streamingContent).toBe("The first answer")
    expect(hook.result.current.error).toBeNull()
    expect(signals.get("conv-1")!.aborted).toBe(false)
  })
})

describe("A3: Edit Repository with a null local_path", () => {
  beforeEach(() => vi.clearAllMocks())

  it("A3: saves a repository that has only a clone URL", async () => {
    const repo = {
      id: "r9",
      name: "cloned-repo",
      url: "https://example.invalid/cloned.git",
      local_path: null,
      provider: "github",
      default_branch: "main",
      fetch_enabled: false,
      fetch_interval_seconds: 300,
      index_on_commit_enabled: false,
      commit_poll_seconds: 60,
      index_uncommitted: false,
      file_count: 1,
      symbol_count: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      status: "ready",
      status_message: null,
      last_indexed_commit: "abc1234",
      last_indexed_at: "2026-01-01T00:00:00Z",
      git_account_id: null,
      git_account_label: null,
      has_custom_token: false,
      index_debt: null,
    }
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/repos/r9" && init?.method === "PUT")
        return Promise.resolve({ ...repo, default_branch: "trunk" })
      if (path === "/repos") return Promise.resolve([repo])
      if (path === "/git-accounts")
        return Promise.resolve({ accounts: [], providers: [] })
      return Promise.resolve([])
    })
    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper: qcWrapper })
    await user.click(await screen.findByRole("button", { name: "Edit" }))
    const dialog = await screen.findByRole("dialog")
    const branch = within(dialog).getByRole("textbox", { name: "Branch" })
    await user.clear(branch)
    await user.type(branch, "trunk")
    await user.click(within(dialog).getByRole("button", { name: "Save" }))
    await vi.waitFor(() => {
      const puts = vi
        .mocked(apiFetch)
        .mock.calls.filter(([, init]) => init?.method === "PUT")
      expect(puts).toHaveLength(1)
      expect(puts[0]![0]).toBe("/repos/r9")
      expect(JSON.parse(String(puts[0]![1]?.body)).default_branch).toBe("trunk")
    })
    await vi.waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    )
  })
})

describe("A4: memory graph 2D builds no 3D data", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    vi.mocked(transformToGraphData).mockClear()
    graph3dProps.mockClear()
  })

  it("A4: a filter change in the 2D view builds no 3D graph data", () => {
    vi.useFakeTimers()
    try {
      mockUseUnifiedGraph.mockReturnValue({
        data: {
          memories: [
            { id: "m1", content: "alpha", source: "api", tags: ["t"], memory_type: null, importance: 0.5, cluster: 0 },
            { id: "m2", content: "beta", source: "api", tags: [], memory_type: null, importance: 0.5, cluster: 0 },
          ],
          clusters: {},
          cluster_names: {},
          similarity_edges: [],
        },
        isLoading: false,
      })
      render(<RealMemoryGraphPage />, { wrapper: qcWrapper })
      const search = screen.getByPlaceholderText("Filter by content…")
      for (const value of ["a", "al", "alp", "alph"]) {
        fireEvent.change(search, { target: { value } })
        act(() => {
          vi.advanceTimersByTime(1500)
        })
      }
      expect(transformToGraphData).not.toHaveBeenCalled()
      expect(graph3dProps).not.toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })
})


import { FailedCapturesSection } from "@/features/activity/components/failed-captures-section"
import type { BufferRow } from "@/hooks/api/use-memory-buffer-api"

describe("A55: discarding a failed capture whose memory exists", () => {
  const ROW: BufferRow = {
    id: "0190f000-0000-7000-8000-00000000b001",
    memory_id: "0190f000-0000-7000-8000-0000abcd1234",
    memory_exists: true,
    project: "darkmem",
    source: "api",
    status: "error",
    is_stale: false,
    attempts: 5,
    max_attempts: 5,
    last_error: "boom",
    created_at: "2026-11-20T10:00:00Z",
    claimed_at: null,
    claimed_by: null,
    token_size: null,
    content_preview: "payments worker keeps restarting",
    content_length: 30,
  }

  function mount(onDiscard: () => Promise<unknown>) {
    render(
      <FailedCapturesSection
        items={[ROW]}
        total={1}
        isLoading={false}
        isError={false}
        onRequeue={vi.fn(() => Promise.resolve())}
        onDiscard={onDiscard}
      />,
    )
  }

  it("A55: opening the discard asks first, names the memory, and cancel deletes nothing", async () => {
    const onDiscard = vi.fn(() => Promise.resolve())
    const user = userEvent.setup()
    mount(onDiscard)
    await user.click(screen.getByRole("button", { name: /discard/i }))
    expect(onDiscard).not.toHaveBeenCalled()
    const dialog = await screen.findByRole("alertdialog")
    expect(dialog.textContent).toContain("abcd1234")
    expect(dialog.textContent?.toLowerCase()).toContain("memory")
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }))
    expect(onDiscard).not.toHaveBeenCalled()
  })

  it("A55: confirming discards the capture", async () => {
    const onDiscard = vi.fn(() => Promise.resolve())
    const user = userEvent.setup()
    mount(onDiscard)
    await user.click(screen.getByRole("button", { name: /discard/i }))
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Discard" }))
    await vi.waitFor(() => expect(onDiscard).toHaveBeenCalledWith(ROW.id))
  })
})

import { toast } from "darkraise-ui/components/sonner"
import { LLMTab } from "@/features/settings/components/llm-tab"

vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe("A37: Settings save dialog", () => {
  const WIRE = {
    extraction: {
      base_url: "http://localhost:11434/v1",
      provider_name: "local",
      model: "qwen2.5:3b",
      api_key: null,
      dimensions: null,
      reasoning: false,
      api_kind: "ollama",
      params: {},
    },
  }

  function mockServer(post: () => Promise<unknown>) {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/config/llm" && init?.method === "POST") return post()
      if (path === "/config/llm") return Promise.resolve(WIRE)
      if (path === "/config/llm-providers")
        return Promise.resolve({
          providers: [
            { name: "local", api_kind: "ollama", base_url: "http://localhost:11434/v1", api_key: null },
          ],
        })
      return Promise.resolve({})
    })
  }

  async function openAndEdit() {
    const user = userEvent.setup()
    render(<LLMTab />, { wrapper: qcWrapper })
    await user.click(await screen.findByLabelText("Edit extraction"))
    const dialog = await screen.findByRole("dialog")
    const model = within(dialog).getByLabelText("extraction model")
    await user.clear(model)
    await user.type(model, "edited-model")
    await user.click(within(dialog).getByRole("button", { name: "Save" }))
    return { dialog, user }
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("A37: a refused save keeps the dialog open, keeps the edits and shows the server's reason", async () => {
    mockServer(() => Promise.reject(new Error("the reason the server gave")))
    const { dialog } = await openAndEdit()
    await vi.waitFor(() =>
      expect(dialog.textContent).toContain("the reason the server gave"),
    )
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(
      (within(dialog).getByLabelText("extraction model") as HTMLInputElement).value,
    ).toBe("edited-model")
    expect(toast.success).not.toHaveBeenCalled()
  })

  it("A37: a successful save closes the dialog and toasts Saved", async () => {
    mockServer(() => Promise.resolve({}))
    await openAndEdit()
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalled())
    expect(String(vi.mocked(toast.success).mock.calls[0]![0])).toMatch(/saved/i)
    await vi.waitFor(() => {
      const d = screen.queryByRole("dialog")
      expect(d === null || d.getAttribute("data-state") === "closed").toBe(true)
    })
  })
})
