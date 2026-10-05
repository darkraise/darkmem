import { describe, expect, it } from "vitest"
import { passwordBytes, passwordTooLong } from "./password-rules"

describe("password rules", () => {
  it("measures UTF-8 bytes, not characters", () => {
    expect(passwordBytes("abc")).toBe(3)
    expect(passwordBytes("é")).toBe(2)
  })

  it("allows exactly 72 bytes and refuses 73", () => {
    expect(passwordTooLong("x".repeat(72))).toBe(false)
    expect(passwordTooLong("x".repeat(73))).toBe(true)
    // 37 two-byte characters are 74 bytes though only 37 characters.
    expect(passwordTooLong("é".repeat(37))).toBe(true)
  })
})
