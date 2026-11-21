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
