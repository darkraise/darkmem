import { describe, it, expect } from "vitest"
import { resolveStoredTab } from "../settings-tab"

describe("resolveStoredTab", () => {
  it("keeps known values", () => {
    expect(resolveStoredTab("assistant")).toBe("assistant")
    expect(resolveStoredTab("classification")).toBe("classification")
  })
  it("falls back when unknown", () => {
    expect(resolveStoredTab("bogus")).toBe("flags")
  })
  it("falls back when null", () => {
    expect(resolveStoredTab(null)).toBe("flags")
  })
})
