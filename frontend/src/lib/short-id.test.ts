import { describe, expect, it } from "vitest"
import { shortId } from "./short-id"

describe("shortId", () => {
  it("takes the random tail, so same-minute UUIDv7s differ", () => {
    const a = "01a10d4c-f2f7-7498-bda7-c3973130a5d5"
    const b = "01a10d4c-f302-7cf0-9194-c59cac34f042"
    expect(shortId(a)).toBe("3130a5d5")
    expect(shortId(b)).toBe("ac34f042")
    expect(shortId(a)).not.toBe(shortId(b))
  })

  it("leaves non-UUID strings and empties alone", () => {
    expect(shortId("conv-1")).toBe("conv-1")
    expect(shortId(null)).toBe("")
    expect(shortId(undefined)).toBe("")
  })
})
