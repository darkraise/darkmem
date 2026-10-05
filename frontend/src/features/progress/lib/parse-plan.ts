import type { OutlineNode } from "@/hooks/api"
import { LEDGER_STATUSES, type ChecklistItem, type Epic, type EpicTask, type LedgerStatus } from "../types"
import { planStem } from "./plan-code"

/**
 * A plan's task heading, as the outline serves it (marker stripped):
 * `Task 6: Incremental code convergence`. Plans head a task at `###` (a few
 * older ones at `##`), mirroring the `## Task index` row of the same number,
 * so the number is the one an agent already uses for the task. A number may
 * carry a letter for a task inserted later (`Task 5a`, `Task 8A`).
 */
const TASK_HEADING = /^Task\s+(\d+[a-z]?)\s*(?:[:.—–-]\s*(.*))?$/i
const HEADING_LINE = /^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$/
const CHECKLIST = /^\s*[-*]\s\[( |x|X)\]\s+(.*)$/

/** `06` and `6` are one task; a suffix letter is compared lowercase. */
export function normalizeTaskNumber(raw: string): string {
  const m = /^(\d+)([a-z]?)$/i.exec(raw.trim())
  return m?.[1] ? `${Number(m[1])}${(m[2] ?? "").toLowerCase()}` : raw.trim().toLowerCase()
}

/**
 * CommonMark's fenced-code rule (§4.5), which the server's markdown-it parse
 * (and so the outline) follows: a fence opens on three or more backticks or
 * tildes indented at most three spaces, and only a run of the same character,
 * at least as long and with nothing after it, closes it. A plain toggle on any
 * fence-looking line inverts for the rest of the file on the first stray
 * fence; `2026-06-02-login-revamp.md` has one, and a toggle loses its Tasks 7
 * and 8.
 */
function fenceTracker(): (line: string) => boolean {
  let open: { char: string; length: number } | null = null
  return (line) => {
    const m = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line)
    if (!open) {
      if (!m?.[1]) return false
      // A backtick fence's info string may not itself hold a backtick.
      if (m[1][0] === "`" && (m[2] ?? "").includes("`")) return false
      open = { char: m[1][0] ?? "`", length: m[1].length }
      return true
    }
    if (m?.[1] && m[1][0] === open.char && m[1].length >= open.length && !(m[2] ?? "").trim()) {
      open = null
    }
    return true
  }
}

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
    const number = m?.[1] && normalizeTaskNumber(m[1])
    // First heading wins: a plan that repeats a task number in a later
    // amendment section still names one task by it.
    if (!m || !number || seen.has(number)) continue
    seen.add(number)
    tasks.push({
      id: `${source.code}-${number.toUpperCase()}`,
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

  const inCode = fenceTracker()
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
    if (inCode(line)) continue

    const heading = HEADING_LINE.exec(line)
    if (!heading) continue
    const level = heading[1]?.length ?? 0
    if (current && level <= current.level) {
      close(i)
      current = null
    }
    const m = TASK_HEADING.exec((heading[2] ?? "").trim())
    if (m?.[1]) {
      current = { number: normalizeTaskNumber(m[1]), level, title: (m[2] ?? "").trim(), start: i + 1 }
    }
  }
  close(lines.length)
  return sections
}

function checklist(lines: string[]): ChecklistItem[] {
  const items: ChecklistItem[] = []
  const inCode = fenceTracker()
  for (const line of lines) {
    if (inCode(line)) continue
    const m = CHECKLIST.exec(line)
    if (m) items.push({ text: (m[2] ?? "").trim(), checked: (m[1] ?? "").toLowerCase() === "x" })
  }
  return items
}

/**
 * The plan filenames `plans/completed.md` records as landed. Each entry is a
 * list item naming its plan by path first
 * (`- 2026-09-29 \`docs/superpowers/plans/<f>.md\` — merged …`); only that
 * first path counts, so a note on the line naming another plan ("supersedes
 * \`b.md\`") does not mark it landed. Matching on the filename keeps a
 * `docs/` prefix (this repository's import) and the mirror's bare
 * `superpowers/` paths alike.
 */
export function parseCompletedPlans(markdown: string): Set<string> {
  const names = new Set<string>()
  for (const line of markdown.split("\n")) {
    if (!/^\s*[-*]\s/.test(line)) continue
    const name = /([\w.-]+\.md)\b/.exec(line)?.[1]
    if (name && name !== "completed.md") names.add(name)
  }
  return names
}

const LEDGER_TASK = /^\s*(?:[-*]\s+)?(?:\|\s*)?(?:\*\*)?(?:Task\s+|#)(\d+[a-z]?)\b(.*)$/i
const LEDGER_TABLE_TASK = /^\s*\|\s*(\d+[a-z]?)\s*\|(.*)$/i
/** A segment that IS a status: the word, then nothing, or a trailer opened
 *  by punctuation (`done, review approved`, `blocked (fixture)`, `done ✅`).
 *  A word running on into prose (`review comments`, `done-when`) is not. */
const STATUS_SEGMENT = new RegExp(
  `^(${LEDGER_STATUSES.join("|")})(?![\\w-])(?:\\s*$|\\s*[^\\w\\s])`,
  "i",
)

/**
 * Task statuses from a plan's execution ledger (the work log's `ledger`
 * entries, concatenated), latest line winning.
 *
 * A ledger line names its task the way the agent does -- `Task 3: ... — done`,
 * `#3 review`, `#3 blocked: waiting on fixture`, or a `| 3 | ... |` table row.
 * The rest of the line is split on its separators (` — `, `|`, `:`), and its
 * status is the last segment that consists of a vocabulary word, so
 * `Task 3: endpoint — done, review approved` reads `done`. A word inside prose
 * (`Task 3: addressed the review comments`) is not a status: a ledger is an
 * event log, most of its lines are narrative, and the ledger outranks the
 * plan's checkboxes, so a misread line would mislabel the task.
 */
export function parsePlanLedger(text: string): Map<string, LedgerStatus> {
  const statuses = new Map<string, LedgerStatus>()
  for (const line of text.split("\n")) {
    const m = LEDGER_TASK.exec(line) ?? LEDGER_TABLE_TASK.exec(line)
    const number = m?.[1]
    if (!m || !number) continue
    const segments = (m[2] ?? "")
      .split(/\s[—–-]\s|\||:/)
      .map((p) => p.replace(/\*\*/g, "").trim())
      .filter(Boolean)
    let status: LedgerStatus | null = null
    for (const segment of segments) {
      const word = STATUS_SEGMENT.exec(segment)?.[1]
      if (word) status = word.toLowerCase() as LedgerStatus
    }
    if (status) statuses.set(normalizeTaskNumber(number), status)
  }
  return statuses
}
