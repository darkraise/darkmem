import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, to: _to, params: _params, ...rest }: { children?: ReactNode; [key: string]: unknown }) => (
    <a {...rest}>{children}</a>
  ),
}))

const prune = vi.fn()
const supersede = vi.fn()
const confirmDedup = vi.fn()
let prunePending = false
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBulkPrune: () => ({ mutate: prune, isPending: prunePending }),
  useBulkSupersede: () => ({ mutate: supersede }),
  useBulkConfirmDedup: () => ({ mutate: confirmDedup }),
  useUndoDreamCycle: () => ({ mutate: vi.fn() }),
}))

interface Page {
  project?: string
  limit: number
  offset: number
}
const empty = { rows: [], total: 0, loading: false, error: false }
let lowTotal = 25
let dupTotal = 0
const memoryRow = (project: string | undefined, offset: number, index: number) => ({
  id: `m-${project ?? "all"}-${offset + index}`,
  project: project ?? "all",
  content_preview: `memory ${project ?? "all"} ${offset + index}`,
  confidence: 0.2,
  expires_at: null,
  status: "active",
  superseded_by: null,
  reason: "low confidence",
  created_at: "2026-07-01T00:00:00Z",
})
const dupRow = (offset: number, index: number) => ({
  id: `d-${offset + index}`,
  source_memory_id: `s-${offset + index}`,
  target_memory_id: `t-${offset + index}`,
  rel_type: "NEAR_DUPLICATE",
  project: "p",
  score: 0.95,
  verdict: null,
  hygiene_state: null,
  detected_at: null,
  created_at: "2026-07-01T00:00:00Z",
  source_content_preview: `source ${offset + index}`,
  source_created_at: "2026-07-01T00:00:00Z",
  target_content_preview: `target ${offset + index}`,
  target_created_at: "2026-07-02T00:00:00Z",
})
const page = (total: number, { offset, limit }: Page, make: (i: number) => object) => ({
  rows: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => make(i)),
  total,
  loading: false,
  error: false,
})

vi.mock("../../use-hygiene-queue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../use-hygiene-queue")>()),
  useHygieneLowConfidenceRows: (q: Page) =>
    page(lowTotal, q, (i) => memoryRow(q.project, q.offset, i)),
  useHygieneDuplicateRows: (q: Page) => page(dupTotal, q, (i) => dupRow(q.offset, i)),
  useHygieneExpiringRows: () => empty,
  useHygieneSupersededRows: () => empty,
}))

import { toast } from "darkraise-ui/components/sonner"
import { HygieneQueue } from "../hygiene-queue"

const lowShell = () => screen.getByRole("region", { name: "Low-confidence memories" })

async function pick(label: RegExp) {
  await userEvent.click(screen.getByRole("checkbox", { name: label }))
}

async function confirm() {
  const dialog = await screen.findByRole("alertdialog")
  const title = within(dialog).getByRole("heading").textContent
  await userEvent.click(within(dialog).getByRole("button", { name: /prune|supersede|confirm/i }))
  return title
}

beforeEach(() => {
  vi.clearAllMocks()
  lowTotal = 25
  dupTotal = 0
  prunePending = false
})

describe("hygiene queue selection", () => {
  it("a project change clears the selection", async () => {
    const { rerender } = render(<HygieneQueue project="a" />)
    for (const n of [0, 1, 2]) await pick(new RegExp(`memory a ${n}$`))
    rerender(<HygieneQueue project="b" />)
    await pick(/memory b 4$/)
    await userEvent.click(within(lowShell()).getByRole("button", { name: /^prune$/i }))
    expect(await confirm()).toBe("Prune 1 row?")
    expect(prune.mock.calls[0]![0]).toEqual(["m-b-4"])
  })

  it("a page change clears the selection", async () => {
    render(<HygieneQueue project="a" />)
    for (const n of [0, 1, 2]) await pick(new RegExp(`memory a ${n}$`))
    await userEvent.click(within(lowShell()).getByRole("link", { name: /next page/i }))
    await pick(/memory a 11$/)
    await userEvent.click(within(lowShell()).getByRole("button", { name: /^prune$/i }))
    expect(await confirm()).toBe("Prune 1 row?")
    expect(prune.mock.calls[0]![0]).toEqual(["m-a-11"])
  })

  it("a bulk action acts on exactly the selected rows on screen", async () => {
    dupTotal = 25
    render(<HygieneQueue project="p" />)
    const dupShell = () => screen.getByRole("region", { name: "Candidate duplicates" })
    await userEvent.click(within(dupShell()).getByRole("link", { name: /next page/i }))
    for (const n of [10, 11]) await pick(new RegExp(`pair d-${n}$`))
    await userEvent.click(within(dupShell()).getByRole("link", { name: /previous page/i }))
    for (const n of [0, 1, 2, 3, 4]) await pick(new RegExp(`pair d-${n}$`))
    expect(within(dupShell()).getByText("5 pairs selected")).toBeInTheDocument()

    await userEvent.click(within(dupShell()).getByRole("button", { name: /supersede instead/i }))
    expect(await confirm()).toBe("Supersede 5 duplicate pairs?")
    expect(supersede.mock.calls[0]![0]).toHaveLength(5)

    await userEvent.click(within(dupShell()).getByRole("button", { name: /confirm dedup/i }))
    expect(await confirm()).toBe("Confirm 5 duplicate pairs?")
    expect(confirmDedup.mock.calls[0]![0]).toEqual(["d-0", "d-1", "d-2", "d-3", "d-4"])

    for (const n of [0, 1, 2, 3, 4]) await pick(new RegExp(`memory p ${n}$`))
    await userEvent.click(within(lowShell()).getByRole("button", { name: /^prune$/i }))
    expect(await confirm()).toBe("Prune 5 rows?")
    expect(prune.mock.calls[0]![0]).toEqual(["m-p-0", "m-p-1", "m-p-2", "m-p-3", "m-p-4"])
  })

  it("a prune in flight cannot be sent again", async () => {
    const { rerender } = render(<HygieneQueue project="p" />)
    for (const n of [0, 1]) await pick(new RegExp(`memory p ${n}$`))
    const button = within(lowShell()).getByRole("button", { name: /^prune$/i })
    expect(button).toBeEnabled()

    prunePending = true
    rerender(<HygieneQueue project="p" />)
    expect(within(lowShell()).getByRole("button", { name: /^prune$/i })).toBeDisabled()
  })

  it("a partial failure names the counts and keeps failed rows selected", async () => {
    prune.mockImplementation((ids: string[], options: { onSuccess: (r: unknown) => void }) =>
      options.onSuccess({
        cycle_id: "c1",
        results: ids.map((id, index) => ({
          id,
          applied: index < 3,
          event_id: index < 3 ? index : null,
          reason: index < 3 ? null : "terminal",
        })),
      }),
    )
    render(<HygieneQueue project="p" />)
    for (const n of [0, 1, 2, 3, 4]) await pick(new RegExp(`memory p ${n}$`))
    await userEvent.click(within(lowShell()).getByRole("button", { name: /^prune$/i }))
    await confirm()

    expect(toast.error).toHaveBeenCalledWith(
      expect.stringContaining("3 succeeded, 2 failed"),
      expect.anything(),
    )
    const checked = screen
      .getAllByRole("checkbox")
      .filter((box) => box.getAttribute("aria-checked") === "true" || (box as HTMLInputElement).checked)
      .map((box) => box.getAttribute("aria-label"))
    expect(checked).toEqual(["Select memory p 3", "Select memory p 4"])
    expect(within(lowShell()).getByText("2 rows selected")).toBeInTheDocument()
  })
})
