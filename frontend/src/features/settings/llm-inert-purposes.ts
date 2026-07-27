/**
 * The two Tier-C purposes T1.05 seeded inert (doc 11 §6): rows exist in
 * `llm_purpose_configs` and resolve through `get_llm_config`, but no
 * consumer dispatches on them yet, and the wire (`LLMConfigResponse`) does
 * not carry them — so unlike the six live purposes there is nothing here
 * to bind live, in either demo or real mode. Rendered anyway, clearly
 * labelled inert and naming their activation task: an omitted purpose
 * reads as "not configured", which is the same misreading the w_* arms
 * wired at zero (`armStatus` in `@/demo/settings`) are built to avoid.
 *
 * model/api_kind mirror `DEFAULT_PURPOSE_CONFIGS` in
 * `backend/app/services/llm_seed.py` — keep in sync.
 */
export interface InertLLMPurpose {
  purpose: "synthesis" | "verification"
  role: string
  model: string
  api_kind: string
  activatesWith: string
}

export const INERT_LLM_PURPOSES: InertLLMPurpose[] = [
  {
    purpose: "synthesis",
    role: "Tier-C article synthesis from the corroborated fact set",
    model: "qwen2.5:3b",
    api_kind: "ollama",
    activatesWith: "T3.02",
  },
  {
    purpose: "verification",
    role: "fact verification-ladder judgments",
    model: "qwen2.5:3b",
    api_kind: "ollama",
    activatesWith: "T2.26",
  },
]
