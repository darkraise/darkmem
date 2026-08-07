/**
 * The two Tier-C purposes T1.05 seeded (doc 11 §6): rows exist in
 * `llm_purpose_configs` and resolve through `get_llm_config`, and since
 * T2.104 `/config/llm` serves both alongside the six live purposes — the
 * backend used to resolve eight and declare six, silently dropping these
 * two the same way `facts_read` dropped fields on the Facts tab.
 *
 * `verification` is **live**: `app/services/verification_judge.py` resolves
 * and dispatches on it since T2.26. `synthesis` has no consumer yet and
 * stays inert until T3.02. This module used to hardcode a `model`/`api_kind`
 * mirror of `DEFAULT_PURPOSE_CONFIGS` (`backend/app/services/llm_seed.py`)
 * for both, with a comment asking a future editor to keep the two in sync by
 * hand — that mirror's own premise ("nothing dispatches on these, in either
 * demo or real mode") went stale for `verification` the moment T2.26 landed
 * and nothing here noticed. T2.104 retires it: connection fields now come
 * from `/config/llm` in real mode (`useLLMTabBinding`), same as the six live
 * purposes, and only demo mode still supplies a fixture, which is what demo
 * mode does everywhere.
 *
 * Read-only regardless of mode: `LLMConfigUpdate` still declares only six
 * purposes, so a write to either of these two is silently dropped on the
 * request side the same way the response side used to drop them — a
 * separate wire-contract change, not this task's to make.
 */
export interface TierCLLMPurpose {
  purpose: "synthesis" | "verification"
  role: string
  /** Task id that gives this purpose its first consumer, or null when it
   *  already has one (dispatched, just not yet write-editable here). */
  activatesWith: string | null
}

export const TIER_C_LLM_PURPOSES: TierCLLMPurpose[] = [
  {
    purpose: "synthesis",
    role: "Tier-C article synthesis from the corroborated fact set",
    activatesWith: "T3.02",
  },
  {
    purpose: "verification",
    role: "fact verification-ladder judgments",
    activatesWith: null,
  },
]
