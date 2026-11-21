import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

export interface AuditEntry {
  id: number
  action: string
  details: Record<string, unknown>
  timestamp: string | null
}

export interface AuditLogPage {
  items: AuditEntry[]
  total: number
  limit: number
  offset: number
}

export function useAuditLog(
  params: { limit?: number; offset?: number; action?: string } = {},
) {
  const { limit = 50, offset = 0, action } = params
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (action) qs.set("action", action)
  return useQuery<AuditLogPage>({
    queryKey: ["auditLog", limit, offset, action ?? null],
    queryFn: ({ signal }) => apiFetch(`/auth/audit?${qs.toString()}`, { signal }),
  })
}
