import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

import { ChatContextPanel } from "../components/chat-context-panel"
import {
  channelStates,
  exclusionItems,
  rowTrace,
  type ChatRetrievalEnvelope,
} from "../lib/retrieval"

const mockUseConversations = vi.fn()
const mockUseConversation = vi.fn()
const mockUseCreateConversation = vi.fn()
const mockUseDeleteConversation = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useConversations: () => mockUseConversations(),
  useConversation: (id: string | null) => mockUseConversation(id),
  useCreateConversation: () => mockUseCreateConversation(),
  useDeleteConversation: () => mockUseDeleteConversation(),
}))

import { RealChatPage } from "../components/real-chat-page"

// T2.58. Chat retrieves through the composition now, so the panel receives a
// retrieval envelope and a per-row score breakdown for the first time. What is
// asserted here is that it renders what it received and nothing else: a panel
// that invented a channel state, a count or a bar would be exactly the
// plausible story doc 07 §8 refuses, and it would be indistinguishable from a
// real one on screen.

const ENVELOPE: ChatRetrievalEnvelope = {
  query: "which pooler",
  channels: {
    "memory.semantic": { ran: true, failed: false },
    "memory.keyword": { ran: true, failed: true },
    "fact.keyword": { ran: false, failed: false },
  },
  reranked: false,
  weights: { semantic_weight: 0.7 },
  excluded: { by_context_conflict: 2, by_result_limit: 0 },
  partial: true,
}

describe("the envelope a converged turn carries", () => {
  it("names every channel the turn asked, and how each fared", () => {
    expect(channelStates(ENVELOPE)).toEqual([
      { name: "memory.semantic", state: "ok" },
      { name: "memory.keyword", state: "failed" },
      { name: "fact.keyword", state: "not asked" },
    ])
  })

  it("distinguishes a channel that failed from one that was never asked", () => {
    // Collapsing the two would report an outage the composition did not have,
    // or hide one it did.
    const states = Object.fromEntries(
      channelStates(ENVELOPE).map((c) => [c.name, c.state]),
    )
    expect(states["memory.keyword"]).not.toBe(states["fact.keyword"])
  })

  it("turns the non-zero exclusion counts into copy that names the reason", () => {
    const items = exclusionItems(ENVELOPE)
    expect(items).toHaveLength(1)
    const item = items[0]!
    expect(item.count).toBe(2)
    expect(item.tag).toBe("by_context_conflict")
    expect(String(item.reason)).toContain("conflicted with this turn's context")
  })

  it("builds no trace for a row that carries no breakdown", () => {
    expect(rowTrace({ rank_fusion_factor: 1 })).toBeUndefined()
  })
})

describe("ChatContextPanel renders the trace and the exclusion counts", () => {
  it("flags the turn as degraded and names the failed channel", () => {
    render(
      <ChatContextPanel
        rows={[{ id: "m1", content: "a row", status: "active" }]}
        envelope={ENVELOPE}
      />,
    )
    expect(screen.getByText("degraded")).toBeInTheDocument()
    expect(screen.getByText(/memory keyword search failed/)).toBeInTheDocument()
    expect(screen.queryByText("not asked")).not.toBeInTheDocument()
  })

  it("renders the exclusion count", () => {
    render(
      <ChatContextPanel
        rows={[{ id: "m1", content: "a row", status: "active" }]}
        envelope={ENVELOPE}
      />,
    )
    expect(screen.getByText(/2 rows excluded/)).toBeInTheDocument()
  })

  it("renders each row's own arm scores, through the Memories adapter", () => {
    render(
      <ChatContextPanel
        rows={[
          {
            id: "m1",
            content: "a row",
            status: "active",
            scores: { semantic: 0.81, keyword: 0.42, rrf_score: 0.0164 },
            rank_fusion_factor: 1,
          },
        ]}
        envelope={ENVELOPE}
      />,
    )
    // The shared trace component renders one bar per arm plus the fused
    // number it labels as the ordering signal.
    expect(screen.getByText("semantic")).toBeInTheDocument()
    expect(screen.getByText("keyword")).toBeInTheDocument()
    expect(screen.getByText("0.81")).toBeInTheDocument()
    expect(screen.getByText("0.42")).toBeInTheDocument()
    expect(screen.getByText("rrf_score")).toBeInTheDocument()
    expect(screen.getByText("0.0164")).toBeInTheDocument()
  })

  it("shows a disputed L2 row with its badge claim verbatim", () => {
    render(
      <ChatContextPanel
        rows={[]}
        facts={[
          {
            id: "f1",
            text: "pgbouncer is the pooler",
            layer: "L2",
            verification_status: "disputed",
            badge: { claim: "disputed: 2 origins assert x, 1 asserts y" },
          },
        ]}
        envelope={ENVELOPE}
      />,
    )
    expect(screen.getByText("L2 · fact")).toBeInTheDocument()
    expect(
      screen.getByText("disputed: 2 origins assert x, 1 asserts y"),
    ).toBeInTheDocument()
  })

  it("names which fact a nested row supports, by the number the turn cites", () => {
    render(
      <ChatContextPanel
        rows={[
          { id: "m1", content: "the first row", status: "active", grouped_under: "f2" },
        ]}
        facts={[
          { id: "f1", index: 1, text: "the first fact", layer: "L2" },
          { id: "f2", index: 2, text: "the second fact", layer: "L2" },
        ]}
        envelope={ENVELOPE}
      />,
    )
    // With two facts on screen, "supports fact F" names neither of them.
    expect(screen.getByText("supports fact F2")).toBeInTheDocument()
    expect(screen.queryByText("supports fact F1")).not.toBeInTheDocument()
  })

  it("says only that a row supports a fact when the fact is not on screen", () => {
    render(
      <ChatContextPanel
        rows={[
          { id: "m1", content: "the first row", status: "active", grouped_under: "gone" },
        ]}
        facts={[{ id: "f1", index: 1, text: "the first fact", layer: "L2" }]}
        envelope={ENVELOPE}
      />,
    )
    expect(screen.getByText("supports a fact")).toBeInTheDocument()
  })

  it("shows no state word and no counts with no envelope at all", () => {
    render(
      <ChatContextPanel rows={[{ id: "m1", content: "a row", status: "active" }]} />,
    )
    expect(screen.queryByText("populated")).not.toBeInTheDocument()
    expect(screen.queryByText("degraded")).not.toBeInTheDocument()
    expect(screen.queryByText(/rows excluded/)).not.toBeInTheDocument()
  })
})

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("RealChatPage hands the panel the envelope of the turn it is showing", () => {
  beforeEach(() => {
    mockUseConversations.mockReturnValue({
      data: { conversations: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })
    mockUseCreateConversation.mockReturnValue({ mutateAsync: vi.fn() })
    mockUseDeleteConversation.mockReturnValue({ mutate: vi.fn() })
  })

  it("reads a historical turn's persisted envelope, not only the live stream", () => {
    // The stored snapshot is what every past turn renders from. An envelope
    // that lived only on the live stream would leave history explainable for
    // exactly as long as the tab stayed open.
    mockUseConversation.mockReturnValue({
      data: {
        id: "c1",
        title: "t",
        created_at: "",
        updated_at: "",
        messages: [
          {
            id: "m1",
            role: "assistant",
            content: "an answer",
            created_at: new Date().toISOString(),
            context: {
              memories: [{ id: "mem1", content: "a stored row", status: "active" }],
              facts: [],
              envelope: ENVELOPE,
            },
          },
        ],
      },
    })

    render(<RealChatPage initialId="c1" />, { wrapper })

    expect(screen.getByText("degraded")).toBeInTheDocument()
    expect(screen.getByText(/2 rows excluded/)).toBeInTheDocument()
  })
})
