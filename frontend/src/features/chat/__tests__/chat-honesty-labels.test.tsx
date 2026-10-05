import { describe, it, expect, vi } from "vitest"
import type { ReactNode } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SourceBadges } from "../components/source-badges"
import { ChatContextPanel } from "../components/chat-context-panel"
import { ChatMessages } from "../components/chat-messages"
import type { ChatMessage } from "@/hooks/api"

// A citation chip with no selection handler links to the memory's page, and
// these renders have no router; a plain anchor stands in for the Link.
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
  }) => (
    <a href={params?.memoryId ? to.replace("$memoryId", params.memoryId) : to} {...rest}>
      {children}
    </a>
  ),
}))

// T1.60 Step 8, three render sites (§6.1/§6.5): the same superseded/active
// fixture is asserted at SourceBadges, ChatContextPanel, and the inline
// MemoryBadge citation chip — the review's own finding was that v1's plan
// only inventoried two of the three sites, so this file exists specifically
// to prove all three, not just the first two anyone thinks of.

describe("SourceBadges honesty labels", () => {
  async function openBadges() {
    await userEvent.click(screen.getByRole("button", { name: /memory/i }))
  }

  it("renders LifecycleBadge for a superseded row", async () => {
    render(
      <SourceBadges
        memories={[{ id: "m1", content: "old fact", status: "superseded" }]}
        entities={[]}
      />,
    )
    await openBadges()
    expect(screen.getByText("superseded")).toBeInTheDocument()
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
  })

  it("renders no lifecycle badge for an active row, but still renders LayerChip", async () => {
    render(
      <SourceBadges
        memories={[{ id: "m2", content: "current fact", status: "active" }]}
        entities={[]}
      />,
    )
    await openBadges()
    expect(screen.queryByText("superseded")).not.toBeInTheDocument()
    expect(screen.queryByText("deprecated")).not.toBeInTheDocument()
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
  })
})

describe("ChatContextPanel honesty labels", () => {
  it("renders LifecycleBadge for a superseded row", () => {
    render(
      <ChatContextPanel
        rows={[{ id: "m1", content: "old fact", status: "superseded" }]}
      />,
    )
    expect(screen.getByText("superseded")).toBeInTheDocument()
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
  })

  it("renders no lifecycle badge for an active row, but still renders LayerChip", () => {
    render(
      <ChatContextPanel
        rows={[{ id: "m2", content: "current fact", status: "active" }]}
      />,
    )
    expect(screen.queryByText("superseded")).not.toBeInTheDocument()
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
  })

  it("shows the empty state when no turn has produced a context yet", () => {
    render(<ChatContextPanel rows={null} />)
    expect(screen.getByText("No context yet")).toBeInTheDocument()
  })
})

describe("Inline citation chip (MemoryBadge, the third render site) honesty labels", () => {
  function assistantMessage(status: "superseded" | "active"): ChatMessage {
    return {
      id: "msg1",
      role: "assistant",
      content: "See [1] for details.",
      context: {
        memories: [
          {
            id: "m1",
            score: 0.9,
            content: "cited memory content",
            source: "api",
            status,
          },
        ],
        entities: [],
      },
      created_at: new Date().toISOString(),
    }
  }

  it("carries the superseded status in the chip's tooltip and renders a colored dot", () => {
    const { container } = render(
      <ChatMessages messages={[assistantMessage("superseded")]} />,
    )
    expect(screen.getByTitle(/status: superseded/)).toBeInTheDocument()
    // The tooltip alone would pass even if the dot render call were deleted
    // — they are two independent mechanisms (Ruling 7: a guard that cannot
    // fail is worse than none). Assert the dot element itself, not just
    // the text a sighted-only tooltip carries.
    const dot = container.querySelector("span.rounded-full")
    expect(dot).not.toBeNull()
    expect(dot).toHaveClass("bg-warning")
  })

  it("carries the active status in the chip's tooltip too — never zero lifecycle signal", () => {
    const { container } = render(
      <ChatMessages messages={[assistantMessage("active")]} />,
    )
    expect(screen.getByTitle(/status: active/)).toBeInTheDocument()
    const dot = container.querySelector("span.rounded-full")
    expect(dot).not.toBeNull()
    expect(dot).toHaveClass("bg-muted-foreground/40")
  })
})
