import { describe, it, expect } from "vitest"

import {
  maxTokensKeyFor,
  readMaxTokens,
  upsertMaxTokens,
} from "../LLMPurposeCard"

describe("maxTokensKeyFor", () => {
  it("maps each provider to its output-cap param key", () => {
    expect(maxTokensKeyFor("openai")).toBe("max_completion_tokens")
    expect(maxTokensKeyFor("ollama")).toBe("num_predict")
    expect(maxTokensKeyFor("zai")).toBe("max_tokens")
    expect(maxTokensKeyFor("deepseek")).toBe("max_tokens")
    expect(maxTokensKeyFor("anthropic")).toBe("max_tokens")
    expect(maxTokensKeyFor(undefined)).toBe("max_tokens")
  })
})

describe("readMaxTokens", () => {
  it("prefers the canonical key for the api_kind", () => {
    expect(readMaxTokens({ max_completion_tokens: 4096 }, "openai")).toBe(4096)
    expect(readMaxTokens({ num_predict: 512 }, "ollama")).toBe(512)
    expect(readMaxTokens({ max_tokens: 4096 }, "zai")).toBe(4096)
  })

  it("falls back to an alias so a value set under another provider still shows", () => {
    expect(readMaxTokens({ max_tokens: 2048 }, "openai")).toBe(2048)
  })

  it("returns undefined when no cap is set", () => {
    expect(readMaxTokens({ temperature: 0 }, "zai")).toBeUndefined()
    expect(readMaxTokens(null, "zai")).toBeUndefined()
    expect(readMaxTokens(undefined, "openai")).toBeUndefined()
  })
})

describe("upsertMaxTokens", () => {
  it("adds the cap to empty params using the provider key", () => {
    expect(JSON.parse(upsertMaxTokens("", "zai", 4096))).toEqual({
      max_tokens: 4096,
    })
    expect(JSON.parse(upsertMaxTokens("", "openai", 4096))).toEqual({
      max_completion_tokens: 4096,
    })
    expect(JSON.parse(upsertMaxTokens("", "ollama", 4096))).toEqual({
      num_predict: 4096,
    })
  })

  it("preserves other params when updating the cap", () => {
    const text = JSON.stringify({ temperature: 0, max_tokens: 2048 })
    expect(JSON.parse(upsertMaxTokens(text, "zai", 8192))).toEqual({
      temperature: 0,
      max_tokens: 8192,
    })
  })

  it("clears the cap when value is null and keeps the rest", () => {
    const text = JSON.stringify({ temperature: 0, max_tokens: 2048 })
    expect(JSON.parse(upsertMaxTokens(text, "zai", null))).toEqual({
      temperature: 0,
    })
  })

  it("returns empty string when removing the only key", () => {
    expect(upsertMaxTokens(JSON.stringify({ max_tokens: 2048 }), "zai", null)).toBe(
      "",
    )
  })

  it("treats a non-positive value as a clear", () => {
    const text = JSON.stringify({ max_tokens: 2048 })
    expect(upsertMaxTokens(text, "zai", 0)).toBe("")
  })
})
