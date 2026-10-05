import type { ChecklistItem, LedgerStatus } from "../types"

/** Where a plan task's status was read from, shown beside it so a reader can
 *  tell a recorded transition from an inference. */
export type PlanStatusSource = "completed" | "ledger" | "steps"

export const PLAN_STATUS_SOURCE_LABEL: Record<PlanStatusSource, string> = {
  completed: "the plan is recorded in plans/completed.md",
  ledger: "the plan's work-log ledger",
  steps: "the task's step checkboxes in the plan",
}

/**
 * A plan task's status, from the strongest signal that speaks to it:
 *
 * 1. **`plans/completed.md`** records the plan as merged, so every task is
 *    `done` -- except one the ledger dropped, which stays `dropped`. Many
 *    landed plans leave their step boxes unticked (`pages-increment-b1`
 *    ticks 5 of 99), so the boxes must not outvote the merge record.
 * 2. **The ledger** -- the execution log dr-superpowers keeps per plan in the
 *    work log -- records the transition the agent made, latest line winning.
 * 3. **The task's own step checkboxes**, which a dr-superpowers plan declares
 *    as its tracking syntax: all ticked is `done`, some is `wip`, none `todo`.
 */
export function planTaskStatus({
  number,
  completed,
  ledger,
  steps,
}: {
  number: string
  completed: boolean
  ledger: Map<string, LedgerStatus> | undefined
  steps: ChecklistItem[] | undefined
}): { status: LedgerStatus; source: PlanStatusSource } {
  const recorded = ledger?.get(number)
  if (completed) {
    return { status: recorded === "dropped" ? "dropped" : "done", source: "completed" }
  }
  if (recorded) return { status: recorded, source: "ledger" }

  const items = steps ?? []
  const ticked = items.filter((s) => s.checked).length
  const status: LedgerStatus =
    items.length > 0 && ticked === items.length ? "done" : ticked > 0 ? "wip" : "todo"
  return { status, source: "steps" }
}
