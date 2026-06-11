import { describe, expect, it } from "vitest"

import { SOURCE_COLORS, sourceColor } from "../source-colors"

describe("sourceColor", () => {
  it("returns the mapped color for known sources", () => {
    expect(sourceColor("claude-code", 0)).toBe("#58a6ff")
  })

  it("rotates fallback colors for unknown sources", () => {
    expect(sourceColor("never-seen", 0)).not.toBe(sourceColor("never-seen", 1))
  })

  it("does not resolve prototype-chain keys as colors", () => {
    expect(SOURCE_COLORS["constructor"]).toBeUndefined()
    expect(sourceColor("constructor", 0)).toMatch(/^#[0-9a-f]{6}$/)
    expect(SOURCE_COLORS["__proto__"]).toBeUndefined()
  })
})
