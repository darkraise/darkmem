import { useQuery } from "@tanstack/react-query"

import { ApiError, apiFetch } from "@/lib/api"

/** `GET /checkpoints/latest`. `resume_line` and `token_estimate` are derived
 *  server-side by the resume path's own functions — never re-assembled here.
 *  A client that rebuilt the line from `summary` + `next_steps` would be a
 *  second implementation of `render_checkpoint`, and the copy affordance
 *  would hand out prose no session ever received. */
export interface CheckpointResponse {
  id: string
  origin_key: string
  project: string
  summary: string
  next_steps: string[]
  created_at: string | null
  resume_line: string
  token_estimate: number
}

/**
 * The newest checkpoint for one run, or `null` when it saved none.
 *
 * The door answers 404 for "this run has no checkpoint" deliberately — it is
 * a different answer from "its note is empty", and the resume path branches
 * on exactly that. So a 404 resolves to `null` here rather than raising: a
 * run with no checkpoint is the ordinary first-session case, not a fault, and
 * surfacing it as an error state would put a red banner on a healthy install.
 * Every other status still throws.
 */
export function useLatestCheckpoint(
  params: { originKey: string | null; project: string },
  options?: { enabled?: boolean },
) {
  const { originKey, project } = params
  return useQuery<CheckpointResponse | null>({
    queryKey: ["checkpoint-latest", originKey, project],
    enabled: (options?.enabled ?? true) && Boolean(originKey),
    queryFn: async () => {
      const qs = new URLSearchParams({
        origin_key: originKey as string,
        project,
      })
      try {
        return await apiFetch<CheckpointResponse>(`/checkpoints/latest?${qs}`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })
}
