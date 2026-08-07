/**
 * The Tier-C purpose that stays read-only on the LLM settings tab (T2.106,
 * following on from T2.104's read-side fix).
 *
 * Doc 11 §6 seeded two Tier-C rows beyond the six live purposes:
 * `synthesis` and `verification`. Both resolve through `get_llm_config` and
 * both have served on `/config/llm` GET since T2.104. The write side is
 * where they diverge, and deliberately so:
 *
 * - `synthesis` has no consumer until T3.02, so widening its write was
 *   cheap and low-consequence. It moved out of this module and into the
 *   normal editable purpose list (`LLMPurposeName`, `LIVE_PURPOSE_META` in
 *   `use-llm-tab-binding.ts`) — it now renders and saves exactly like the
 *   six always-live purposes.
 * - `verification` is live: `app/services/verification_judge.py` resolves
 *   and dispatches on it since T2.26, and its qualification record is
 *   G-D's gate evidence (doc 17 §6) — a precision/recall measurement
 *   pinned to one resolved model identity. Letting an operator repoint
 *   that identity through this form is a real capability with a real
 *   failure mode: the judge's gated door already fails closed the moment
 *   the resolved identity no longer matches the recorded qualification,
 *   so a repoint cannot silently keep serving stale verdicts — but the
 *   write-time half of that story (warn before save, or invalidate the
 *   on-disk record at the moment of a repoint) means touching the
 *   verification ladder's enforcement path, which is out of scope here.
 *   `LLMConfigUpdate` deliberately does not declare this purpose, so a
 *   write to it is dropped before the route ever sees it. This module
 *   stays the single Tier-C entry for it, rendered disabled with the
 *   reason stated inline (`TierCPurposeCard`) — never a field that looks
 *   editable and silently drops its write.
 */
export interface TierCLLMPurpose {
  purpose: "verification"
  role: string
  /** Task id that gives this purpose its first consumer, or null when it
   *  already has one (dispatched, just not yet write-editable here). */
  activatesWith: string | null
}

export const TIER_C_LLM_PURPOSES: TierCLLMPurpose[] = [
  {
    purpose: "verification",
    role: "fact verification-ladder judgments",
    activatesWith: null,
  },
]
