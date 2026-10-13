import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { demoBoardRecords, DEMO_BOARD_VIEWS } from "@/demo/board"

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


/** How often the board re-reads its records while the Progress tab is shown.
 *  The server answers 304 from two aggregates when nothing changed. */
export const BOARD_REFRESH_MS = 10_000

const DEMO_REFUSAL = "The demo is read-only: its board cannot be changed."

export function useBoardRecords(project: string) {
  return useQuery<BoardRecords>({
    queryKey: ["boardRecords", project],
    queryFn: () =>
      apiFetch<BoardRecords>(
        `/board/records?${new URLSearchParams({ project })}`,
      ),
    enabled: !DEMO,
    refetchInterval: DEMO ? false : BOARD_REFRESH_MS,
    initialData: DEMO ? demoBoardRecords(project) : undefined,
  })
}

export function useBoardViews(project: string) {
  return useQuery<BoardView[]>({
    queryKey: ["boardViews", project],
    queryFn: () =>
      apiFetch<BoardView[]>(`/board/views?${new URLSearchParams({ project })}`),
    enabled: !DEMO,
    initialData: DEMO
      ? DEMO_BOARD_VIEWS.map((view) => ({ ...view, project }))
      : undefined,
  })
}

function invalidate(
  qc: QueryClient,
  key: "boardRecords" | "boardViews",
  project: string,
) {
  void qc.invalidateQueries({ queryKey: [key, project] })
}

export function useRegisterRowEdit(project: string) {
  const qc = useQueryClient()
  return useMutation<
    RowEditResult,
    Error,
    { documentId: string; number: number; expectedHash: string } & RowChanges
  >({
    mutationFn: ({ documentId, number, expectedHash, ...changes }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<RowEditResult>(
            `/board/registers/${documentId}/rows/${number}`,
            {
              method: "PATCH",
              body: JSON.stringify({ expected_hash: expectedHash, ...changes }),
            },
          ),
    onSettled: () => invalidate(qc, "boardRecords", project),
  })
}

export function useCreateBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<
    BoardView,
    Error,
    { name: string; definition: ViewDefinition }
  >({
    mutationFn: ({ name, definition }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<BoardView>("/board/views", {
            method: "POST",
            body: JSON.stringify({ project, name, definition }),
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}

export function useUpdateBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<
    BoardView,
    Error,
    { id: string; name?: string; definition?: ViewDefinition }
  >({
    mutationFn: ({ id, ...changes }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<BoardView>(`/board/views/${encodeURIComponent(id)}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}

export function useDeleteBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<void>(`/board/views/${encodeURIComponent(id)}`, {
            method: "DELETE",
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}
