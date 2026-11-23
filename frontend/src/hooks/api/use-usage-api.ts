import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { DEMO_USAGE_OVERVIEW, DEMO_USAGE_SERIES } from "@/demo/usage"

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

export interface SubjectTotalRow {
  subject_id: string
  cost_micros: number
  calls: number
  prompt_tokens: number
  cached_tokens: number
  completion_tokens: number
  unmeasured_calls: number
  unpriced_calls: number
}

export interface JobUsageRow {
  job_key: string
  runs: number
  cost_micros: number
  calls: number
  prompt_tokens: number
  cached_tokens: number
  completion_tokens: number
  unmeasured_calls: number
  unpriced_calls: number
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

/** Demo mode runs with no backend. Every usage read is REST-only, so in demo
 *  it 401s -- and `handleUnauthorized` turns a 401 into a hard redirect to
 *  /login, which takes the whole demo down rather than merely leaving the
 *  usage numbers absent. Same guard, and the same reason, as `useProjects`.
 *  Two of these hooks mount outside the Usage page (the Activity Jobs and
 *  Pipeline tabs), so guarding only that route would not be enough. */
const LIVE = !DEMO

export type UsageWindow = "24h" | "7d" | "30d" | "all"

/** `GET /usage/overview` — the window total with its breakdowns. Every number
 *  arrives with its own confidence (unmeasured/unpriced counts); a caller that
 *  renders only `total_cost_micros` is presenting a floor as a total. */
export function useUsageOverview(window: UsageWindow = "30d", project?: string) {
  const qs = new URLSearchParams({ window })
  if (project) qs.set("project", project)
  return useQuery<UsageOverview>({
    queryKey: ["usage", "overview", window, project ?? null],
    queryFn: ({ signal }) => apiFetch(`/usage/overview?${qs.toString()}`, { signal }),
    enabled: LIVE,
    initialData: LIVE ? undefined : DEMO_USAGE_OVERVIEW,
  })
}

export function useUsageSeries(
  window: UsageWindow = "30d",
  bucket: "hour" | "day" | "week" | "month" = "day",
) {
  return useQuery<UsageSeries>({
    queryKey: ["usage", "series", window, bucket],
    queryFn: ({ signal }) => apiFetch(`/usage/series?window=${window}&bucket=${bucket}`, { signal }),
    enabled: LIVE,
    initialData: LIVE ? undefined : DEMO_USAGE_SERIES,
  })
}

export function useUsageTop(
  window: UsageWindow = "30d",
  by: "cost" | "calls" | "duration" = "cost",
  limit = 20,
) {
  return useQuery<UsageTop>({
    queryKey: ["usage", "top", window, by, limit],
    queryFn: ({ signal }) => apiFetch(`/usage/top?window=${window}&by=${by}&limit=${limit}`, { signal }),
    enabled: LIVE,
  })
}

export function useUsageSubject(
  subjectType: string,
  subjectId: string | null | undefined,
) {
  return useQuery<UsageSubject>({
    queryKey: ["usage", "subject", subjectType, subjectId],
    queryFn: ({ signal }) =>
      apiFetch(`/usage/by-subject/${subjectType}/${encodeURIComponent(subjectId!)}`, { signal }),
    enabled: LIVE && Boolean(subjectId),
  })
}

/** `POST /usage/subject-totals` — totals for the rows a page is already
 *  drawing, in one request rather than one per row.
 *
 *  Returns a Map keyed by subject id. A subject with no recorded calls is
 *  **absent**, never a zero: the caller must say "no spend recorded" rather
 *  than assert a measurement it does not have. */
export function useSubjectTotals(subjectType: string, subjectIds: string[]) {
  const ids = [...new Set(subjectIds)].sort()
  return useQuery<Map<string, SubjectTotalRow>>({
    queryKey: ["usage", "subjectTotals", subjectType, ids],
    enabled: LIVE && ids.length > 0,
    queryFn: async ({ signal }) => {
      const body = await apiFetch<{ totals: SubjectTotalRow[] }>(
        "/usage/subject-totals",
        {
          method: "POST",
          signal,
          // The route caps the list; slicing here keeps a long page from
          // getting a 422 instead of the rows it can have.
          body: JSON.stringify({
            subject_type: subjectType,
            subject_ids: ids.slice(0, 200),
          }),
        },
      )
      return new Map(body.totals.map((t) => [t.subject_id, t]))
    },
  })
}

/** `GET /usage/by-job` — spend per job key over the window. */
export function useUsageByJob(window: UsageWindow = "30d") {
  return useQuery<{ jobs: JobUsageRow[] }>({
    queryKey: ["usage", "byJob", window],
    queryFn: ({ signal }) => apiFetch(`/usage/by-job?window=${window}`, { signal }),
    enabled: LIVE,
  })
}

export function useModelPrices() {
  return useQuery<ModelPrices>({
    queryKey: ["usage", "prices"],
    queryFn: ({ signal }) => apiFetch("/usage/prices", { signal }),
    enabled: LIVE,
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
