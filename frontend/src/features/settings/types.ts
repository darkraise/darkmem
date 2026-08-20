// Relocated out of src/demo/types.ts by T1.68. `DemoRankArm` and
// `DemoBehavioralFlag` are built from real `/config/feature-flags` data by
// `useFlagsTabBinding`'s real branch (`armFrom`, the behavioralFlags map).
// `DemoGraphFlag` and `DemoCorroborationGate` are structurally part of that
// same real branch's return type (FlagsTabBinding) even though no backend
// row exists yet to populate them with (`graphAugmentationAvailable`/
// `corroborationAvailable` are always false in real mode) — real,
// non-demo-exclusive code needs the import to compile either way.
// `DemoLLMPurpose`/`ApiKind`/`LLMPurposeName`/`DemoLLMSaveTrace` are built
// from real `/config/llm` data by `useLLMTabBinding`'s real branch.
// `DemoCodeBucket` has no backend table in either mode (its own binding
// comment says so) but is likewise part of the same real hook's return
// type. `MaintenanceOpKey` is the real dispatch vocabulary
// `useMaintenanceTabBinding`'s real branch switches on to trigger actual
// `/reembed/*` and job-trigger calls. See the task's report for the full
// per-type evidence trail.

export type FlagSource = "default" | "override"

export interface DemoRankArm {
  /** The w_* key, e.g. "w_conf". */
  key: string
  /** Legacy alias still carried on the row (e.g. confidence_rank_gamma). */
  alias?: string
  desc: string
  value: number
  coded_default: number
  source: FlagSource
  step?: number
  /** Task id that turns this arm on; absent = already live (T1.57 ruling 1,
   *  read from the backend's own `RankArm.activation`, never guessed here). */
  activatesWith?: string
  /** No entry in the gate-ledger's "Arm activation log" yet — flipping this
   *  arm is possible but its win, if any, is unmeasured (T1.57 ruling 3). */
  unmeasured?: boolean
}

export interface DemoGraphFlag {
  key: string
  desc: string
  enabled: boolean
  source: FlagSource
  /** The paired RRF list weight; null = context augmentation, no weight. */
  paired_arm: DemoRankArm | null
  no_weight_note?: string
}

export interface DemoCorroborationGate {
  n_base: number
  n_diverse: number
  source: FlagSource
  gate_note: string
}

/** hybrid_search_enabled / reranker_enabled / relation_rescue — plain
 *  on/off feature_flags rows, distinct from the w_* rank arms above. */
export interface DemoBehavioralFlag {
  key: string
  desc: string
  enabled: boolean
  source: FlagSource
  /** No recorded gate-ledger win — see DemoRankArm.unmeasured. */
  unmeasured?: boolean
}

export type ApiKind =
  | "openai"
  | "ollama"
  | "anthropic"
  | "google"
  | "deepseek"
  | "zai"

export type LLMPurposeName =
  | "embedding"
  | "extraction"
  | "classification"
  | "reasoning"
  | "summarization"
  | "reranker"
  // T2.106: writable alongside the six live purposes — seeded inert (no
  // consumer until T3.02), so it is rendered as a normal editable card,
  // not a Tier-C read-only one. `verification` stays out of this union:
  // it is not writable through `/config/llm` (see the backend schema's
  // docstring), so it is not a valid `savePurpose` target and continues
  // to render through `TIER_C_LLM_PURPOSES` / `TierCPurposeCard` only.
  | "synthesis"

export interface DemoLLMPurpose {
  purpose: LLMPurposeName
  tier: string
  role: string
  /** The `llm_providers` row this purpose resolves through. Editable — the
   *  connection fields below are the resolved, read-only view. */
  provider_name: string
  model: string
  api_kind: ApiKind
  base_url: string
  /** "" = not set (ollama needs none); stored unmasked, displayed masked. */
  api_key: string
  /** params (jsonb) as JSON text. */
  params: string
  /** Only the embedding purpose carries dimensions. */
  dimensions?: number
  /** Absent on embedding — it has no reasoning mode to disable. */
  reasoning?: boolean
  hint?: { tone: "info" | "caution"; text: string }
}

export interface DemoCodeBucket {
  key: "symbol" | "module" | "overview"
  model: string
  note: string
}

export interface DemoLLMSaveTrace {
  purpose: LLMPurposeName
  fields: string[]
}

export type MaintenanceOpKey =
  | "reembed_memories"
  | "reembed_entities"
  | "expired_memory_cleanup"
  | "graph_orphan_cleanup"
  | "tag_orphan_cleanup"
  | "prune_caches"
