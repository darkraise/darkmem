import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { DEMO_MCP_CALLS, DEMO_MCP_CALL_SUMMARY } from "@/demo/mcp-calls"

const LIVE = !DEMO

export type McpCallStatus = "ok" | "error" | "denied"

/** One `tools/call` as the MCP call log stored it. `arguments` is already
 *  minimised server-side: content arguments arrive as `{chars}`/`{items}`
 *  sizes, and query text only when the operator switched it on. */
export interface McpCallRow {
  id: string
  occurred_at: string
  tool: string
  scope: string | null
  status: McpCallStatus
  duration_ms: number
  api_key_id: string | null
  key_name: string | null
  client: string | null
  project: string | null
  arguments: Record<string, unknown>
  result_count: number | null
  result_ids: string[]
  error: string | null
}

export interface McpCallList {
  items: McpCallRow[]
  total: number
}

export interface McpToolStat {
  tool: string
  scope: string | null
  calls: number
  errors: number
  denied: number
  avg_duration_ms: number
  p95_duration_ms: number
  last_at: string
}

export interface McpCallerStat {
  api_key_id: string | null
  key_name: string | null
  client: string | null
  calls: number
  errors: number
  last_at: string
  top_tool: string
}

export interface McpObjectStat {
  id: string
  hits: number
  last_at: string
  tools: string[]
}

export interface McpCallSummary {
  since: string
  until: string
  total: number
  errors: number
  denied: number
  avg_duration_ms: number
  p95_duration_ms: number
  tools: McpToolStat[]
  callers: McpCallerStat[]
  top_objects: McpObjectStat[]
  series: { bucket: string; calls: number; errors: number }[]
  query_text_logged: boolean
}

export type McpCallWindow = "24h" | "7d" | "30d"

const WINDOW_MS: Record<McpCallWindow, number> = {
  "24h": 24 * 3600_000,
  "7d": 7 * 24 * 3600_000,
  "30d": 30 * 24 * 3600_000,
}

export function mcpWindowSince(
  window: McpCallWindow,
  now = Date.now(),
): string {
  return new Date(now - WINDOW_MS[window]).toISOString()
}

export interface McpCallListParams {
  tool?: string
  status?: McpCallStatus
  api_key_id?: string
  client?: string
  object_id?: string
  since?: string
  limit?: number
}

export function mcpCallsQueryString(params: McpCallListParams): string {
  const qs = new URLSearchParams()
  if (params.tool) qs.set("tool", params.tool)
  if (params.status) qs.set("status", params.status)
  if (params.api_key_id) qs.set("api_key_id", params.api_key_id)
  if (params.client) qs.set("client", params.client)
  if (params.object_id) qs.set("object_id", params.object_id)
  if (params.since) qs.set("since", params.since)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  return qs.toString()
}

const POLL_MS = 10_000

/** `GET /mcp-calls` — newest first, server-filtered. Read `total`, not
 *  `items.length`, for a count. */
export function useMcpCalls(params: McpCallListParams) {
  const query = mcpCallsQueryString(params)
  return useQuery<McpCallList>({
    queryKey: ["mcp-calls", "list", params],
    queryFn: () => apiFetch(`/mcp-calls${query ? `?${query}` : ""}`),
    enabled: LIVE,
    initialData: LIVE ? undefined : DEMO_MCP_CALLS,
    refetchInterval: LIVE ? POLL_MS : undefined,
  })
}

/** `GET /mcp-calls/summary` over the window ending now. */
export function useMcpCallSummary(window: McpCallWindow) {
  return useQuery<McpCallSummary>({
    queryKey: ["mcp-calls", "summary", window],
    queryFn: () =>
      apiFetch(
        `/mcp-calls/summary?since=${encodeURIComponent(mcpWindowSince(window))}`,
      ),
    enabled: LIVE,
    initialData: LIVE ? undefined : DEMO_MCP_CALL_SUMMARY,
    refetchInterval: LIVE ? POLL_MS * 3 : undefined,
  })
}
