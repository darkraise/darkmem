import { useEffect, useState } from "react"
import { DEMO } from "@/lib/demo-flag"
import { useDemoPipelineFailures } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoPipelineFailure } from "@/demo/types"
import { relativeTime } from "@/lib/format"
import {
  useForgetFailure,
  usePipelineFailures,
  useRetryAllFailures,
  useRetryFailure,
  type PipelineFailure,
} from "@/hooks/api"

function fromPipelineFailure(
  f: PipelineFailure,
  retryQueued: boolean,
): DemoPipelineFailure {
  return {
    id: f.id,
    target_kind: f.entity_type === "memory" ? "memory" : "code_repo",
    target_label: f.entity_preview || `${f.entity_type} ${f.entity_id.slice(0, 8)}`,
    pipeline: f.pipeline_name === "code_index" ? "code_index" : "memory_ingest",
    failed_step: f.failed_step,
    reason: f.error_message ?? "(no error message recorded)",
    attempts: f.attempts,
    first_failed: relativeTime(f.first_failed_at),
    last_attempt: relativeTime(f.last_attempt_at),
    retry_queued: retryQueued,
  }
}

export interface PipelineTriageState {
  failures: DemoPipelineFailure[]
  isLoading: boolean
  isError: boolean
  retry: (id: string) => void
  retryAll: () => void
  forget: (id: string) => void
}

/**
 * `DEMO ? demo : real`, following `use-contribution-calendar.ts`. The real
 * branch reads `/pipeline-failures`; retry/forget outcomes normally arrive
 * via the `pipeline.failure.updated` WS event (which already invalidates
 * this query — see `lib/websocket.ts`), so `retryingIds` is a purely local
 * optimistic overlay that disables the button until the row either
 * resolves (disappears from the unresolved list) or the retry request
 * itself is rejected.
 */
export function usePipelineTriage(): PipelineTriageState {
  const demoFailures = useDemoPipelineFailures()
  const retryDemo = useDemoStore((s) => s.retryFailure)
  const retryAllDemo = useDemoStore((s) => s.retryAllFailures)
  const forgetDemo = useDemoStore((s) => s.forgetFailure)

  const query = usePipelineFailures(undefined, !DEMO)
  const retryMutation = useRetryFailure()
  const retryAllMutation = useRetryAllFailures()
  const forgetMutation = useForgetFailure()
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set())

  const liveIds = new Set((query.data?.items ?? []).map((f) => f.id))
  useEffect(() => {
    setRetryingIds((prev) => {
      const next = new Set([...prev].filter((id) => liveIds.has(id)))
      return next.size === prev.size ? prev : next
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data])

  if (DEMO) {
    return {
      failures: demoFailures,
      isLoading: false,
      isError: false,
      retry: retryDemo,
      retryAll: retryAllDemo,
      forget: forgetDemo,
    }
  }

  return {
    failures: (query.data?.items ?? []).map((f) =>
      fromPipelineFailure(f, retryingIds.has(f.id)),
    ),
    isLoading: query.isLoading,
    isError: query.isError,
    retry: (id) => {
      setRetryingIds((prev) => new Set(prev).add(id))
      retryMutation.mutate(id, {
        onError: () => {
          setRetryingIds((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        },
      })
    },
    retryAll: () => {
      setRetryingIds(new Set(liveIds))
      retryAllMutation.mutate(undefined, {
        onError: () => setRetryingIds(new Set()),
      })
    },
    forget: (id) => forgetMutation.mutate(id),
  }
}
