import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** One managed-block target, as the inject writer would resolve it. */
export interface DistributionTarget {
  tool: string
  context_file: string
  mcp_config: string
  refresh: string
  /** Whether this target is actually watched. Server-computed, because
   *  `refresh` alone does not answer it: an adapter declaring `watch` on an
   *  install with watch off is refused by `resolve_adapter`, so a screen
   *  reading the raw field would report a cadence the writer would not serve. */
  watched: boolean
}

export interface DistributionPolicy {
  token_budget: number
  /**
   * The curb. One flag, stored server-side, that stops every target at once.
   *
   * It **has** an enforcer since T4.06: `inject_watch.watch_refresh` reads it
   * fresh on every refresh and refuses while it is on, which is what makes
   * "takes effect immediately" true rather than hopeful. It is enforced
   * server-side because the client is the thing being curbed. The
   * session-start path still has no HTTP door, so the curb governs the watch
   * cadence today and will govern that one the moment it has a caller.
   */
  curbed: boolean
  /** Watch mode (T4.06, doc 15 §3.5), off by default. Permits the cadence;
   *  it does not impose it — a target refreshes on watch only if its own
   *  adapter asks for that cadence. */
  watch_enabled: boolean
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
