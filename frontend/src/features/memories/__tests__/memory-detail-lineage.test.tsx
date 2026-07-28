import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T1.47 — memory-detail supersession lineage. Ruling 1: a superseded
// memory must render, labelled, by default — never filtered out, which is
// literally what once made two memories vanish from this corpus. Ruling 3:
// the successor link must navigate, not just display an id — asserted via
// the resolved href, not merely the link's presence. Ruling 4: the
// lifecycle badge is an honesty signal and renders in both detail levels.

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
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
import { RealMemoryDetailView } from "../components/real-memory-detail-view"

const SUPERSEDED = {
  id: "mem-1",
  content: "we use nomic-embed-text for embeddings",
  source: "mcp",
  tags: [],
  created_at: new Date().toISOString(),
  status: "superseded" as const,
  superseded_by: "succ-1",
  technologies: ["nomic-embed-text"],
}

const SUCCESSOR = {
  id: "succ-1",
  content: "we switched embeddings to qwen3-embedding:0.6b",
  source: "mcp",
  tags: [],
  created_at: new Date().toISOString(),
  status: "active" as const,
  technologies: ["qwen3-embedding"],
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
    mockRoutes({ "/memories/mem-1": SUPERSEDED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getAllByText("superseded").length).toBeGreaterThan(0)
  })

  it("renders lineage in both directions: what replaced it, and an honest label for what it replaced (ruling 2)", async () => {
    mockRoutes({ "/memories/mem-1": SUPERSEDED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    await screen.findByText("Replaced by")
    // Forward direction resolves to the real successor.
    await screen.findByText(/switched embeddings to qwen3-embedding/i)
    // Reverse direction: the backend has no predecessor lookup, so this
    // must say so honestly rather than rendering "none" (which would be
    // indistinguishable from "we checked and there aren't any").
    expect(screen.getByText("Replaced")).toBeInTheDocument()
    expect(
      screen.getByText(/no reverse lookup from a memory to the earlier/i),
    ).toBeInTheDocument()
  })

  it("the successor link navigates to the memory that replaced it, not merely displays its id (ruling 3)", async () => {
    mockRoutes({ "/memories/mem-1": SUPERSEDED, "/memories/succ-1": SUCCESSOR })

    render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

    const link = await screen.findByRole("link", { name: /succ-1/i })
    expect(link).toHaveAttribute("href", "/memories/succ-1")
  })

  it.each(["simple", "advanced"] as const)(
    "the superseded badge and successor link render in %s detail level (ruling 4)",
    async (level) => {
      useDetailLevel.setState({ level })
      mockRoutes({ "/memories/mem-1": SUPERSEDED, "/memories/succ-1": SUCCESSOR })

      render(<RealMemoryDetailView memoryId="mem-1" />, { wrapper })

      await screen.findByText(/switched embeddings to qwen3-embedding/i)
      expect(screen.getAllByText("superseded").length).toBeGreaterThan(0)
    },
  )

  it("a deprecated memory (successor removed) is labelled, not hidden", async () => {
    mockRoutes({
      "/memories/mem-2": {
        ...SUPERSEDED,
        id: "mem-2",
        status: "deprecated",
        superseded_by: null,
      },
    })

    render(<RealMemoryDetailView memoryId="mem-2" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getAllByText("deprecated").length).toBeGreaterThan(0)
    expect(
      screen.getByText(/successor memory was later removed/i),
    ).toBeInTheDocument()
  })

  it("an active memory reads as not-superseded, plainly", async () => {
    mockRoutes({
      "/memories/mem-3": { ...SUPERSEDED, id: "mem-3", status: "active", superseded_by: null },
    })

    render(<RealMemoryDetailView memoryId="mem-3" />, { wrapper })

    await screen.findByText(/we use nomic-embed-text for embeddings/i)
    expect(screen.getByText(/not superseded/i)).toBeInTheDocument()
  })
})
