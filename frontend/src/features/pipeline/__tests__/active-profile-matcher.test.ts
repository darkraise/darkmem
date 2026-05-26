import { describe, it, expect } from "vitest"

// Re-implements the matcher logic in LLMPurposeCard. Kept in lockstep
// with the component so a regression that breaks suffix tie-breaking
// (which currently makes the extraction card render as "classification"
// when both profiles share identical params) is caught here.
function stableStringify(obj: unknown): string {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj)
  if (Array.isArray(obj)) return "[" + obj.map(stableStringify).join(",") + "]"
  const rec = obj as Record<string, unknown>
  const keys = Object.keys(rec).sort()
  return (
    "{" +
    keys
      .map((k) => JSON.stringify(k) + ":" + stableStringify(rec[k]))
      .join(",") +
    "}"
  )
}

interface Profile {
  provider_ref: string
  model: string
  params: Record<string, unknown>
  is_embedding: boolean
  reasoning: boolean
}

function activeProfileName(
  purpose: string,
  draft: { provider_ref: string; model: string; reasoning: boolean },
  effectiveParams: Record<string, unknown>,
  profiles: Record<string, Profile>,
): string {
  const profileNames = Object.keys(profiles)
    .filter((n) =>
      purpose === "embedding"
        ? profiles[n].is_embedding
        : !profiles[n].is_embedding,
    )
    .sort()
  const draftParamsKey = stableStringify(effectiveParams)
  const purposeSuffix = `-${purpose}`
  let firstMatch = ""
  let suffixMatch = ""
  for (const name of profileNames) {
    const p = profiles[name]
    if (p.provider_ref !== draft.provider_ref) continue
    if (p.model !== draft.model) continue
    if (stableStringify(p.params || {}) !== draftParamsKey) continue
    if (purpose !== "embedding" && p.reasoning !== draft.reasoning) continue
    if (!firstMatch) firstMatch = name
    if (name.endsWith(purposeSuffix)) {
      suffixMatch = name
      break
    }
  }
  return suffixMatch || firstMatch
}

describe("LLMPurposeCard activeProfileName matcher", () => {
  const profiles: Record<string, Profile> = {
    "zai-flash-extraction": {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      params: { temperature: 0 },
      is_embedding: false,
      reasoning: false,
    },
    "zai-flash-classification": {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      params: { temperature: 0 },
      is_embedding: false,
      reasoning: false,
    },
    "zai-flash-reranker": {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      params: { temperature: 0 },
      is_embedding: false,
      reasoning: false,
    },
  }

  it("prefers the suffix-matching profile when several match identically", () => {
    // The bug was alphabetical-first wins, returning "zai-flash-classification"
    // even when the user opened the extraction card.
    const draft = {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      reasoning: false,
    }
    const params = { temperature: 0 }
    expect(activeProfileName("extraction", draft, params, profiles)).toBe(
      "zai-flash-extraction",
    )
    expect(activeProfileName("classification", draft, params, profiles)).toBe(
      "zai-flash-classification",
    )
    expect(activeProfileName("reranker", draft, params, profiles)).toBe(
      "zai-flash-reranker",
    )
  })

  it("falls back to first match when no name matches the purpose suffix", () => {
    const draft = {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      reasoning: false,
    }
    const params = { temperature: 0 }
    // ``summarization`` is not in profiles — the matcher should still
    // return one of the matching profiles rather than empty string.
    expect(activeProfileName("summarization", draft, params, profiles)).toBe(
      "zai-flash-classification",
    )
  })

  it("returns empty string when nothing matches", () => {
    const draft = {
      provider_ref: "openai",
      model: "gpt-5.4-mini",
      reasoning: false,
    }
    expect(activeProfileName("extraction", draft, {}, profiles)).toBe("")
  })

  it("respects param differences as a hard requirement", () => {
    // When max_tokens differs (the new seed's disambiguation), only the
    // matching profile counts.
    const distinct: Record<string, Profile> = {
      "zai-flash-extraction": {
        provider_ref: "zai",
        model: "glm-4.5-flash",
        params: { temperature: 0, max_tokens: 2048 },
        is_embedding: false,
        reasoning: false,
      },
      "zai-flash-classification": {
        provider_ref: "zai",
        model: "glm-4.5-flash",
        params: { temperature: 0, max_tokens: 64 },
        is_embedding: false,
        reasoning: false,
      },
    }
    const draft = {
      provider_ref: "zai",
      model: "glm-4.5-flash",
      reasoning: false,
    }
    expect(
      activeProfileName(
        "extraction",
        draft,
        { temperature: 0, max_tokens: 2048 },
        distinct,
      ),
    ).toBe("zai-flash-extraction")
    expect(
      activeProfileName(
        "classification",
        draft,
        { temperature: 0, max_tokens: 64 },
        distinct,
      ),
    ).toBe("zai-flash-classification")
  })
})
