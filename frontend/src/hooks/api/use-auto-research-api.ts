import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** The budget as the *reader* resolves it — the clamps and the fail-closed
 *  parse live on the read path, so this is what a run will actually do rather
 *  than an echo of what was sent. */
export interface AutoResearchConfig {
  enabled: boolean
  max_findings_per_run: number
  max_content_chars: number
  default_enabled: boolean
  /** The largest value each budget accepts; the smallest is 1. Optional
   *  only so a payload from before the field still reads. */
  max_findings_per_run_ceiling?: number
  max_content_chars_ceiling?: number
}

export interface AutoResearchUpdate {
  enabled?: boolean
  max_findings_per_run?: number
  max_content_chars?: number
}

export function useAutoResearch() {
  return useQuery<AutoResearchConfig>({
    queryKey: ["autoResearch"],
    queryFn: ({ signal }) => apiFetch<AutoResearchConfig>("/config/auto-research", { signal }),
    enabled: !DEMO,
  })
}

export function useUpdateAutoResearch() {
  const qc = useQueryClient()
  return useMutation<AutoResearchConfig, Error, AutoResearchUpdate>({
    mutationFn: (patch) =>
      apiFetch<AutoResearchConfig>("/config/auto-research", {
        method: "PUT",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["autoResearch"] }),
  })
}

/** One filed run, as the operator surface lists it.
 *
 *  `occurred_at` rides back to the re-run deliberately: `events` is
 *  partitioned by month under a composite `(id, created_at)` key, so the
 *  client returning the bound it was given is what prunes the lookup to one
 *  partition instead of scanning every month. */
export interface ResearchRunSummary {
  event_id: number
  occurred_at: string
  run_id: string | null
  subject: string
  project: string
  /** What the run journalled filing. */
  filed: number
  /** How many of those rows still exist — re-derivation reaches no others. */
  live: number
}

export interface ResearchRunList {
  items: ResearchRunSummary[]
  total: number
}

export interface ResearchRerunResult {
  event_id: number
  subject: string
  project: string
  filed: number
  reprocessed: number
  missing: number
  /** Of the missing, those still in the capture buffer rather than deleted. */
  pending: number
  errors: number
}

export function useResearchRuns() {
  return useQuery<ResearchRunList>({
    queryKey: ["autoResearch", "runs"],
    queryFn: ({ signal }) => apiFetch<ResearchRunList>("/config/auto-research/runs", { signal }),
    enabled: !DEMO,
  })
}

export function useRerunResearchRun() {
  const qc = useQueryClient()
  return useMutation<
    ResearchRerunResult,
    Error,
    { eventId: number; occurredAt: string }
  >({
    mutationFn: ({ eventId, occurredAt }) =>
      apiFetch<ResearchRerunResult>(
        `/config/auto-research/runs/${eventId}/rerun`,
        { method: "POST", body: JSON.stringify({ occurred_at: occurredAt }) },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["autoResearch", "runs"] }),
  })
}
