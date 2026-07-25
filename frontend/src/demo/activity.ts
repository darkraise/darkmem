import type {
  DemoDayBucket,
  DemoDreamAction,
  DemoFeedEvent,
  DemoJobField,
  DemoPipelineFailure,
  DemoPipelineRun,
  DreamActionType,
  FeedCategory,
  PipelineFailedStep,
} from "./types"

// ---------------------------------------------------------------------------
// S18 — derive_memory_failed_step, client-side mirror. Hard step errors win
// in phase order; a merely degraded extraction only names extraction_partial
// when no hard error exists. Phases 3–4 never produce a named failure.
// ---------------------------------------------------------------------------

export function deriveRunFailedStep(
  run: DemoPipelineRun,
): PipelineFailedStep | null {
  if (run.steps[0] === "error") return "content_embedding"
  if (run.steps[1] === "error") return "extraction"
  if (run.substeps?.vector === "error") return "vector_write"
  if (run.substeps?.graph === "error") return "graph_write"
  if (run.steps[1] === "degraded") return "extraction_partial"
  return null
}

/** extraction_partial is degraded-not-fatal — warning role, not failure red. */
export function failedStepSeverity(
  step: PipelineFailedStep,
): "warn" | "error" {
  return step === "extraction_partial" ? "warn" : "error"
}

// ---------------------------------------------------------------------------
// S19 — feed filtering.
// ---------------------------------------------------------------------------

export const FEED_CATEGORIES: FeedCategory[] = [
  "capture",
  "pipeline",
  "verification",
  "consolidation",
  "code",
]

export function filterFeed(
  events: DemoFeedEvent[],
  category: FeedCategory | "all",
): DemoFeedEvent[] {
  if (category === "all") return events
  return events.filter((e) => e.category === category)
}

// ---------------------------------------------------------------------------
// S20 — triage grouping + the poison heuristic. attempts is unbounded
// server-side; ≥5 is a triage-surface heuristic, not a backend gate.
// ---------------------------------------------------------------------------

export const POISON_ATTEMPTS = 5

export function isPoison(failure: DemoPipelineFailure): boolean {
  return failure.attempts >= POISON_ATTEMPTS
}

export function groupFailuresByStep(
  failures: DemoPipelineFailure[],
): { step: string; failures: DemoPipelineFailure[] }[] {
  const groups: { step: string; failures: DemoPipelineFailure[] }[] = []
  for (const failure of failures) {
    const group = groups.find((g) => g.step === failure.failed_step)
    if (group) group.failures.push(failure)
    else groups.push({ step: failure.failed_step, failures: [failure] })
  }
  return groups
}

// ---------------------------------------------------------------------------
// S21 — config_schema validation, mirroring the backend's set_config rules:
// unknown keys rejected, ints only, min/max bounds enforced.
// ---------------------------------------------------------------------------

export type JobConfigValidation =
  | { ok: true; config: Record<string, number> }
  | { ok: false; errors: Record<string, string> }

export function validateJobConfig(
  schema: DemoJobField[],
  values: Record<string, unknown>,
): JobConfigValidation {
  const errors: Record<string, string> = {}
  const config: Record<string, number> = {}
  const known = new Set(schema.map((f) => f.key))
  for (const key of Object.keys(values)) {
    if (!known.has(key)) errors[key] = `unknown key "${key}" — rejected`
  }
  for (const field of schema) {
    const raw = values[field.key]
    if (raw === undefined) continue
    const num = typeof raw === "number" ? raw : Number(raw)
    if (!Number.isInteger(num)) {
      errors[field.key] = `${field.key} must be an integer`
      continue
    }
    if (field.min !== undefined && num < field.min) {
      errors[field.key] = `${field.key} must be ≥ ${field.min}`
      continue
    }
    if (field.max !== undefined && num > field.max) {
      errors[field.key] = `${field.key} must be ≤ ${field.max}`
      continue
    }
    config[field.key] = num
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors }
  return { ok: true, config }
}

// ---------------------------------------------------------------------------
// S23 — dream digest grouping + batch-undo eligibility.
// ---------------------------------------------------------------------------

export function dreamActionsOfType(
  actions: DemoDreamAction[],
  type: DreamActionType,
): DemoDreamAction[] {
  return actions.filter((a) => a.type === type)
}

/** Eligible for (batch) undo: not blocked, not already undone. */
export function eligibleForUndo(actions: DemoDreamAction[]): DemoDreamAction[] {
  return actions.filter((a) => !a.undo_blocked && !a.undone)
}

// ---------------------------------------------------------------------------
// S24 — UTC day-bucket lookup + neighbour-day arithmetic.
// ---------------------------------------------------------------------------

export function dayBucket(
  buckets: DemoDayBucket[],
  date: string,
): DemoDayBucket | undefined {
  return buckets.find((b) => b.date === date)
}

export function shiftDay(date: string, delta: number): string {
  const ms = Date.parse(`${date}T00:00:00Z`)
  const shifted = new Date(ms + delta * 86_400_000)
  return shifted.toISOString().slice(0, 10)
}

export function isValidDay(date: unknown): date is string {
  return (
    typeof date === "string" &&
    /^\d{4}-\d{2}-\d{2}$/.test(date) &&
    !Number.isNaN(Date.parse(`${date}T00:00:00Z`))
  )
}
