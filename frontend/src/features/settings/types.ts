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
  /** The range the server accepts, from `numeric_bounds`; absent in demo. */
  min?: number
  max?: number
  /** Task id that turns this arm on; absent = already live (T1.57 ruling 1,
   *  read from the backend's own `RankArm.activation`, never guessed here). */
  activatesWith?: string
}

export interface DemoGraphFlag {
  key: string
  desc: string
  enabled: boolean
  source: FlagSource
  /** The paired RRF list weight; null = context augmentation, no weight. */
  paired_arm: DemoRankArm | null
  no_weight_note?: string
  /** Task id whose measurement may turn this channel on, read off the
   *  backend's `GRAPH_CHANNELS` registry rather than guessed here. */
  activatesWith?: string
}

/** What happened to one verification-ladder threshold between the config row
 *  and the decision. `default` = nothing committed; `honoured` = the committed
 *  value survived; `clamped` = it did not, and `note` says why. */
export type LadderParamState = "default" | "honoured" | "clamped"

export interface DemoLadderParam {
  name: string
  /** What the config row holds; null when nothing is committed. */
  committed: number | null
  /** What the ladder actually runs at — the number that matters. */
  effective: number
  floor: number
  /** Whether a recorded measurement licenses this parameter below its floor. */
  measured: boolean
  state: LadderParamState
  note?: string
}

/** The corroboration promotion gate as the *reader* resolves it, never an echo
 *  of what was typed. The thresholds are floors: a below-floor value is
 *  clamped rather than refused, so committed and effective must both be
 *  carried — showing only the committed number tells an operator the ladder is
 *  running at a value it is not. */
export interface DemoCorroborationGate {
  params: DemoLadderParam[]
  /** Which parameters a recorded measurement licenses below their floor. */
  measured: string[]
  /** Whether a config row exists at all — distinct from a row holding the
   *  defaults, and only one of the two means an operator has been here. */
  rowPresent: boolean
  /** The task id whose measurement is the only thing that may loosen a floor,
   *  served by the backend so a renumbered task cannot leave this form naming
   *  a gate that no longer exists. Not rendered; the demo fixture still
   *  carries it. */
  measurementTask?: string
  gate_note?: string
}

/** A pipeline/embedding tunable: a plain bounded number in the same
 *  `feature_flags` row as the arms, governing throughput or cache lifetime
 *  rather than gating a phase. Bounds mirror `FeatureFlagsUpdate`'s
 *  `Field(ge=, le=)` so the field refuses locally what the API would 422 on. */
export interface DemoTunable {
  key: string
  desc: string
  value: number
  coded_default: number
  source: FlagSource
  min: number
  max: number
  step?: number
  /** Rendered after the input, e.g. "minutes" — never part of the value. */
  unit?: string
}

/** hybrid_search_enabled / reranker_enabled / relation_rescue — plain
 *  on/off feature_flags rows, distinct from the w_* rank arms above. */
export interface DemoBehavioralFlag {
  key: string
  desc: string
  enabled: boolean
  source: FlagSource
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
  /** Not rendered; the demo fixture still carries it. */
  tier?: string
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
