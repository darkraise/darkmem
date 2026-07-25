import type { ApiKind, DemoFlagsState, DemoRankArm } from "./types"

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

export function sourceLabel(source: "default" | "override"): string {
  return source === "default" ? "coded default" : "override"
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

/** Derived from api_kind directly, not a stored provider flag: these two
 *  vendors expose no embeddings endpoint — selecting either 404s. */
export function embeddingKindWarning(kind: ApiKind): string | null {
  if (kind === "anthropic" || kind === "deepseek") {
    return `${kind} exposes no embeddings endpoint — selecting it here 404s on every request. This hint is derived from api_kind directly, not a stored provider flag.`
  }
  return null
}

/** Display masking for a stored key; the row keeps the unmasked value. */
export function maskKey(key: string): string {
  if (key === "") return ""
  const tail = key.length > 4 ? key.slice(-4) : ""
  return `••••••••••••${tail}`
}
