/**
 * Types for the Progress board — a projection of the planning corpus.
 *
 * Spec: `docs/superpowers/specs/2026-09-04-progress-board-design.md`. The board
 * derives from the filed planning documents and the work log, and writes
 * nothing.
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

/**
 * A plan task's reference: the plan's code, a dash, and the task's number in
 * the plan (`CRF-6` is "Task 6" of `comprehensive-review-fixes`). The number
 * is the one an agent already uses for the task, so the reference is that
 * number made unique across the project's plans.
 */
export const PLAN_REF = /^[A-Z0-9]+-\d+[A-Z]?$/

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
  /** The task's board reference: `T3.01` for an epic task, `CRF-6` for a
   *  plan task. Unique across one project's board. */
  id: string
  /** What `#` looks up: `3.01` for `T3.01`, `6` for `CRF-6`. Not unique --
   *  every plan has a task 1. */
  number: string
  title: string
  /** The `## Lane X — …` heading this task sits under, or `null` outside one. */
  lane: string | null
  /** The backtick metadata line, split on each pair's first colon. */
  meta: Record<string, string>
  /** The implementer's definition-of-done checklist. Never a progress measure
   *  for an epic task; a plan task's steps are, see `plan-status.ts`. */
  doneWhen: ChecklistItem[]
  /** A plan task's predecessor in its plan, which it waits on: plans execute
   *  in task order unless they say otherwise. Absent for epic tasks, whose
   *  dependencies are the declared `Depends:` metadata. */
  after?: string
  /** The heading block that opens this task's section in its document, when
   *  known, so the board can open the plan at the task. */
  blockId?: string | null
}

export interface ChecklistItem {
  text: string
  checked: boolean
}

export interface Epic {
  /** `E3`, `EH1`, `M1` — the id prefix, from the `# ` heading. For a plan,
   *  its code (`CRF`). */
  key: string
  /** An epic file under `planning/tasks/`, or a plan under `plans/`. */
  kind: "epic" | "plan"
  filename: string
  /** The filed document this group was read from. */
  documentId?: string
  title: string
  goal: string | null
  entryGate: string | null
  doneWhen: string | null
  branch: string | null
  lanes: string[]
  tasks: EpicTask[]
}
