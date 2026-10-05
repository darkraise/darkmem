import type { OutlineNode } from "@/hooks/api"
import { LEDGER_STATUSES, type ChecklistItem, type Epic, type EpicTask, type LedgerStatus } from "../types"
import { planStem } from "./plan-code"

/**
 * A plan's task heading, as the outline serves it (marker stripped):
 * `Task 6: Incremental code convergence`. Every dr-superpowers plan heads each
 * task this way, mirroring its `## Task index` row of the same number, so the
 * number is the one an agent already uses for the task.
 */
const TASK_HEADING = /^Task\s+(\d+)\s*(?:[:.—–-]\s*(.*))?$/
const HEADING_LINE = /^(#{1,6})\s+(.*?)\s*#*\s*$/
const FENCE = /^\s*(```|~~~)/
const CHECKLIST = /^\s*[-*]\s\[( |x|X)\]\s+(.*)$/

export interface PlanSource {
  code: string
  filename: string
  documentId: string
  /** The document's title, used when the outline carries no `# ` heading. */
  title: string | null
}

/**
 * A plan's tasks from its outline alone -- headings, no body text -- so the
 * board can list every filed plan's tasks without reading megabytes of plan
 * source. A plan with no task headings (the older free-form plans) yields no
 * tasks, and the board leaves it out.
 */
export function planFromOutline(nodes: OutlineNode[], source: PlanSource): Epic {
  const title =
    nodes.find((n) => n.level === 1)?.text.trim() ||
    source.title ||
    planStem(source.filename)

  const tasks: EpicTask[] = []
  const seen = new Set<string>()
  for (const node of nodes) {
    const m = TASK_HEADING.exec(node.text.trim())
    const number = m?.[1] && String(Number(m[1]))
    // First heading wins: a plan that repeats a task number in a later
    // amendment section still names one task by it.
    if (!m || !number || seen.has(number)) continue
    seen.add(number)
    tasks.push({
      id: `${source.code}-${number}`,
      number,
      title: (m[2] ?? "").trim() || `Task ${number}`,
      lane: null,
      meta: {},
      doneWhen: [],
      after: tasks[tasks.length - 1]?.id,
      blockId: node.block_id,
    })
  }

  return {
    key: source.code,
    kind: "plan",
    filename: source.filename,
    documentId: source.documentId,
    title,
    goal: null,
    entryGate: null,
    doneWhen: null,
    branch: null,
    lanes: [],
    tasks,
  }
}

export interface PlanSection {
  title: string
  /** The section's markdown, heading excluded. */
  body: string
  /** The section's `- [ ]` steps, outside fenced code. */
  steps: ChecklistItem[]
}

/**
 * A plan's task sections from its source, by task number.
 *
 * Fenced code is skipped when finding headings and steps: plans quote test
 * files whose comments read `# ── Task 3: ...` and fixtures holding `- [ ]`,
 * and neither is the plan's own structure.
 */
export function parsePlanSections(markdown: string): Map<string, PlanSection> {
  const sections = new Map<string, PlanSection>()
  const lines = markdown.split("\n")

  let fenced = false
  let current: { number: string; level: number; title: string; start: number } | null = null
  const close = (end: number) => {
    if (!current || sections.has(current.number)) return
    const body = lines.slice(current.start, end)
    sections.set(current.number, {
      title: current.title,
      body: body.join("\n").trim(),
      steps: checklist(body),
    })
  }

  for (const [i, line] of lines.entries()) {
    if (FENCE.test(line)) {
      fenced = !fenced
      continue
    }
    if (fenced) continue

    const heading = HEADING_LINE.exec(line)
    if (!heading) continue
    const level = heading[1]?.length ?? 0
    if (current && level <= current.level) {
      close(i)
      current = null
    }
    const m = TASK_HEADING.exec((heading[2] ?? "").trim())
    if (m?.[1]) {
      current = { number: String(Number(m[1])), level, title: (m[2] ?? "").trim(), start: i + 1 }
    }
  }
  close(lines.length)
  return sections
}

function checklist(lines: string[]): ChecklistItem[] {
  const items: ChecklistItem[] = []
  let fenced = false
  for (const line of lines) {
    if (FENCE.test(line)) {
      fenced = !fenced
      continue
    }
    if (fenced) continue
    const m = CHECKLIST.exec(line)
    if (m) items.push({ text: (m[2] ?? "").trim(), checked: (m[1] ?? "").toLowerCase() === "x" })
  }
  return items
}

/**
 * The plan filenames `plans/completed.md` records as landed. Each line names
 * its plan by path; matching on the filename keeps a `docs/` prefix (this
 * repository's import) and the mirror's bare `superpowers/` paths alike.
 */
export function parseCompletedPlans(markdown: string): Set<string> {
  const names = new Set<string>()
  for (const m of markdown.matchAll(/([\w.-]+\.md)\b/g)) {
    const name = m[1]
    if (name && name !== "completed.md") names.add(name)
  }
  return names
}

const LEDGER_TASK = /^\s*(?:[-*]\s+)?(?:\|\s*)?(?:\*\*)?(?:Task\s+|#)(\d+)\b(.*)$/i
const LEDGER_TABLE_TASK = /^\s*\|\s*(\d+)\s*\|(.*)$/
const STATUS_WORD = new RegExp(`\\b(${LEDGER_STATUSES.join("|")})\\b`, "i")

/**
 * Task statuses from a plan's execution ledger (the work log's `ledger`
 * entries, concatenated), latest line winning.
 *
 * A ledger line names its task the way the agent does -- `Task 3: ... — done`,
 * `#3 review`, or a `| 3 | ... |` table row -- and its status is the first
 * vocabulary word after the line's last separator, so
 * `Task 3: endpoint — done, review approved` reads `done`. A line naming a
 * task but no vocabulary word is narrative, not a transition, and changes
 * nothing; a ledger is an event log, and most of its lines are not statuses.
 */
export function parsePlanLedger(text: string): Map<string, LedgerStatus> {
  const statuses = new Map<string, LedgerStatus>()
  for (const line of text.split("\n")) {
    const m = LEDGER_TASK.exec(line) ?? LEDGER_TABLE_TASK.exec(line)
    const number = m?.[1]
    if (!m || !number) continue
    const rest = m[2] ?? ""
    const parts = rest.split(/\s[—–-]\s|\||:/).map((p) => p.trim()).filter(Boolean)
    const status = statusIn(parts[parts.length - 1]) ?? statusIn(rest)
    if (status) statuses.set(String(Number(number)), status)
  }
  return statuses
}

function statusIn(text: string | undefined): LedgerStatus | null {
  const word = text ? STATUS_WORD.exec(text)?.[1] : undefined
  return word ? (word.toLowerCase() as LedgerStatus) : null
}
