import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

export interface UsageBreakdownRow {
  key: string
  cost_micros: number
  calls: number
  prompt_tokens: number
  cached_tokens: number
  completion_tokens: number
  unmeasured_calls: number
  unpriced_calls: number
}

export interface UsageOverview {
  window_start: string | null
  window_end: string
  total_cost_micros: number
  total_calls: number
  prompt_tokens: number
  cached_tokens: number
  completion_tokens: number
  reasoning_tokens: number
  unmeasured_calls: number
  unpriced_calls: number
  unpriced_models: string[]
  merged_classification_present: boolean
  cache_hit_ratio: number | null
  failed_calls: number
  failed_cost_micros: number
  by_purpose: UsageBreakdownRow[]
  by_model: UsageBreakdownRow[]
  by_subject_type: UsageBreakdownRow[]
}

export interface UsageSeriesBucket {
  bucket_start: string
  cost_micros: number
  calls: number
  prompt_tokens: number
  completion_tokens: number
  unmeasured_calls: number
}

export interface UsageSeries {
  bucket: string
  buckets: UsageSeriesBucket[]
}

export interface UsageCallRow {
  id: string
  occurred_at: string
  purpose: string
  model: string
  provider: string | null
  api_kind: string
  subject_type: string
  subject_id: string | null
  project: string | null
  prompt_tokens: number | null
  cached_tokens: number | null
  completion_tokens: number | null
  reasoning_tokens: number | null
  tokens_measured: boolean
  cost_micros: number | null
  ok: boolean
  error_kind: string | null
  duration_ms: number
  merged_classification: boolean
}

export interface UsageSubject {
  subject_type: string
  subject_id: string
  total_cost_micros: number
  total_calls: number
  batched_embedding: boolean
  calls: UsageCallRow[]
}

export interface UsageTopRow {
  subject_type: string
  subject_id: string | null
  project: string | null
  cost_micros: number
  calls: number
  duration_ms: number
  unmeasured_calls: number
}

export interface UsageTop {
  by: string
  items: UsageTopRow[]
}

export interface ModelPriceRow {
  model: string
  input_micros_per_mtok: number
  cached_micros_per_mtok: number
  output_micros_per_mtok: number
  overridden: boolean
}

export interface ModelPrices {
  models: ModelPriceRow[]
}

export type UsageWindow = "24h" | "7d" | "30d" | "all"

/** `GET /usage/overview` — the window total with its breakdowns. Every number
 *  arrives with its own confidence (unmeasured/unpriced counts); a caller that
 *  renders only `total_cost_micros` is presenting a floor as a total. */
export function useUsageOverview(window: UsageWindow = "30d", project?: string) {
  const qs = new URLSearchParams({ window })
  if (project) qs.set("project", project)
  return useQuery<UsageOverview>({
    queryKey: ["usage", "overview", window, project ?? null],
    queryFn: () => apiFetch(`/usage/overview?${qs.toString()}`),
  })
}

export function useUsageSeries(
  window: UsageWindow = "30d",
  bucket: "hour" | "day" | "week" | "month" = "day",
) {
  return useQuery<UsageSeries>({
    queryKey: ["usage", "series", window, bucket],
    queryFn: () => apiFetch(`/usage/series?window=${window}&bucket=${bucket}`),
  })
}

export function useUsageTop(
  window: UsageWindow = "30d",
  by: "cost" | "calls" | "duration" = "cost",
  limit = 20,
) {
  return useQuery<UsageTop>({
    queryKey: ["usage", "top", window, by, limit],
    queryFn: () => apiFetch(`/usage/top?window=${window}&by=${by}&limit=${limit}`),
  })
}

export function useUsageSubject(
  subjectType: string,
  subjectId: string | null | undefined,
) {
  return useQuery<UsageSubject>({
    queryKey: ["usage", "subject", subjectType, subjectId],
    queryFn: () =>
      apiFetch(`/usage/by-subject/${subjectType}/${encodeURIComponent(subjectId!)}`),
    enabled: Boolean(subjectId),
  })
}

export function useModelPrices() {
  return useQuery<ModelPrices>({
    queryKey: ["usage", "prices"],
    queryFn: () => apiFetch("/usage/prices"),
  })
}

export function useSaveModelPrices() {
  const qc = useQueryClient()
  return useMutation<
    ModelPrices,
    Error,
    Record<string, Partial<Omit<ModelPriceRow, "model" | "overridden">>>
  >({
    mutationFn: (prices) =>
      apiFetch("/usage/prices", {
        method: "PUT",
        body: JSON.stringify({ prices }),
      }),
    onSuccess: () => {
      // Prices change what every future row costs, not what the stored rows
      // cost: past rows keep the rates they were written with. Only the price
      // table itself is refetched.
      void qc.invalidateQueries({ queryKey: ["usage", "prices"] })
    },
  })
}
