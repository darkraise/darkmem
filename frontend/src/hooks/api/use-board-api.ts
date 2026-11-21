import { useRef } from "react"
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { isHashConflict } from "@/lib/hash-precondition"
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
    queryFn: ({ signal }) =>
      apiFetch<BoardRecords>(
        `/board/records?${new URLSearchParams({ project })}`, { signal }),
    enabled: !DEMO,
    refetchInterval: DEMO ? false : BOARD_REFRESH_MS,
    initialData: DEMO ? demoBoardRecords(project) : undefined,
  })
}

export function useBoardViews(project: string) {
  return useQuery<BoardView[]>({
    queryKey: ["boardViews", project],
    queryFn: ({ signal }) =>
      apiFetch<BoardView[]>(`/board/views?${new URLSearchParams({ project })}`, { signal }),
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

/** One register's edits, sent one at a time. `superseded` maps each hash an
 *  edit was sent with to the hash it answered, so an edit made against a
 *  hash this queue's own write replaced is sent with the newer one; a hash
 *  some other writer produced is not in it and goes out as given. */
interface RegisterQueue {
  tail: Promise<unknown>
  queued: number
  conflict: unknown
  superseded: Map<string, string>
}

function currentHash(queue: RegisterQueue, hash: string): string {
  const seen = new Set<string>()
  while (queue.superseded.has(hash) && !seen.has(hash)) {
    seen.add(hash)
    hash = queue.superseded.get(hash)!
  }
  return hash
}

export function useRegisterRowEdit(project: string) {
  const qc = useQueryClient()
  const queues = useRef(new Map<string, RegisterQueue>())

  const enqueue = (
    documentId: string,
    expectedHash: string,
    send: (hash: string) => Promise<RowEditResult>,
  ): Promise<RowEditResult> => {
    let queue = queues.current.get(documentId)
    if (!queue) {
      queue = { tail: Promise.resolve(), queued: 0, conflict: null, superseded: new Map() }
      queues.current.set(documentId, queue)
    }
    const q = queue
    q.queued++
    const run = q.tail.then(async () => {
      // An edit queued behind a real conflict was made against the view the
      // conflict just proved stale.
      if (q.conflict !== null) throw q.conflict
      const hash = currentHash(q, expectedHash)
      try {
        const result = await send(hash)
        q.superseded.delete(result.content_hash)
        q.superseded.set(hash, result.content_hash)
        return result
      } catch (error) {
        if (isHashConflict(error)) q.conflict = error
        throw error
      }
    })
    const settle = () => {
      if (--q.queued === 0) q.conflict = null
    }
    q.tail = run.then(settle, settle)
    return run
  }

  return useMutation<
    RowEditResult,
    Error,
    { documentId: string; number: number; expectedHash: string } & RowChanges
  >({
    mutationFn: ({ documentId, number, expectedHash, ...changes }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : enqueue(documentId, expectedHash, (hash) =>
            apiFetch<RowEditResult>(
              `/board/registers/${documentId}/rows/${number}`,
              {
                method: "PATCH",
                body: JSON.stringify({ expected_hash: hash, ...changes }),
              },
            ),
          ),
    // The answered hash goes into the cache at once, so an edit made before
    // the re-read lands does not send the hash this one replaced.
    onSuccess: (result) =>
      qc.setQueryData<BoardRecords>(["boardRecords", project], (prev) =>
        prev
          ? {
              ...prev,
              registers: prev.registers.map((register) =>
                register.document_id === result.document_id
                  ? { ...register, content_hash: result.content_hash }
                  : register,
              ),
            }
          : prev,
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
