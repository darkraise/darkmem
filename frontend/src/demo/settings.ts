import { embeddingKindWarning as sharedEmbeddingKindWarning } from "@/features/setup/api-kinds"
import type {
  ApiKind,
  DemoLadderParam,
  DemoRankArm,
} from "@/features/settings/types"
import type { DemoFlagsState } from "./types"

// ---------------------------------------------------------------------------
// S25 — invariant 23: a w_* arm at 0 is INACTIVE (built-but-unspent), never
// omitted and never implied "off entirely"; raising it above zero is a
// deliberate, measured activation.
// ---------------------------------------------------------------------------

export type ArmStatus = "active" | "inactive"

export function armStatus(value: number): ArmStatus {
  return value > 0 ? "active" : "inactive"
}

/** The seven w_* ranking arms in display order. */
export function allArms(flags: DemoFlagsState): DemoRankArm[] {
  return [
    ...flags.fusion_arms,
    ...flags.graph_flags.flatMap((f) => (f.paired_arm ? [f.paired_arm] : [])),
    flags.context_boost,
  ]
}

export function activeArmCount(flags: DemoFlagsState): number {
  return allArms(flags).filter((a) => armStatus(a.value) === "active").length
}

// ---------------------------------------------------------------------------
// The verification ladder's thresholds are FLOORS, not settings (doc 08 §4.1).
// A config row may tighten one freely; loosening it below its shipped default
// is honoured only when a recorded measurement names that parameter, and an
// unbacked loosening is clamped back rather than refused.
//
// This mirrors the backend's `ladder_config.resolve_ladder` so demo mode
// demonstrates the clamp instead of pretending the edit took. Real mode never
// calls it — there the report comes off the wire, from the one authority that
// also enforces it. Duplicating the *display* of a rule is not duplicating the
// rule; nothing here decides whether a fact promotes.
// ---------------------------------------------------------------------------

export function resolveLadderParam(
  param: DemoLadderParam,
  committed: number | null,
  measured: readonly string[],
): DemoLadderParam {
  if (committed === null) {
    return { ...param, committed: null, effective: param.floor, state: "default", note: undefined }
  }
  const licensed = measured.includes(param.name)
  if (committed < param.floor && !licensed) {
    return {
      ...param,
      committed,
      effective: param.floor,
      state: "clamped",
      note:
        `${committed} is below the minimum of ${param.floor}, so ` +
        `${param.floor} is used. Going lower needs a recorded measurement.`,
    }
  }
  // An origin count of zero would make `k >= n` true for a fact with no
  // sources at all, which no measurement can authorise. `time_gap_days` is a
  // duration and carries no such hazard.
  if (committed < 1 && param.name !== "time_gap_days") {
    return {
      ...param,
      committed,
      effective: 1,
      state: "clamped",
      note:
        `${committed} is below the absolute minimum of 1, so 1 is used. ` +
        `A fact always needs at least one source.`,
    }
  }
  return { ...param, committed, effective: committed, state: "honoured", note: undefined }
}

// ---------------------------------------------------------------------------
// S27 — cron validation, mirroring the JobRegistry contract: five-field
// expressions are minute-precision; six-field put the seconds field first,
// Quartz-style. No other arity is accepted.
// ---------------------------------------------------------------------------

export type CronInfo =
  | { ok: true; fields: 5 | 6; hint: string }
  | { ok: false; error: string }

export function cronInfo(expr: string): CronInfo {
  const fields = expr.trim().split(/\s+/).filter(Boolean)
  if (fields.length === 5) {
    return { ok: true, fields: 5, hint: "five-field, minute precision" }
  }
  if (fields.length === 6) {
    return {
      ok: true,
      fields: 6,
      hint: "six-field, seconds-first (Quartz-style)",
    }
  }
  return {
    ok: false,
    error: `expected 5 or 6 fields, got ${fields.length}`,
  }
}

// ---------------------------------------------------------------------------
// S26 — LLM purpose-card field validation + api_kind-derived hints.
// ---------------------------------------------------------------------------

/** params (jsonb) must parse to a JSON object — not an array or scalar. */
export function validateParamsJson(
  text: string,
): { ok: true } | { ok: false; error: string } {
  const trimmed = text.trim()
  if (trimmed === "") return { ok: true }
  try {
    const parsed: unknown = JSON.parse(trimmed)
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return { ok: false, error: "params must be a JSON object" }
    }
    return { ok: true }
  } catch {
    return { ok: false, error: "invalid JSON" }
  }
}

export const API_KINDS: ApiKind[] = [
  "openai",
  "ollama",
  "anthropic",
  "google",
  "deepseek",
  "zai",
]

/** Derives from `api_kind` via the one canonical mirror of the backend's
 *  `llm_quirks.py` supports_embedding table (`features/setup/api-kinds.ts`)
 *  — never a second hard-coded vendor-name check duplicated in this module. */
export function embeddingKindWarning(kind: ApiKind): string | null {
  return sharedEmbeddingKindWarning(kind)
}

/** Display masking for a stored key; the row keeps the unmasked value. */
export function maskKey(key: string): string {
  if (key === "") return ""
  const tail = key.length > 4 ? key.slice(-4) : ""
  return `••••••••••••${tail}`
}
