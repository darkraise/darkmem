import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** One managed-block target, as the inject writer would resolve it. */
export interface DistributionTarget {
  tool: string
  context_file: string
  mcp_config: string
  refresh: string
}

export interface DistributionPolicy {
  token_budget: number
  /** The curb. One flag, server-side, stopping every target at once. */
  curbed: boolean
}

export interface DistributionState {
  targets: DistributionTarget[]
  policy: DistributionPolicy
}

export function useDistribution(options: { enabled?: boolean } = {}) {
  return useQuery<DistributionState>({
    queryKey: ["distribution"],
    queryFn: () => apiFetch<DistributionState>("/distribution"),
    enabled: options.enabled ?? true,
  })
}

export function useSetDistributionPolicy() {
  const qc = useQueryClient()
  return useMutation<DistributionPolicy, Error, DistributionPolicy>({
    mutationFn: (policy) =>
      apiFetch<DistributionPolicy>("/distribution/policy", {
        method: "PUT",
        body: JSON.stringify(policy),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["distribution"] })
    },
  })
}
