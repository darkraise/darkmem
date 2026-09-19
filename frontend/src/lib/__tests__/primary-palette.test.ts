import { describe, expect, it } from "vitest"
import { hslTripleToRgb, readPrimaryParticleColors } from "../primary-palette"

describe("hslTripleToRgb", () => {
  it("converts the theme's space-separated HSL triple", () => {
    expect(hslTripleToRgb("0 100% 50%")).toEqual([255, 0, 0])
    expect(hslTripleToRgb(" 120 100% 25% ")).toEqual([0, 128, 0])
    expect(hslTripleToRgb("221 83% 53%")).toEqual([36, 99, 235])
  })

  it("rejects anything that is not a triple", () => {
    expect(hslTripleToRgb("")).toBeNull()
    expect(hslTripleToRgb("#22c55e")).toBeNull()
  })
})

describe("readPrimaryParticleColors", () => {
  it("tints every particle colour from --primary", () => {
    const root = document.createElement("div")
    root.style.setProperty("--primary", "0 100% 50%")
    document.body.appendChild(root)
    try {
      expect(readPrimaryParticleColors(root)).toEqual({
        nodes: ["rgb(255, 0, 0)", "rgba(255, 0, 0, 0.7)"],
        accents: ["rgb(255, 0, 0)"],
        link: "255,0,0",
        mouseLink: "255,0,0",
      })
    } finally {
      root.remove()
    }
  })
})
