import { describe, expect, it } from "vitest"
import { safeRedirect } from "./safe-redirect"

describe("safeRedirect", () => {
  it("keeps an in-app path with its search", () => {
    expect(safeRedirect("/memories")).toBe("/memories")
    expect(safeRedirect("/settings?tab=llm")).toBe("/settings?tab=llm")
  })

  it("refuses anything that leaves the app", () => {
    expect(safeRedirect("https://evil.example")).toBeUndefined()
    expect(safeRedirect("//evil.example/x")).toBeUndefined()
    expect(safeRedirect("memories")).toBeUndefined()
    expect(safeRedirect(42)).toBeUndefined()
  })

  it("refuses the guest pages, which would bounce straight back", () => {
    expect(safeRedirect("/login")).toBeUndefined()
    expect(safeRedirect("/login?redirect=/x")).toBeUndefined()
    expect(safeRedirect("/setup")).toBeUndefined()
    expect(safeRedirect("/loginhelp")).toBe("/loginhelp")
  })
})
