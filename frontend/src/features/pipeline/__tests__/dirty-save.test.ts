import { describe, it, expect } from "vitest"

import { firstInvalidDirty } from "../dirty-save"

describe("firstInvalidDirty", () => {
  const merged: Record<string, { url: string } | undefined> = {
    a: { url: "" }, // pre-existing invalid, untouched
    b: { url: "ok" },
    c: { url: "" },
  }
  const isInvalid = (r: { url: string }) => !r.url

  it("ignores invalid rows the user did not edit", () => {
    // Only 'b' (valid) is dirty; the untouched invalid 'a' must not block.
    expect(firstInvalidDirty(merged, new Set(["b"]), isInvalid)).toBeNull()
  })

  it("returns a dirty invalid row", () => {
    expect(firstInvalidDirty(merged, new Set(["c"]), isInvalid)).toBe("c")
  })

  it("returns null when nothing is dirty", () => {
    expect(firstInvalidDirty(merged, new Set(), isInvalid)).toBeNull()
  })
})
