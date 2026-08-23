// Relocated out of src/demo/types.ts by T1.68: every type below is
// constructed from real backend data in its feature's real branch —
// `fromJob` (use-job-board.ts), `categoryOfEventType` (event-taxonomy.ts),
// `fromPipelineLog` (use-pipeline-runs.ts), `fromPipelineFailure`
// (use-pipeline-triage.ts) — following the `DEMO ? demo : real` idiom, not
// demo fixture data. See the task's report for the full per-type evidence
// trail, including the types that stay (DemoFeedEvent, DemoDayEvent,
// DemoBufferMonitor, ...) because their real branch never constructs one.

export interface DemoJobField {
  key: string
  type: "int"
  label: string
  value: number
  min?: number
  max?: number
  help?: string
}

export interface DemoJob {
  key: string
  name: string
  description: string
  /** Disabling stops the scheduled loop from restarting; fields stay editable. */
  enabled: boolean
  cron: string
  cron_label: string
  /** Floor: the loop never fires more often than this. Registration constant. */
  min_interval_seconds: number
  /** Ceiling: a run past this duration counts as overrun. Registration
   *  constant. Null in real mode — JobItem does not expose it over the
   *  wire, and this is never fabricated to fill the demo's read-only field. */
  max_run_seconds: number | null
  running: boolean
  lock_held_since: string | null
  /** Null in real mode: no cron-next calculator exists client-side and the
   *  API does not return a computed next-fire time — never fabricated. */
  next_run_label: string | null
  /** null = never ran (fresh install honesty — the list can never be empty). */
  last_run_label: string | null
  last_status: "ok" | "error" | null
  last_summary: string | null
  config_schema: DemoJobField[]
}

export type JobTriggerResult =
  | { ok: true }
  | { ok: false; status: 409; lock_held_since: string | null }

export type FeedCategory =
  | "capture"
  | "pipeline"
  | "verification"
  | "consolidation"
  | "code"

export type PipelineStepState =
  | "ok"
  | "pending"
  | "error"
  | "degraded"
  | "skipped"

export interface PipelineWriteSubsteps {
  vector: "ok" | "error" | "skipped"
  graph: "ok" | "error" | "skipped"
}

export type PipelineTerminal = "running" | "completed" | "partial" | "failed"

export interface DemoPipelineRun {
  id: string
  /** The memory this run processed, or null once it has been deleted. The
   *  usage subject for a Phase-2 call is this id, so a row cannot show what it
   *  cost without carrying it. */
  memory_id: string | null
  content: string
  time_label: string
  /** The five phases in fixed order: content embed → extract & classify →
   *  entity embed → dedup → write. */
  steps: [
    PipelineStepState,
    PipelineStepState,
    PipelineStepState,
    PipelineStepState,
    PipelineStepState,
  ]
  /** Phase 5's two savepoints — non-null once write was attempted. */
  substeps: PipelineWriteSubsteps | null
  terminal: PipelineTerminal
  counts: { entities: number; relations: number } | null
  note: string | null
}

export interface DemoPipelineFailure {
  id: string
  target_kind: "memory" | "code_repo"
  target_label: string
  pipeline: "memory_ingest" | "code_index"
  failed_step: string
  /** The raw error_message, shown verbatim — never summarised to "failed". */
  reason: string
  attempts: number
  first_failed: string
  last_attempt: string
  retry_queued: boolean
}
