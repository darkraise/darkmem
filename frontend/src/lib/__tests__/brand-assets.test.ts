import { describe, it, expect } from "vitest"
import { readFileSync, existsSync } from "node:fs"
import { resolve } from "node:path"
import { buildFaviconSvg, buildLogoSvg, markDataUri } from "../brand-mark"

const publicDir = resolve(__dirname, "../../../public")
const read = (name: string) => readFileSync(resolve(publicDir, name), "utf8").trim()

const REGENERATE = "regenerate with `node scripts/generate-brand-assets.mjs` from frontend/"

describe("committed brand assets", () => {
  it("logo.svg is exactly what the mark module emits", () => {
    expect(read("logo.svg"), REGENERATE).toBe(buildLogoSvg())
  })

  it("favicon.svg is exactly what the mark module emits", () => {
    expect(read("favicon.svg"), REGENERATE).toBe(buildFaviconSvg())
  })

  // The sidebar hides darkraise-ui's own <img> and paints this file as a mask,
  // so a missing file is an invisible brand rather than a broken-image icon.
  it("logo.svg exists, because the mask silently renders nothing without it", () => {
    expect(existsSync(resolve(publicDir, "logo.svg"))).toBe(true)
  })
})

describe("mask compatibility", () => {
  it("logo.svg carries one ink, so the alpha channel is the only tone", () => {
    const svg = read("logo.svg")
    const fills = [...svg.matchAll(/(?:fill|stroke)="([^"]+)"/g)]
      .map((m) => m[1])
      .filter((v) => v !== "none")
    expect(new Set(fills)).toEqual(new Set(["#000"]))
  })

  it("keeps its tonal steps, since a flat mask would lose the taper", () => {
    const opacities = [...read("logo.svg").matchAll(/opacity="([^"]+)"/g)].map((m) => m[1])
    expect(new Set(opacities).size).toBeGreaterThan(1)
  })
})

describe("markDataUri", () => {
  it("embeds the ink it was handed", () => {
    expect(decodeURIComponent(markDataUri("hsl(262 83% 58%)"))).toContain("hsl(262 83% 58%)")
  })

  it("percent-encodes so the URI survives an href", () => {
    const uri = markDataUri("hsl(221 83% 53%)")
    expect(uri.startsWith("data:image/svg+xml,")).toBe(true)
    expect(uri).not.toContain("<")
    expect(uri).not.toContain("#")
  })
})
