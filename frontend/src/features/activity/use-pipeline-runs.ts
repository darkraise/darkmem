import { DEMO } from "@/demo/flag"
import { useDemoPipelineRuns } from "@/demo/hooks"
import type { DemoPipelineRun, PipelineStepState } from "@/demo/types"
import { relativeTime } from "@/lib/format"
import { usePipelineLogs, type PipelineLog } from "@/hooks/api"

function stepState(raw: unknown, degradedValue: string): PipelineStepState {
  if (raw === "ok") return "ok"
  if (raw === degradedValue) return "degraded"
  if (raw === "skipped") return "skipped"
  if (raw === "pending") return "pending"
  // "error" and the batch-backstop "unknown" (pipeline.py's process_batch
  // catch-all, which cannot tell embed/extract apart from a whole-batch
  // exception) both read as a hard failure — there is no honest way to
  // distinguish "unknown" from "error" at this remove, and rendering it as
  // anything softer would understate a batch that never ran at all.
  return "error"
}

function substep(raw: unknown): "ok" | "error" | "skipped" {
  if (raw === "ok") return "ok"
  if (raw === "error") return "error"
  // "pending"/"unknown" never survive to a terminal broadcast in practice
  // (vector/graph are always resolved to ok/error/skipped by the time
  // _derive_outcome runs) — skipped is the closest honest reading of an
  // unrecognised value reaching this far.
  return "skipped"
}

/** Phase 3 (entity embed) and Phase 4 (dedup) carry no per-memory status
 *  field on the wire — `pipeline.py`'s status dict has exactly `embed`,
 *  `extract`, `vector`, `graph`. A batch-wide failure in either phase never
 *  reaches `_write_memory` at all and is caught by `process_batch`'s
 *  backstop, which already marks `extract` (and everything after it)
 *  failed/unknown. So the two steps this UI has no direct signal for are
 *  mirrored from `extract`'s outcome rather than invented: extract reaching
 *  "ok"/"degraded" is only possible if entity embed and dedup already ran
 *  without escaping as a batch exception, and extract "error"/pending means
 *  they were never reached.
 */
function impliedStep(extract: PipelineStepState): PipelineStepState {
  if (extract === "ok" || extract === "degraded") return "ok"
  if (extract === "pending") return "pending"
  return "skipped"
}

function writeState(
  vector: "ok" | "error" | "skipped",
  graph: "ok" | "error" | "skipped",
): PipelineStepState {
  if (vector === "error") return "error"
  if (graph === "error") return "degraded"
  if (vector === "skipped" && graph === "skipped") return "skipped"
  return "ok"
}

function fromPipelineLog(log: PipelineLog): DemoPipelineRun {
  const details = log.details as Record<string, unknown>
  const embed = stepState(details.embed, "__never__")
  const extract = stepState(details.extract, "partial")
  const vector = substep(details.vector)
  const graph = substep(details.graph)
  const entities = typeof details.entities_count === "number" ? details.entities_count : 0
  const relations = typeof details.relations_count === "number" ? details.relations_count : 0
  const outcome = details.outcome
  const terminal: DemoPipelineRun["terminal"] =
    outcome === "completed" || outcome === "partial" || outcome === "failed"
      ? outcome
      : "failed"

  return {
    id: String(log.id),
    content: log.memory_id ? `memory ${log.memory_id.slice(0, 8)}` : "(memory deleted)",
    time_label: relativeTime(log.timestamp),
    steps: [
      embed,
      extract,
      impliedStep(extract),
      impliedStep(extract),
      writeState(vector, graph),
    ],
    substeps: { vector, graph },
    terminal,
    counts: extract === "ok" || extract === "degraded" ? { entities, relations } : null,
    note: typeof details.error === "string" ? details.error : null,
  }
}

/**
 * `DEMO ? demo : real`, following `use-contribution-calendar.ts`. The real
 * branch reads `/analytics/pipeline-logs`, which journals through the
 * `extracted` event (T1.45 ruling 1) — one row per memory per batch, always
 * a terminal outcome. There is no per-phase progress broadcast (doc 05
 * §10), so unlike the demo fixture, real mode never has an "in flight" row:
 * PipelineTab's running section is honestly always empty rather than
 * approximated from a signal that doesn't exist.
 */
export function usePipelineRuns(): {
  runs: DemoPipelineRun[]
  isLoading: boolean
  isError: boolean
} {
  const demoRuns = useDemoPipelineRuns()
  const query = usePipelineLogs(50, !DEMO)

  if (DEMO) {
    return { runs: demoRuns, isLoading: false, isError: false }
  }

  return {
    runs: query.data ? query.data.map(fromPipelineLog) : [],
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
