import { describe, it, expect } from "vitest"
import {
  API_KIND_OPTIONS,
  apiKindSupportsEmbedding,
  embeddingKindWarning,
} from "../api-kinds"

describe("cannot-embed hint derives from api_kind", () => {
  it("flags the two vendors with no embeddings endpoint", () => {
    expect(apiKindSupportsEmbedding("anthropic")).toBe(false)
    expect(apiKindSupportsEmbedding("deepseek")).toBe(false)
    expect(embeddingKindWarning("anthropic")).toMatch(/no embeddings endpoint/)
    expect(embeddingKindWarning("deepseek")).toMatch(/no embeddings endpoint/)
  })

  it("leaves every embedding-capable kind unwarned", () => {
    for (const kind of ["openai", "ollama", "google", "zai"]) {
      expect(apiKindSupportsEmbedding(kind)).toBe(true)
      expect(embeddingKindWarning(kind)).toBeNull()
    }
  })

  it("covers every api_kind the dropdown offers", () => {
    for (const opt of API_KIND_OPTIONS) {
      expect(typeof apiKindSupportsEmbedding(opt.value)).toBe("boolean")
    }
  })

  it("treats an unknown or unset kind as capable", () => {
    expect(apiKindSupportsEmbedding(undefined)).toBe(true)
  })
})
