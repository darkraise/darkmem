import { describe, it, expect, vi, beforeEach } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T1.47 — memory-detail supersession lineage. Ruling 1: a superseded
// memory must render, labelled, by default — never filtered out, which is
// literally what once made two memories vanish from this corpus. Ruling 2:
// lineage renders both directions, with real data on each side once the
// backend gained the `predecessors` field (controller scope extension,
// 2026-07-28) — see memory-lineage backend tests for the detector-produced
// pair this frontend fixture mirrors. Ruling 3: the successor/predecessor
// links navigate, not just display an id — asserted via the resolved href.
// Ruling 4: the lifecycle badge is an honesty signal and renders in both
// detail levels.

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
const navigateMock = vi.fn()
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => navigateMock,
  Link: ({
    to,
    params,
    children,
    ...rest
  }: {
    to: string
    params?: Record<string, string>
    children?: ReactNode
    [key: string]: unknown
  }) => {
    const href = params?.memoryId
      ? to.replace("$memoryId", params.memoryId)
      : to
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  },
}))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem/use-detail-level"
import { AppPageHeader } from "@/components/app-chrome"
import { RealMemoryDetailView } from "../components/real-memory-detail-view"

// A real detector-produced pair, mirrored client-side: REPLACED is the old
// row `detect_supersessions` flipped, SUCCESSOR is the new memory whose
// GET /memories/{id} response now carries REPLACED back through
// `predecessors` (T1.47's backend half).
const REPLACED = {
  id: "mem-1",
  content: "we use nomic-embed-text for embeddings",
  source: "mcp",
  tags: [],
  created_at: "2026-01-01T00:00:00Z",
  status: "superseded" as const,
  superseded_by: "succ-1",
  technologies: ["nomic-embed-text"],
  predecessors: [] as const,
}

const SUCCESSOR = {
  id: "succ-1",
  content: "we switched embeddings to qwen3-embedding:0.6b",
  source: "mcp",
  tags: [],
  created_at: "2026-02-01T00:00:00Z",
  status: "active" as const,
  superseded_by: null,
  technologies: ["qwen3-embedding"],
  predecessors: [
    {
      id: "mem-1",
      content: "we use nomic-embed-text for embeddings",
      created_at: "2026-01-01T00:00:00Z",
      status: "superseded" as const,
    },
  ],
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function mockRoutes(routes: Record<string, unknown>) {
  vi.mocked(apiFetch).mockImplementation((path: unknown) => {
    const p = path as string
    if (p in routes) return Promise.resolve(routes[p])
    return Promise.reject(new Error(`unmocked path: ${p}`))
  })
}

describe("memory-detail supersession lineage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("renders a superseded memory's own content and badge by default — never filtered out (ruling 1)", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getAllByText("superseded").length).toBeGreaterThan(0)
  })

  it("renders lineage in both directions with real data on each side (ruling 2)", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    // View the successor: its forward direction is "not superseded" (nothing
    // has replaced it yet) and its reverse direction must show the real
    // predecessor the backend's `predecessors` field carries — not a
    // fabricated or hand-reconstructed row.
    render(<RealMemoryDetailView memoryId="succ-1" />, { wrapper })

    await screen.findByText("Replaced by")
    expect(screen.getByText(/not superseded/i)).toBeInTheDocument()

    await screen.findByText("Replaced")
    const predecessorLink = await screen.findByRole("link", { name: /mem-1/i })
    expect(predecessorLink).toHaveAttribute("href", "/memories/mem-1")
    expect(
      screen.getByText(/we use nomic-embed-text for embeddings/i),
    ).toBeInTheDocument()
  })

  it("distinguishes 'replaced nothing' (an empty list) from 'unknown' (not computed) in the reverse direction (ruling 2)", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    // REPLACED itself has predecessors: [] — the backend confirmed it
    // replaced nothing, which must read as a fact, not a gap.
    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })
    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getByText(/replaced nothing/i)).toBeInTheDocument()
    expect(screen.queryByText(/^unknown/i)).not.toBeInTheDocument()
  })

  it("reads the reverse direction as unknown when a row was never fetched through the single-get door (ruling 2)", async () => {
    // Simulates a Memory object that reached this component from a reader
    // other than GET /memories/{id} (e.g. reused from a search result),
    // where the backend never computed predecessors for that read.
    const { predecessors: _drop, ...withoutPredecessors } = REPLACED
    mockRoutes({
      "/memories/mem-4": { ...withoutPredecessors, id: "mem-4" },
      "/memories/succ-1": SUCCESSOR,
    })

    render(<RealMemoryDetailView memoryId="mem-4" />, { wrapper })
    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getByText(/^unknown\.$/i)).toBeInTheDocument()
    expect(screen.queryByText(/replaced nothing/i)).not.toBeInTheDocument()
  })

  it("the successor link navigates to the memory that replaced it, not merely displays its id (ruling 3)", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    const link = await screen.findByRole("link", { name: /succ-1/i })
    expect(link).toHaveAttribute("href", "/memories/succ-1")
  })

  it("the predecessor link navigates to the memory it replaced, not merely displays its id (ruling 3)", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="succ-1" />, { wrapper })

    const link = await screen.findByRole("link", { name: /mem-1/i })
    expect(link).toHaveAttribute("href", "/memories/mem-1")
  })

  it.each(["simple", "advanced"] as const)(
    "the superseded badge and successor link render in %s detail level (ruling 4)",
    async (level) => {
      useDetailLevel.setState({ level })
      mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

      render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

      await screen.findByText(/switched embeddings to qwen3-embedding/i)
      expect(screen.getAllByText("superseded").length).toBeGreaterThan(0)
    },
  )

  it("a deprecated memory (successor removed) is labelled, not hidden", async () => {
    mockRoutes({
      "/memories/mem-2": {
        ...REPLACED,
        id: "mem-2",
        status: "deprecated",
        superseded_by: null,
      },
    })

    render(<RealMemoryDetailView memoryId="mem-2" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getAllByText("deprecated").length).toBeGreaterThan(0)
    expect(
      screen.getByText(/replaced this one was later deleted/i),
    ).toBeInTheDocument()
  })

  it("an active memory reads as not-superseded, plainly", async () => {
    mockRoutes({
      "/memories/mem-3": { ...REPLACED, id: "mem-3", status: "active", superseded_by: null },
    })

    render(<RealMemoryDetailView memoryId="mem-3" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getByText(/not superseded/i)).toBeInTheDocument()
  })

  it("badges the successor with its own status, not this memory's", async () => {
    mockRoutes({ "/memories/mem-1": REPLACED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    await screen.findByText(/switched embeddings to qwen3-embedding/i)
    // One "superseded" badge, this memory's own: the successor beside it is
    // active, which carries no lifecycle badge.
    expect(screen.getAllByText("superseded")).toHaveLength(1)
  })
})

describe("memory-detail delete", () => {
  beforeEach(() => vi.clearAllMocks())

  it("deletes after a confirmation and returns to the list", async () => {
    vi.mocked(apiFetch).mockImplementation((path: unknown, init?: unknown) => {
      if ((init as RequestInit | undefined)?.method === "DELETE") {
        return Promise.resolve(undefined)
      }
      return path === "/memories/succ-1"
        ? Promise.resolve(SUCCESSOR)
        : Promise.reject(new Error(`unmocked path: ${String(path)}`))
    })
    render(
      <>
        <AppPageHeader />
        <RealMemoryDetailView memoryId="succ-1" />
      </>,
      { wrapper },
    )

    fireEvent.click(await screen.findByRole("button", { name: /^delete$/i }))
    expect(await screen.findByText(/not a content purge/i)).toBeInTheDocument()
    const confirm = screen
      .getAllByRole("button", { name: /^delete$/i })
      .find((button) => button.closest('[role="alertdialog"]'))!
    fireEvent.click(confirm)

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/memories/succ-1", { method: "DELETE" }),
    )
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: "/memories" }))
  })

  it("never re-reads the memory it is deleting (M23b: one console 404)", async () => {
    // The server's memory.deleted broadcast invalidates every ["memory"]
    // query, often before the DELETE itself answers.
    let answerDelete: (value: unknown) => void = () => {}
    vi.mocked(apiFetch).mockImplementation((path: unknown, init?: unknown) => {
      if ((init as RequestInit | undefined)?.method === "DELETE") {
        return new Promise((resolve) => {
          answerDelete = resolve
        })
      }
      return path === "/memories/succ-1"
        ? Promise.resolve(SUCCESSOR)
        : Promise.reject(new Error(`unmocked path: ${String(path)}`))
    })
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <AppPageHeader />
        <RealMemoryDetailView memoryId="succ-1" />
      </QueryClientProvider>,
    )

    fireEvent.click(await screen.findByRole("button", { name: /^delete$/i }))
    const confirm = (await screen.findAllByRole("button", { name: /^delete$/i }))
      .find((button) => button.closest('[role="alertdialog"]'))!
    fireEvent.click(confirm)
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/memories/succ-1", { method: "DELETE" }),
    )
    const reads = () =>
      vi.mocked(apiFetch).mock.calls.filter(
        ([path, init]) => path === "/memories/succ-1" && !(init as RequestInit | undefined)?.method,
      ).length
    const readsBefore = reads()

    await qc.invalidateQueries({ queryKey: ["memory"] })
    answerDelete(undefined)
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: "/memories" }))
    await qc.invalidateQueries({ queryKey: ["memory"] })

    expect(reads()).toBe(readsBefore)
    // Still on screen until the navigation lands, not a "not found" flash.
    expect(screen.getByText(SUCCESSOR.content)).toBeInTheDocument()
  })
})
