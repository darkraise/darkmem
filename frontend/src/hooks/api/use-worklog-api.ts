import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from "@tanstack/react-query"
import { ApiError, apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { DEMO_WORKLOG_ENTRIES, DEMO_WORKSTREAMS } from "@/demo/worklog"

export type WorklogKind = "checkpoint" | "ledger" | "note"
export type WorkstreamState = "open" | "closed"

export interface Workstream {
  id: string
  project: string
  key: string
  title: string | null
  client: string | null
  state: WorkstreamState
  closed_at: string | null
  retain: boolean
  properties: Record<string, unknown>
  last_entry_at: string
  created_at: string
  updated_at: string
}

export interface WorklogEntry {
  id: string
  workstream_id: string
  seq: number
  run_key: string
  kind: WorklogKind
  body: string
  properties: Record<string, unknown>
  created_at: string
}

export interface WorkstreamPage {
  items: Workstream[]
  next_before: string | null
}

export interface WorklogEntryPage {
  items: WorklogEntry[]
  next_after: number | null
}

export interface WorklogResume {
  workstream: Workstream
  checkpoint: WorklogEntry | null
  notes: WorklogEntry[]
  notes_truncated: boolean
  ledger: WorklogEntry[]
}

export interface WorklogSearchHit {
  entry: WorklogEntry
  workstream: string
  rrf_score: number
  arms: ("keyword" | "semantic")[]
}

export interface WorklogSearchResponse {
  items: WorklogSearchHit[]
  semantic_ran: boolean
}

export interface WorklogSearchParams {
  project: string
  query: string
  workstream?: string
  kind?: WorklogKind
}

export interface WorkstreamPatch {
  state?: WorkstreamState
  retain?: boolean
  title?: string | null
  properties?: Record<string, unknown>
}

/** How often an open workstream's entries are re-read (spec §8). */
export const WORKLOG_LIVE_MS = 5_000
const WORKSTREAM_PAGE = 50
const ENTRY_PAGE = 200

const DEMO_REFUSAL = "The demo is read-only: its work log cannot be changed."

function demoWorkstreams(project: string, state: WorkstreamState): WorkstreamPage {
  return {
    items: DEMO_WORKSTREAMS.filter((w) => w.project === project && w.state === state),
    next_before: null,
  }
}

function demoEntries(workstreamId: string | null, kind: WorklogKind | null): WorklogEntryPage {
  const all = workstreamId ? (DEMO_WORKLOG_ENTRIES[workstreamId] ?? []) : []
  return { items: kind ? all.filter((e) => e.kind === kind) : all, next_after: null }
}

function demoResume(project: string, key: string): WorklogResume | null {
  const workstream = DEMO_WORKSTREAMS.find((w) => w.project === project && w.key === key)
  if (!workstream) return null
  const entries = DEMO_WORKLOG_ENTRIES[workstream.id] ?? []
  const checkpoints = entries.filter((e) => e.kind === "checkpoint")
  return {
    workstream,
    checkpoint: checkpoints[checkpoints.length - 1] ?? null,
    notes: entries.filter((e) => e.kind === "note"),
    notes_truncated: false,
    ledger: entries.filter((e) => e.kind === "ledger").slice(-20),
  }
}

function demoSearch(params: WorklogSearchParams): WorklogSearchResponse {
  const needle = params.query.toLowerCase()
  const byId = new Map(DEMO_WORKSTREAMS.map((w) => [w.id, w]))
  const hits = Object.values(DEMO_WORKLOG_ENTRIES)
    .flat()
    .filter((e) => {
      const w = byId.get(e.workstream_id)
      return (
        w?.project === params.project &&
        (!params.workstream || w.key === params.workstream) &&
        (!params.kind || e.kind === params.kind) &&
        e.body.toLowerCase().includes(needle)
      )
    })
  return {
    items: hits.map((e, rank) => ({
      entry: e,
      workstream: byId.get(e.workstream_id)!.key,
      rrf_score: 1 / (60 + rank + 1),
      arms: ["keyword"],
    })),
    semantic_ran: false,
  }
}
/** One state of a project's workstreams, newest-created first, paged back on
 *  the server's `(created_at, id)` cursor. */
export function useWorkstreams(project: string, state: WorkstreamState) {
  return useInfiniteQuery({
    queryKey: ["worklogWorkstreams", project, state],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams({ project, state, limit: String(WORKSTREAM_PAGE) })
      if (pageParam) qs.set("before", pageParam)
      return apiFetch<WorkstreamPage>(`/worklog/workstreams?${qs}`)
    },
    getNextPageParam: (last: WorkstreamPage) => last.next_before,
    enabled: !DEMO,
    initialData: DEMO
      ? ({
          pages: [demoWorkstreams(project, state)],
          pageParams: [null],
        } as InfiniteData<WorkstreamPage, string | null>)
      : undefined,
  })
}

/** A workstream's entries oldest first, paged forward on `seq`. `live` re-reads
 *  every loaded page on WORKLOG_LIVE_MS; a short last page re-read with the same
 *  cursor picks up whatever was appended since. */
export function useWorklogEntries(
  workstreamId: string | null,
  kind: WorklogKind | null,
  live: boolean,
) {
  return useInfiniteQuery({
    queryKey: ["worklogEntries", workstreamId, kind],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams({ limit: String(ENTRY_PAGE) })
      if (kind) qs.set("kind", kind)
      if (pageParam !== null) qs.set("after", String(pageParam))
      return apiFetch<WorklogEntryPage>(`/worklog/workstreams/${workstreamId}/entries?${qs}`)
    },
    getNextPageParam: (last: WorklogEntryPage) => last.next_after,
    enabled: !DEMO && workstreamId !== null,
    refetchInterval: live && !DEMO ? WORKLOG_LIVE_MS : false,
    initialData: DEMO
      ? ({
          pages: [demoEntries(workstreamId, kind)],
          pageParams: [null],
        } as InfiniteData<WorklogEntryPage, number | null>)
      : undefined,
  })
}

/** What a new session would load for one workstream; `null` when the key names
 *  no workstream in that project, which the route answers with a 404. */
export function useWorklogResume(project: string, key: string, enabled = true) {
  return useQuery<WorklogResume | null>({
    queryKey: ["worklogResume", project, key],
    queryFn: async () => {
      const qs = new URLSearchParams({ project, workstream: key })
      try {
        return await apiFetch<WorklogResume>(`/worklog/resume?${qs}`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    enabled: !DEMO && enabled,
    initialData: DEMO ? demoResume(project, key) : undefined,
  })
}

export function useWorklogSearch() {
  return useMutation<WorklogSearchResponse, Error, WorklogSearchParams>({
    mutationFn: (params) =>
      DEMO
        ? Promise.resolve(demoSearch(params))
        : apiFetch<WorklogSearchResponse>("/worklog/search", {
            method: "POST",
            body: JSON.stringify(params),
          }),
  })
}

function invalidateWorklog(qc: QueryClient, purgedId?: string) {
  // "projects" too: the Activity list picks which projects to ask from its
  // per-project workstream counts, and queries are otherwise fresh for 60 s.
  for (const key of ["worklogWorkstreams", "worklogEntries", "worklogResume", "projects"]) {
    void qc.invalidateQueries({
      queryKey: [key],
      // A purged workstream's own reads would only answer 404 on refetch.
      predicate: purgedId
        ? (query) =>
            query.queryKey[1] !== purgedId &&
            (query.state.data as WorklogResume | null | undefined)?.workstream?.id !== purgedId
        : undefined,
    })
  }
}

export function useWorkstreamUpdate() {
  const qc = useQueryClient()
  return useMutation<Workstream, Error, { id: string } & WorkstreamPatch>({
    mutationFn: ({ id, ...patch }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<Workstream>(`/worklog/workstreams/${id}`, {
            method: "PATCH",
            body: JSON.stringify(patch),
          }),
    onSuccess: () => invalidateWorklog(qc),
  })
}

export function useWorkstreamPurge() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<void>(`/worklog/workstreams/${id}`, { method: "DELETE" }),
    onSuccess: (_done, id) => {
      // The workstream is gone for good: off the cached lists at once (or the
      // panel re-selects it), and its own reads are left out of the refetch.
      qc.setQueriesData<InfiniteData<WorkstreamPage, string | null>>(
        { queryKey: ["worklogWorkstreams"] },
        (data) =>
          data && {
            ...data,
            pages: data.pages.map((page) => ({
              ...page,
              items: page.items.filter((w) => w.id !== id),
            })),
          },
      )
      invalidateWorklog(qc, id)
    },
  })
}
