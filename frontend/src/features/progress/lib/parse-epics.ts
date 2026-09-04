import { TASK_ID, type ChecklistItem, type Epic, type EpicTask } from "../types"

const CHECKLIST = /^\s*-\s\[( |x|X)\]\s+(.*)$/
const TASK_HEADING = /^####\s+(\S+)\s+—\s*(.*)$/
const LANE_HEADING = /^##\s+(Lane\s.*)$/
const EPIC_HEADING = /^#\s+(\S+)\s+—\s*(.*)$/

/**
 * A `**Label:**` field, which runs to the next blank line.
 *
 * Every one of these in the corpus is multi-line prose wrapped at ~95 columns,
 * so reading only the label's own line truncates every entry gate mid-sentence
 * — and the entry gate is what the startable filter reads.
 */
function field(lines: string[], label: string): string | null {
  const marker = `**${label}:**`
  const parts: string[] = []
  let found = false

  for (const line of lines) {
    if (!found) {
      if (!line.startsWith(marker)) continue
      found = true
      parts.push(line.slice(marker.length).trim())
      continue
    }
    if (line.trim() === "") break
    parts.push(line.trim())
  }

  if (!found) return null
  return parts.join(" ").trim() || null
}

function checklist(lines: string[]): ChecklistItem[] {
  const items: ChecklistItem[] = []
  for (const line of lines) {
    const m = CHECKLIST.exec(line)
    if (m) items.push({ text: (m[2] ?? "").trim(), checked: (m[1] ?? "").toLowerCase() === "x" })
  }
  return items
}

/**
 * The backtick metadata line under a task heading:
 *
 *     `Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: —` · ...
 *
 * Split on the FIRST colon only — `Doc: 09 §4.1–§4.2` and `Gate: G-D (entry)`
 * both carry further punctuation that a greedy split eats.
 */
function metadata(lines: string[]): Record<string, string> {
  const line = lines.find((l) => l.startsWith("`Model:"))
  if (!line) return {}

  const meta: Record<string, string> = {}
  for (const pair of line.split("·")) {
    const inner = pair.trim().replace(/^`/, "").replace(/`$/, "")
    const colon = inner.indexOf(":")
    if (colon === -1) continue
    meta[inner.slice(0, colon).trim()] = inner.slice(colon + 1).trim()
  }
  return meta
}

function isBoundary(line: string): boolean {
  return TASK_HEADING.test(line) || LANE_HEADING.test(line) || line.startsWith("# ")
}

/**
 * One `docs/planning/tasks/*.md` file → its epic and tasks.
 *
 * `EH2-dotnet-migration.md` is deliberately task-free and carries neither a
 * `**Goal:**` nor an `**Entry gate:**` — it must parse to an epic with an empty
 * task list rather than throwing, because a parser that throws on it takes the
 * whole board down.
 */
export function parseEpics(markdown: string, filename: string): Epic {
  const lines = markdown.split("\n")

  let heading: RegExpExecArray | null = null
  for (const line of lines) {
    heading = EPIC_HEADING.exec(line)
    if (heading) break
  }

  // The epic's own fields live above the first lane or task heading; scoping to
  // that prefix keeps a task's `**Done when:**` from being read as the epic's.
  const bodyStart = lines.findIndex((l) => LANE_HEADING.test(l) || TASK_HEADING.test(l))
  const preamble = bodyStart === -1 ? lines : lines.slice(0, bodyStart)

  const lanes: string[] = []
  const tasks: EpicTask[] = []
  let lane: string | null = null

  for (const [i, line] of lines.entries()) {
    const laneMatch = LANE_HEADING.exec(line)
    if (laneMatch) {
      lane = (laneMatch[1] ?? "").trim()
      lanes.push(lane)
      continue
    }

    const taskMatch = TASK_HEADING.exec(line)
    const id = taskMatch?.[1]
    if (!taskMatch || !id || !TASK_ID.test(id)) continue

    let end = lines.length
    for (let j = i + 1; j < lines.length; j++) {
      if (isBoundary(lines[j] ?? "")) {
        end = j
        break
      }
    }
    const body = lines.slice(i + 1, end)

    tasks.push({
      id,
      title: (taskMatch[2] ?? "").trim(),
      lane,
      meta: metadata(body),
      doneWhen: checklist(body),
    })
  }

  return {
    key: heading?.[1] ?? filename.replace(/-.*$/, ""),
    filename,
    title: heading?.[2]?.trim() ?? filename,
    goal: field(preamble, "Goal"),
    entryGate: field(preamble, "Entry gate"),
    doneWhen: field(preamble, "Done when"),
    branch: field(preamble, "Epic branch"),
    lanes,
    tasks,
  }
}
