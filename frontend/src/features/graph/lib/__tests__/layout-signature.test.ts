import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"
import { layoutSignature } from "../graph-utils"

const IDS = ["m3", "m1", "m2"]

describe("layoutSignature", () => {
  it("is stable for the same layout", () => {
    expect(layoutSignature(100, 300, IDS)).toBe(layoutSignature(100, 300, IDS))
  })

  it("ignores the order the server returned the memories in", () => {
    expect(layoutSignature(100, 300, ["m1", "m2", "m3"])).toBe(
      layoutSignature(100, 300, ["m3", "m2", "m1"]),
    )
  })

  it("does not mutate the caller's array while sorting", () => {
    const ids = ["m3", "m1", "m2"]
    layoutSignature(100, 300, ids)
    expect(ids).toEqual(["m3", "m1", "m2"])
  })

  it("changes when the memory set does", () => {
    expect(layoutSignature(100, 300, ["m1", "m2"])).not.toBe(
      layoutSignature(100, 300, ["m1", "m2", "m3"]),
    )
  })

  it.each([
    ["spacing", 200, 300],
    ["tightness", 100, 120],
  ])("changes when %s does", (_name, spacing, tightness) => {
    expect(layoutSignature(spacing, tightness, IDS)).not.toBe(
      layoutSignature(100, 300, IDS),
    )
  })

  // The regression this exists for: the renderer re-ran ForceAtlas2 whenever
  // the entity layer toggled, scattering every memory node twice per toggle --
  // once on the switch and again when the fetch landed. Entities hang off
  // memories that are already placed, so they are not an input here.
  it("takes no input describing the entity overlay", () => {
    const here = path.dirname(fileURLToPath(import.meta.url))
    const src = readFileSync(path.resolve(here, "../graph-utils.ts"), "utf8")
    const fn = src.slice(src.indexOf("export function layoutSignature"))
    const params = fn.slice(fn.indexOf("("), fn.indexOf(")"))
    expect(params).not.toMatch(/entit/i)
    expect(layoutSignature.length).toBe(3)
  })
})
