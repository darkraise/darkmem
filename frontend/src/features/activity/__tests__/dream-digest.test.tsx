import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// Every Done-when clause on T2.38 is a statement about what renders — "every
// action shows what changed", "undo reachable at both granularities", "an
// undone action still appears, marked undone", "Simple/Advanced honoured" —
// so this suite mounts the real component tree, never just the adapter
// hook. A hook-only test cannot see any of these (controller finding on
// T2.36: its eight adapter tests all passed while three render-level
// Criticals sat in the component).

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})

import { apiFetch, ApiError } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
import { useDetailLevel } from "@/components/darkmem"
import { diffFields, LiveDreamDigest } from "../components/dream-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const CYCLE_ID = "20260803-01"

const CYCLES_RESPONSE = {
  items: [
    {
      cycle_id: CYCLE_ID,
      started_at: "2026-08-03T02:00:00Z",
      ended_at: "2026-08-03T02:05:00Z",
      projects: ["darkmem"],
      total: 3,
      counts: { subsume: 1, associate: 1, refine: 1 },
      undone_count: 1,
      origin: null,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
}

const OBJECT_A = "11111111-1111-1111-1111-111111111111"
const OBJECT_B = "22222222-2222-2222-2222-222222222222"

function digestResponse() {
  return {
    cycle_id: CYCLE_ID,
    started_at: "2026-08-03T02:00:00Z",
    ended_at: "2026-08-03T02:05:00Z",
    counts: { subsume: 1, associate: 1, refine: 1 },
    undone_count: 1,
    objects: [
      {
        object_id: OBJECT_A,
        project: "darkmem",
        actions: [
          // Deliberately interleaved kinds within one object: associate
          // (event 101) journalled before subsume (event 102). Journal order
          // is application order; a regroup-by-kind would put them in the
          // opposite section and describe a cycle that did not occur.
          {
            event_id: 101,
            created_at: "2026-08-03T02:01:00Z",
            action: "associate",
            object_id: OBJECT_A,
            project: "darkmem",
            detector: "dedup",
            origin: null,
            actor: null,
            before: {},
            after: { rel_type: "DUPLICATE_OF" },
            detail: { verdict: "dup", score: 0.9 },
            undone: false,
            undone_at: null,
            undone_by: null,
            undo_batch_id: null,
            undoable: true,
            undo_blocked_reason: null,
          },
          {
            event_id: 102,
            created_at: "2026-08-03T02:02:00Z",
            action: "subsume",
            object_id: OBJECT_A,
            project: "darkmem",
            detector: "dedup",
            origin: null,
            actor: null,
            before: { status: "active" },
            after: { status: "superseded" },
            detail: { verdict: "dup", score: 0.9 },
            undone: true,
            undone_at: "2026-08-03T05:00:00Z",
            undone_by: "alice",
            undo_batch_id: "batch-xyz",
            undoable: false,
            undo_blocked_reason: "already_undone",
          },
        ],
      },
      {
        object_id: OBJECT_B,
        project: "darkmem",
        actions: [
          {
            event_id: 103,
            created_at: "2026-08-03T02:03:00Z",
            action: "refine",
            object_id: OBJECT_B,
            project: "darkmem",
            detector: "dedup",
            origin: null,
            actor: null,
            before: { summary: "old summary" },
            after: { summary: "new summary" },
            detail: { fields: ["summary"] },
            undone: false,
            undone_at: null,
            undone_by: null,
            undo_batch_id: null,
            undoable: true,
            undo_blocked_reason: null,
          },
        ],
      },
    ],
  }
}

function mockReads() {
  vi.mocked(apiFetch).mockImplementation((path: string, opts?: RequestInit) => {
    if (!opts || opts.method === undefined) {
      if (path.startsWith("/dream-digest/cycles/")) {
        return Promise.resolve(digestResponse())
      }
      if (path.startsWith("/dream-digest/cycles")) {
        return Promise.resolve(CYCLES_RESPONSE)
      }
    }
    return Promise.reject(new Error(`unexpected apiFetch call: ${path}`))
  })
}

describe("diffFields (pure)", () => {
  it("unions keys from both sides and reports only the ones that differ", () => {
    expect(diffFields({ a: 1, b: 2 }, { a: 1, b: 3, c: 4 })).toEqual([
      { field: "b", from: "2", to: "3" },
      { field: "c", from: "—", to: "4" },
    ])
  })

  it("reports nothing when before and after are identical", () => {
    expect(diffFields({ status: "active" }, { status: "active" })).toEqual([])
  })
})

describe("LiveDreamDigest (DEMO off — real /dream-digest)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("invariant 14: a failed cycle-list read renders as an error, never an empty history", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(/could not load dream cycles/i)
    expect(screen.queryByText(/no consolidation cycles yet/i)).not.toBeInTheDocument()
  })

  it("renders a genuinely empty cycle history distinctly from a failed read", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(/no consolidation cycles yet/i)
  })

  it("groups actions exactly as the server returned them — never regrouped by action kind", async () => {
    mockReads()
    render(<LiveDreamDigest />, { wrapper })

    const objectHeading = await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    const groupPanel = objectHeading.closest("div.border-border")!.parentElement!
    const badges = within(groupPanel).getAllByText(/^(associate edge|supersede)$/)
    // Journal order (created_at 02:01 then 02:02): associate, then subsume —
    // exactly the interleaving the fixture set up, not a by-kind sort.
    expect(badges.map((b) => b.textContent)).toEqual(["associate edge", "supersede"])
  })

  it("every action shows what changed", async () => {
    mockReads()
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    // subsume's before/after
    expect(screen.getByText(/status:/)).toBeInTheDocument()
    expect(screen.getByText(/active/)).toBeInTheDocument()
    expect(screen.getByText(/superseded/)).toBeInTheDocument()
    // refine's before/after, in the other object's group
    expect(screen.getByText(/old summary/)).toBeInTheDocument()
    expect(screen.getByText(/new summary/)).toBeInTheDocument()
  })

  it("an undone action still appears, marked undone — never dropped from the list", async () => {
    mockReads()
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    // Event 102 is journalled undone: it must still render its row (with the
    // supersede badge asserted above) and carry the undone marker and actor.
    expect(screen.getByText(/undone — journaled/)).toBeInTheDocument()
    expect(screen.getByText(/alice/)).toBeInTheDocument()
  })

  it("undo is reachable per-action", async () => {
    mockReads()
    const user = userEvent.setup()
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    const undoButtons = screen.getAllByRole("button", { name: /^undo$/i })
    await user.click(undoButtons[0]!)

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/dream-digest/actions/101/undo",
        expect.objectContaining({ method: "POST" }),
      ),
    )
  })

  it("undo is reachable per-batch (object group), naming exactly the eligible ids", async () => {
    mockReads()
    const user = userEvent.setup()
    render(<LiveDreamDigest />, { wrapper })

    const objectHeading = await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    const groupPanelA = objectHeading.closest("div.border-border")!.parentElement!
    // Object A has one eligible action (101) and one already-undone (102) —
    // the group button must name only 101, never silently drop it either.
    // Scoped to object A's panel: object B's group also reads "(1)".
    const groupButton = within(groupPanelA).getByRole("button", {
      name: /undo group \(1\)/i,
    })
    await user.click(groupButton)

    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: /^undo$/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        `/dream-digest/cycles/${CYCLE_ID}/undo`,
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ event_ids: [101] }),
        }),
      ),
    )
  })

  it("409-then-refetch: a refusal is reported as 'nothing happened' and the digest re-reads", async () => {
    let postCount = 0
    vi.mocked(apiFetch).mockImplementation((path: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        postCount += 1
        return Promise.reject(
          new ApiError("conflict", 409, [
            { event_id: 101, action: "associate", reason: "state_changed" },
          ]),
        )
      }
      if (path.startsWith("/dream-digest/cycles/")) return Promise.resolve(digestResponse())
      return Promise.resolve(CYCLES_RESPONSE)
    })
    const user = userEvent.setup()
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    const readsBeforeUndo = vi
      .mocked(apiFetch)
      .mock.calls.filter((c) => c[1]?.method === undefined).length

    await user.click(screen.getAllByRole("button", { name: /^undo$/i })[0]!)

    await waitFor(() => expect(postCount).toBe(1))
    await waitFor(() => {
      const readsAfter = vi
        .mocked(apiFetch)
        .mock.calls.filter((c) => c[1]?.method === undefined).length
      // The digest and cycle list are re-read after the settle, on a
      // refusal exactly as on a success — never patched locally.
      expect(readsAfter).toBeGreaterThan(readsBeforeUndo)
    })

    expect(toast.error).toHaveBeenCalledWith(
      expect.stringMatching(/refused, nothing happened/i),
      expect.anything(),
    )
  })

  it("a non-409 undo failure is reported distinctly as 'state unknown', not as a refusal", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, opts?: RequestInit) => {
      if (opts?.method === "POST") return Promise.reject(new ApiError("boom", 500))
      if (path.startsWith("/dream-digest/cycles/")) return Promise.resolve(digestResponse())
      return Promise.resolve(CYCLES_RESPONSE)
    })
    const user = userEvent.setup()
    render(<LiveDreamDigest />, { wrapper })

    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)
    await user.click(screen.getAllByRole("button", { name: /^undo$/i })[0]!)

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringMatching(/state unknown/i),
        expect.anything(),
      ),
    )
    // The two outcomes must never share a message — collapsing "refused"
    // into "state unknown" (or the reverse) is exactly the shape this task
    // was told to avoid.
    expect(toast.error).not.toHaveBeenCalledWith(
      expect.stringMatching(/refused, nothing happened/i),
      expect.anything(),
    )
  })

  it("Simple mode collapses technical detail but never an honesty label", async () => {
    mockReads()
    useDetailLevel.setState({ level: "advanced" })
    const { rerender } = render(<LiveDreamDigest />, { wrapper })
    await screen.findByText(`object ${OBJECT_A.slice(0, 8)}`)

    // Advanced: the technical event-id/detail line is present.
    expect(screen.getByText(/event #101/)).toBeInTheDocument()

    useDetailLevel.setState({ level: "simple" })
    rerender(<LiveDreamDigest />)

    // Collapsed: the raw event id / detail JSON line is gone.
    expect(screen.queryByText(/event #101/)).not.toBeInTheDocument()
    // Never collapsed: undo reachability, the undone marker, and the
    // before/after diff — the honesty and substance of the row.
    expect(screen.getAllByRole("button", { name: /^undo$/i }).length).toBeGreaterThan(0)
    expect(screen.getByText(/undone — journaled/)).toBeInTheDocument()
    expect(screen.getByText(/status:/)).toBeInTheDocument()
  })
})
