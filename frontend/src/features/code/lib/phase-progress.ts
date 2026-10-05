import type { DemoIndexPhase } from "@/demo/types"

/** One wording for indexing progress, shared by the Repositories card and the
 *  graph's indexing state so the same run never reads two different ways:
 *  `phase 06 of 14, 2 skipped`. The denominator is every phase; skipped
 *  opt-in phases are named rather than silently dropped from the count. */
export function phaseProgressLabel(
  phases: DemoIndexPhase[] | null | undefined,
) {
  if (!phases || phases.length === 0) return null
  const current = phases.find((p) => p.state === "current")
  if (!current) return null
  const skipped = phases.filter((p) => p.state === "skipped").length
  return `phase ${String(current.n).padStart(2, "0")} of ${phases.length}${
    skipped > 0 ? `, ${skipped} skipped` : ""
  }`
}

/** Share of the non-skipped phases already done, 0–100. */
export function phaseProgressPercent(
  phases: DemoIndexPhase[] | null | undefined,
) {
  if (!phases) return 0
  const active = phases.filter((p) => p.state !== "skipped").length
  const done = phases.filter((p) => p.state === "done").length
  return Math.round((done / Math.max(active, 1)) * 100)
}
