import { describe, it, expect } from "vitest"
import { llmProfileSchema } from "../schemas"

describe("llmProfileSchema", () => {
  it("rejects Anthropic + reasoning_effort", () => {
    const r = llmProfileSchema.safeParse({
      name: "anthropic", api_kind: "anthropic", model: "claude-opus-4-7", reasoning_effort: "high",
    })
    expect(r.success).toBe(false)
    if (!r.success) {
      expect(r.error.issues[0].message).toContain("Anthropic")
    }
  })

  it("requires thinking=disabled for deepseek-v4-flash", () => {
    const r = llmProfileSchema.safeParse({
      name: "ds", api_kind: "deepseek", model: "deepseek-v4-flash",
    })
    expect(r.success).toBe(false)
  })

  it("accepts a valid OpenAI profile", () => {
    const r = llmProfileSchema.safeParse({
      name: "openai", api_kind: "openai", model: "gpt-5.4-mini", reasoning_effort: "none",
    })
    expect(r.success).toBe(true)
  })
})
