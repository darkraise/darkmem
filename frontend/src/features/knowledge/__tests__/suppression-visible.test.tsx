import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// T2.95 emits `label_suppressed` on every fact-bearing surface: the reason a
// promoted rung was withheld for want of its evidence record. It was declared
// on the frontend API types — with a comment explaining exactly why it matters
// — and rendered by nothing, so "suppression must be visible" held for API
// readers and failed at the screen. A suppressed `corroborated` and a genuine
// `candidate` were pixel-identical, which is the difference between "not yet
// corroborated" and "corroborated, but we have not earned the right to say so".
//
// This guards the render, not the plumbing: the field reaching FactRowData is
// what the type checker already enforces.
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))

import { SuppressedBadge } from "../components/fact-parts"

const REASON =
  "verification_unmeasured: the corroboration ladder has no G-C evidence " +
  "record, so promoted statuses are withheld and this row is served as a " +
  "candidate."

describe("SuppressedBadge", () => {
  it("tells the reader the label was withheld", () => {
    render(<SuppressedBadge reason={REASON} />)
    expect(screen.getByText("label withheld")).toBeInTheDocument()
  })

  it("carries the gate's own sentence rather than a paraphrase", () => {
    render(<SuppressedBadge reason={REASON} />)
    // The reason arrives as a full sentence from claim_gates. This surface
    // must not re-word it: a paraphrase is a second producer of the claim.
    expect(screen.getByTitle(REASON)).toBeInTheDocument()
  })

  it("is visually distinguishable from the under-sourced caution", async () => {
    const { UnderSourcedBadge } = await import("../components/fact-parts")
    const { container: suppressed } = render(<SuppressedBadge reason={REASON} />)
    const { container: underSourced } = render(<UnderSourcedBadge />)
    // Different overlays for different facts about a row: one says the rung is
    // real but slipping, the other says the rung is real but unsayable.
    expect(suppressed.textContent).not.toBe(underSourced.textContent)
  })
})
