import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T3.20 — inject records in the timeline (doc 13 §6.5). The calendar half is
// in `src/features/dashboard/__tests__`; both surfaces are covered, this file
// owns the one the task's Verify command reaches.
//
// Doc 01's F10 promise is context before the first prompt; the obligation is
// that the human can always see what the agent was told. An injection the
// human cannot inspect is the silent context swap invariant 14 forbids.

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, ...rest }: { children?: ReactNode; [k: string]: unknown }) => (
    <a {...rest}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import { DayTab } from "../components/day-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const FACT_A = "0f2c1a5e-0000-4000-8000-00000000000a"
const FACT_B = "0f2c1a5e-0000-4000-8000-00000000000b"
const MEMORY_A = "0f2c1a5e-0000-4000-8000-00000000000c"

function injectRow(over: Record<string, unknown> = {}) {
  return {
    id: 1,
    created_at: "2026-08-11T11:20:00Z",
    event_type: "inject",
    object_type: "system",
    object_id: null,
    project: "darkmem",
    actor: null,
    api_key_id: null,
    source: null,
    payload: {
      tool: "claude-code",
      context_file: "CLAUDE.md",
      fact_ids: [FACT_A, FACT_B],
      article_ids: [],
      memory_ids: [MEMORY_A],
      budget_tokens: 1200,
      tokens_used: 640,
    },
    ...over,
  }
}

function renderDay(items: unknown[]) {
  vi.mocked(apiFetch).mockResolvedValue({ items, total: items.length })
  render(<DayTab day="2026-08-11" onDayChange={() => {}} />, { wrapper })
}

beforeEach(() => {
  vi.clearAllMocks()
  useDetailLevel.setState({ level: "advanced" })
})

describe("inject records in the day timeline", () => {
  it("renders the item count and the budget on the row itself", async () => {
    renderDay([injectRow()])

    expect(await screen.findByText(/3 items pushed/)).toBeInTheDocument()
    expect(screen.getByText(/640 \/ 1,200 token budget/)).toBeInTheDocument()
  })

  it("names the target rather than the generic system object", async () => {
    // `object_type` is `system` and `object_id` is null for an inject, so the
    // generic label names nothing at all.
    renderDay([injectRow()])

    expect(
      await screen.findByText(/distribution target: claude-code \(CLAUDE\.md\)/),
    ).toBeInTheDocument()
  })

  it("says the budget was not recorded rather than implying a zero", async () => {
    renderDay([
      injectRow({
        payload: {
          tool: "cursor",
          context_file: ".cursorrules",
          fact_ids: [],
          article_ids: [],
          memory_ids: [MEMORY_A],
        },
      }),
    ])

    expect(await screen.findByText(/token budget not recorded/)).toBeInTheDocument()
    expect(screen.queryByText(/0 \/ 0 token budget/)).not.toBeInTheDocument()
  })

  it("clicking through shows exactly what was pushed, per layer", async () => {
    renderDay([injectRow()])

    await userEvent.click(
      await screen.findByRole("button", { name: /show exactly what was pushed/i }),
    )

    expect(screen.getByText(/2 facts · 0 articles · 1 memory/)).toBeInTheDocument()
    expect(screen.getByText(FACT_A)).toBeInTheDocument()
    expect(screen.getByText(FACT_B)).toBeInTheDocument()
    expect(screen.getByText(MEMORY_A)).toBeInTheDocument()
  })

  it("a curb reads as nothing pushed, not as a push of zero items", async () => {
    // A separate event type precisely so a reader counting injections does not
    // count a curb as a push of nothing.
    renderDay([
      injectRow({
        event_type: "inject_curbed",
        payload: {
          tool: "claude-code",
          context_file: "CLAUDE.md",
          reason: "operator turned push off",
        },
      }),
    ])

    expect(await screen.findByText(/Push curbed for/)).toBeInTheDocument()
    expect(screen.getByText(/operator turned push off/)).toBeInTheDocument()
    expect(screen.queryByText(/0 items pushed/)).not.toBeInTheDocument()
  })

  it("a watch refresh names what shifted; a session start names no cause", async () => {
    // T4.06. A re-inject with no cause is indistinguishable from a session
    // start in this timeline.
    renderDay([
      injectRow({
        id: 2,
        payload: {
          tool: "claude-code",
          context_file: "CLAUDE.md",
          fact_ids: [FACT_A],
          article_ids: [],
          memory_ids: [],
          budget_tokens: 1200,
          tokens_used: 90,
          cadence: "watch",
          trigger: "file_opened",
        },
      }),
    ])

    expect(
      await screen.findByText(/re-injected because the/),
    ).toBeInTheDocument()
    expect(screen.getByText("open file")).toBeInTheDocument()
  })

  it("a session-start push claims no trigger", async () => {
    renderDay([
      injectRow({
        payload: {
          tool: "claude-code",
          context_file: "CLAUDE.md",
          fact_ids: [FACT_A],
          article_ids: [],
          memory_ids: [],
          budget_tokens: 1200,
          tokens_used: 90,
          cadence: "session_start",
          trigger: null,
        },
      }),
    ])

    await screen.findByText(/1 item pushed/)
    expect(screen.queryByText(/re-injected because/)).not.toBeInTheDocument()
  })

  it("an unrecognised trigger renders verbatim rather than vanishing", async () => {
    // The swap happened; hiding its cause because this map is stale is worse
    // than showing a raw token.
    renderDay([
      injectRow({
        payload: {
          tool: "claude-code",
          context_file: "CLAUDE.md",
          fact_ids: [],
          article_ids: [],
          memory_ids: [FACT_A],
          budget_tokens: 1200,
          tokens_used: 90,
          cadence: "watch",
          trigger: "branch_switched",
        },
      }),
    ])

    expect(await screen.findByText("branch_switched")).toBeInTheDocument()
  })

  it("a non-inject event grows no inject panel", async () => {
    renderDay([
      injectRow({
        event_type: "created",
        object_type: "memory",
        object_id: "0f2c1a5e-0000-4000-8000-0000000000ff",
      }),
    ])

    expect(await screen.findByText(/created/)).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /show exactly what was pushed/i }),
    ).not.toBeInTheDocument()
  })
})

describe("inject records honour the detail level (invariant 14)", () => {
  it("simple keeps the count, the budget and the per-layer breakdown", async () => {
    useDetailLevel.setState({ level: "simple" })
    renderDay([injectRow()])

    await userEvent.click(
      await screen.findByRole("button", { name: /show exactly what was pushed/i }),
    )

    // What the agent was told, and how much of it, is the honesty signal —
    // never the thing that gets collapsed.
    expect(screen.getByText(/3 items pushed/)).toBeInTheDocument()
    expect(screen.getByText(/640 \/ 1,200 token budget/)).toBeInTheDocument()
    expect(screen.getByText(/2 facts · 0 articles · 1 memory/)).toBeInTheDocument()
  })

  it("simple collapses the raw ids", async () => {
    useDetailLevel.setState({ level: "simple" })
    renderDay([injectRow()])

    await userEvent.click(
      await screen.findByRole("button", { name: /show exactly what was pushed/i }),
    )

    expect(screen.queryByText(FACT_A)).not.toBeInTheDocument()
    expect(screen.queryByText(MEMORY_A)).not.toBeInTheDocument()
  })
})
