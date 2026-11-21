import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** One managed-block target: the file a client tool reads at session start. */
export interface DistributionTarget {
  tool: string
  context_file: string
  mcp_config: string
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
  rejected: RejectedTarget[]
}

export function useDistribution(options: { enabled?: boolean } = {}) {
  return useQuery<DistributionState>({
    queryKey: ["distribution"],
    queryFn: ({ signal }) => apiFetch<DistributionState>("/distribution", { signal }),
    enabled: options.enabled ?? true,
  })
}
