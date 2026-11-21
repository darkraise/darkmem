import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** One row of `GET /api-keys`. No secret is ever on this shape — the
 *  plaintext exists once, on the create response, and nowhere afterwards. */
export interface ApiKeySummary {
  id: string
  name: string
  key_id: string
  scopes: string[]
  created_at: string
  last_used_at: string | null
  expires_at: string | null
  revoked_at: string | null
}

/** The issue response. `token` is the only copy that will ever exist. */
export interface ApiKeyCreated extends ApiKeySummary {
  token: string
}

export interface ApiKeyCreateParams {
  name: string
  scopes: string[]
  expires_at?: string | null
}

/** `GET /api-keys` — **including revoked keys**, and that is load-bearing
 *  rather than incidental: revocation sets `revoked_at` and keeps the row so
 *  the calls a key already made keep a resolvable label. A list filtered to
 *  live keys would turn every historical entry into a bare uuid. */
export function useApiKeys(options?: { enabled?: boolean }) {
  return useQuery<ApiKeySummary[]>({
    queryKey: ["api-keys"],
    queryFn: ({ signal }) => apiFetch<ApiKeySummary[]>("/api-keys", { signal }),
    enabled: !DEMO && (options?.enabled ?? true),
  })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  return useMutation<ApiKeyCreated, Error, ApiKeyCreateParams>({
    mutationFn: (params) =>
      apiFetch<ApiKeyCreated>("/api-keys", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  })
}

export function useRevokeApiKey() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiFetch<void>(`/api-keys/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  })
}
