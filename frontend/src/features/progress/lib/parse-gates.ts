import { TASK_ID } from "../types"

export interface EpicGate {
  /** The epic key the summary row names, e.g. `E3`. */
  key: string
  /** The Gate cell verbatim, for display. */
  text: string
  /** True when the cell records a gate still standing between this epic and
   *  its work. `CLEARED` clears; `open` and `closed` hold; anything else
   *  (`demand-gated`, `consumes implementation; gates nothing`) is not a
   *  gate and holds nothing. */
  holding: boolean
}

const SUMMARY_HEADER = "| Epic | Tasks |"

/**
 * The per-epic summary table's Gate column.
 *
 * Gate *state* lives in `progress.md` and not in the epic files, which is the
 * same scope/state split the two parsers already follow: an epic header states
 * the gate's condition ("G-D cleared"), never whether it has been met.
 *
 * `**Total**` is skipped -- it is an aggregate row, not an epic.
 */
export function parseGates(markdown: string): Map<string, EpicGate> {
  const gates = new Map<string, EpicGate>()
  let inTable = false

  for (const line of markdown.split("\n")) {
    if (line.startsWith(SUMMARY_HEADER)) {
      inTable = true
      continue
    }
    if (!inTable) continue
    if (!line.startsWith("|")) {
      inTable = false
      continue
    }

    const cells = line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim())
    if (cells.length < 2) continue

    // `E3 — Synthesis & reach` -> `E3`; `**Total**` matches nothing.
    const key = /^([A-Z]+\d+)\s+—/.exec(cells[0] ?? "")?.[1]
    if (!key) continue

    const text = cells[cells.length - 1] ?? ""
    gates.set(key, { key, text, holding: /\b(open|closed)\b/i.test(text) })
  }

  return gates
}

/**
 * The task ids an epic's entry gate holds shut, when it names any.
 *
 * E3's gate was amended to hold three named tasks rather than the whole epic,
 * on the argument that a gate certifying groundedness may only hold what
 * asserts groundedness. A board that blanked the epic would contradict the
 * file it renders.
 *
 * Scoped to ids the epic actually owns: the gate text also names the task that
 * *clears* the gate (E3 names T2.41), which belongs to another epic and is not
 * held by this one.
 */
export function gateHeldTaskIds(
  entryGate: string | null,
  ownTaskIds: Iterable<string>,
): Set<string> {
  const held = new Set<string>()
  if (!entryGate) return held

  const own = new Set(ownTaskIds)
  for (const token of entryGate.split(/[^A-Za-z0-9.]+/)) {
    if (TASK_ID.test(token) && own.has(token)) held.add(token)
  }
  return held
}
