import type {
  BoardProperty,
  BoardRecords,
  GroupableProperty,
  PlanProgress,
  TaskStep,
  Untracked,
  ViewDefinition,
} from "@/hooks/api/use-board-api"

export type RecordType = "register_row" | "plan_task"

export const REGISTER_STATES = [
  "open",
  "planned",
  "doing",
  "verify",
  "done",
  "deferred",
  "n/a",
] as const
export const TASK_STATES = ["todo", "wip", "review", "blocked", "done"] as const
/** The states whose rows need a Note (`REGISTER_NOTE_REQUIRED` in dr-forge). */
export const NOTE_REQUIRED = new Set<string>(["verify", "deferred", "n/a"])

export const PROPERTY_LABELS: Record<BoardProperty, string> = {
  type: "Type",
  title: "Title",
  number: "#",
  state: "State",
  source: "Source",
  note: "Note",
  assigned: "Assigned",
  acceptance: "Acceptance",
  plan_progress: "Plan progress",
  plan: "Plan",
  spec: "Spec",
  workstream_state: "Workstream",
  commit: "Commit",
  last_activity: "Last activity",
}
export const PROPERTIES = Object.keys(PROPERTY_LABELS) as BoardProperty[]
export const GROUPABLE: GroupableProperty[] = [
  "type",
  "state",
  "source",
  "assigned",
  "plan",
  "workstream_state",
]

export const UNTRACKED_LABEL: Record<Untracked, string> = {
  no_workstream: "untracked — no workstream names this plan",
  no_properties: "untracked — the ledger carries no task properties",
}

/** One card or table row: a register row or a plan task, flattened. */
export interface BoardRecord {
  id: string
  type: RecordType
  number: number
  /** `#12` for a register row, the heading from `Task` on for a plan task. */
  label: string
  title: string
  state: string
  rawState: string | null
  source: string
  sourceTitle: string | null
  documentId: string
  /** The register's hash when it was read: the PATCH's `expected_hash`. */
  contentHash: string | null
  blockFirst: boolean
  /** A register row's Note, or a blocked task's reason. */
  note: string | null
  noteBlank: boolean
  assigned: string | null
  acceptance: string | null
  planProgress: PlanProgress | null
  /** Why a register row's plan could not be read; its progress is then null. */
  planError: string | null
  plan: string | null
  spec: string | null
  workstreamKey: string | null
  workstreamState: "open" | "closed" | null
  commit: string | null
  lastActivity: string | null
  untracked: Untracked | null
  sharedNumber: boolean
  steps: TaskStep[]
}

export function shortName(uri: string | null): string {
  if (!uri) return ""
  const leaf = uri.split("/").pop() ?? uri
  return leaf.endsWith(".md") ? leaf.slice(0, -3) : leaf
}

export function isBlankNote(note: string | null | undefined): boolean {
  const trimmed = (note ?? "").trim()
  return trimmed === "" || trimmed === "-"
}

export function flattenRecords(data: BoardRecords): BoardRecord[] {
  const records: BoardRecord[] = []
  const planErrors = new Map(data.plans.map((plan) => [plan.uri, plan.error]))
  for (const register of data.registers) {
    for (const row of register.rows) {
      records.push({
        id: `r:${register.document_id}:${row.number}`,
        type: "register_row",
        number: row.number,
        label: `#${row.number}`,
        title: row.item,
        state: row.state,
        rawState: row.raw_state,
        source: register.uri,
        sourceTitle: register.title,
        documentId: register.document_id,
        contentHash: register.content_hash,
        blockFirst: register.block_first,
        note: row.note,
        noteBlank: row.note_blank,
        assigned: row.assigned,
        acceptance: row.acceptance,
        planProgress: row.plan_progress,
        planError: row.plan_uri ? (planErrors.get(row.plan_uri) ?? null) : null,
        plan: row.plan_uri,
        spec: null,
        workstreamKey: null,
        workstreamState: null,
        commit: null,
        lastActivity: null,
        untracked: null,
        sharedNumber: false,
        steps: [],
      })
    }
  }
  for (const plan of data.plans) {
    for (const task of plan.tasks) {
      records.push({
        id: `t:${plan.document_id}:${task.line}`,
        type: "plan_task",
        number: task.number,
        label: task.label,
        title: task.title || task.label,
        state: task.state,
        rawState: task.raw_state,
        source: plan.uri,
        sourceTitle: plan.title,
        documentId: plan.document_id,
        contentHash: null,
        blockFirst: false,
        note: task.blocked_reason,
        noteBlank: !task.blocked_reason,
        assigned: null,
        acceptance: null,
        planProgress: null,
        planError: null,
        plan: plan.uri,
        spec: plan.spec_uri,
        workstreamKey: plan.workstream?.key ?? null,
        workstreamState: plan.workstream?.state ?? null,
        commit: task.commit,
        lastActivity: task.last_activity,
        untracked: task.untracked,
        sharedNumber: task.shared_number,
        steps: task.steps,
      })
    }
  }
  return records
}

export function formatProgress(progress: PlanProgress | null): string | null {
  if (!progress) return null
  if (progress.untracked) return UNTRACKED_LABEL[progress.untracked]
  return `${progress.done} of ${progress.total} done`
}

/** A property as text: what filters match, groups key on and sorts compare. */
export function propertyValue(
  record: BoardRecord,
  property: BoardProperty,
): string | null {
  switch (property) {
    case "type":
      return record.type
    case "title":
      return record.title
    case "number":
      return String(record.number)
    case "state":
      return record.state
    case "source":
      return record.source
    case "note":
      return record.note
    case "assigned":
      return record.assigned
    case "acceptance":
      return record.acceptance
    case "plan_progress":
      return formatProgress(record.planProgress)
    case "plan":
      return record.plan
    case "spec":
      return record.spec
    case "workstream_state":
      return record.workstreamState
    case "commit":
      return record.commit
    case "last_activity":
      return record.lastActivity
  }
}

function compare(
  a: BoardRecord,
  b: BoardRecord,
  property: BoardProperty,
): number {
  if (property === "number") return a.number - b.number
  const left = propertyValue(a, property) ?? ""
  const right = propertyValue(b, property) ?? ""
  return left.localeCompare(right)
}

/** The records a view shows, in its order. `text` matches title and Note. */
export function applyView(
  records: BoardRecord[],
  definition: ViewDefinition,
  text: string,
): BoardRecord[] {
  const needle = text.trim().toLowerCase()
  const shown = records.filter((record) => {
    if (!definition.show_untracked && record.state === "untracked") return false
    for (const filter of definition.filters) {
      const value = propertyValue(record, filter.property) ?? ""
      if (filter.operator === "in" && !filter.values.includes(value))
        return false
      if (filter.operator === "not_in" && filter.values.includes(value))
        return false
      if (
        filter.operator === "contains" &&
        !filter.values.some((v) =>
          value.toLowerCase().includes(v.toLowerCase()),
        )
      ) {
        return false
      }
    }
    if (!needle) return true
    return (
      record.title.toLowerCase().includes(needle) ||
      (record.note ?? "").toLowerCase().includes(needle)
    )
  })
  const sort = definition.sort
  if (!sort) return shown
  const sign = sort.direction === "asc" ? 1 : -1
  return [...shown].sort(
    (a, b) => sign * compare(a, b, sort.property) || a.id.localeCompare(b.id),
  )
}

export interface BoardColumn {
  key: string
  title: string
  records: BoardRecord[]
}

export interface BoardLane {
  key: string
  title: string
  /** Set on a State lane: the one type whose cards it holds. */
  type: RecordType | null
  columns: BoardColumn[]
}

const NONE = "(none)"

function groupTitle(property: GroupableProperty, key: string): string {
  if (key === NONE) return NONE
  if (property === "source" || property === "plan") return shortName(key)
  if (property === "type")
    return key === "register_row" ? "Register rows" : "Plan tasks"
  return key
}

/** Columns for a grouping. State splits into one lane per type, each across
 *  its own vocabulary, so the two vocabularies never share a column. */
export function boardLanes(
  records: BoardRecord[],
  groupBy: GroupableProperty | null,
  showUntracked: boolean,
): BoardLane[] {
  if (groupBy === "state") {
    const lanes: BoardLane[] = []
    const specs: [RecordType, string, string[]][] = [
      ["register_row", "Register rows", [...REGISTER_STATES, "unrecognised"]],
      [
        "plan_task",
        "Plan tasks",
        [
          ...TASK_STATES,
          "unrecognised",
          ...(showUntracked ? ["untracked"] : []),
        ],
      ],
    ]
    for (const [type, title, states] of specs) {
      const own = records.filter((r) => r.type === type)
      if (own.length === 0) continue
      lanes.push({
        key: type,
        title,
        type,
        columns: states.map((state) => ({
          key: state,
          title: state,
          records: own.filter((r) => r.state === state),
        })),
      })
    }
    return lanes
  }
  if (groupBy === null) {
    return [
      {
        key: "all",
        title: "All",
        type: null,
        columns: [{ key: "all", title: "All", records }],
      },
    ]
  }
  const columns = new Map<string, BoardRecord[]>()
  for (const record of records) {
    const key = propertyValue(record, groupBy) || NONE
    const column = columns.get(key)
    if (column) column.push(record)
    else columns.set(key, [record])
  }
  const keys = [...columns.keys()].sort((a, b) =>
    a === NONE ? 1 : b === NONE ? -1 : a.localeCompare(b),
  )
  return [
    {
      key: groupBy,
      title: "",
      type: null,
      columns: keys.map((key) => ({
        key,
        title: groupTitle(groupBy, key),
        records: columns.get(key) ?? [],
      })),
    },
  ]
}

export type MoveIntent = "locked" | "noop" | "note" | "patch"

/** What dropping `record` into `toState` asks for. Only register rows move;
 *  a state that needs a Note always opens the Note dialog first. */
export function planMove(record: BoardRecord, toState: string): MoveIntent {
  if (record.type !== "register_row") return "locked"
  if (record.state === toState) return "noop"
  if (NOTE_REQUIRED.has(toState)) return "note"
  return "patch"
}
