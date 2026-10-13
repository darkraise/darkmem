export type Untracked = "no_workstream" | "no_properties"

export interface PlanProgress {
  done: number
  total: number
  untracked: Untracked | null
}

export interface RegisterRow {
  number: number
  item: string
  assigned: string
  acceptance: string
  state: string
  raw_state: string
  note: string
  note_blank: boolean
  line: number
}

export interface BoardRegisterRow extends RegisterRow {
  plan_uri: string | null
  plan_progress: PlanProgress | null
}

export interface BoardRegister {
  document_id: string
  uri: string
  title: string | null
  covers: string | null
  content_hash: string | null
  block_first: boolean
  rows: BoardRegisterRow[]
  malformed: { line: number; text: string; reason: string }[]
  error: string | null
}

export interface TaskStep {
  checked: boolean
  text: string
}

export interface PlanTask {
  number: number
  label: string
  title: string
  line: number
  state: string
  raw_state: string | null
  untracked: Untracked | null
  shared_number: boolean
  blocked_reason: string | null
  commit: string | null
  last_activity: string | null
  steps: TaskStep[]
}

export interface BoardPlan {
  document_id: string
  uri: string
  title: string | null
  content_hash: string | null
  workstream: { id: string; key: string; state: "open" | "closed" } | null
  other_workstreams: number
  spec_uri: string | null
  untracked: Untracked | null
  tasks: PlanTask[]
  orphans: number[]
  error: string | null
}

export interface BoardRecords {
  project: string
  registers: BoardRegister[]
  plans: BoardPlan[]
}

export type BoardProperty =
  | "type"
  | "title"
  | "number"
  | "state"
  | "source"
  | "note"
  | "assigned"
  | "acceptance"
  | "plan_progress"
  | "plan"
  | "spec"
  | "workstream_state"
  | "commit"
  | "last_activity"

export type GroupableProperty =
  | "type"
  | "state"
  | "source"
  | "assigned"
  | "plan"
  | "workstream_state"

export interface ViewFilter {
  property: BoardProperty
  operator: "in" | "not_in" | "contains"
  values: string[]
}

export interface ViewDefinition {
  layout: "board" | "table"
  group_by: GroupableProperty | null
  filters: ViewFilter[]
  sort: { property: BoardProperty; direction: "asc" | "desc" } | null
  columns: BoardProperty[]
  show_untracked: boolean
}

export interface BoardView {
  id: string
  project: string
  name: string
  position: number
  definition: ViewDefinition
  builtin: boolean
  created_at: string | null
  updated_at: string | null
}

export interface RowChanges {
  state?: string
  note?: string
  assigned?: string
}

export interface RowEditResult {
  document_id: string
  content_hash: string
  row: RegisterRow
}
