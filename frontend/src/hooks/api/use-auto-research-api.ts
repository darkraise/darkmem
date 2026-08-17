import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** The budget as the *reader* resolves it — the clamps and the fail-closed
 *  parse live on the read path, so this is what a run will actually do rather
 *  than an echo of what was sent. */
export interface AutoResearchConfig {
  enabled: boolean
  max_findings_per_run: number
  max_content_chars: number
  default_enabled: boolean
}

export interface AutoResearchUpdate {
  enabled?: boolean
  max_findings_per_run?: number
  max_content_chars?: number
}

export function useAutoResearch() {
  return useQuery<AutoResearchConfig>({
    queryKey: ["autoResearch"],
    queryFn: () => apiFetch<AutoResearchConfig>("/config/auto-research"),
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
    queryFn: () => apiFetch<ResearchRunList>("/config/auto-research/runs"),
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
