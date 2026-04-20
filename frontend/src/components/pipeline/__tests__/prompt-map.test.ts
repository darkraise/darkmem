import { describe, it, expect, vi } from "vitest"
import { EXPECTED_PROMPT_KEYS, checkPromptExhaustiveness } from "../prompt-map"

describe("prompt-map", () => {
  it("expected set includes all stage-bound and orphan keys", () => {
    expect(EXPECTED_PROMPT_KEYS.has("extraction_entities")).toBe(true)
    expect(EXPECTED_PROMPT_KEYS.has("chat")).toBe(true)
    expect(EXPECTED_PROMPT_KEYS.has("agent_instructions")).toBe(true)
  })

  it("warns when server has an extra key", () => {
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {})
    checkPromptExhaustiveness([...EXPECTED_PROMPT_KEYS, "ranking"])
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it("warns when server is missing a key", () => {
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {})
    const trimmed = [...EXPECTED_PROMPT_KEYS].filter((k) => k !== "chat")
    checkPromptExhaustiveness(trimmed)
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })
})
