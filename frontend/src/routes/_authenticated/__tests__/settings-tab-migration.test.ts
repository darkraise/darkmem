import { describe, it, expect } from "vitest"
import { resolveStoredTab } from "../settings-tab"

describe("settings tab migration", () => {
  it("migrates ml -> flags", () => {
    expect(resolveStoredTab("ml")).toBe("flags")
  })
  it("migrates prompts -> assistant", () => {
    expect(resolveStoredTab("prompts")).toBe("assistant")
  })
  it("keeps assistant idempotently", () => {
    expect(resolveStoredTab("assistant")).toBe("assistant")
  })
  it("falls back when unknown", () => {
    expect(resolveStoredTab("bogus")).toBe("flags")
  })
  it("falls back when null", () => {
    expect(resolveStoredTab(null)).toBe("flags")
  })
})
