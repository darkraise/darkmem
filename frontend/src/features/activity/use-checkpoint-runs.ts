import { DEMO } from "@/lib/demo-flag"
import { useDemoSessionRuns } from "@/demo/hooks"
import type { DemoSessionRun } from "@/demo/types"
import { relativeTime } from "@/lib/format"
import { useEvents, useLatestCheckpoint, type EventLogEntry } from "@/hooks/api"

/** One journalled moment in a run's checkpoint history. The two event types
 *  are the whole vocabulary: `checkpoint_saved` is the run writing its note,
 *  `resumed` is a later session having loaded one. */
export interface CheckpointEventRow {
  id: string
  timeLabel: string
  event: "checkpoint_saved" | "resumed"
  detail: string
  tokensLabel: string | null
}

/** The one run shape CheckpointsTab renders, whichever source fed it. */
export interface CheckpointRunData {
  id: string
  title: string
  originKey: string
  project: string
  metaLabel: string
  history: CheckpointEventRow[]
}

/** The latest digest for one run.
 *
 * `resumeLine` is the server's `resume_line` — the exact text the resume
 * inject leads its managed block with. It is never assembled here: a second
 * rendering would drift silently, and the copy affordance's whole claim is
 * that what it hands you is what your session receives.
 *
 * `keyDecisions` / `touchedFiles` are demo-only. The shipped
 * `session_checkpoints` row carries `summary` and `next_steps` and nothing
 * else, so the real branch leaves them empty rather than inventing them from
 * the summary — a surface that showed "decisions" the store does not hold
 * would be reading structure into prose.
 */
export interface CheckpointDigestData {
  savedLabel: string
  summary: string
  nextSteps: string[]
  resumeLine: string
  tokenEstimate: number | null
  keyDecisions: string[]
  touchedFiles: string[]
}

const CHECKPOINT_OBJECT_TYPE = "checkpoint"
// One page, server-filtered to the checkpoint object type. Not a count: the
// run list is what this page witnesses, and `total` is shown beside it so a
// truncated page never reads as the whole history.
const EVENT_LIMIT = 200

function fromDemoRun(run: DemoSessionRun): CheckpointRunData {
  return {
    id: run.id,
    title: run.title,
    originKey: run.origin_key,
    project: run.project,
    metaLabel: run.meta_label,
    history: run.history.map((event, i) => ({
      id: `${run.id}-${event.time_label}-${i}`,
      timeLabel: event.time_label,
      event: event.event,
      detail: event.detail,
      tokensLabel: event.tokens_label,
    })),
  }
}

function originKeyOf(entry: EventLogEntry): string | null {
  const key = entry.payload.origin_key
  return typeof key === "string" && key ? key : null
}

function detailOf(entry: EventLogEntry): string {
  if (entry.event_type === "resumed") {
    return "a fresh session loaded this run's digest"
  }
  const steps = entry.payload.next_steps
  if (typeof steps === "number") {
    return `digest saved with ${steps} next step${steps === 1 ? "" : "s"}`
  }
  return "digest saved"
}

function tokensLabelOf(entry: EventLogEntry): string | null {
  const used = entry.payload.tokens_used
  return typeof used === "number" ? `~${used.toLocaleString()}` : null
}

/** Runs, newest activity first, grouped from the journal.
 *
 * There is no list-runs endpoint and this is not a stand-in for one: the
 * journal *is* where a run becomes visible, since both the save and the
 * resume write to it. An event whose payload names no `origin_key` is
 * dropped rather than bucketed under a placeholder — the coarse
 * `unknown:` merge the checkpoint door refuses at write time would be
 * reintroduced here as a display bucket, and two runs sharing one row is
 * exactly the confusion that refusal exists to prevent.
 */
function fromEventLog(entries: EventLogEntry[]): CheckpointRunData[] {
  const runs = new Map<string, CheckpointRunData>()

  for (const entry of entries) {
    const originKey = originKeyOf(entry)
    if (!originKey) continue
    if (entry.event_type !== "checkpoint_saved" && entry.event_type !== "resumed") {
      continue
    }
    const project = entry.project ?? "default"
    const id = `${project}::${originKey}`
    let run = runs.get(id)
    if (!run) {
      run = {
        id,
        title: originKey,
        originKey,
        project,
        // `/events` returns newest first, so the first entry seen for a run
        // is its most recent moment.
        metaLabel: `last activity ${relativeTime(entry.created_at)}`,
        history: [],
      }
      runs.set(id, run)
    }
    run.history.push({
      id: String(entry.id),
      timeLabel: relativeTime(entry.created_at),
      event: entry.event_type,
      detail: detailOf(entry),
      tokensLabel: tokensLabelOf(entry),
    })
  }

  return [...runs.values()]
}

/** `DEMO ? demo : real`, following `use-feed.ts`. */
export function useCheckpointRuns(): {
  runs: CheckpointRunData[]
  isLoading: boolean
  isError: boolean
} {
  const demoRuns = useDemoSessionRuns()
  const query = useEvents(
    { object_type: CHECKPOINT_OBJECT_TYPE, limit: EVENT_LIMIT },
    { enabled: !DEMO },
  )

  if (DEMO) {
    return { runs: demoRuns.map(fromDemoRun), isLoading: false, isError: false }
  }
  return {
    runs: query.data ? fromEventLog(query.data.items) : [],
    isLoading: query.isLoading,
    isError: query.isError,
  }
}

/** The selected run's latest digest, or `null` when it saved none. */
export function useCheckpointDigest(run: CheckpointRunData | null): {
  digest: CheckpointDigestData | null
  isLoading: boolean
} {
  const demoRuns = useDemoSessionRuns()
  const query = useLatestCheckpoint(
    { originKey: run?.originKey ?? null, project: run?.project ?? "default" },
    { enabled: !DEMO },
  )

  if (DEMO) {
    const demo = demoRuns.find((r) => r.id === run?.id)
    const latest = demo?.latest
    return {
      digest: latest
        ? {
            savedLabel: latest.saved_label,
            summary: latest.summary,
            nextSteps: latest.next_steps,
            resumeLine: latest.resume_block,
            tokenEstimate: latest.token_estimate,
            keyDecisions: latest.key_decisions,
            touchedFiles: latest.touched_files,
          }
        : null,
      isLoading: false,
    }
  }

  const row = query.data
  return {
    digest: row
      ? {
          savedLabel: row.created_at
            ? `saved ${relativeTime(row.created_at)}`
            : "saved",
          summary: row.summary,
          nextSteps: row.next_steps,
          resumeLine: row.resume_line,
          tokenEstimate: row.token_estimate,
          keyDecisions: [],
          touchedFiles: [],
        }
      : null,
    isLoading: query.isLoading,
  }
}
