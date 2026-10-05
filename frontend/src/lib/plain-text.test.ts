import { describe, it, expect } from "vitest"
import { plainText } from "./plain-text"

describe("plainText", () => {
  it("unwraps bold, italic and code", () => {
    // The exact string that reached the detail dialog looking wrong.
    expect(plainText("**G-Z** holds T9.02 only.")).toBe("G-Z holds T9.02 only.")
    expect(plainText("the _belief_ axis")).toBe("the belief axis")
    expect(plainText("reads `progress.md`")).toBe("reads progress.md")
  })

  it("leaves a lone asterisk alone", () => {
    // Far more often a bullet or a footnote than an unclosed emphasis.
    expect(plainText("see * below")).toBe("see * below")
  })

  it("leaves a snake_case identifier alone", () => {
    // The corpus is full of these; treating the underscores as emphasis
    // would silently rename a symbol in the UI.
    expect(plainText("calls resolve_origin_key twice")).toBe(
      "calls resolve_origin_key twice",
    )
  })

  it("handles several spans in one string", () => {
    expect(plainText("**A** and **B** with `c`")).toBe("A and B with c")
  })
})
