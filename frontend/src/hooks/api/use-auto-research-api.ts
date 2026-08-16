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
