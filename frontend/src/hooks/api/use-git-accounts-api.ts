import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface GitAccount {
  id: string
  label: string
  provider: string
  host: string
  username: string
  // Last four characters. The token itself never leaves the server.
  token_hint: string
  scopes: string | null
  is_default: boolean
  last_verified_at: string | null
  repo_count: number
  created_at: string
  updated_at: string
}

export interface GitForge {
  provider: string
  label: string
  default_host: string
}

export interface GitAccountsResponse {
  accounts: GitAccount[]
  providers: GitForge[]
}

export interface CreateGitAccountInput {
  label: string
  token: string
  provider?: string
  host?: string | null
  is_default?: boolean
}

export interface UpdateGitAccountInput {
  label?: string
  token?: string
  is_default?: boolean
}

export interface VerifyGitTokenInput {
  token: string
  provider?: string
  host?: string | null
}

export interface VerifyGitTokenResult {
  username: string
  scopes: string | null
  host: string
  provider: string
}

export const GIT_ACCOUNTS_KEY = ["gitAccounts"] as const

export function useGitAccounts() {
  return useQuery<GitAccountsResponse>({
    queryKey: GIT_ACCOUNTS_KEY,
    queryFn: () => apiFetch<GitAccountsResponse>("/git-accounts"),
    // Demo mode runs with no backend; without this gate the query 401s and
    // the auth interceptor redirects the whole demo to /login. The fixture
    // reaches the UI through the demo store, not through this hook.
    enabled: !DEMO,
  })
}

function useInvalidate() {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: GIT_ACCOUNTS_KEY })
    // A repo row renders its account's label, so both lists go stale together.
    qc.invalidateQueries({ queryKey: ["repos"] })
  }
}

export function useCreateGitAccount() {
  const invalidate = useInvalidate()
  return useMutation<GitAccount, Error, CreateGitAccountInput>({
    mutationFn: (data) =>
      apiFetch<GitAccount>("/git-accounts", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidate,
  })
}

export function useUpdateGitAccount() {
  const invalidate = useInvalidate()
  return useMutation<GitAccount, Error, { id: string; data: UpdateGitAccountInput }>({
    mutationFn: ({ id, data }) =>
      apiFetch<GitAccount>(`/git-accounts/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidate,
  })
}

export function useDeleteGitAccount() {
  const invalidate = useInvalidate()
  return useMutation<void, Error, { id: string; reassignTo?: string }>({
    mutationFn: ({ id, reassignTo }) =>
      apiFetch<void>(
        `/git-accounts/${id}${reassignTo ? `?reassign_to=${reassignTo}` : ""}`,
        { method: "DELETE" },
      ),
    onSuccess: invalidate,
  })
}

export function useVerifyGitToken() {
  return useMutation<VerifyGitTokenResult, Error, VerifyGitTokenInput>({
    mutationFn: (data) =>
      apiFetch<VerifyGitTokenResult>("/git-accounts/verify", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  })
}
