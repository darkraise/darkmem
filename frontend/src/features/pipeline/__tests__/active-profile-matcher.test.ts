import { describe, it, expect } from "vitest"
import { resolveActiveProfileName } from "../LLMPurposeCard"

describe("resolveActiveProfileName", () => {
  const profileNames = [
    "zai-flash-classification",
    "zai-flash-extraction",
    "zai-flash-reranker",
  ]

  it("returns the linked profile when it exists in the filtered set", () => {
    expect(
      resolveActiveProfileName("zai-flash-extraction", profileNames),
    ).toBe("zai-flash-extraction")
    expect(
      resolveActiveProfileName("zai-flash-classification", profileNames),
    ).toBe("zai-flash-classification")
  })

  it("returns empty string when the linked name is unknown to the set", () => {
    // Profile was renamed or deleted, or belongs to another purpose.
    expect(resolveActiveProfileName("zai-flash-summarization", profileNames)).toBe(
      "",
    )
  })

  it("returns empty string when no profile is linked", () => {
    expect(resolveActiveProfileName(null, profileNames)).toBe("")
    expect(resolveActiveProfileName(undefined, profileNames)).toBe("")
    expect(resolveActiveProfileName("", profileNames)).toBe("")
  })

  it("returns empty string against an empty profile set", () => {
    expect(resolveActiveProfileName("zai-flash-extraction", [])).toBe("")
  })
})
