import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface LlmPurposeConfig {
  // Which `llm_providers` row this purpose resolves through. Served on the
  // read side and accepted on the write side (`POST /config/llm`); null only
  // when the purpose has no row and resolution fell back to a built-in
  // default. base_url/api_kind/api_key below are the resolved, read-only view
  // joined from that row — they are not declared on the update schema, so
  // posting them back is silently dropped.
  provider_name: string | null
  base_url: string
  model: string
  api_key: string | null
  dimensions: number | null
  reasoning: boolean
  api_kind: string
  params: Record<string, unknown>
  // Present only on the classification purpose; null means the LLM-backed
  // classifier (T1.04). Readable and writable since 2026-08-18 — both wire
  // schemas declare it now. Before that the response omitted it and the
  // request schema stripped it, so this control read a value that was never
  // served and wrote one that was silently dropped.
  classifier_kind?: "llm" | "local" | null
}

export interface LlmConfigResponse {
  embedding?: LlmPurposeConfig
  extraction?: LlmPurposeConfig
  classification?: LlmPurposeConfig
  reasoning?: LlmPurposeConfig
  summarization?: LlmPurposeConfig
  reranker?: LlmPurposeConfig
  // Tier-C purposes (T2.104 read, T2.106 write). Both resolve and serve
  // alongside the six live purposes. `synthesis` is seeded inert (first
  // consumer T3.02) and is now writable through this hook, same as the six
  // live purposes. `verification` is live and dispatched (T2.26) and stays
  // read-only here on purpose: `LLMConfigUpdate` deliberately does not
  // declare it, because repointing the qualified judge's model through a
  // settings form is a real capability whose write-time guard would mean
  // touching the verification ladder (see the backend schema's docstring
  // for the full reasoning). A write to `verification` through this hook
  // is a no-op — dropped by the backend before the route sees it.
  synthesis?: LlmPurposeConfig
  verification?: LlmPurposeConfig
}

export function useLlmConfig(enabled: boolean = true) {
  return useQuery<LlmConfigResponse>({
    queryKey: ["llmConfig"],
    queryFn: () => apiFetch<LlmConfigResponse>("/config/llm"),
    enabled,
  })
}

export interface LlmConfigUpdateResponse extends LlmConfigResponse {
  obsolete_after_change: {
    memories: number
    code_chunks: number
    entities: number
  } | null
}

export function useUpdateLlmConfig() {
  const qc = useQueryClient()
  return useMutation<LlmConfigUpdateResponse, Error, Record<string, unknown>>({
    mutationFn: (data) =>
      apiFetch<LlmConfigUpdateResponse>("/config/llm", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
      qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}

/** One rank_fusion_factor arm (doc 07 §3), read straight from the backend's
 *  `RANK_ARMS` — `activation` is the task id that turns it on, or null if
 *  it is already live. T1.57 ruling 1: the single source both the "inactive,
 *  activated by T2.30" label and this type must agree with. */
export interface RankArmInfo {
  name: string
  flag: string
  value: number
  activation: string | null
}

/** One doc 07 §4 graph channel, read straight off the backend's
 *  `GRAPH_CHANNELS` — the flag/weight pairing and the activation task id both
 *  come from there rather than being re-typed here, for the reason
 *  `RankArmInfo` does. `weight_flag` is null for a channel that injects
 *  context instead of a ranked list: there is no weight, and rendering a zero
 *  would invent a knob the fusion never reads. */
export interface GraphChannelInfo {
  name: string
  flag: string
  enabled: boolean
  weight_flag: string | null
  weight: number | null
  activation: string | null
}

/** One label the classifier may emit under the current mode + areas, resolved
 *  by the backend's own `get_merged_llm_types`. */
export interface ClassificationLabel {
  name: string
  description: string
  /** The area that contributed it; null for the `fact` fallback and for every
   *  label in simple mode, where no area is responsible. */
  area: string | null
}

export interface FeatureFlags {
  hybrid_search_enabled: boolean
  reranker_enabled: boolean
  pipeline_concurrency: number
  // classification_areas / classification_mode are classification tuning
  // parameters, not behavioral on/off flags; they live in this row for
  // transport convenience but don't gate a pipeline phase the way the boolean
  // flags above do.
  classification_areas: string[]
  classification_mode: "simple" | "expanded"
  embedding_batch_size: number
  embedding_concurrency: number
  entity_cache_ttl_minutes: number
  relation_rescue: boolean
  confidence_rank_gamma: number
  // Doc 07 §3 rank_fusion_factor arms wired at zero by T1.31.
  w_importance: number
  w_heat: number
  w_recency: number
  w_context_boost: number
  // Doc 07 §4's graph arms. In FEATURE_FLAGS_DEFAULTS since T2.32; absent from
  // the response model until 2026-08-21, which is why the Flags tab reported
  // "no config row exists for these yet" — it was reading a missing field.
  ppr_enabled: boolean
  w_ppr: number
  dual_level_enabled: boolean
  w_dual: number
  community_injection_enabled: boolean
  rank_arms: RankArmInfo[]
  graph_channels: GraphChannelInfo[]
  classification_labels: ClassificationLabel[]
  /** False in simple mode: the merge function returns SIMPLE_TYPES and never
   *  reads the enabled areas, so the area toggles change nothing. */
  classification_areas_apply: boolean
  // Which flags are subject to the gate-ledger's "flip on a measured win"
  // rule, and which of those have actually cleared one (T1.57 ruling 3).
  measurable_flags: string[]
  measured_flags: string[]
}

export function useFeatureFlags(enabled: boolean = true) {
  return useQuery<FeatureFlags>({
    queryKey: ["featureFlags"],
    queryFn: () => apiFetch<FeatureFlags>("/config/feature-flags"),
    staleTime: 30_000,
    enabled,
  })
}

export function useUpdateFeatureFlags() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<FeatureFlags>) =>
      apiFetch<FeatureFlags>("/config/feature-flags", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      // Paint the server's own answer rather than waiting for a refetch to
      // tell us what we already know. Invalidating alone left a window where
      // the control sat at its pre-save value, and if that refetch raced the
      // write it painted the stale value back for good.
      qc.setQueryData(["featureFlags"], data)
      qc.invalidateQueries({ queryKey: ["featureFlags"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}

export interface RepoAllowlist {
  patterns: string[]
}

export function useRepoAllowlist(enabled: boolean = true) {
  return useQuery<RepoAllowlist>({
    queryKey: ["repoAllowlist"],
    queryFn: () => apiFetch<RepoAllowlist>("/config/repo-allowlist"),
    staleTime: 30_000,
    enabled,
  })
}

export function useUpdateRepoAllowlist() {
  const qc = useQueryClient()
  return useMutation<RepoAllowlist, Error, string[]>({
    mutationFn: (patterns) =>
      apiFetch<RepoAllowlist>("/config/repo-allowlist", {
        method: "PUT",
        body: JSON.stringify({ patterns }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repoAllowlist"] }),
  })
}

export interface LadderParam {
  name: string
  /** What the config row holds; null when nothing is committed. */
  committed: number | null
  /** What the ladder actually runs at. The number that matters. */
  effective: number
  floor: number
  /** Whether `ladder_measurements` names this parameter — the only thing that
   *  lets `effective` sit below `floor`. */
  measured: boolean
  state: "default" | "honoured" | "clamped"
  /** Present only when clamped: the operator-facing reason. */
  note: string | null
}

export interface VerificationLadder {
  params: LadderParam[]
  measured: string[]
  row_present: boolean
  measurement_task: string
}

export function useVerificationLadder(enabled: boolean = true) {
  return useQuery<VerificationLadder>({
    queryKey: ["verificationLadder"],
    queryFn: () => apiFetch<VerificationLadder>("/config/verification-ladder"),
    staleTime: 30_000,
    enabled,
  })
}

/** A partial write. An explicit `null` clears a commitment and returns that
 *  parameter to its floor; an omitted key is left alone. The response is the
 *  *resolved* report, so a clamped save reports the clamp rather than echoing
 *  the number back. */
export function useUpdateVerificationLadder() {
  const qc = useQueryClient()
  return useMutation<VerificationLadder, Error, Record<string, number | null>>({
    mutationFn: (patch) =>
      apiFetch<VerificationLadder>("/config/verification-ladder", {
        method: "PUT",
        body: JSON.stringify(patch),
      }),
    onSuccess: (data) => {
      // Paint the response immediately...
      qc.setQueryData(["verificationLadder"], data)
    },
    // ...then reconcile. Two in-flight PUTs return snapshots taken at
    // different moments and HTTP responses may arrive out of order, so
    // setQueryData alone can leave the cache holding the older one. The
    // refetch is authoritative; without it the UI can show a threshold the
    // database no longer has.
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["verificationLadder"] })
    },
  })
}

export interface ClassificationAreaInfo {
  key: string
  display_name: string
  types: string[]
  type_descriptions: Record<string, string>
}

export function useClassificationAreas() {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () =>
      apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
    enabled: !DEMO,
  })
}

// -- System prompts (UI-editable overrides of the in-code defaults) ---------

export interface SystemPromptsResponse {
  defaults: Record<string, string>
  overrides: Record<string, string>
  effective: Record<string, string>
}

export function useSystemPrompts(options?: { enabled?: boolean }) {
  return useQuery<SystemPromptsResponse>({
    queryKey: ["systemPrompts"],
    queryFn: () => apiFetch<SystemPromptsResponse>("/config/system-prompts"),
    enabled: options?.enabled ?? true,
  })
}

export function useUpdateSystemPrompts() {
  const qc = useQueryClient()
  return useMutation<
    SystemPromptsResponse,
    Error,
    { overrides: Record<string, string> }
  >({
    mutationFn: (body) =>
      apiFetch<SystemPromptsResponse>("/config/system-prompts", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["systemPrompts"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}


export interface NotificationSettings {
  telegram: { enabled: boolean; bot_token: string; chat_id: string }
  notify_on: { job_failure: boolean }
}

/** `GET /config/notifications`. The bot token comes back masked as `***`;
 *  writing that mask back means "leave the stored token alone". */
export function useNotifications(options?: { enabled?: boolean }) {
  return useQuery<NotificationSettings>({
    queryKey: ["notifications"],
    queryFn: () => apiFetch<NotificationSettings>("/config/notifications"),
    enabled: options?.enabled ?? true,
  })
}

export function useUpdateNotifications() {
  const qc = useQueryClient()
  return useMutation<NotificationSettings, Error, Partial<NotificationSettings>>({
    mutationFn: (patch) =>
      apiFetch<NotificationSettings>("/config/notifications", {
        method: "PUT",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })
}

/** Sends one real message with the stored settings, so a wrong credential is
 *  found here rather than during the incident it was meant to report. */
export function useTestNotification() {
  return useMutation<{ sent: boolean; error: string | null }, Error, void>({
    mutationFn: () =>
      apiFetch("/config/notifications/test", { method: "POST" }),
  })
}
