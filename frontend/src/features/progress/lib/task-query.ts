import type { BoardTask } from "../use-progress-corpus"

/**
 * What the board's filter box was asked for.
 *
 * - `#6` → every task numbered 6 (one per plan that has a task 6). `#3.01`
 *   finds epic task `T3.01` the same way.
 * - `CRF-6`, `crf#6`, `CRF 6` → the one task with that reference.
 * - `T3.01` → the epic task with that id.
 * - anything else → a text match over reference and title.
 */
export type TaskQuery =
  | { kind: "empty" }
  | { kind: "number"; number: string }
  | { kind: "ref"; ref: string }
  | { kind: "text"; text: string }

const NUMBER = /^#\s*(\d+(?:\.\d+[a-z]?)?)$/i
const PLAN_REF = /^([a-z0-9]+)\s*[-#\s]\s*(\d+)$/i
const EPIC_ID = /^T[A-Z]?\d+\.\d+[a-z]?$/i

/** `#06` and `#6` are one task number; an epic number keeps its dotted form. */
function normalizeNumber(raw: string): string {
  return /^\d+$/.test(raw) ? String(Number(raw)) : raw.toLowerCase()
}

export function parseTaskQuery(raw: string): TaskQuery {
  const q = raw.trim()
  if (!q) return { kind: "empty" }

  const number = NUMBER.exec(q)?.[1]
  if (number) return { kind: "number", number: normalizeNumber(number) }

  if (EPIC_ID.test(q)) return { kind: "ref", ref: q.toUpperCase() }

  const ref = PLAN_REF.exec(q)
  if (ref?.[1] && ref[2]) {
    return { kind: "ref", ref: `${ref[1].toUpperCase()}-${normalizeNumber(ref[2])}` }
  }
  return { kind: "text", text: q.toLowerCase() }
}

/** True when `entry` is what the query names exactly -- the candidates the
 *  filter box's Enter opens. A text query names nothing exactly. */
export function isExactMatch(entry: BoardTask, query: TaskQuery): boolean {
  if (query.kind === "number") return entry.task.number.toLowerCase() === query.number
  if (query.kind === "ref") return entry.task.id.toUpperCase() === query.ref
  return false
}

/**
 * Whether `entry` passes the filter box.
 *
 * A reference query also passes a text match on the raw string, so typing a
 * hyphenated title fragment (`e2e-2`, read as code `E2E`, task 2) still finds
 * the titles that contain it.
 */
export function matchesTaskQuery(entry: BoardTask, query: TaskQuery, raw: string): boolean {
  if (query.kind === "empty") return true
  if (isExactMatch(entry, query)) return true
  if (query.kind === "number") return false
  const text = raw.trim().toLowerCase()
  return `${entry.task.id} ${entry.task.title}`.toLowerCase().includes(text)
}

/** The task a reference names (`CRF-6`, `crf#6`, `T3.01`), or null. */
export function findTaskByRef(tasks: BoardTask[], ref: string | null | undefined): BoardTask | null {
  if (!ref) return null
  const query = parseTaskQuery(ref)
  if (query.kind !== "ref") return null
  return tasks.find((t) => isExactMatch(t, query)) ?? null
}
