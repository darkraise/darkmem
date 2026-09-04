import { TASK_ID, type Epic, type EpicTask, type LedgerRow } from "../types"
import { gateHeldTaskIds, type EpicGate } from "./parse-gates"

export interface StartableVerdict {
  startable: boolean
  /** Why not, for the card. Empty when startable. */
  reason: string | null
}

/** Statuses that satisfy a dependency. `dropped` counts: its premise no
 *  longer holds, so nothing waits on it. */
const SATISFIED = new Set(["done", "dropped"])

/**
 * A `Depends:` cell, split into the ids it names and whether it also carries
 * prose no board can resolve.
 *
 * `Depends: —` is none. `Depends: T2.26, T2.54` is two ids. And
 * `Depends: T2.109, **an owner-recorded argument**` is one id plus a human
 * precondition -- which must not be silently dropped, or the board reports a
 * task as startable when the thing actually blocking it is a decision nobody
 * has taken.
 */
export function parseDepends(raw: string | undefined): {
  ids: string[]
  prose: string[]
} {
  const ids: string[] = []
  const prose: string[] = []
  if (!raw) return { ids, prose }

  for (const part of raw.split(",")) {
    const token = part.trim()
    if (!token || token === "—" || token === "-") continue
    if (TASK_ID.test(token)) ids.push(token)
    else prose.push(token)
  }
  return { ids, prose }
}

/**
 * "What can I start right now?" -- the one question the board answers that
 * neither file answers alone. It is a three-way join the reader currently
 * does in their head, per task: the ledger row's status, every dependency's
 * row, and the epic's entry gate.
 */
export function startableVerdict(
  task: EpicTask,
  row: LedgerRow | undefined,
  epic: Epic,
  gate: EpicGate | undefined,
  rows: Map<string, LedgerRow>,
): StartableVerdict {
  if (!row) return { startable: false, reason: "no ledger row" }
  if (row.status !== "todo") {
    return { startable: false, reason: `status is ${row.rawStatus}` }
  }

  if (gate?.holding) {
    const held = gateHeldTaskIds(epic.entryGate, epic.tasks.map((t) => t.id))
    // A gate that names specific tasks holds only those. One that names none
    // holds the epic.
    if (held.size === 0 || held.has(task.id)) {
      return { startable: false, reason: `held by ${gate.text}` }
    }
  }

  const { prose } = parseDepends(task.meta.Depends)
  if (prose.length > 0) {
    return { startable: false, reason: `depends on ${prose.join(", ")}` }
  }

  const unmet = unmetDependencies(task, rows)
  if (unmet.length > 0) {
    return { startable: false, reason: `waiting on ${unmet.join(", ")}` }
  }

  return { startable: true, reason: null }
}

/** The dependency ids of `task` that are not yet satisfied. */
export function unmetDependencies(
  task: EpicTask,
  rows: Map<string, LedgerRow>,
): string[] {
  return parseDepends(task.meta.Depends).ids.filter((id) => {
    const dep = rows.get(id)
    return !dep || !SATISFIED.has(dep.rawStatus)
  })
}
