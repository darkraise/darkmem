/**
 * Types for the Progress board — a projection of the planning corpus.
 *
 * Spec: `docs/superpowers/specs/2026-09-04-progress-board-design.md`. The board
 * derives from two committed markdown files and writes nothing.
 */

/** `progress.md`'s status vocabulary, in workflow order. */
export const LEDGER_STATUSES = [
  "todo",
  "wip",
  "blocked",
  "review",
  "done",
  "dropped",
] as const

export type LedgerStatus = (typeof LEDGER_STATUSES)[number]

export function isLedgerStatus(value: string): value is LedgerStatus {
  return (LEDGER_STATUSES as readonly string[]).includes(value)
}

/**
 * Task ids carry an optional epic letter: `T3.01`, `T1.42a`, `TH1.14`.
 *
 * The `H` is not optional decoration — EH1's 18 tasks all use it, and a
 * pattern without it drops every one of them while still parsing 291 rows and
 * looking healthy.
 */
export const TASK_ID = /^T[A-Z]?\d+\.\d+[a-z]?$/

export interface LedgerRow {
  id: string
  title: string
  size: string
  model: string
  effort: string
  version: string
  owner: string
  /** `null` when the file carries a value outside the vocabulary. */
  status: LedgerStatus | null
  /** Always the file's own text, so an unrecognised value stays inspectable. */
  rawStatus: string
  commit: string
  review: string
  note: string
}

export interface EpicTask {
  id: string
  title: string
  /** The `## Lane X — …` heading this task sits under, or `null` outside one. */
  lane: string | null
  /** The backtick metadata line, split on each pair's first colon. */
  meta: Record<string, string>
  /** The implementer's definition-of-done checklist. Never a progress measure. */
  doneWhen: ChecklistItem[]
}

export interface ChecklistItem {
  text: string
  checked: boolean
}

export interface Epic {
  /** `E3`, `EH1`, `M1` — the id prefix, from the `# ` heading. */
  key: string
  filename: string
  title: string
  goal: string | null
  entryGate: string | null
  doneWhen: string | null
  branch: string | null
  lanes: string[]
  tasks: EpicTask[]
}
