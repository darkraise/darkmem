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
  /**
   * The curb. One flag, stored server-side, that will stop every target at
   * once. It has no enforcer yet: the inject writer is T3.10's and is held by
   * G-D, so the row's only reader today is the GET that serves this shape
   * back (`backend/app/api/routes/distribution.py` says the same). Setting it
   * is recorded and journalled; it stops nothing, because nothing pushes.
   */
  curbed: boolean
}

/** A configured tool the registry refused, and why. Served rather than
 *  logged-only: an operator whose row vanishes from the screen with the reason
 *  on the server cannot tell a rejection from a typo. */
export interface RejectedTarget {
  tool: string
  reason: string
}

export interface DistributionState {
  targets: DistributionTarget[]
  policy: DistributionPolicy
  rejected: RejectedTarget[]
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
